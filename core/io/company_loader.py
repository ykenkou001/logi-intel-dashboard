"""Excel/CSV ファイルから CompanyProfile を構築する（フェーズ4.0「実データ入力フォーム」）。

入力フォーマット:
    - Excel 1 ファイル + マルチシート（推奨）: profile / sites / wait_time /
      handling_time / kpi_history（template_writer.py が生成するテンプレと同形式）
    - CSV 複数ファイル（補助）: 同じシート名のファイル群を 1 ディレクトリに配置

設計方針:
    - シート/ファイル名は固定（template_writer と整合）
    - profile シートは縦並び（A列=項目名・B列=値）の単一行入力
    - 他シートは横並びの表形式（1行目=ヘッダ・2行目=説明・3行目以降=データ）
    - エラーは行・列・期待型を含む ValueError として明示する
    - 数値型は openpyxl が float で返すケースがあるため、int フィールドは
      Pydantic v2 のデフォルト挙動（float→int の loss-less 変換）に委ねる
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from pydantic import ValidationError

from core.static.sample_company import (
    CompanyProfile,
    CompanySite,
    HandlingTimeRow,
    KpiHistoryEntry,
    WaitTimeRow,
)

PROFILE_SHEET = "profile"
SITES_SHEET = "sites"
WAIT_TIME_SHEET = "wait_time"
HANDLING_TIME_SHEET = "handling_time"
KPI_HISTORY_SHEET = "kpi_history"


def load_company_profile_from_excel(path: Path) -> CompanyProfile:
    """Excel ファイル（マルチシート）から CompanyProfile を構築する。

    Args:
        path: Excel ファイルのパス

    Returns:
        構築された CompanyProfile（data_source は profile シートの値か "actual" 既定）

    Raises:
        FileNotFoundError: ファイルが存在しない
        ValueError: シート欠落・必須項目欠落・型不正
    """
    if not path.is_file():
        raise FileNotFoundError(f"Excel ファイルが見つかりません: {path}")

    wb = load_workbook(path, read_only=True, data_only=True)
    sheet_names = set(wb.sheetnames)

    required = {PROFILE_SHEET, SITES_SHEET}
    missing = required - sheet_names
    if missing:
        raise ValueError(
            f"必須シートが欠落しています: {sorted(missing)}（取得: {sorted(sheet_names)}）"
        )

    profile_kv = _read_profile_sheet(wb[PROFILE_SHEET])
    sites_rows = _read_tabular_sheet(wb[SITES_SHEET])
    wait_rows = _read_tabular_sheet(wb[WAIT_TIME_SHEET]) if WAIT_TIME_SHEET in sheet_names else []
    handling_rows = (
        _read_tabular_sheet(wb[HANDLING_TIME_SHEET]) if HANDLING_TIME_SHEET in sheet_names else []
    )
    kpi_rows = (
        _read_tabular_sheet(wb[KPI_HISTORY_SHEET]) if KPI_HISTORY_SHEET in sheet_names else []
    )

    return _build_profile(profile_kv, sites_rows, wait_rows, handling_rows, kpi_rows)


def load_company_profile_from_csv(dir_path: Path) -> CompanyProfile:
    """CSV ファイル群（同名シート）から CompanyProfile を構築する。

    Args:
        dir_path: CSV ディレクトリ（profile.csv / sites.csv / ... を含む）

    Returns:
        構築された CompanyProfile

    Raises:
        FileNotFoundError: profile.csv / sites.csv が見つからない
        ValueError: 必須項目欠落・型不正
    """
    if not dir_path.is_dir():
        raise FileNotFoundError(f"CSV ディレクトリが見つかりません: {dir_path}")

    profile_csv = dir_path / f"{PROFILE_SHEET}.csv"
    sites_csv = dir_path / f"{SITES_SHEET}.csv"
    if not profile_csv.is_file():
        raise FileNotFoundError(f"必須 CSV が見つかりません: {profile_csv}")
    if not sites_csv.is_file():
        raise FileNotFoundError(f"必須 CSV が見つかりません: {sites_csv}")

    profile_kv = _read_profile_csv(profile_csv)
    sites_rows = _read_tabular_csv(sites_csv)
    wait_rows = _read_tabular_csv_optional(dir_path / f"{WAIT_TIME_SHEET}.csv")
    handling_rows = _read_tabular_csv_optional(dir_path / f"{HANDLING_TIME_SHEET}.csv")
    kpi_rows = _read_tabular_csv_optional(dir_path / f"{KPI_HISTORY_SHEET}.csv")

    return _build_profile(profile_kv, sites_rows, wait_rows, handling_rows, kpi_rows)


# --- profile (縦並び単一行) -------------------------------------------------


def _read_profile_sheet(ws: Any) -> dict[str, Any]:
    """profile シート（A列=項目名・B列=値）を辞書として読み込む。

    1 行目はヘッダなので 2 行目以降を見る。
    項目名末尾の "[必須]"/"[任意]" 表記は除去する。
    空の値はスキップ（Optional フィールドの未指定を表現）。
    """
    kv: dict[str, Any] = {}
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or row[0] is None:
            continue
        raw_key = str(row[0])
        key = _strip_marker(raw_key).strip()
        if not key:
            continue
        value = row[1] if len(row) > 1 else None
        if value is None or (isinstance(value, str) and value.strip() == ""):
            # 任意項目の空欄はスキップ
            continue
        if key in kv:
            raise ValueError(f"profile シート 行 {row_idx}: 項目 '{key}' が重複")
        kv[key] = value
    return kv


def _read_profile_csv(path: Path) -> dict[str, Any]:
    """profile.csv（item, value, ...）を辞書として読み込む。"""
    kv: dict[str, Any] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return kv
    # 1 行目をヘッダとしてスキップ
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        key = _strip_marker(row[0]).strip()
        if not key:
            continue
        value: Any = row[1] if len(row) > 1 else None
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue
        kv[key] = value
    return kv


# --- 表形式シート ---------------------------------------------------------


def _read_tabular_sheet(ws: Any) -> list[dict[str, Any]]:
    """表形式シート（1行目=ヘッダ・2行目=説明・3行目以降=データ）を読み込む。"""
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 3:
        return []
    headers = [_strip_marker(str(h)).strip() if h is not None else "" for h in rows[0]]
    out: list[dict[str, Any]] = []
    # 3 行目以降がデータ（rows[2:]）
    for data_row in rows[2:]:
        if not any(v is not None for v in data_row):
            continue
        record: dict[str, Any] = {}
        for header, value in zip(headers, data_row, strict=False):
            if not header:
                continue
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            record[header] = value
        if record:
            out.append(record)
    return out


def _read_tabular_csv(path: Path) -> list[dict[str, Any]]:
    """CSV（1行目=ヘッダ・2行目以降=データ）を読み込む。説明行はないものとする。"""
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return out
    headers = [_strip_marker(h).strip() for h in rows[0]]
    for data_row in rows[1:]:
        if not data_row or not any(v.strip() for v in data_row):
            continue
        record: dict[str, Any] = {}
        for header, value in zip(headers, data_row, strict=False):
            if not header or value.strip() == "":
                continue
            record[header] = value
        if record:
            out.append(record)
    return out


def _read_tabular_csv_optional(path: Path) -> list[dict[str, Any]]:
    return _read_tabular_csv(path) if path.is_file() else []


# --- 構築 ---------------------------------------------------------------


def _build_profile(
    profile_kv: dict[str, Any],
    sites_rows: list[dict[str, Any]],
    wait_rows: list[dict[str, Any]],
    handling_rows: list[dict[str, Any]],
    kpi_rows: list[dict[str, Any]],
) -> CompanyProfile:
    """各シート/CSV の dict 群から CompanyProfile を構築する。

    Pydantic v2 のバリデーションが失敗した場合は、行を特定できる ValueError を投げる。
    """
    payload: dict[str, Any] = {}
    payload.update(profile_kv)

    # data_source の既定値: 実データ取込なので "actual" を既定にする
    payload.setdefault("data_source", "actual")

    payload["sites"] = _validate_list(CompanySite, sites_rows, sheet=SITES_SHEET)
    payload["wait_time_rows"] = _validate_list(WaitTimeRow, wait_rows, sheet=WAIT_TIME_SHEET)
    payload["handling_time_rows"] = _validate_list(
        HandlingTimeRow, handling_rows, sheet=HANDLING_TIME_SHEET
    )
    payload["kpi_history"] = _validate_list(KpiHistoryEntry, kpi_rows, sheet=KPI_HISTORY_SHEET)

    try:
        return CompanyProfile.model_validate(payload)
    except ValidationError as e:
        raise ValueError(_format_validation_error(e, sheet=PROFILE_SHEET)) from e


def _validate_list(
    model_cls: Any,
    rows: list[dict[str, Any]],
    sheet: str,
) -> list[Any]:
    """各行を Pydantic モデルにバリデーションする。失敗時は行番号付き ValueError。"""
    validated: list[Any] = []
    for row_idx, record in enumerate(rows, start=3):  # 表形式は 3 行目以降がデータ
        try:
            validated.append(model_cls.model_validate(record))
        except ValidationError as e:
            raise ValueError(
                f"シート '{sheet}' 行 {row_idx} のバリデーションに失敗: "
                f"{_format_validation_error(e, sheet=sheet)}"
            ) from e
    return validated


def _strip_marker(s: str) -> str:
    """項目名から '[必須]' '[任意]' マーカーを削除する。"""
    for marker in ("[必須]", "[任意]"):
        s = s.replace(marker, "")
    return s


def _format_validation_error(e: ValidationError, sheet: str) -> str:
    """ValidationError を人間が読める形式に整形する。"""
    parts: list[str] = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"])
        msg = err["msg"]
        parts.append(f"  - {loc}: {msg}")
    return f"シート '{sheet}': バリデーションエラー\n" + "\n".join(parts)
