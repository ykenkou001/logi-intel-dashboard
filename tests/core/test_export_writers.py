"""出口層 writer の統合テスト（実ファイル生成）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.export import docx_form3_writer, excel_writer, markdown_writer, ppt_writer
from core.export.citation import Citation, estat_citation


@pytest.fixture(autouse=True)
def redirect_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """outputs/ を一時ディレクトリにリダイレクト。"""
    monkeypatch.setattr("core.export.response.OUTPUTS_DIR", tmp_path)


# ---- markdown_writer ----


def test_write_macro_overview_markdown() -> None:
    path = markdown_writer.write_macro_overview(
        prefecture="東京都",
        sections=[
            ("運輸業概況", "事業所数 15,234 件"),
            ("燃料価格", "レギュラー 168 円/L"),
        ],
        citations=[Citation(label="経済センサス2021", url="https://example.com")],
        company_id="testco",
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "東京都" in content
    assert "15,234" in content
    assert "経済センサス2021" in content


def test_write_clo_plan_markdown_includes_executive_summary() -> None:
    path = markdown_writer.write_clo_plan_draft(
        company_name="テスト株式会社",
        company_id="testco",
        plan_period="2026〜2030",
        executive_summary="経営層向け要約。年間取扱9万トン以上のため CLO 選任義務あり。",
        sections=[("Ⅱ 積載率", "本文")],
        citations=[Citation(label="A", url="https://a.example.com")],
    )
    content = path.read_text(encoding="utf-8")
    assert "エグゼクティブサマリー" in content
    assert "経営層向け要約" in content


# ---- excel_writer ----


def test_write_data_table_excel() -> None:
    from openpyxl import load_workbook

    path = excel_writer.write_data_table(
        title="運輸業事業所数 都道府県別",
        company_id="testco",
        headers=["都道府県", "事業所数"],
        rows=[["東京都", 15234], ["大阪府", 9821]],
        citations=[
            estat_citation("経済センサス2021", "0004005642"),
        ],
    )
    assert path.exists()
    wb = load_workbook(path)
    assert "Summary" in wb.sheetnames
    assert "Data" in wb.sheetnames
    assert "出典" in wb.sheetnames

    ws_summary = wb["Summary"]
    assert ws_summary.freeze_panes == "A8"
    assert len(ws_summary._charts) >= 1
    assert ws_summary.cell(row=5, column=1).value == 2

    ws = wb["Data"]
    # タイトル行・ヘッダ行・データ2行
    assert ws.cell(row=2, column=1).value == "都道府県"
    assert ws.cell(row=3, column=2).value == 15234
    assert ws.freeze_panes == "A3"
    assert "DataTable" in ws.tables

    # 出典シート
    ws_cit = wb["出典"]
    assert ws_cit.cell(row=3, column=1).value == "経済センサス2021"
    assert ws_cit.freeze_panes == "A3"
    assert "CitationTable" in ws_cit.tables


# ---- ppt_writer ----


def test_write_clo_plan_ppt_creates_pptx() -> None:
    from pptx import Presentation

    path = ppt_writer.write_clo_plan_draft(
        company_name="テスト株式会社",
        company_id="testco",
        plan_period="2026〜2030",
        executive_summary=["年間取扱 12 万トン", "CLO 選任義務あり"],
        body_slides=[
            ppt_writer.SlideContent(
                title="Ⅱ 積載率向上",
                body_lines=["現状 70% → 目標 80%", "施策: 共同配送・ルート最適化"],
                footnote="出典: 自動車輸送統計年報",
            ),
        ],
        citations=[Citation(label="A", url="https://a.example.com")],
    )
    assert path.exists()
    prs = Presentation(str(path))
    # 表紙 + サマリー + 本文 + 出典 = 4 枚
    assert len(prs.slides) == 4
    assert prs.slide_width > prs.slide_height


def test_ppt_executive_summary_is_second_slide() -> None:
    """エグゼクティブサマリーが必ず 2 枚目に配置される。"""
    from pptx import Presentation

    path = ppt_writer.write_clo_plan_draft(
        company_name="X",
        company_id="x",
        plan_period="2026",
        executive_summary=["要約テキスト"],
        body_slides=[],
        citations=[Citation(label="A", url="https://a.example.com")],
    )
    prs = Presentation(str(path))
    slide2 = prs.slides[1]
    slide2_text = "\n".join(shape.text for shape in slide2.shapes if hasattr(shape, "text"))
    assert "エグゼクティブサマリー" in slide2_text


def test_ppt_uses_codex_recommended_design_surface() -> None:
    """PPT が素の空白スライドではなく、デザイン要素を含む。"""
    from pptx import Presentation

    path = ppt_writer.write_clo_plan_draft(
        company_name="X",
        company_id="x",
        plan_period="2026",
        executive_summary=["推奨: 共同配送を先行", "投資額: 1億円"],
        body_slides=[],
        citations=[Citation(label="A", url="https://a.example.com")],
    )
    prs = Presentation(str(path))
    first_slide_text = "\n".join(
        shape.text for shape in prs.slides[0].shapes if hasattr(shape, "text")
    )
    assert "C L O   M I D - T E R M   P L A N   D R A F T" in first_slide_text
    assert "物流効率化法 第46条／第65条 対応" in first_slide_text


# ---- docx_form3_writer ----


def test_write_form3_docx_creates_docx() -> None:
    from docx import Document

    path = docx_form3_writer.write_form3(
        company_name="テスト株式会社",
        company_id="testco",
        main_business="その他の電子部品・デバイス製造業",
        jsic_code="3159",
        clo_name="専務執行役員 田中 太郎",
        plan_period="2026年度〜2030年度",
        sections=[
            docx_form3_writer.PlanSection(
                title="Ⅱ 積載率向上",
                shipper_class="特定第一種荷主",
                measures=[
                    docx_form3_writer.PlanMeasure(
                        measure="共同配送の推進",
                        description="同一地域への配送を集約",
                        timing="2026〜2028年度",
                    ),
                ],
            ),
        ],
        is_chain_franchise=False,
    )
    assert path.exists()
    doc = Document(str(path))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "テスト株式会社" in full_text or any(
        "テスト株式会社" in c.text for table in doc.tables for row in table.rows for c in row.cells
    )
    table_cells = [c.text for table in doc.tables for row in table.rows for c in row.cells]
    assert any("提出前レビュー用ドラフト" in text for text in table_cells)
    assert len(doc.tables) >= 3


def test_write_form3_chain_franchise_uses_section5_title() -> None:
    """連鎖化事業者は様式第3「第5条関係」のタイトル。"""
    from docx import Document

    path = docx_form3_writer.write_form3(
        company_name="チェーン本部",
        company_id="chain",
        main_business="コンビニエンスストア",
        jsic_code="5891",
        clo_name="x",
        plan_period="2026〜2030",
        sections=[],
        is_chain_franchise=True,
    )
    doc = Document(str(path))
    headings = [p.text for p in doc.paragraphs if p.style and p.style.name.startswith("Heading")]
    assert any("第5条関係" in h for h in headings)
