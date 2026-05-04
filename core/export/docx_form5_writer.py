"""様式第5（定期報告書）Word 出力。

毎年 7 月末提出の様式第5 ドラフトを生成する。
公式 Word テンプレート `core/templates/clo_report_form5.docx` が配置されている場合は
それに流し込み、なければ基本構造の Word を生成する。

設計方針:
    - Ⅰ 特定荷主の名称等
    - Ⅱ 判断基準の遵守状況（特定第一種・第二種で行を分割）
    - Ⅲ 判断基準を遵守できなかった場合の追加措置
    - Ⅳ 荷待ち時間等の計測データ
    - Ⅴ 中長期計画の進捗状況
    - 連鎖化事業者は荷役等項目なし（自動判別）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Pt

from core.export.response import make_output_path
from core.export.submission_checklist import SubmissionChecklist
from core.legal.improvement_check import ComplianceItem, ComplianceReport
from core.static.sample_company import HandlingTimeRow, WaitTimeRow

_OFFICIAL_TEMPLATE = Path("core/templates/clo_report_form5.docx")


@dataclass(frozen=True)
class ProgressRow:
    """中長期計画 vs 実績 ギャップの 1 行。"""

    measure_name: str
    plan_target: str
    actual_result: str
    status_mark: str        # "☑ 達成" / "△ 継続対応" / "☒ 未達"


@dataclass
class Form5Sections:
    """様式第5 各セクションの入力データ。"""

    company_name: str
    company_id: str
    main_business: str
    jsic_code: str
    eligibility_categories: list[str]
    """例: ["first_class_shipper", "second_class_shipper"]。連鎖化なら ["chain_franchise"]"""
    clo_name: str
    report_period: str

    compliance: ComplianceReport
    """改善基準告示準拠チェック結果（Ⅱ・Ⅲ セクションの基礎）"""

    wait_time_rows: list[WaitTimeRow] = field(default_factory=list)
    handling_time_rows: list[HandlingTimeRow] = field(default_factory=list)
    progress_rows: list[ProgressRow] = field(default_factory=list)

    submission_checklist: SubmissionChecklist | None = None
    data_source: str = "estimated"
    """"sample" / "estimated" / "actual"。'sample' の場合は冒頭にドラフト警告を出力。"""


_CATEGORY_LABELS: dict[str, str] = {
    "first_class_shipper": "特定第一種荷主",
    "second_class_shipper": "特定第二種荷主",
    "chain_franchise": "特定連鎖化事業者",
}


def write_form5(sections: Form5Sections) -> Path:
    """様式第5（定期報告書）の Word を生成する。

    Returns:
        生成ファイルのパス
    """
    path = make_output_path(
        file_type="docx",
        purpose="form5",
        company_id=sections.company_id,
        extension="docx",
    )

    use_official_template = _OFFICIAL_TEMPLATE.exists()
    doc = Document(str(_OFFICIAL_TEMPLATE)) if use_official_template else Document()

    _add_form5_draft_notice(
        doc,
        data_source=sections.data_source,
        use_official_template=use_official_template,
    )

    is_chain = "chain_franchise" in sections.eligibility_categories
    title_text = (
        "定期報告書（様式第5／第65条関係）"
        if is_chain
        else "定期報告書（様式第5／第46条関係）"
    )
    title = doc.add_heading(title_text, level=1)
    for run in title.runs:
        run.font.size = Pt(16)

    _write_section_basic_info(doc, sections)
    _write_section_compliance(doc, sections, is_chain=is_chain)
    _write_section_additional_measures(doc, sections)
    _write_section_wait_handling(doc, sections, is_chain=is_chain)
    _write_section_progress(doc, sections)

    if sections.submission_checklist is not None:
        _write_section_submission_checklist(doc, sections.submission_checklist)

    doc.save(str(path))
    return path


def _add_form5_draft_notice(
    doc: Any,
    *,
    data_source: str,
    use_official_template: bool,
) -> None:
    """様式第5 にドラフト警告を冒頭で出す（sample データ or 公式テンプレ未取得時）。"""
    notice_lines: list[str] = []
    if data_source == "sample":
        notice_lines.append(
            "⚠️ 本書類はデモ用架空企業データに基づく PoC 用ドラフトです。"
            "経営判断・国交省提出には使用できません。"
        )
    if not use_official_template:
        notice_lines.append(
            "※ 国交省公式 Word テンプレート（様式第5）が未取得のため、"
            "構造のみ準拠した参考ドラフトを生成しています。"
            "提出時は MLIT ポータルから公式 Word を取得して整形してください。"
        )
    if not notice_lines:
        return
    para = doc.add_paragraph()
    run = para.add_run("\n".join(notice_lines))
    run.bold = True
    run.font.size = Pt(10)


def _write_section_basic_info(doc: Any, s: Form5Sections) -> None:
    """Ⅰ 特定荷主の名称等。"""
    doc.add_heading("Ⅰ 特定荷主の名称等", level=2)
    table = doc.add_table(rows=6, cols=2)
    table.style = "Table Grid"
    cat_label = "／".join(
        _CATEGORY_LABELS.get(c, c) for c in s.eligibility_categories
    )
    rows_data = [
        ("事業者の名称", s.company_name),
        ("主たる事業", s.main_business),
        ("主たる事業の細分類番号", s.jsic_code),
        ("区分", cat_label or "（該当なし）"),
        ("CLO 役職名・氏名", s.clo_name),
        ("報告対象期間", s.report_period),
    ]
    for row_idx, (label, value) in enumerate(rows_data):
        row = table.rows[row_idx]
        row.cells[0].text = label
        row.cells[1].text = value


def _write_section_compliance(
    doc: Any, s: Form5Sections, *, is_chain: bool,
) -> None:
    """Ⅱ 判断基準の遵守状況。"""
    doc.add_heading("Ⅱ 判断基準の遵守状況", level=2)
    doc.add_paragraph(s.compliance.summary)

    table = doc.add_table(rows=len(s.compliance.items) + 1, cols=3)
    table.style = "Table Grid"
    header = table.rows[0]
    header.cells[0].text = "判断基準項目"
    header.cells[1].text = "遵守状況"
    header.cells[2].text = "実測／基準"

    for row_idx, item in enumerate(s.compliance.items, start=1):
        cells = table.rows[row_idx].cells
        cells[0].text = item.name
        cells[1].text = _status_label(item)
        cells[2].text = _measured_threshold_text(item)

    if is_chain:
        doc.add_paragraph(
            "（連鎖化事業者は荷役等時間短縮の判断基準対象外。"
            "本報告書では積載率・荷待ち時間・拘束時間を中心に記載）"
        )


def _write_section_additional_measures(doc: Any, s: Form5Sections) -> None:
    """Ⅲ 判断基準を遵守できなかった場合の追加措置。"""
    doc.add_heading("Ⅲ 判断基準を遵守できなかった場合の追加措置", level=2)
    if not s.compliance.additional_measures_required:
        doc.add_paragraph("該当なし（全項目において判断基準を遵守）")
        return

    violations = [
        i for i in s.compliance.items
        if i.status in ("violation", "not_measured")
    ]
    if not violations:
        doc.add_paragraph("追加措置の要否判定中（詳細は次回報告書で更新）")
        return

    table = doc.add_table(rows=len(violations) + 1, cols=3)
    table.style = "Table Grid"
    header = table.rows[0]
    header.cells[0].text = "違反／未計測項目"
    header.cells[1].text = "追加措置"
    header.cells[2].text = "実施時期"
    for row_idx, item in enumerate(violations, start=1):
        cells = table.rows[row_idx].cells
        cells[0].text = item.name
        cells[1].text = _proposed_additional_measure(item)
        cells[2].text = "次年度以降（計画書 改定時に統合）"


def _write_section_wait_handling(
    doc: Any, s: Form5Sections, *, is_chain: bool,
) -> None:
    """Ⅳ 荷待ち時間等の計測データ。"""
    doc.add_heading("Ⅳ 荷待ち時間等の計測データ", level=2)

    if s.wait_time_rows:
        doc.add_heading("4-1. 荷待ち時間 計測実績", level=3)
        wait_table = doc.add_table(rows=len(s.wait_time_rows) + 1, cols=5)
        wait_table.style = "Table Grid"
        wh = wait_table.rows[0]
        wh.cells[0].text = "集計区分"
        wh.cells[1].text = "計測便数"
        wh.cells[2].text = "平均（分）"
        wh.cells[3].text = "最大（分）"
        wh.cells[4].text = "2時間超 件数"
        for row_idx, w in enumerate(s.wait_time_rows, start=1):
            cells = wait_table.rows[row_idx].cells
            cells[0].text = w.bucket_label
            cells[1].text = f"{w.measured_count:,}便"
            cells[2].text = f"{w.average_minutes:.0f}"
            cells[3].text = f"{w.max_minutes:.0f}"
            cells[4].text = f"{w.over_2h_count:,}件"

    if s.handling_time_rows and not is_chain:
        doc.add_heading("4-2. 荷役等時間 計測実績", level=3)
        h_table = doc.add_table(rows=len(s.handling_time_rows) + 1, cols=5)
        h_table.style = "Table Grid"
        hh = h_table.rows[0]
        hh.cells[0].text = "納品形態"
        hh.cells[1].text = "計測件数"
        hh.cells[2].text = "平均（分）"
        hh.cells[3].text = "最大（分）"
        hh.cells[4].text = "1時間超 割合"
        for row_idx, h in enumerate(s.handling_time_rows, start=1):
            cells = h_table.rows[row_idx].cells
            cells[0].text = h.bucket_label
            cells[1].text = f"{h.measured_count:,}件"
            cells[2].text = f"{h.average_minutes:.0f}"
            cells[3].text = f"{h.max_minutes:.0f}"
            cells[4].text = f"{h.over_1h_pct:.1f}%"

    if not s.wait_time_rows and not s.handling_time_rows:
        doc.add_paragraph(
            "（計測データが未取得。動態管理システム等による"
            "荷待ち時間・荷役等時間の計測体制整備が必要）"
        )


def _write_section_progress(doc: Any, s: Form5Sections) -> None:
    """Ⅴ 中長期計画の進捗状況。"""
    doc.add_heading("Ⅴ 中長期計画の進捗状況", level=2)
    if not s.progress_rows:
        doc.add_paragraph("（中長期計画書 提出済の場合のみ記載。初回報告時は空欄）")
        return

    table = doc.add_table(rows=len(s.progress_rows) + 1, cols=4)
    table.style = "Table Grid"
    header = table.rows[0]
    header.cells[0].text = "施策"
    header.cells[1].text = "計画目標"
    header.cells[2].text = "当年度実績"
    header.cells[3].text = "達成状況"
    for row_idx, p in enumerate(s.progress_rows, start=1):
        cells = table.rows[row_idx].cells
        cells[0].text = p.measure_name
        cells[1].text = p.plan_target
        cells[2].text = p.actual_result
        cells[3].text = p.status_mark


def _write_section_submission_checklist(
    doc: Any, checklist: SubmissionChecklist,
) -> None:
    """Ⅵ 提出準備チェックリスト（Codex 1 取込）。"""
    doc.add_heading("Ⅵ 提出準備チェックリスト（実務）", level=2)
    doc.add_paragraph(f"提出経路: {checklist.submission_method}")

    table = doc.add_table(rows=len(checklist.items) + 1, cols=3)
    table.style = "Table Grid"
    header = table.rows[0]
    header.cells[0].text = "項目"
    header.cells[1].text = "内容"
    header.cells[2].text = "値（自動補完／自社記載）"
    for row_idx, item in enumerate(checklist.items, start=1):
        cells = table.rows[row_idx].cells
        cells[0].text = item.label
        cells[1].text = item.guidance
        cells[2].text = item.auto_value or "（自社で記載）"

    if checklist.form_usage_notes:
        doc.add_heading("様式の使い分け", level=3)
        for note in checklist.form_usage_notes:
            doc.add_paragraph(f"・{note}")


def _status_label(item: ComplianceItem) -> str:
    return {
        "compliant": "☑ 遵守",
        "violation": "☒ 違反",
        "borderline": "△ 要注意",
        "not_measured": "― 未計測",
    }[item.status]


def _measured_threshold_text(item: ComplianceItem) -> str:
    if item.measured_value is None:
        return f"基準: {item.threshold}{item.unit}"
    return f"実測 {item.measured_value}{item.unit} ／ 基準 {item.threshold}{item.unit}"


def _proposed_additional_measure(item: ComplianceItem) -> str:
    """違反／未計測項目に対する標準的な追加措置文言を返す。"""
    if item.status == "not_measured":
        return f"{item.name} の計測体制整備（動態管理システム連携）"
    if "荷待ち" in item.name:
        return "バース予約システム導入・納入時間帯分散による削減"
    if "荷役" in item.name:
        return "パレット標準化・WMS 連携による削減"
    if "拘束" in item.name or "労働" in item.name:
        return "中継輸送導入・配車計画見直しによる拘束時間削減"
    if "休息" in item.name:
        return "運行スケジュールの根本的見直しと連続休息確保"
    return "改善基準告示遵守のための運用見直し"


__all__ = [
    "Form5Sections",
    "HandlingTimeRow",
    "ProgressRow",
    "WaitTimeRow",
    "write_form5",
]
