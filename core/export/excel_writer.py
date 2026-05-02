"""Excel 形式の成果物生成（数値表 + 出典シート）。

社内 BI への取込・経営会議の付録資料として使う。openpyxl ベース。

設計方針:
    - メインシート: 数値表
    - 出典シート: 全数値の出典 URL を 1 行 1 件で列挙（経営会議で「出典は？」即答可能に）
    - 列幅は内容に応じて自動調整（手作業の整形を最小化）
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from core.export.citation import Citation
from core.export.response import make_output_path

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="305496")
_CITATION_HEADER_FILL = PatternFill("solid", fgColor="548235")


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
    ws_main = wb.active
    if ws_main is None:
        ws_main = wb.create_sheet("Data")
    ws_main.title = "Data"

    # タイトル行（A1 マージ）
    ws_main.cell(row=1, column=1, value=title).font = Font(bold=True, size=14)
    if len(headers) > 1:
        ws_main.merge_cells(
            start_row=1, start_column=1, end_row=1, end_column=len(headers),
        )

    # ヘッダ行（2 行目）
    for col_idx, h in enumerate(headers, start=1):
        cell = ws_main.cell(row=2, column=col_idx, value=h)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center")

    # データ行（3 行目〜）
    for row_idx, row in enumerate(rows, start=3):
        for col_idx, val in enumerate(row, start=1):
            ws_main.cell(row=row_idx, column=col_idx, value=val)

    # 列幅自動調整
    for col_idx, h in enumerate(headers, start=1):
        max_len = len(str(h))
        for row in rows:
            if col_idx - 1 < len(row):
                max_len = max(max_len, len(str(row[col_idx - 1])))
        ws_main.column_dimensions[get_column_letter(col_idx)].width = min(
            max_len * 2 + 4, 60,
        )

    # 出典シート
    ws_cit = wb.create_sheet("出典")
    ws_cit.cell(row=1, column=1, value="出典一覧（全数値の根拠）").font = Font(
        bold=True, size=14,
    )
    cit_headers = ["ラベル", "URL", "statsDataId/告示番号", "取得時刻", "経路"]
    for col_idx, h in enumerate(cit_headers, start=1):
        cell = ws_cit.cell(row=2, column=col_idx, value=h)
        cell.font = _HEADER_FONT
        cell.fill = _CITATION_HEADER_FILL
    for row_idx, c in enumerate(citations, start=3):
        ws_cit.cell(row=row_idx, column=1, value=c.label)
        ws_cit.cell(row=row_idx, column=2, value=c.url)
        identifier = c.stats_data_id or c.notice_number or c.ordinance_number or ""
        ws_cit.cell(row=row_idx, column=3, value=identifier)
        ws_cit.cell(row=row_idx, column=4, value=c.fetched_at)
        ws_cit.cell(row=row_idx, column=5, value=c.accessed_via)

    # 出典シート列幅
    cit_widths = [40, 60, 30, 25, 25]
    for col_idx, w in enumerate(cit_widths, start=1):
        ws_cit.column_dimensions[get_column_letter(col_idx)].width = w

    wb.save(path)
    return path
