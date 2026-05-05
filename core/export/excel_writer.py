"""Excel 形式の成果物生成（数値表 + 出典シート）。

社内 BI への取込・経営会議の付録資料として使う。openpyxl ベース。

設計方針:
    - メインシート: 数値表
    - 出典シート: 全数値の出典 URL を 1 行 1 件で列挙（経営会議で「出典は？」即答可能に）
    - 列幅は内容に応じて自動調整（手作業の整形を最小化）
"""

from __future__ import annotations

import re
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
_THIN_BORDER = Border(
    left=Side(style="thin", color="D9E2F3"),
    right=Side(style="thin", color="D9E2F3"),
    top=Side(style="thin", color="D9E2F3"),
    bottom=Side(style="thin", color="D9E2F3"),
)


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
    """Create an executive-friendly summary sheet with KPI blocks and a chart."""
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A8"

    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=15, color="1F4E79")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
    ws.cell(row=2, column=1, value="社内レビュー用 分析サマリー").font = Font(
        bold=True,
        color="666666",
    )

    kpis = [
        ("データ行数", len(rows), "件"),
        ("出典数", len(citations), "件"),
        ("数値列数", _count_numeric_columns(rows), "列"),
    ]
    for idx, (label, value, unit) in enumerate(kpis, start=1):
        col = 1 + (idx - 1) * 2
        ws.cell(row=4, column=col, value=label)
        value_cell = ws.cell(row=5, column=col, value=value)
        unit_cell = ws.cell(row=5, column=col + 1, value=unit)
        for cell in (ws.cell(row=4, column=col), value_cell, unit_cell):
            cell.fill = _KPI_FILL
            cell.border = _THIN_BORDER
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=4, column=col).font = Font(bold=True, color="1F4E79")
        value_cell.font = Font(bold=True, size=16, color="1F4E79")

    chart_rows = _extract_measure_chart_rows(rows)
    chart_title = "施策別コスト削減・投資額（万円/年）"
    chart_value_headers = ["コスト削減（万円/年）", "投資額（万円）"]
    if not chart_rows:
        chart_rows = _extract_generic_numeric_chart_rows(headers, rows)
        chart_title = "主要数値サマリー"
        chart_value_headers = ["値"]

    start_row = 8
    ws.cell(row=start_row, column=1, value="チャート用データ").font = Font(
        bold=True,
        color="1F4E79",
    )
    table_start = start_row + 1
    headers_to_write = ["項目", *chart_value_headers]
    for col_idx, value in enumerate(headers_to_write, start=1):
        cell = ws.cell(row=table_start, column=col_idx, value=value)
        cell.font = _HEADER_FONT
        cell.fill = _SUMMARY_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _THIN_BORDER

    for row_offset, chart_row in enumerate(chart_rows, start=1):
        for col_idx, value in enumerate(chart_row, start=1):
            cell = ws.cell(row=table_start + row_offset, column=col_idx, value=value)
            cell.border = _THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if col_idx > 1:
                cell.number_format = "#,##0"

    for col_idx, width in enumerate([34, 18, 18, 18], start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    if chart_rows:
        max_row = table_start + len(chart_rows)
        max_col = len(headers_to_write)
        chart = BarChart()
        chart.title = chart_title
        chart.y_axis.title = "万円" if len(headers_to_write) > 2 else "値"
        chart.x_axis.title = "項目"
        data = Reference(
            ws,
            min_col=2,
            max_col=max_col,
            min_row=table_start,
            max_row=max_row,
        )
        categories = Reference(ws, min_col=1, min_row=table_start + 1, max_row=max_row)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        chart.height = 8.0
        chart.width = 15.5
        ws.add_chart(chart, "E8")


def _count_numeric_columns(rows: list[list[object]]) -> int:
    if not rows:
        return 0
    max_len = max(len(row) for row in rows)
    count = 0
    for col_idx in range(max_len):
        if any(col_idx < len(row) and isinstance(row[col_idx], int | float) for row in rows):
            count += 1
    return count


def _extract_measure_chart_rows(rows: list[list[object]]) -> list[list[object]]:
    chart_rows: list[list[object]] = []
    for row in rows:
        if len(row) < 4 or "施策" not in str(row[1]):
            continue
        label = str(row[0])[:28]
        investment_man = _extract_man_yen(str(row[2]), prefix="投資")
        cost_saving_man = _extract_man_yen(str(row[3]), prefix="コスト")
        if investment_man is None and cost_saving_man is None:
            continue
        chart_rows.append(
            [
                label,
                cost_saving_man or 0,
                investment_man or 0,
            ]
        )
    return chart_rows[:8]


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
