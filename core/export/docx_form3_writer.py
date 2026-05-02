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
from docx.shared import Pt

from core.export.response import make_output_path

# 公式テンプレートが配置されていればそれを使う
_OFFICIAL_TEMPLATE = Path("core/templates/clo_plan_form3.docx")


@dataclass
class PlanMeasure:
    """計画書の 1 施策。"""

    measure: str          # 実施措置（短い見出し）
    description: str      # 計画内容
    timing: str           # 実施時期（例: "2026〜2028年度"）


@dataclass
class PlanSection:
    """計画書の 1 セクション。"""

    title: str                      # セクション見出し（例: "Ⅱ 積載率向上"）
    shipper_class: str = ""         # "特定第一種荷主" 等（必要時のみ）
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

    Returns:
        生成ファイルのパス
    """
    path = make_output_path(
        file_type="docx",
        purpose="form3",
        company_id=company_id,
        extension="docx",
    )

    doc = Document(str(_OFFICIAL_TEMPLATE)) if _OFFICIAL_TEMPLATE.exists() else Document()

    # タイトル
    title_text = (
        "中長期計画書（様式第3／第5条関係）"
        if is_chain_franchise
        else "中長期計画書（様式第3／第46条関係）"
    )
    title = doc.add_heading(title_text, level=1)
    for run in title.runs:
        run.font.size = Pt(16)

    # Ⅰ 事業者の名称等
    doc.add_heading("Ⅰ 事業者の名称等", level=2)
    table = doc.add_table(rows=5, cols=2)
    table.style = "Table Grid"
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
        else:
            doc.add_paragraph("（記載なし）")

        if section.note:
            doc.add_paragraph(section.note)

    doc.save(str(path))
    return path
