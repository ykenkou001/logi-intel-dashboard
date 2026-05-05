"""様式第3別紙（中長期計画書）Word 出力。

国交省公式テンプレート `core/templates/clo_plan_form3.docx` が配置されている場合は
それに流し込み、なければ基本構造の Word を生成する。

設計方針:
    - 必須3項目（積載率向上 / 荷待ち時間短縮 / 荷役等時間短縮）× 実施措置/計画内容/実施時期
    - 連鎖化事業者は荷役等項目なし（自動判別）
    - python-docx ベース・外部依存不要
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from core.export.response import make_output_path

# 公式テンプレートが配置されていればそれを使う
_OFFICIAL_TEMPLATE = Path("core/templates/clo_plan_form3.docx")

_NAVY = "1F4E79"
_BLUE = "305496"
_LIGHT_BLUE = "D9EAF7"
_LIGHT_YELLOW = "FFF2CC"
_LIGHT_GRAY = "F2F2F2"
_BORDER_GRAY = "BFBFBF"

_BODY_FONT = "Yu Gothic"


@dataclass
class PlanMeasure:
    """計画書の 1 施策。"""

    measure: str  # 実施措置（短い見出し）
    description: str  # 計画内容
    timing: str  # 実施時期（例: "2026〜2028年度"）


@dataclass
class PlanSection:
    """計画書の 1 セクション。"""

    title: str  # セクション見出し（例: "Ⅱ 積載率向上"）
    shipper_class: str = ""  # "特定第一種荷主" 等（必要時のみ）
    measures: list[PlanMeasure] = None  # type: ignore[assignment]
    note: str = ""

    def __post_init__(self) -> None:
        if self.measures is None:
            self.measures = []


def write_form3(
    company_name: str,
    company_id: str,
    main_business: str,
    jsic_code: str,
    clo_name: str,
    plan_period: str,
    sections: list[PlanSection],
    is_chain_franchise: bool = False,
    data_source: str = "estimated",
) -> Path:
    """様式第3別紙（中長期計画書）の Word を生成する。

    Args:
        company_name: 事業者の名称
        company_id: ファイル名用識別子
        main_business: 主たる事業の名称
        jsic_code: 主たる事業の細分類番号（4桁）
        clo_name: CLO 役職・氏名
        plan_period: 計画期間
        sections: 必須3項目のセクションリスト
        is_chain_franchise: 連鎖化事業者か（True なら様式第3「第5条関係」として扱う）
        data_source: "sample" / "estimated" / "actual"。'sample' の場合はトップに警告枠を出力

    Returns:
        生成ファイルのパス
    """
    path = make_output_path(
        file_type="docx",
        purpose="form3",
        company_id=company_id,
        extension="docx",
    )

    use_official_template = _OFFICIAL_TEMPLATE.exists()
    doc = Document(str(_OFFICIAL_TEMPLATE)) if use_official_template else Document()
    _prepare_document(doc)

    # ドラフト注記（公式テンプレ未取得時 or sample データ時に必ず先頭に出す）
    _add_draft_notice(doc, data_source=data_source, use_official_template=use_official_template)

    # タイトル
    title_text = (
        "中長期計画書（様式第3／第5条関係）"
        if is_chain_franchise
        else "中長期計画書（様式第3／第46条関係）"
    )
    title = doc.add_heading(title_text, level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(31, 78, 121)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run(f"{company_name} / {plan_period} / 提出前レビュー用ドラフト")
    subtitle_run.font.size = Pt(10)
    subtitle_run.font.color.rgb = RGBColor(89, 89, 89)

    # Ⅰ 事業者の名称等
    doc.add_heading("Ⅰ 事業者の名称等", level=2)
    table = doc.add_table(rows=5, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    rows_data = [
        ("事業者の名称", company_name),
        ("主たる事業", main_business),
        ("主たる事業の細分類番号", jsic_code),
        ("CLO 役職・氏名", clo_name),
        ("計画期間", plan_period),
    ]
    for row_idx, (label, value) in enumerate(rows_data):
        row = table.rows[row_idx]
        row.cells[0].text = label
        row.cells[1].text = value
    _style_info_table(table)

    # 必須項目セクション
    for section in sections:
        doc.add_heading(section.title, level=2)
        if section.shipper_class:
            doc.add_paragraph(f"【{section.shipper_class}】").runs[0].bold = True

        if section.measures:
            measure_table = doc.add_table(rows=len(section.measures) + 1, cols=3)
            measure_table.style = "Table Grid"
            header = measure_table.rows[0]
            header.cells[0].text = "実施措置"
            header.cells[1].text = "計画内容"
            header.cells[2].text = "実施時期"
            for row_idx, m in enumerate(section.measures, start=1):
                cells = measure_table.rows[row_idx].cells
                cells[0].text = m.measure
                cells[1].text = m.description
                cells[2].text = m.timing
            _style_measure_table(measure_table)
        else:
            doc.add_paragraph("（記載なし）")

        if section.note:
            doc.add_paragraph(section.note)

    doc.save(str(path))
    return path


def _prepare_document(doc: Document) -> None:
    """Set page and base typography defaults for the generated review draft."""
    section = doc.sections[0]
    section.start_type = WD_SECTION_START.NEW_PAGE
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)

    styles = doc.styles
    if "Normal" in styles:
        normal = styles["Normal"]
        normal.font.name = _BODY_FONT
        normal._element.rPr.rFonts.set(qn("w:eastAsia"), _BODY_FONT)
        normal.font.size = Pt(9.5)
        normal.paragraph_format.space_after = Pt(4)
        normal.paragraph_format.line_spacing = 1.08

    for style_name, size, color in (
        ("Heading 1", 16, _NAVY),
        ("Heading 2", 12, _NAVY),
    ):
        if style_name in styles:
            style = styles[style_name]
            style.font.name = _BODY_FONT
            style._element.rPr.rFonts.set(qn("w:eastAsia"), _BODY_FONT)
            style.font.bold = True
            style.font.size = Pt(size)
            style.font.color.rgb = RGBColor.from_string(color)
            style.paragraph_format.space_before = Pt(10)
            style.paragraph_format.space_after = Pt(5)


def _style_info_table(table) -> None:
    widths = (Inches(1.65), Inches(5.7))
    for row in table.rows:
        for col_idx, cell in enumerate(row.cells):
            cell.width = widths[col_idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_margins(cell, top=90, start=110, bottom=90, end=110)
            _set_cell_border(cell)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.size = Pt(9.5)
        _shade_cell(row.cells[0], _LIGHT_BLUE)
        row.cells[0].paragraphs[0].runs[0].bold = True


def _style_measure_table(table) -> None:
    widths = (Inches(1.45), Inches(4.65), Inches(1.25))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            cell.width = widths[col_idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_margins(cell, top=95, start=105, bottom=95, end=105)
            _set_cell_border(cell)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.alignment = (
                    WD_ALIGN_PARAGRAPH.CENTER if col_idx in (0, 2) else WD_ALIGN_PARAGRAPH.LEFT
                )
                for run in paragraph.runs:
                    run.font.size = Pt(8.8 if col_idx == 1 else 9.0)
        if row_idx == 0:
            for cell in row.cells:
                _shade_cell(cell, _BLUE)
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraph.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                        run.font.size = Pt(9)


def _shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def _set_cell_margins(
    cell,
    *,
    top: int,
    start: int,
    bottom: int,
    end: int,
) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin_name, value in (
        ("top", top),
        ("start", start),
        ("bottom", bottom),
        ("end", end),
    ):
        node = tc_mar.find(qn(f"w:{margin_name}"))
        if node is None:
            node = OxmlElement(f"w:{margin_name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _set_cell_border(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), _BORDER_GRAY)


def _add_draft_notice(
    doc: Document,
    *,
    data_source: str,
    use_official_template: bool,
) -> None:
    """ドラフト注記をドキュメントの先頭に挿入する。

    出すべき条件:
    - 公式 Word テンプレ `core/templates/clo_plan_form3.docx` が未配置
    - 入力データが sample（架空企業）

    どちらかに該当する場合、提出可否を誤認させないため "ドラフト" バナーを出す。
    """
    notice_lines: list[str] = []
    if data_source == "sample":
        notice_lines.append(
            "⚠️ 本書類はデモ用架空企業データに基づく PoC 用ドラフトです。"
            "経営判断・国交省提出には使用できません。"
        )
    if not use_official_template:
        notice_lines.append(
            "※ 国交省公式 Word テンプレート（様式第3別紙）が未取得のため、"
            "構造のみ準拠した参考ドラフトを生成しています。"
            "提出時は MLIT ポータルから公式 Word を取得して整形してください。"
        )
    if data_source == "estimated":
        notice_lines.append(
            "※ 入力プロフィールは業界統計推計を含むため、"
            "提出前に自社実測データで上書きしてください。"
        )
    if not notice_lines:
        return

    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.rows[0].cells[0]
    _shade_cell(cell, _LIGHT_YELLOW)
    _set_cell_margins(cell, top=140, start=140, bottom=140, end=140)
    _set_cell_border(cell)

    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run("提出前レビュー用ドラフト\n")
    run.bold = True
    run.font.size = Pt(10.5)
    run.font.color.rgb = RGBColor(156, 87, 0)

    for idx, line in enumerate(notice_lines):
        line_run = paragraph.add_run(line)
        line_run.font.size = Pt(9)
        line_run.bold = True
        if idx < len(notice_lines) - 1:
            paragraph.add_run("\n")

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
