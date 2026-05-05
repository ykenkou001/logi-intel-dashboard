"""Excel 形式の成果物生成（数値表 + 出典シート）。

社内 BI への取込・経営会議の付録資料として使う。openpyxl ベース。

設計方針:
    - メインシート: 数値表
    - 出典シート: 全数値の出典 URL を 1 行 1 件で列挙（経営会議で「出典は？」即答可能に）
    - 列幅は内容に応じて自動調整（手作業の整形を最小化）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from core.export.citation import Citation
from core.export.response import make_output_path

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="305496")
_CITATION_HEADER_FILL = PatternFill("solid", fgColor="548235")
_SUMMARY_FILL = PatternFill("solid", fgColor="1F4E79")
_KPI_FILL = PatternFill("solid", fgColor="D9EAF7")
_PALE_GREEN_FILL = PatternFill("solid", fgColor="E2F0D9")
_PALE_YELLOW_FILL = PatternFill("solid", fgColor="FFF2CC")
_WHITE_FILL = PatternFill("solid", fgColor="FFFFFF")
_THIN_BORDER = Border(
    left=Side(style="thin", color="D9E2F3"),
    right=Side(style="thin", color="D9E2F3"),
    top=Side(style="thin", color="D9E2F3"),
    bottom=Side(style="thin", color="D9E2F3"),
)


@dataclass(frozen=True)
class _MeasureSummary:
    name: str
    cost_saving_man: float
    investment_man: float
    co2_tons: float | None

    @property
    def payback_years(self) -> float | None:
        if self.cost_saving_man <= 0:
            return None
        return self.investment_man / self.cost_saving_man


@dataclass(frozen=True)
class _TargetSummary:
    name: str
    current: str
    target: str
    citation: str


def write_data_table(
    title: str,
    company_id: str,
    headers: list[str],
    rows: list[list[object]],
    citations: list[Citation],
    purpose: str = "data_table",
) -> Path:
    """データ表 + 出典シートの Excel を生成する。

    Args:
        title: メインシートのタイトル（A1 に書き込み）
        company_id: ファイル名用の識別子
        headers: 列見出し（1 行目）
        rows: データ行のリスト（各行は値のリスト）
        citations: 出典リスト
        purpose: ファイル名用の用途識別子

    Returns:
        生成ファイルのパス
    """
    path = make_output_path(
        file_type="excel",
        purpose=purpose,
        company_id=company_id,
        extension="xlsx",
    )

    wb = Workbook()
    ws_summary = wb.active
    if ws_summary is None:
        ws_summary = wb.create_sheet("Summary")
    ws_summary.title = "Summary"
    ws_main = wb.create_sheet("Data")

    # タイトル行（A1 マージ）
    ws_main.cell(row=1, column=1, value=title).font = Font(bold=True, size=14)
    if len(headers) > 1:
        ws_main.merge_cells(
            start_row=1,
            start_column=1,
            end_row=1,
            end_column=len(headers),
        )

    # ヘッダ行（2 行目）
    for col_idx, h in enumerate(headers, start=1):
        cell = ws_main.cell(row=2, column=col_idx, value=h)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _THIN_BORDER

    # データ行（3 行目〜）
    for row_idx, row in enumerate(rows, start=3):
        for col_idx, val in enumerate(row, start=1):
            cell = ws_main.cell(row=row_idx, column=col_idx, value=val)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = _THIN_BORDER
            if isinstance(val, int):
                cell.number_format = "#,##0"
            elif isinstance(val, float):
                cell.number_format = "#,##0.0"

    # 列幅自動調整
    for col_idx, h in enumerate(headers, start=1):
        max_len = len(str(h))
        for row in rows:
            if col_idx - 1 < len(row):
                max_len = max(max_len, len(str(row[col_idx - 1])))
        ws_main.column_dimensions[get_column_letter(col_idx)].width = min(
            max_len * 2 + 4,
            60,
        )
    ws_main.freeze_panes = "A3"
    ws_main.row_dimensions[2].height = 24
    if rows and headers:
        data_ref = f"A2:{get_column_letter(len(headers))}{len(rows) + 2}"
        data_table = Table(displayName="DataTable", ref=data_ref)
        data_table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws_main.add_table(data_table)

    # 出典シート
    ws_cit = wb.create_sheet("出典")
    ws_cit.cell(row=1, column=1, value="出典一覧（全数値の根拠）").font = Font(
        bold=True,
        size=14,
    )
    cit_headers = ["ラベル", "URL", "statsDataId/告示番号", "取得時刻", "経路"]
    for col_idx, h in enumerate(cit_headers, start=1):
        cell = ws_cit.cell(row=2, column=col_idx, value=h)
        cell.font = _HEADER_FONT
        cell.fill = _CITATION_HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _THIN_BORDER
    for row_idx, c in enumerate(citations, start=3):
        ws_cit.cell(row=row_idx, column=1, value=c.label)
        url_cell = ws_cit.cell(row=row_idx, column=2, value=c.url)
        url_cell.hyperlink = c.url
        url_cell.style = "Hyperlink"
        identifier = c.stats_data_id or c.notice_number or c.ordinance_number or ""
        ws_cit.cell(row=row_idx, column=3, value=identifier)
        ws_cit.cell(row=row_idx, column=4, value=c.fetched_at)
        ws_cit.cell(row=row_idx, column=5, value=c.accessed_via)
        for col_idx in range(1, len(cit_headers) + 1):
            cell = ws_cit.cell(row=row_idx, column=col_idx)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = _THIN_BORDER

    # 出典シート列幅
    cit_widths = [40, 60, 30, 25, 25]
    for col_idx, w in enumerate(cit_widths, start=1):
        ws_cit.column_dimensions[get_column_letter(col_idx)].width = w
    ws_cit.freeze_panes = "A3"
    if citations:
        cit_ref = f"A2:E{len(citations) + 2}"
        cit_table = Table(displayName="CitationTable", ref=cit_ref)
        cit_table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium4",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws_cit.add_table(cit_table)

    _build_summary_sheet(ws_summary, title, headers, rows, citations)

    wb.save(path)
    return path


def _build_summary_sheet(
    ws,
    title: str,
    headers: list[str],
    rows: list[list[object]],
    citations: list[Citation],
) -> None:
    """Create a human-readable summary sheet before the raw Data sheet."""
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A8"

    measures = _extract_measure_summaries(rows)
    targets = _extract_target_rows(rows)
    total_cost_man = sum(m.cost_saving_man for m in measures)
    total_investment_man = sum(m.investment_man for m in measures)
    total_co2_tons = sum(m.co2_tons or 0 for m in measures)
    payback = total_investment_man / total_cost_man if total_cost_man else None

    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=15, color="1F4E79")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
    ws.cell(
        row=2,
        column=1,
        value="社内レビュー用サマリー: 優先施策・投資額・効果を1枚で確認",
    ).font = Font(bold=True, color="666666")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=8)

    _write_kpi_card(ws, col=1, label="年間コスト削減", value=_format_man(total_cost_man))
    _write_kpi_card(ws, col=3, label="初期投資", value=_format_man(total_investment_man))
    _write_kpi_card(
        ws,
        col=5,
        label="単純回収目安",
        value=_format_payback(payback),
    )
    _write_kpi_card(ws, col=7, label="CO2削減", value=f"{total_co2_tons:,.0f} t/年")

    ws.cell(row=7, column=1, value="優先施策サマリー").font = Font(
        bold=True,
        size=12,
        color="1F4E79",
    )
    measure_table_start = 8
    measure_headers = [
        "優先",
        "施策",
        "年間コスト削減",
        "初期投資",
        "回収目安",
        "CO2削減",
        "読み方",
    ]
    _write_header_row(ws, measure_table_start, measure_headers)

    sorted_measures = sorted(measures, key=lambda m: m.cost_saving_man, reverse=True)
    for idx, measure in enumerate(sorted_measures[:8], start=1):
        payback_text = _format_payback(measure.payback_years)
        note = _measure_note(measure)
        values = [
            idx,
            measure.name,
            measure.cost_saving_man,
            measure.investment_man,
            payback_text,
            measure.co2_tons or 0,
            note,
        ]
        _write_body_row(ws, measure_table_start + idx, values, measure_headers)

    if sorted_measures:
        table_end = measure_table_start + len(sorted_measures[:8])
        table = Table(displayName="SummaryMeasureTable", ref=f"A{measure_table_start}:G{table_end}")
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws.add_table(table)

    plan_start = measure_table_start + max(len(sorted_measures[:8]), 1) + 3
    target_plan_rows = _build_target_plan_rows(targets, sorted_measures)
    if target_plan_rows:
        ws.cell(row=plan_start, column=1, value="目標達成計画").font = Font(
            bold=True,
            size=12,
            color="1F4E79",
        )
        plan_headers = ["数値目標", "現状", "目標", "対応施策", "実施時期目安", "確認KPI"]
        _write_header_row(ws, plan_start + 1, plan_headers)
        for idx, row in enumerate(target_plan_rows, start=1):
            _write_body_row(ws, plan_start + 1 + idx, row, plan_headers)
        plan_end = plan_start + 1 + len(target_plan_rows)
        table = Table(displayName="TargetPlanTable", ref=f"A{plan_start + 1}:F{plan_end}")
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium4",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws.add_table(table)

    chart_anchor_row = 8
    chart_data_start = 42
    chart_rows = _write_chart_helper(ws, chart_data_start, sorted_measures[:5], headers, rows)
    if chart_rows:
        chart = BarChart()
        chart.type = "bar"
        chart.style = 10
        chart.title = "コスト削減効果 上位施策"
        chart.y_axis.title = ""
        chart.x_axis.title = "万円/年"
        data = Reference(
            ws,
            min_col=2,
            max_col=2,
            min_row=chart_data_start,
            max_row=chart_data_start + chart_rows,
        )
        categories = Reference(
            ws,
            min_col=1,
            min_row=chart_data_start + 1,
            max_row=chart_data_start + chart_rows,
        )
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        chart.height = 6.0
        chart.width = 13.0
        ws.add_chart(chart, f"I{chart_anchor_row}")

    target_start = plan_start + max(len(target_plan_rows), 1) + 4
    if targets:
        ws.cell(row=target_start, column=1, value="数値目標").font = Font(
            bold=True,
            size=12,
            color="1F4E79",
        )
        target_headers = ["指標", "現状", "目標", "出典"]
        _write_header_row(ws, target_start + 1, target_headers)
        for idx, target in enumerate(targets, start=1):
            row = [target.name, target.current, target.target, target.citation]
            _write_body_row(ws, target_start + 1 + idx, row, target_headers)

    notes_row = target_start + len(targets) + 4
    ws.cell(row=notes_row, column=1, value="確認ポイント").font = Font(
        bold=True,
        color="1F4E79",
    )
    review_notes = [
        "金額単位は万円。詳細な元データは Data シート、根拠 URL は 出典 シートを参照。",
        f"出典数: {len(citations)}件。経営会議で根拠確認が必要な場合は 出典 シートから確認。",
    ]
    for idx, note in enumerate(review_notes, start=1):
        cell = ws.cell(row=notes_row + idx, column=1, value=note)
        ws.merge_cells(
            start_row=notes_row + idx,
            start_column=1,
            end_row=notes_row + idx,
            end_column=8,
        )
        cell.fill = _PALE_YELLOW_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = _THIN_BORDER

    widths = [10, 30, 16, 30, 16, 20, 34, 3, 3, 34, 16]
    for col_idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    for row_idx in range(1, notes_row + len(review_notes) + 1):
        ws.row_dimensions[row_idx].height = 24
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 22


def _write_kpi_card(ws, *, col: int, label: str, value: str) -> None:
    ws.merge_cells(start_row=4, start_column=col, end_row=4, end_column=col + 1)
    ws.merge_cells(start_row=5, start_column=col, end_row=5, end_column=col + 1)
    label_cell = ws.cell(row=4, column=col, value=label)
    value_cell = ws.cell(row=5, column=col, value=value)
    for cell in (label_cell, value_cell):
        cell.fill = _KPI_FILL
        cell.border = _THIN_BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center")
    label_cell.font = Font(bold=True, color="1F4E79")
    value_cell.font = Font(bold=True, size=15, color="1F4E79")


def _write_header_row(ws, row_idx: int, headers: list[str]) -> None:
    for col_idx, value in enumerate(headers, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.font = _HEADER_FONT
        cell.fill = _SUMMARY_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _THIN_BORDER


def _write_body_row(
    ws,
    row_idx: int,
    values: list[object],
    headers: list[str],
) -> None:
    for col_idx, value in enumerate(values, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.fill = _WHITE_FILL
        cell.border = _THIN_BORDER
        cell.alignment = Alignment(
            horizontal="center"
            if headers[col_idx - 1] in {"優先", "回収目安", "実施時期目安"}
            else "left",
            vertical="center",
            wrap_text=True,
        )
        if headers[col_idx - 1] in {"年間コスト削減", "初期投資", "CO2削減"}:
            cell.number_format = "#,##0"
            cell.alignment = Alignment(horizontal="right", vertical="center")
        if headers[col_idx - 1] == "読み方" and str(value).startswith("短期"):
            cell.fill = _PALE_GREEN_FILL


def _write_chart_helper(
    ws,
    start_row: int,
    measures: list[_MeasureSummary],
    headers: list[str],
    rows: list[list[object]],
) -> int:
    if measures:
        ws.cell(row=start_row, column=1, value="施策")
        ws.cell(row=start_row, column=2, value="年間コスト削減")
        for idx, measure in enumerate(measures, start=1):
            ws.cell(row=start_row + idx, column=1, value=measure.name)
            ws.cell(row=start_row + idx, column=2, value=measure.cost_saving_man)
        return len(measures)

    generic_rows = _extract_generic_numeric_chart_rows(headers, rows)
    if not generic_rows:
        return 0
    ws.cell(row=start_row, column=1, value="項目")
    ws.cell(row=start_row, column=2, value="値")
    for idx, row in enumerate(generic_rows, start=1):
        ws.cell(row=start_row + idx, column=1, value=row[0])
        ws.cell(row=start_row + idx, column=2, value=row[1])
    return len(generic_rows)


def _extract_measure_summaries(rows: list[list[object]]) -> list[_MeasureSummary]:
    measures: list[_MeasureSummary] = []
    for row in rows:
        if len(row) < 4 or "施策" not in str(row[1]):
            continue
        investment_man = _extract_man_yen(str(row[2]), prefix="投資") or 0
        cost_saving_man = _extract_man_yen(str(row[3]), prefix="コスト") or 0
        co2_tons = _extract_co2_tons(str(row[3]))
        if investment_man == 0 and cost_saving_man == 0 and co2_tons is None:
            continue
        measures.append(
            _MeasureSummary(
                name=str(row[0]),
                cost_saving_man=cost_saving_man,
                investment_man=investment_man,
                co2_tons=co2_tons,
            )
        )
    return measures


def _extract_target_rows(rows: list[list[object]]) -> list[_TargetSummary]:
    targets: list[_TargetSummary] = []
    for row in rows:
        if len(row) < 5 or "数値目標" not in str(row[1]):
            continue
        targets.append(_TargetSummary(str(row[0]), str(row[2]), str(row[3]), str(row[4])))
    return targets[:8]


def _build_target_plan_rows(
    targets: list[_TargetSummary],
    measures: list[_MeasureSummary],
) -> list[list[object]]:
    plan_rows: list[list[object]] = []
    for target in targets:
        related = _related_measures_for_target(target.name, measures)
        if not related:
            related = measures[:3]
        measure_names = " / ".join(m.name for m in related[:3]) or "施策設計が必要"
        timing = _target_plan_timing(related)
        plan_rows.append(
            [
                target.name,
                target.current,
                target.target,
                measure_names,
                timing,
                _target_kpi(target.name),
            ]
        )
    return plan_rows


def _related_measures_for_target(
    target_name: str,
    measures: list[_MeasureSummary],
) -> list[_MeasureSummary]:
    name = target_name.lower()
    if "積載" in target_name:
        keywords = ("積載", "共同配送", "モーダル")
    elif "co2" in name or "CO2" in target_name or "原単位" in target_name:
        return sorted(measures, key=lambda m: m.co2_tons or 0, reverse=True)
    elif "コスト" in target_name or "利益" in target_name:
        return sorted(measures, key=lambda m: m.cost_saving_man, reverse=True)
    elif "モーダル" in target_name or "鉄道" in target_name:
        keywords = ("モーダル", "鉄道")
    else:
        return sorted(measures, key=lambda m: m.cost_saving_man, reverse=True)
    return [m for m in measures if any(k in m.name for k in keywords)]


def _target_plan_timing(measures: list[_MeasureSummary]) -> str:
    if not measures:
        return "2026年度に施策設計"
    best_rank = min(range(len(measures)), default=0)
    if best_rank == 0:
        return "2026年度（先行）"
    if best_rank <= 2:
        return "2026〜2027年度"
    return "2027〜2028年度"


def _target_kpi(target_name: str) -> str:
    name = target_name.lower()
    if "積載" in target_name:
        return "積載率、空車率、共同配送便数"
    if "co2" in name or "CO2" in target_name or "原単位" in target_name:
        return "CO2排出量、輸送量、CO2原単位"
    if "コスト" in target_name or "利益" in target_name:
        return "物流費、営業利益、投資回収"
    if "モーダル" in target_name or "鉄道" in target_name:
        return "鉄道/船舶輸送量、トラック代替率"
    return "月次実績、前年差、計画差"


def _measure_note(measure: _MeasureSummary) -> str:
    if measure.payback_years is not None and measure.payback_years <= 1.0:
        return "短期回収。優先検討"
    if measure.cost_saving_man >= measure.investment_man:
        return "効果大。実行計画化"
    if measure.co2_tons and measure.co2_tons >= 1000:
        return "環境効果大。ESG説明向き"
    return "効果・実現性を要確認"


def _format_man(value: float) -> str:
    if value >= 10000:
        return f"{value / 10000:.1f}億円"
    return f"{value:,.0f}万円"


def _format_payback(value: float | None) -> str:
    if value is None:
        return "-"
    if value < 0.1:
        return "<0.1年"
    return f"{value:.1f}年"


def _extract_generic_numeric_chart_rows(
    headers: list[str],
    rows: list[list[object]],
) -> list[list[object]]:
    if not headers or not rows:
        return []
    numeric_col = None
    for col_idx in range(len(headers)):
        if any(col_idx < len(row) and isinstance(row[col_idx], int | float) for row in rows):
            numeric_col = col_idx
            break
    if numeric_col is None:
        return []
    label_col = 0 if numeric_col != 0 else 1
    chart_rows = []
    for row in rows[:8]:
        if numeric_col >= len(row):
            continue
        value = row[numeric_col]
        if not isinstance(value, int | float):
            continue
        label = str(row[label_col]) if label_col < len(row) else f"Row {len(chart_rows) + 1}"
        chart_rows.append([label[:28], value])
    return chart_rows


def _extract_man_yen(text: str, *, prefix: str) -> float | None:
    pattern = rf"{re.escape(prefix)}\s*約?([0-9,]+(?:\.[0-9]+)?)万円"
    match = re.search(pattern, text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _extract_co2_tons(text: str) -> float | None:
    match = re.search(r"CO2\s*約?([0-9,]+(?:\.[0-9]+)?)トン", text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))
