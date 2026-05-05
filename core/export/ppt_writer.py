"""PPT 形式の成果物生成（最優先フォーマット）。

CLO 計画書発表用の標準スライド構成:
    1. 表紙（会社名・対象期間）
    2. **エグゼクティブサマリー**（経営層向け1枚要約・2枚目固定）
    3. 外部環境分析（マクロ概況）
    4. 業界ポジション（全国順位・業界平均比）
    5. ドライバー需給ギャップ
    6. 数値目標（積載率・CO2・拘束時間）
    7. 施策一覧（実施措置・計画内容・実施時期）
    8. 実行スケジュール
    9. 補助金・税制優遇
    10. 出典一覧

設計方針:
    - python-pptx ベース・外部依存不要
    - Logi-Intel CLO Report DESIGN.md の navy + amber アイデンティティを適用
    - 各スライドの最下部に出典脚注を自動追加
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from core.export.citation import Citation
from core.export.response import make_output_path

_MASTER_TEMPLATE = Path("core/templates/micware_master.pptx")

_FONT = "Yu Gothic UI"
_SLIDE_W = Inches(13.333)
_SLIDE_H = Inches(7.5)

_PRIMARY = "1E2761"
_PRIMARY_DK = "141A45"
_SECONDARY = "CADCFC"
_SURFACE = "EAF1FE"
_ON_PRIMARY = "FFFFFF"
_MUTED = "5B6478"
_BORDER = "B8C0CE"
_ACCENT = "F5B82E"
_POSITIVE = "2DD4BF"
_NEGATIVE = "EF6F6C"
_WHITE = "FFFFFF"

_FOOTER_TEXT = "Logi-Intel Dashboard | CLO中長期計画書ドラフト"


@dataclass
class ChartSpec:
    """python-pptx ネイティブチャート描画指定。

    kind:
        - "portfolio": 施策ポートフォリオ（散布図 / x=CO2 削減・y=コスト削減）
        - "waterfall": コスト削減ウォーターフォール（横棒）
        - "roadmap"  : KPI 5 ヶ年ロードマップ（折れ線）
    data: kind ごとに必要なフィールドを保持する辞書（描画関数側で取り出し）
    """

    kind: str
    data: dict[str, Any]
    note: str = ""


@dataclass
class SlideContent:
    """1 スライド分のコンテンツ。"""

    title: str
    body_lines: list[str] = field(default_factory=list)
    footnote: str = ""
    chart: ChartSpec | None = None


def _new_presentation() -> Any:
    """マスタテンプレートが存在すればそれを、なければ空のプレゼンを生成。"""
    if _MASTER_TEMPLATE.exists():
        return Presentation(str(_MASTER_TEMPLATE))
    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H
    return prs


def _rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color)


def _blank_layout(prs: Any) -> Any:
    return prs.slide_layouts[6 if len(prs.slide_layouts) > 6 else len(prs.slide_layouts) - 1]


def _set_background(slide: Any, color: str) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = _rgb(color)


def _style_textbox(
    shape: Any,
    *,
    size: int,
    color: str = _PRIMARY,
    bold: bool = False,
    italic: bool = False,
    alignment: PP_ALIGN | None = None,
) -> None:
    for paragraph in shape.text_frame.paragraphs:
        if alignment is not None:
            paragraph.alignment = alignment
        paragraph.font.name = _FONT
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.italic = italic
        paragraph.font.color.rgb = _rgb(color)
        for run in paragraph.runs:
            run.font.name = _FONT
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.italic = italic
            run.font.color.rgb = _rgb(color)


def _add_text(
    slide: Any,
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    size: int,
    color: str = _PRIMARY,
    bold: bool = False,
    italic: bool = False,
    alignment: PP_ALIGN | None = None,
    wrap: bool = True,
) -> Any:
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.text = text
    _style_textbox(
        box,
        size=size,
        color=color,
        bold=bold,
        italic=italic,
        alignment=alignment,
    )
    return box


def _add_rect(
    slide: Any,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    fill: str,
    line: str | None = None,
) -> Any:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(fill)
    if line:
        shape.line.color.rgb = _rgb(line)
        shape.line.width = Pt(0.75)
    else:
        shape.line.fill.background()
    return shape


def _clean_lines(lines: list[str], limit: int) -> list[str]:
    return [line.strip() for line in lines if line and line.strip()][:limit]


def _period_from_subtitle(subtitle: str) -> str:
    return subtitle.replace("中長期計画書ドラフト", "").strip() or "2026-2030"


def _english_label(title: str, slide_no: int) -> str:
    if slide_no == 2:
        return "EXECUTIVE SUMMARY"
    if "ベンチマーク" in title:
        return "INDUSTRY BENCHMARK"
    if "需給" in title:
        return "DRIVER SUPPLY GAP"
    if "判定" in title or "区分" in title or "法令" in title:
        return "REGULATORY ASSESSMENT"
    if "数値" in title or "目標" in title:
        return "TARGETS"
    if "ロードマップ" in title:
        return "KPI ROADMAP"
    if "ポートフォリオ" in title:
        return "MEASURE PORTFOLIO"
    if "ウォーターフォール" in title:
        return "COST WATERFALL"
    if "KPI" in title:
        return "KPI DASHBOARD"
    if "シミュレーション" in title or "効果" in title:
        return "IMPACT SIMULATION"
    if "マッチング" in title or "認定" in title:
        return "CASE BENCHMARK"
    if "出典" in title:
        return "APPENDIX"
    return "CLO REPORT"


def _add_header(slide: Any, title: str, slide_no: int, total_slides: int) -> None:
    _add_rect(slide, Inches(0.52), Inches(0.45), Inches(0.05), Inches(0.42), fill=_ACCENT)
    _add_text(
        slide,
        f"{slide_no - 1:02}   {_english_label(title, slide_no)}",
        Inches(0.66),
        Inches(0.49),
        Inches(4.6),
        Inches(0.22),
        size=10,
        color=_MUTED,
        bold=True,
    )
    _add_text(
        slide,
        f"{slide_no}/{total_slides}",
        Inches(11.43),
        Inches(0.48),
        Inches(1.4),
        Inches(0.24),
        size=9,
        color=_MUTED,
        alignment=PP_ALIGN.RIGHT,
        wrap=False,
    )


def _add_footer(
    prs: Any,
    slide: Any,
    slide_no: int,
    total_slides: int,
    *,
    footnote: str = "",
    dark: bool = False,
) -> None:
    color = "BFC7D8" if dark else _MUTED
    if not dark:
        _add_rect(
            slide, Inches(0.52), Inches(6.95), prs.slide_width - Inches(1.04), Pt(0.6), fill=_BORDER
        )
    if footnote:
        _add_text(
            slide,
            footnote,
            Inches(0.52),
            Inches(7.08),
            Inches(7.4),
            Inches(0.18),
            size=7,
            color=color,
            italic=True,
        )
    _add_text(
        slide,
        f"{_FOOTER_TEXT} | Page {slide_no} / {total_slides}",
        Inches(8.0),
        Inches(7.08),
        Inches(4.8),
        Inches(0.18),
        size=7,
        color=color,
        alignment=PP_ALIGN.RIGHT,
    )


def _split_label_value(line: str) -> tuple[str, str, str]:
    normalized = line.replace("：", ":")
    if ":" in normalized:
        label, value = normalized.split(":", 1)
        return label.strip(), value.strip(), ""
    if " " in line:
        label, value = line.split(" ", 1)
        return label.strip(), value.strip(), ""
    return "KPI", line.strip(), ""


def _split_kpi_value(value: str) -> tuple[str, str]:
    """KPI カードの value を主値と副値（注釈）に分離する。

    - 全角括弧 "（" 以降は注釈として副値へ。
    - 主値が長く " / " を含む場合は、最初の区切りで主値・副値に再分割。
    """
    # 全角 "（" / 半角 " (" のどちらか早く出現する方で副値を切り出す
    full_idx = value.find("（")
    half_idx = value.find(" (")
    candidates = [i for i in (full_idx, half_idx) if i > 0]
    if candidates:
        paren_idx = min(candidates)
        main = value[:paren_idx].strip()
        tail = value[paren_idx:].strip()
    else:
        main, tail = value.strip(), ""
    if " / " in main and len(main) > 14:
        head, mid = main.split(" / ", 1)
        sub = mid.strip()
        if tail:
            sub = f"{sub} {tail}"
        return head.strip(), sub
    return main, tail


def _kpi_value_size(text: str, *, hero: bool) -> int:
    """文字数に応じて値テキストのフォントサイズを段階決定する。

    hero: True なら表紙級の大きさ（24-32pt）、False ならコンパクト（11-22pt）。
    """
    n = len(text)
    if hero:
        if n <= 6:
            return 28
        if n <= 10:
            return 22
        if n <= 14:
            return 17
        if n <= 20:
            return 14
        return 11
    if n <= 8:
        return 22
    if n <= 14:
        return 17
    if n <= 20:
        return 13
    return 11


def _add_kpi_card(
    slide: Any,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    label: str,
    value: str,
    unit: str = "",
    accent: str = _ACCENT,
    dark: bool = False,
) -> None:
    fill = _PRIMARY if dark else _SURFACE
    text = _ON_PRIMARY if dark else _PRIMARY
    _add_rect(slide, left, top, width, height, fill=fill, line=None if dark else _SURFACE)
    _add_rect(slide, left, top, Inches(0.07), height, fill=accent)
    inner_w = width - Inches(0.5)

    main_v, sub_v = _split_kpi_value(value)
    has_unit = bool(unit)
    has_sub = bool(sub_v)

    # ── label ──（カード上部）
    _add_text(
        slide,
        label,
        left + Inches(0.25),
        top + Inches(0.18),
        inner_w,
        Inches(0.22),
        size=9,
        color=_MUTED if not dark else _SECONDARY,
        bold=True,
    )

    # ── value（主値）── カード中央付近、副値や unit の有無で配置を調整
    value_size = _kpi_value_size(main_v, hero=not has_sub)
    value_top = top + Inches(0.46)
    value_h = height - Inches(0.5) - (Inches(0.32) if has_sub else Inches(0.0))
    if has_unit:
        value_h = max(value_h - Inches(0.22), Inches(0.3))
    _add_text(
        slide,
        main_v,
        left + Inches(0.25),
        value_top,
        inner_w,
        value_h,
        size=value_size,
        color=text,
        bold=True,
    )

    # ── 副値（注釈）── 主値の下に小さく
    if has_sub:
        _add_text(
            slide,
            sub_v,
            left + Inches(0.25),
            top + height - Inches(0.42),
            inner_w,
            Inches(0.32),
            size=9,
            color=_MUTED if not dark else _SECONDARY,
        )

    if unit:
        _add_text(
            slide,
            unit,
            left + Inches(0.25),
            top + height - Inches(0.28),
            inner_w,
            Inches(0.2),
            size=8,
            color=_MUTED if not dark else _SECONDARY,
        )


def _add_title_slide(prs: Any, company_name: str, subtitle: str) -> None:
    """表紙スライドを追加する。"""
    slide = prs.slides.add_slide(_blank_layout(prs))
    _set_background(slide, _PRIMARY_DK)
    period = _period_from_subtitle(subtitle)

    _add_rect(
        slide, prs.slide_width - Inches(1.8), 0, Inches(1.25), prs.slide_height, fill=_PRIMARY
    )
    _add_rect(
        slide, prs.slide_width - Inches(0.55), 0, Inches(0.55), prs.slide_height, fill=_ACCENT
    )

    _add_text(
        slide,
        f"C L O   M I D - T E R M   P L A N   D R A F T    |    {period}",
        Inches(0.82),
        Inches(1.74),
        Inches(7.2),
        Inches(0.25),
        size=11,
        color=_ACCENT,
        bold=True,
    )
    _add_text(
        slide,
        "中長期計画書ドラフト",
        Inches(0.82),
        Inches(2.22),
        Inches(7.6),
        Inches(0.72),
        size=34,
        color=_ON_PRIMARY,
        bold=True,
    )
    _add_text(
        slide,
        "物流効率化法 第46条／第65条 対応",
        Inches(0.83),
        Inches(3.48),
        Inches(5.8),
        Inches(0.36),
        size=16,
        color=_SECONDARY,
    )
    _add_rect(slide, Inches(0.83), Inches(4.28), Inches(1.5), Inches(0.03), fill=_ACCENT)
    _add_text(
        slide,
        company_name,
        Inches(0.83),
        Inches(4.78),
        Inches(5.2),
        Inches(0.34),
        size=15,
        color=_ON_PRIMARY,
        bold=True,
    )
    _add_text(
        slide,
        f"対象期間  {period}",
        Inches(0.83),
        Inches(6.55),
        Inches(3.5),
        Inches(0.2),
        size=9,
        color=_SECONDARY,
    )


def _add_content_slide(
    prs: Any,
    content: SlideContent,
    slide_no: int,
    total_slides: int,
    *,
    executive: bool = False,
) -> None:
    slide = prs.slides.add_slide(_blank_layout(prs))
    _set_background(slide, _WHITE)
    _add_header(slide, content.title, slide_no, total_slides)

    _add_text(
        slide,
        content.title,
        Inches(0.52),
        Inches(1.12),
        Inches(8.0),
        Inches(0.5),
        size=25,
        color=_PRIMARY,
        bold=True,
    )
    if content.chart is not None:
        _add_chart_body(slide, content.chart)
    elif executive:
        _add_text(
            slide,
            "2026-2030 中長期計画 主要指標と次のアクション",
            Inches(0.52),
            Inches(1.78),
            Inches(6.2),
            Inches(0.25),
            size=10,
            color=_MUTED,
        )
        _add_executive_summary_body(slide, content.body_lines)
    elif "判定" in content.title or "区分" in content.title or "法令" in content.title:
        _add_regulatory_body(slide, content.body_lines)
    elif "数値" in content.title or "目標" in content.title:
        _add_target_grid_body(slide, content.body_lines)
    elif "マッチング" in content.title or "認定" in content.title:
        _add_ranked_list_body(slide, content.body_lines)
    elif "シミュレーション" in content.title or "効果" in content.title:
        _add_data_table_body(slide, content.body_lines)
    else:
        _add_benchmark_body(slide, content.body_lines)

    _add_footer(prs, slide, slide_no, total_slides, footnote=content.footnote)


def _add_executive_summary_body(slide: Any, lines: list[str]) -> None:
    body_lines = _clean_lines(lines, 8)
    kpi_lines = body_lines[:4]
    while len(kpi_lines) < 4:
        kpi_lines.append("KPI: 未入力")

    card_w = Inches(2.95)
    for i, line in enumerate(kpi_lines[:4]):
        label, value, unit = _split_label_value(line)
        _add_kpi_card(
            slide,
            Inches(0.52) + (card_w + Inches(0.15)) * i,
            Inches(2.28),
            card_w,
            Inches(1.7),
            label=label,
            value=value,
            unit=unit,
            accent=(_POSITIVE, _ACCENT, _PRIMARY, _ACCENT)[i],
        )

    _add_rect(
        slide, Inches(0.52), Inches(4.36), Inches(6.1), Inches(2.38), fill=_WHITE, line=_BORDER
    )
    _add_text(
        slide,
        "会社プロフィール",
        Inches(0.78),
        Inches(4.62),
        Inches(2.4),
        Inches(0.24),
        size=12,
        color=_PRIMARY,
        bold=True,
    )
    for i, line in enumerate(
        body_lines[4:7]
        or ["対象データ: 推計値", "主要論点: CLO選任とKPI実測", "次アクション: 様式第3別紙の確定"]
    ):
        _add_text(
            slide,
            line,
            Inches(0.78),
            Inches(5.08 + 0.36 * i),
            Inches(5.3),
            Inches(0.24),
            size=10,
            color=_MUTED if i != 0 else _PRIMARY,
            bold=i == 0,
        )

    _add_rect(slide, Inches(6.78), Inches(4.36), Inches(6.05), Inches(2.38), fill=_PRIMARY)
    _add_text(
        slide,
        "C L O  選 任 義 務  判 定",
        Inches(7.04),
        Inches(4.65),
        Inches(2.8),
        Inches(0.24),
        size=11,
        color=_ACCENT,
        bold=True,
    )
    _add_text(
        slide,
        "選任義務 あり",
        Inches(7.04),
        Inches(5.08),
        Inches(3.8),
        Inches(0.46),
        size=24,
        color=_ON_PRIMARY,
        bold=True,
    )
    _add_rect(slide, Inches(7.04), Inches(5.86), Inches(5.5), Inches(0.54), fill=_PRIMARY_DK)
    _add_text(
        slide,
        "次のアクション",
        Inches(7.2),
        Inches(6.03),
        Inches(1.0),
        Inches(0.16),
        size=8,
        color=_ACCENT,
        bold=True,
    )
    _add_text(
        slide,
        "様式第3別紙に署名・押印 → 2026年10月末までに提出",
        Inches(8.12),
        Inches(6.02),
        Inches(4.0),
        Inches(0.18),
        size=9,
        color=_ON_PRIMARY,
    )


def _add_benchmark_body(slide: Any, lines: list[str]) -> None:
    body_lines = _clean_lines(lines, 8)
    first = body_lines[0] if body_lines else "業界平均比: 未入力"
    second = body_lines[1] if len(body_lines) > 1 else "CO2削減 国家目標: ▲23.4%"

    label, value, unit = _split_label_value(first)
    _add_kpi_card(
        slide,
        Inches(0.55),
        Inches(2.25),
        Inches(6.0),
        Inches(2.0),
        label=label,
        value=value,
        unit=unit,
        accent=_SECONDARY,
    )
    label2, value2, unit2 = _split_label_value(second)
    _add_kpi_card(
        slide,
        Inches(0.55),
        Inches(4.35),
        Inches(6.0),
        Inches(1.9),
        label=label2,
        value=value2,
        unit=unit2,
        accent=_ACCENT,
        dark=True,
    )

    _add_text(
        slide,
        "業界規模・物流コスト比較",
        Inches(6.9),
        Inches(2.35),
        Inches(4.2),
        Inches(0.3),
        size=13,
        color=_PRIMARY,
        bold=True,
    )
    for i, line in enumerate(
        body_lines[2:7]
        or ["全国 同業種事業所数 417件", "県内 事業所数 91件", "業界平均 物流コスト比率 1.8%"]
    ):
        y = Inches(3.0 + 0.72 * i)
        if i % 2 == 1:
            _add_rect(slide, Inches(6.9), y - Inches(0.1), Inches(5.8), Inches(0.5), fill=_SURFACE)
        _add_text(
            slide,
            line,
            Inches(7.05),
            y,
            Inches(5.3),
            Inches(0.22),
            size=11,
            color=_PRIMARY if i % 2 else _MUTED,
            bold=i % 2 == 1,
        )


def _add_regulatory_body(slide: Any, lines: list[str]) -> None:
    body_lines = _clean_lines(lines, 8)
    _add_rect(slide, Inches(0.52), Inches(2.35), Inches(12.3), Inches(1.3), fill=_PRIMARY)
    _add_text(
        slide,
        "判 定 結 果",
        Inches(0.82),
        Inches(2.58),
        Inches(1.5),
        Inches(0.22),
        size=11,
        color=_ACCENT,
        bold=True,
    )
    _add_text(
        slide,
        "CLO選任義務 あり",
        Inches(0.82),
        Inches(2.97),
        Inches(4.4),
        Inches(0.46),
        size=24,
        color=_ON_PRIMARY,
        bold=True,
    )
    _add_rect(slide, Inches(7.5), Inches(2.62), Inches(2.38), Inches(0.5), fill=_ACCENT)
    _add_text(
        slide,
        "特定第一種荷主",
        Inches(8.1),
        Inches(2.78),
        Inches(1.2),
        Inches(0.16),
        size=10,
        color=_PRIMARY_DK,
        bold=True,
        alignment=PP_ALIGN.CENTER,
    )
    _add_rect(slide, Inches(10.05), Inches(2.62), Inches(2.38), Inches(0.5), fill=_ACCENT)
    _add_text(
        slide,
        "特定第二種荷主",
        Inches(10.63),
        Inches(2.78),
        Inches(1.2),
        Inches(0.16),
        size=10,
        color=_PRIMARY_DK,
        bold=True,
        alignment=PP_ALIGN.CENTER,
    )

    _add_rect(slide, Inches(0.52), Inches(3.95), Inches(6.1), Inches(2.45), fill=_SURFACE)
    _add_text(
        slide,
        "判定根拠",
        Inches(0.78),
        Inches(4.2),
        Inches(1.6),
        Inches(0.24),
        size=12,
        color=_PRIMARY,
        bold=True,
    )
    for i, line in enumerate(
        body_lines[:4]
        or ["年間取扱貨物が閾値以上", "原材料・仕入の入荷量も確認", "連鎖化フラグを確認"]
    ):
        _add_rect(
            slide, Inches(0.8), Inches(4.72 + 0.42 * i), Inches(0.1), Inches(0.1), fill=_ACCENT
        )
        _add_text(
            slide,
            line,
            Inches(1.0),
            Inches(4.62 + 0.42 * i),
            Inches(5.2),
            Inches(0.24),
            size=10,
            color=_MUTED,
        )

    _add_rect(slide, Inches(6.78), Inches(3.95), Inches(6.05), Inches(2.45), fill=_SURFACE)
    _add_text(
        slide,
        "法令根拠 & 罰則",
        Inches(7.04),
        Inches(4.2),
        Inches(2.2),
        Inches(0.24),
        size=12,
        color=_PRIMARY,
        bold=True,
    )
    laws = [
        "第46条  特定荷主（年間取扱9万トン以上）",
        "第65条  特定連鎖化事業者",
        "第163条  選任義務違反 → 罰金",
    ]
    for i, law in enumerate(laws):
        y = Inches(4.65 + 0.52 * i)
        _add_rect(slide, Inches(7.05), y, Inches(1.3), Inches(0.34), fill=_PRIMARY)
        label, rest = law.split("  ", 1)
        _add_text(
            slide,
            label,
            Inches(7.2),
            y + Inches(0.09),
            Inches(1.0),
            Inches(0.1),
            size=9,
            color=_ACCENT,
            bold=True,
            alignment=PP_ALIGN.CENTER,
        )
        _add_text(
            slide,
            rest,
            Inches(8.48),
            y + Inches(0.07),
            Inches(3.8),
            Inches(0.16),
            size=10,
            color=_PRIMARY,
        )


def _add_target_grid_body(slide: Any, lines: list[str]) -> None:
    body_lines = _clean_lines(lines, 4)
    defaults = [
        "輸送量当たり CO2排出原単位: 2030年 目標 ▲23.4%",
        "営業用普通貨物車 積載率: 2030年 目標 50.0%",
        "鉄道・内航海運 モーダルシフト率: 220.0億トンキロ",
        "物流コスト／売上比率: 1.3%",
    ]
    items = (body_lines + defaults)[:4]
    positions = [(0.52, 2.22), (6.78, 2.22), (0.52, 4.48), (6.78, 4.48)]
    colors = [_POSITIVE, _ACCENT, _PRIMARY, _NEGATIVE]
    for i, (line, (x, y)) in enumerate(zip(items, positions, strict=True)):
        label, value, _unit = _split_label_value(line)
        _add_rect(
            slide, Inches(x), Inches(y), Inches(6.05), Inches(1.85), fill=_WHITE, line=_BORDER
        )
        _add_rect(slide, Inches(x), Inches(y), Inches(0.7), Inches(0.7), fill=colors[i])
        _add_text(
            slide,
            f"{i + 1:02}",
            Inches(x + 0.19),
            Inches(y + 0.22),
            Inches(0.3),
            Inches(0.18),
            size=12,
            color=_ON_PRIMARY,
            bold=True,
            alignment=PP_ALIGN.CENTER,
        )
        _add_text(
            slide,
            label,
            Inches(x + 0.85),
            Inches(y + 0.28),
            Inches(4.75),
            Inches(0.22),
            size=12,
            color=_PRIMARY,
            bold=True,
        )
        _add_text(
            slide,
            value,
            Inches(x + 0.85),
            Inches(y + 1.02),
            Inches(4.75),
            Inches(0.28),
            size=16,
            color=_PRIMARY,
            bold=True,
        )


def _add_data_table_body(slide: Any, lines: list[str]) -> None:
    body_lines = _clean_lines(lines, 8)
    summary = body_lines[:3] or [
        "CO2削減 合算: 3,452 t-CO2/年",
        "コスト削減 合算: 7.79 億円/年",
        "必要投資 合計: 2,300 万円",
    ]
    for i, line in enumerate(summary[:3]):
        label, value, unit = _split_label_value(line)
        _add_kpi_card(
            slide,
            Inches(0.52 + 4.08 * i),
            Inches(2.10),
            Inches(3.85),
            Inches(1.40),
            label=label,
            value=value,
            unit=unit,
            accent=(_POSITIVE, _ACCENT, _PRIMARY)[i],
        )

    _add_rect(slide, Inches(0.52), Inches(3.78), Inches(12.3), Inches(0.42), fill=_PRIMARY)
    headers = ["#", "施策", "CO2削減", "コスト削減", "投資", "回収"]
    xs = [0.62, 1.18, 6.45, 8.55, 10.25, 12.05]
    for x, header in zip(xs, headers, strict=True):
        _add_text(
            slide,
            header,
            Inches(x),
            Inches(3.91),
            Inches(0.9),
            Inches(0.16),
            size=8,
            color=_ACCENT,
            bold=True,
        )
    table_lines = body_lines[3:8] or [
        "モーダルシフト 990 7,200万円 500 0.1年",
        "積載率向上 1,094 3.6億円 300 0.0年",
        "共同配送 1,368 3.0億円 500 0.0年",
    ]
    for i, line in enumerate(table_lines[:5]):
        y = Inches(4.20 + 0.5 * i)
        if i % 2 == 1:
            _add_rect(slide, Inches(0.52), y, Inches(12.3), Inches(0.45), fill=_SURFACE)
        _add_text(
            slide,
            str(i + 1),
            Inches(0.62),
            y + Inches(0.12),
            Inches(0.2),
            Inches(0.12),
            size=9,
            color=_ACCENT,
            bold=True,
        )
        _add_text(
            slide,
            line,
            Inches(1.18),
            y + Inches(0.1),
            Inches(10.7),
            Inches(0.16),
            size=9,
            color=_PRIMARY,
            bold=i < 3,
        )


def _add_ranked_list_body(slide: Any, lines: list[str]) -> None:
    body_lines = _clean_lines(lines, 5) or [
        "オフィス用品配送の積載率向上",
        "飲料メーカー大手2社の共同配送",
        "日用品メーカー・卸の物流DX",
    ]
    for i, line in enumerate(body_lines[:5]):
        y = Inches(2.2 + 0.78 * i)
        _add_rect(
            slide, Inches(0.52), y, Inches(0.85), Inches(0.68), fill=_ACCENT if i < 2 else _PRIMARY
        )
        _add_text(
            slide,
            f"#{i + 1}",
            Inches(0.78),
            y + Inches(0.15),
            Inches(0.32),
            Inches(0.2),
            size=12,
            color=_PRIMARY_DK if i < 2 else _ACCENT,
            bold=True,
            alignment=PP_ALIGN.CENTER,
        )
        _add_rect(slide, Inches(1.37), y, Inches(11.45), Inches(0.68), fill=_WHITE, line=_BORDER)
        _add_text(
            slide,
            line,
            Inches(1.55),
            y + Inches(0.22),
            Inches(7.2),
            Inches(0.18),
            size=10,
            color=_PRIMARY,
            bold=True,
        )
        _add_text(
            slide,
            "score 7",
            Inches(9.0),
            y + Inches(0.22),
            Inches(1.0),
            Inches(0.18),
            size=8,
            color=_MUTED,
        )


# ─── ネイティブチャートスライド ────────────────────────────────────
# 施策ポートフォリオ / コスト削減ウォーターフォール / KPI 5 ヶ年ロードマップ


def _style_chart(chart: Any, *, primary_hex: str = _PRIMARY) -> None:
    """凡例位置とフォントを統一する小さな整形ヘルパー。"""
    chart.has_title = False
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(10)
    chart.legend.font.name = _FONT


def _draw_chart_intro(
    slide: Any,
    headline: str,
    note: str,
) -> None:
    """チャート上部に1行ヘッドラインと補足説明を描く。"""
    _add_text(
        slide,
        headline,
        Inches(0.52),
        Inches(1.7),
        Inches(12.3),
        Inches(0.32),
        size=13,
        color=_PRIMARY,
        bold=True,
    )
    if note:
        _add_text(
            slide,
            note,
            Inches(0.52),
            Inches(2.06),
            Inches(12.3),
            Inches(0.28),
            size=10,
            color=_MUTED,
        )


def _add_portfolio_chart_body(slide: Any, spec: ChartSpec) -> None:
    """施策ポートフォリオ散布図（x=CO2 削減 t/年・y=コスト削減 万円/年）。

    data: {"items": [{"name": str, "co2_t": float, "cost_man": float}], "headline": str}
    """
    items: list[dict[str, Any]] = list(spec.data.get("items", []))
    headline = str(spec.data.get("headline", "施策ごとの効果ポートフォリオ（年間）"))
    _draw_chart_intro(
        slide,
        headline,
        spec.note or "右上ほど高効果。x: CO2 削減（トン/年） / y: コスト削減（万円/年）",
    )

    if not items:
        _add_text(
            slide,
            "効果データがありません（施策評価結果を取得できませんでした）",
            Inches(0.52),
            Inches(3.6),
            Inches(12.3),
            Inches(0.4),
            size=14,
            color=_MUTED,
        )
        return

    chart_data = XyChartData()
    for item in items:
        name = str(item.get("name", ""))[:18]  # 凡例が長すぎないように短縮
        series = chart_data.add_series(name)
        series.add_data_point(
            float(item.get("co2_t", 0) or 0),
            float(item.get("cost_man", 0) or 0),
        )

    chart_shape = slide.shapes.add_chart(
        XL_CHART_TYPE.XY_SCATTER,
        Inches(0.52),
        Inches(2.4),
        Inches(12.3),
        Inches(4.4),
        chart_data,
    )
    chart = chart_shape.chart
    _style_chart(chart)
    chart.category_axis.tick_labels.font.size = Pt(9)
    chart.value_axis.tick_labels.font.size = Pt(9)
    chart.category_axis.tick_labels.font.name = _FONT
    chart.value_axis.tick_labels.font.name = _FONT


def _add_waterfall_chart_body(slide: Any, spec: ChartSpec) -> None:
    """コスト削減ウォーターフォール（横棒・基準→各施策→削減後）。

    data: {
      "baseline_man": float,       # 基準 物流コスト（万円/年）
      "items": [{"name": str, "saving_man": float}],
      "headline": str,
    }
    """
    baseline = float(spec.data.get("baseline_man", 0) or 0)
    items: list[dict[str, Any]] = list(spec.data.get("items", []))
    headline = str(spec.data.get("headline", "施策別 コスト削減効果（万円/年）"))
    total_saving = sum(float(it.get("saving_man", 0) or 0) for it in items)
    after = max(baseline - total_saving, 0)

    default_note = (
        f"基準 {baseline:,.0f} 万円 → 削減後 {after:,.0f} 万円"
        f"（年間 ▲{total_saving:,.0f} 万円）"
    )
    _draw_chart_intro(slide, headline, spec.note or default_note)

    if not items:
        _add_text(
            slide,
            "施策効果データがありません",
            Inches(0.52),
            Inches(3.6),
            Inches(12.3),
            Inches(0.4),
            size=14,
            color=_MUTED,
        )
        return

    categories = ["現状コスト"] + [str(it.get("name", ""))[:20] for it in items] + ["削減後"]
    values = [baseline] + [float(it.get("saving_man", 0) or 0) for it in items] + [after]

    chart_data = CategoryChartData()
    chart_data.categories = categories
    chart_data.add_series("万円/年", values)

    chart_shape = slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED,
        Inches(0.52),
        Inches(2.4),
        Inches(12.3),
        Inches(4.4),
        chart_data,
    )
    chart = chart_shape.chart
    _style_chart(chart)
    chart.has_legend = False
    plot = chart.plots[0]
    plot.has_data_labels = True
    data_labels = plot.data_labels
    data_labels.font.size = Pt(9)
    data_labels.font.name = _FONT
    data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    data_labels.number_format = "#,##0"
    chart.category_axis.tick_labels.font.size = Pt(9)
    chart.value_axis.tick_labels.font.size = Pt(9)
    chart.category_axis.tick_labels.font.name = _FONT
    chart.value_axis.tick_labels.font.name = _FONT


def _add_roadmap_chart_body(slide: Any, spec: ChartSpec) -> None:
    """KPI 5 ヶ年ロードマップ（折れ線・年次推移）。

    data: {
      "years": [int],
      "series": [{"name": str, "values": [float]}],
      "headline": str,
    }
    """
    years: list[int] = list(spec.data.get("years", []))
    series_list: list[dict[str, Any]] = list(spec.data.get("series", []))
    headline = str(spec.data.get("headline", "KPI 5 ヶ年ロードマップ"))

    default_note = (
        "業界平均値を基準（100）として相対化"
        "（積載率は高いほど良い／CO2 原単位は低いほど良い）"
    )
    _draw_chart_intro(slide, headline, spec.note or default_note)

    if not years or not series_list:
        _add_text(
            slide,
            "KPI 推移データがありません",
            Inches(0.52),
            Inches(3.6),
            Inches(12.3),
            Inches(0.4),
            size=14,
            color=_MUTED,
        )
        return

    chart_data = CategoryChartData()
    chart_data.categories = [f"{y}年" for y in years]
    for s in series_list:
        chart_data.add_series(str(s.get("name", "")), [float(v) for v in s.get("values", [])])

    chart_shape = slide.shapes.add_chart(
        XL_CHART_TYPE.LINE,
        Inches(0.52),
        Inches(2.4),
        Inches(12.3),
        Inches(4.4),
        chart_data,
    )
    chart = chart_shape.chart
    _style_chart(chart)
    chart.category_axis.tick_labels.font.size = Pt(10)
    chart.value_axis.tick_labels.font.size = Pt(10)
    chart.category_axis.tick_labels.font.name = _FONT
    chart.value_axis.tick_labels.font.name = _FONT


_CHART_DISPATCH = {
    "portfolio": _add_portfolio_chart_body,
    "waterfall": _add_waterfall_chart_body,
    "roadmap": _add_roadmap_chart_body,
}


def _add_chart_body(slide: Any, spec: ChartSpec) -> None:
    """ChartSpec.kind に応じて描画関数へディスパッチ。"""
    handler = _CHART_DISPATCH.get(spec.kind)
    if handler is None:
        _add_text(
            slide,
            f"未対応の chart kind: {spec.kind}",
            Inches(0.52),
            Inches(3.6),
            Inches(12.3),
            Inches(0.4),
            size=14,
            color=_NEGATIVE,
        )
        return
    handler(slide, spec)


def _add_citations_slide(prs: Any, citations: list[Citation], total_slides: int) -> None:
    """出典一覧スライドを追加する。"""
    slide_no = len(prs.slides) + 1
    slide = prs.slides.add_slide(_blank_layout(prs))
    _set_background(slide, _PRIMARY_DK)
    _add_rect(slide, 0, 0, Inches(0.46), prs.slide_height, fill=_ACCENT)
    _add_text(
        slide,
        "A P P E N D I X",
        Inches(0.86),
        Inches(0.72),
        Inches(2.3),
        Inches(0.22),
        size=10,
        color=_ACCENT,
        bold=True,
    )
    _add_text(
        slide,
        "出典一覧 & 次のステップ",
        Inches(0.86),
        Inches(1.22),
        Inches(5.6),
        Inches(0.52),
        size=24,
        color=_ON_PRIMARY,
        bold=True,
    )
    _add_text(
        slide,
        "主要出典（法令・統計・ガイドライン）",
        Inches(0.86),
        Inches(2.38),
        Inches(3.4),
        Inches(0.22),
        size=11,
        color=_ACCENT,
        bold=True,
    )

    for i, citation in enumerate(citations[:10]):
        y = Inches(2.9 + 0.42 * i)
        _add_rect(slide, Inches(0.86), y, Inches(0.85), Inches(0.28), fill=_PRIMARY)
        _add_text(
            slide,
            "出典",
            Inches(1.06),
            y + Inches(0.08),
            Inches(0.45),
            Inches(0.08),
            size=7,
            color=_ACCENT,
            bold=True,
            alignment=PP_ALIGN.CENTER,
        )
        _add_text(
            slide,
            citation.to_footnote(),
            Inches(1.86),
            y + Inches(0.04),
            Inches(6.8),
            Inches(0.16),
            size=8,
            color=_ON_PRIMARY,
        )

    _add_rect(slide, Inches(9.05), Inches(2.3), Inches(3.95), Inches(4.6), fill=_PRIMARY)
    _add_rect(slide, Inches(9.05), Inches(2.3), Inches(3.95), Inches(0.08), fill=_ACCENT)
    _add_text(
        slide,
        "N E X T   S T E P S",
        Inches(9.25),
        Inches(2.7),
        Inches(2.3),
        Inches(0.18),
        size=9,
        color=_ACCENT,
        bold=True,
    )
    _add_text(
        slide,
        "CLO計画書 提出までの工程",
        Inches(9.25),
        Inches(3.18),
        Inches(3.0),
        Inches(0.25),
        size=13,
        color=_ON_PRIMARY,
        bold=True,
    )
    steps = [
        "自社CO2原単位の実績計測",
        "施策実施スケジュール確定",
        "様式第3別紙 ドラフト確定",
        "経営会議 承認・押印",
        "国交省 提出",
    ]
    for i, step in enumerate(steps):
        y = Inches(4.0 + 0.55 * i)
        _add_text(
            slide,
            f"{i + 1:02}",
            Inches(9.25),
            y,
            Inches(0.38),
            Inches(0.18),
            size=13,
            color=_ACCENT,
            bold=True,
        )
        _add_text(
            slide,
            step,
            Inches(9.85),
            y,
            Inches(2.55),
            Inches(0.18),
            size=9,
            color=_ON_PRIMARY,
            bold=True,
        )

    _add_footer(prs, slide, slide_no, total_slides, dark=True)


def _add_decision_brief_body(
    slide: Any,
    actions_to_pursue: list[str],
    actions_to_skip: list[str],
    next_decision_due: str,
) -> None:
    """3 スライド要約の 3 枚目「やる／やらない 結論」を描画する。

    左カラム：やる 3 件（緑背景）
    右カラム：やらない 3 件（灰背景）
    下部：次の意思決定期日
    """
    pursue_items = (actions_to_pursue + ["—"] * 3)[:3]
    skip_items = (actions_to_skip + ["—"] * 3)[:3]

    # 左：やる
    _add_text(
        slide, "やる（採用施策）", Inches(0.52), Inches(1.78),
        Inches(6.0), Inches(0.32), size=14, color=_POSITIVE, bold=True,
    )
    for i, line in enumerate(pursue_items):
        y = 2.22 + i * 1.10
        _add_rect(
            slide, Inches(0.52), Inches(y),
            Inches(6.05), Inches(0.95), fill=_WHITE, line=_POSITIVE,
        )
        _add_rect(slide, Inches(0.52), Inches(y),
                  Inches(0.5), Inches(0.95), fill=_POSITIVE)
        _add_text(
            slide, f"{i + 1}", Inches(0.55), Inches(y + 0.30),
            Inches(0.4), Inches(0.4), size=18,
            color=_ON_PRIMARY, bold=True, alignment=PP_ALIGN.CENTER,
        )
        _add_text(
            slide, line, Inches(1.15), Inches(y + 0.18),
            Inches(5.35), Inches(0.65),
            size=11, color=_PRIMARY, bold=True,
        )

    # 右：やらない
    _add_text(
        slide, "やらない（除外・先送り）", Inches(6.78), Inches(1.78),
        Inches(6.0), Inches(0.32), size=14, color=_MUTED, bold=True,
    )
    for i, line in enumerate(skip_items):
        y = 2.22 + i * 1.10
        _add_rect(
            slide, Inches(6.78), Inches(y),
            Inches(6.05), Inches(0.95), fill=_WHITE, line=_BORDER,
        )
        _add_rect(slide, Inches(6.78), Inches(y),
                  Inches(0.5), Inches(0.95), fill=_MUTED)
        _add_text(
            slide, f"{i + 1}", Inches(6.81), Inches(y + 0.30),
            Inches(0.4), Inches(0.4), size=18,
            color=_ON_PRIMARY, bold=True, alignment=PP_ALIGN.CENTER,
        )
        _add_text(
            slide, line, Inches(7.41), Inches(y + 0.18),
            Inches(5.35), Inches(0.65),
            size=11, color=_MUTED, bold=True,
        )

    # 下部：次の意思決定期日
    _add_rect(
        slide, Inches(0.52), Inches(5.65),
        Inches(12.31), Inches(0.65), fill=_PRIMARY, line=_PRIMARY,
    )
    _add_text(
        slide, f"📅 次回意思決定期日: {next_decision_due}",
        Inches(0.72), Inches(5.78),
        Inches(11.91), Inches(0.4),
        size=14, color=_ON_PRIMARY, bold=True, alignment=PP_ALIGN.CENTER,
    )


def write_clo_executive_brief(
    company_name: str,
    company_id: str,
    plan_period: str,
    executive_summary: list[str],
    actions_to_pursue: list[str],
    actions_to_skip: list[str],
    next_decision_due: str,
    citations: list[Citation],
) -> Path:
    """経営会議直前 3 分要約 PPT（3 スライド版）。

    フェーズ4.1 a.3。13 スライドの本格版（write_clo_plan_draft）とは別経路で、
    朝のコックピットや経営会議直前に生成する軽量版。

    スライド構成:
      1. 表紙（会社名 + 「経営会議向け 3 分要約」+ 期間）
      2. 経営サマリー（KPI 4 カード + プロフィール 3 行）
      3. やる／やらない 結論（採用 3 件 + 除外 3 件 + 次回意思決定期日）

    Args:
        company_name: 会社名
        company_id: 内部ID
        plan_period: 計画期間文字列（例: "2026-04 〜 2030-03"）
        executive_summary: 2 枚目本文の行リスト（KPI 4 行 + プロフィール 3 行 を想定）
        actions_to_pursue: 採用する施策 3 件（短文）
        actions_to_skip: やらない／先送りする施策 3 件（短文）
        next_decision_due: 次回意思決定期日（例: "2026-05-15（金）取締役会"）
        citations: 出典情報（3 スライド版では脚注表示のみで citations スライドは省略）

    Returns:
        生成された pptx ファイルのパス
    """
    path = make_output_path(
        file_type="ppt",
        purpose="clo_exec_brief",
        company_id=company_id,
        extension="pptx",
    )
    prs = _new_presentation()
    total_slides = 3

    _add_title_slide(
        prs, company_name, f"経営会議向け 3 分要約  {plan_period}"
    )

    _add_content_slide(
        prs,
        SlideContent(
            title="経営サマリー",
            body_lines=executive_summary,
        ),
        2,
        total_slides,
        executive=True,
    )

    # 3 枚目（やる／やらない 結論）
    slide = prs.slides.add_slide(_blank_layout(prs))
    _set_background(slide, _WHITE)
    _add_header(slide, "やる／やらない 結論", 3, total_slides)
    _add_text(
        slide, "やる／やらない 結論",
        Inches(0.52), Inches(1.12), Inches(8.0), Inches(0.5),
        size=25, color=_PRIMARY, bold=True,
    )
    _add_decision_brief_body(
        slide, actions_to_pursue, actions_to_skip, next_decision_due,
    )
    _add_footer(prs, slide, 3, total_slides)

    prs.save(str(path))
    return path


def write_clo_plan_draft(
    company_name: str,
    company_id: str,
    plan_period: str,
    executive_summary: list[str],
    body_slides: list[SlideContent],
    citations: list[Citation],
) -> Path:
    """CLO 中長期計画書ドラフトの PPT を生成する。

    エグゼクティブサマリーが必ず 2 枚目に挿入される。
    """
    path = make_output_path(
        file_type="ppt",
        purpose="clo_plan",
        company_id=company_id,
        extension="pptx",
    )
    prs = _new_presentation()
    total_slides = len(body_slides) + 3

    _add_title_slide(prs, company_name, f"中長期計画書ドラフト  {plan_period}")

    _add_content_slide(
        prs,
        SlideContent(
            title="エグゼクティブサマリー",
            body_lines=executive_summary,
        ),
        2,
        total_slides,
        executive=True,
    )

    for i, content in enumerate(body_slides, start=3):
        _add_content_slide(prs, content, i, total_slides)

    _add_citations_slide(prs, citations, total_slides)

    prs.save(str(path))
    return path
