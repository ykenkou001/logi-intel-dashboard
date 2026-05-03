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

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
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
class SlideContent:
    """1 スライド分のコンテンツ。"""

    title: str
    body_lines: list[str]
    footnote: str = ""


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
) -> Any:
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
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
    if "KPI" in title or "ポートフォリオ" in title:
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
        Inches(12.45),
        Inches(0.48),
        Inches(0.45),
        Inches(0.18),
        size=9,
        color=_MUTED,
        alignment=PP_ALIGN.RIGHT,
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
    _add_text(
        slide,
        label,
        left + Inches(0.25),
        top + Inches(0.26),
        width - Inches(0.45),
        Inches(0.25),
        size=9,
        color=_MUTED if not dark else _SECONDARY,
        bold=True,
    )
    value_size = 30 if len(value) <= 10 else 16
    _add_text(
        slide,
        value,
        left + Inches(0.25),
        top + Inches(0.72),
        width - Inches(0.48),
        Inches(0.55),
        size=value_size,
        color=text,
        bold=True,
    )
    if unit:
        _add_text(
            slide,
            unit,
            left + Inches(0.25),
            top + height - Inches(0.35),
            width - Inches(0.48),
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
    if executive:
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
            Inches(2.16),
            Inches(3.85),
            Inches(1.0),
            label=label,
            value=value,
            unit=unit,
            accent=(_POSITIVE, _ACCENT, _PRIMARY)[i],
        )

    _add_rect(slide, Inches(0.52), Inches(3.55), Inches(12.3), Inches(0.45), fill=_PRIMARY)
    headers = ["#", "施策", "CO2削減", "コスト削減", "投資", "回収"]
    xs = [0.62, 1.18, 6.45, 8.55, 10.25, 12.05]
    for x, header in zip(xs, headers, strict=True):
        _add_text(
            slide,
            header,
            Inches(x),
            Inches(3.7),
            Inches(0.9),
            Inches(0.12),
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
        y = Inches(4.0 + 0.5 * i)
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
