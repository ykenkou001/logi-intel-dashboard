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
    - micware ブランドテンプレートが core/templates/micware_master.pptx に
      配置されていればそれを使い、なければ素のフォーマットで生成
    - 各スライドの最下部に出典脚注を自動追加
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt

from core.export.citation import Citation
from core.export.response import make_output_path

# micware ブランドマスタが存在すればそれを使う
_MASTER_TEMPLATE = Path("core/templates/micware_master.pptx")


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
    return Presentation()


def _add_title_slide(prs: Any, title: str, subtitle: str) -> None:
    """表紙スライドを追加する。

    placeholder のレイアウトに依存すると右下に偏る等の崩れが起きるため、
    明示的にテキストボックスを中央配置する。
    """
    # 6 = Blank レイアウト相当（無ければ後ろから）
    blank_idx = 6 if len(prs.slide_layouts) > 6 else len(prs.slide_layouts) - 1
    layout = prs.slide_layouts[blank_idx]
    slide = prs.slides.add_slide(layout)

    slide_width = prs.slide_width
    slide_height = prs.slide_height
    margin = Inches(0.7)
    box_width = slide_width - margin * 2

    # タイトル: 中央上寄りに配置
    title_box = slide.shapes.add_textbox(
        margin, Inches(2.2), box_width, Inches(1.5),
    )
    title_tf = title_box.text_frame
    title_tf.word_wrap = True
    title_p = title_tf.paragraphs[0]
    title_p.text = title
    title_p.alignment = 2  # PP_ALIGN.CENTER
    title_p.font.size = Pt(40)
    title_p.font.bold = True

    # サブタイトル: タイトルの下に配置
    subtitle_box = slide.shapes.add_textbox(
        margin, Inches(4.0), box_width, Inches(1.0),
    )
    subtitle_tf = subtitle_box.text_frame
    subtitle_tf.word_wrap = True
    subtitle_p = subtitle_tf.paragraphs[0]
    subtitle_p.text = subtitle
    subtitle_p.alignment = 2  # PP_ALIGN.CENTER
    subtitle_p.font.size = Pt(20)

    # スライドサイズが想定外（HEIGHT が違う）場合の参照用
    _ = slide_height


def _add_content_slide(prs: Any, content: SlideContent) -> None:
    """本文スライドを追加する。"""
    layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = content.title

    # 本文テキストボックス
    left = Inches(0.5)
    top = Inches(1.5)
    width = Inches(9)
    height = Inches(5)
    body = slide.shapes.add_textbox(left, top, width, height)
    tf = body.text_frame
    tf.word_wrap = True
    for i, line in enumerate(content.body_lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(16)

    # 脚注（最下部）
    if content.footnote:
        fn_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(6.8), Inches(9), Inches(0.4),
        )
        fn = fn_box.text_frame
        fn.text = content.footnote
        fn.paragraphs[0].font.size = Pt(9)


def _add_citations_slide(prs: Any, citations: list[Citation]) -> None:
    """出典一覧スライドを追加する。"""
    layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = "出典一覧"

    body = slide.shapes.add_textbox(
        Inches(0.5), Inches(1.5), Inches(9), Inches(5.5),
    )
    tf = body.text_frame
    tf.word_wrap = True
    for i, c in enumerate(citations):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = c.to_footnote()
        p.font.size = Pt(11)


def write_clo_plan_draft(
    company_name: str,
    company_id: str,
    plan_period: str,
    executive_summary: list[str],
    body_slides: list[SlideContent],
    citations: list[Citation],
) -> Path:
    """CLO 中長期計画書ドラフトの PPT を生成する。

    エグゼクティブサマリーが必ず 2 枚目に挿入される（CLAUDE.md §1.5 のミッション宣言）。

    Args:
        company_name: 会社名
        company_id: ファイル名用識別子
        plan_period: 計画期間文字列
        executive_summary: 2 枚目のサマリー本文（行のリスト）
        body_slides: 3 枚目以降の本文スライド
        citations: 末尾出典スライドの内容

    Returns:
        生成ファイルのパス
    """
    path = make_output_path(
        file_type="ppt",
        purpose="clo_plan",
        company_id=company_id,
        extension="pptx",
    )
    prs = _new_presentation()

    # 1 枚目: 表紙
    _add_title_slide(prs, company_name, f"中長期計画書ドラフト  {plan_period}")

    # 2 枚目: エグゼクティブサマリー（必須）
    _add_content_slide(prs, SlideContent(
        title="エグゼクティブサマリー",
        body_lines=executive_summary,
    ))

    # 3 枚目以降: 本文
    for content in body_slides:
        _add_content_slide(prs, content)

    # 末尾: 出典一覧
    _add_citations_slide(prs, citations)

    prs.save(str(path))
    return path
