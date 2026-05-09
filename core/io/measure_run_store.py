"""施策実行記録の永続化（outputs/measure_runs/<company_id>.json）。

MeasureExecutionRecord を waste_trap.py から共通 I/O 層に昇格させ、
「誰が・いつ・どの施策を実行・見直したか」を JSON ファイルで追跡する。

設計方針:
    - company_store.py と同じ構造（base_dir は実行時解決、S3 backend 対応）。
    - ファイル形式: JSON 配列 [{...}, ...]（append ごとに追記）。
    - 同一 measure_id でも複数回 append 可。最新の実績を保持しながら
      経緯を全件追跡するため、重複除去は呼出側の判断に委ねる。
    - LOGI_STORAGE_BACKEND=s3 のときは S3 への複製も行う（Lambda 対応）。
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_RUNS_DIR = Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs")) / "measure_runs"

# ---------------------------------------------------------------------------
# 型定義（waste_trap.py から昇格）
# ---------------------------------------------------------------------------

TrapSeverity = Literal["low", "medium", "high"]

RootCause = Literal[
    "scale_misfit",  # 規模不適合
    "resource_missing",  # 必要リソース不足
    "governance_gap",  # ガバナンス未整備
    "wrong_kpi",  # KPI 設計の誤り
    "external_factor",  # 燃料急騰等の外部要因
    "data_quality",  # データ品質問題
    "adoption_resistance",  # 現場の抵抗
    "implementation_quality",  # 実装品質
    "unknown",
]


# ---------------------------------------------------------------------------
# 入力モデル（waste_trap.py から昇格）
# ---------------------------------------------------------------------------


class MeasureExecutionRecord(BaseModel):
    """施策の実行状況 1 件分。Override 4 分類 + 実績データの集約。

    frozen=True で不変にすることで、一度作成したレコードが分析途中に
    変更されるリスクを排除する（Codex 勧告⑤準拠）。
    """

    model_config = ConfigDict(frozen=True)

    measure_id: str = Field(description="ALL_MEASURES の measure_id を参照")
    started_on: date | None = Field(
        default=None,
        description="開始日（months_since_start 計算用）",
    )
    invested_jpy: int | None = Field(
        default=None,
        ge=0,
        description="投資実績（円）",
    )
    expected_effect_jpy: int | None = Field(
        default=None,
        description="期待効果（年・円・PlanDraft 由来）",
    )
    actual_effect_jpy: int | None = Field(
        default=None,
        description="実績効果（年・円）。未計測なら None で判定保留",
    )
    measured_count: int | None = Field(
        default=None,
        ge=0,
        description="計測サンプル数。<30 なら判定保留",
    )
    data_completeness: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="データ完全度（0.0〜1.0）。<0.5 なら判定保留",
    )
    seasonal_factor_active: bool = Field(
        default=False,
        description="季節性影響中（夏需要・年末等）",
    )
    external_event_active: bool = Field(
        default=False,
        description="外部要因（燃料急騰・災害等）の影響中",
    )
    payback_months_estimated: int | None = Field(
        default=None,
        ge=0,
        description="想定回収月数。経過月数 < この値なら判定保留",
    )
    suspected_root_cause: RootCause = Field(
        default="unknown",
        description="現場が疑う root cause（事前ヒアリング由来）",
    )


# ---------------------------------------------------------------------------
# 永続化ヘルパー
# ---------------------------------------------------------------------------


def _resolve_runs_dir(base_dir: Path | None) -> Path:
    """base_dir が None なら実行時に DEFAULT_RUNS_DIR を参照する。

    デフォルト引数は定義時にバインドされるため、テストで環境変数を
    差し替えても反映されない。None sentinel で実行時解決する。
    """
    return DEFAULT_RUNS_DIR if base_dir is None else base_dir


def _runs_path(company_id: str, base_dir: Path) -> Path:
    return base_dir / f"{company_id}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_runs(
    company_id: str,
    runs: list[MeasureExecutionRecord],
    base_dir: Path | None = None,
) -> Path:
    """施策実行記録リストを JSON ファイルに上書き保存する。

    既存ファイルを完全に置き換える。履歴を保持したい場合は append_run を使う。
    """
    resolved = _resolve_runs_dir(base_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    path = _runs_path(company_id, resolved)
    payload = [r.model_dump(mode="json") for r in runs]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _maybe_publish_to_s3(path)
    return path


def load_runs(
    company_id: str,
    base_dir: Path | None = None,
) -> list[MeasureExecutionRecord]:
    """保存済みの施策実行記録を全件取得する。ファイルが存在しない場合は空リストを返す。"""
    s3_data = _maybe_fetch_from_s3(company_id)
    if s3_data is not None:
        return _parse_runs(s3_data)

    resolved = _resolve_runs_dir(base_dir)
    path = _runs_path(company_id, resolved)
    if not path.is_file():
        return []
    return _parse_runs(path.read_text(encoding="utf-8"))


def append_run(
    company_id: str,
    run: MeasureExecutionRecord,
    base_dir: Path | None = None,
) -> Path:
    """施策実行記録を 1 件追加する。既存レコードは保持される。

    同一 measure_id でも追記可（経緯の全件追跡が目的）。
    """
    existing = load_runs(company_id, base_dir)
    return save_runs(company_id, [*existing, run], base_dir)


def merge_with_stored(
    company_id: str,
    incoming: list[MeasureExecutionRecord],
    base_dir: Path | None = None,
) -> list[MeasureExecutionRecord]:
    """受け取った runs と保存済み runs を結合して返す。

    incoming の measure_id が stored にあれば incoming で上書き（最新優先）、
    stored にしかない measure_id は kept として残す。新規の incoming も追加。
    重複排除は measure_id ベース、同一 measure_id は incoming 側を採用。
    """
    stored = load_runs(company_id, base_dir)
    stored_by_id: dict[str, MeasureExecutionRecord] = {r.measure_id: r for r in stored}
    incoming_by_id: dict[str, MeasureExecutionRecord] = {r.measure_id: r for r in incoming}
    merged = {**stored_by_id, **incoming_by_id}  # incoming が上書き
    return list(merged.values())


# ---------------------------------------------------------------------------
# 内部関数
# ---------------------------------------------------------------------------


def _parse_runs(raw: str) -> list[MeasureExecutionRecord]:
    data = json.loads(raw)
    return [MeasureExecutionRecord.model_validate(item) for item in data]


def _maybe_publish_to_s3(path: Path) -> None:
    """S3 backend 利用時はローカル書出後に複製。それ以外は no-op。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return
    import contextlib

    from core.storage import get_storage

    with contextlib.suppress(Exception):
        get_storage().publish(path)


def _maybe_fetch_from_s3(company_id: str) -> str | None:
    """S3 backend 利用時は measure_runs/<id>.json を S3 から取得。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return None
    from core.storage import get_storage

    storage = get_storage()
    data = storage.read_bytes(f"measure_runs/{company_id}.json")
    return data.decode("utf-8") if data is not None else None


__all__ = [
    "MeasureExecutionRecord",
    "RootCause",
    "TrapSeverity",
    "append_run",
    "load_runs",
    "merge_with_stored",
    "save_runs",
]
