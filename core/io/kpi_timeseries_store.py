"""月次 KPI スナップショットの永続化（outputs/kpi_timeseries/<id>.jsonl）。

Tier S2 / フェーズ5.5 — `OperationKpiSnapshot` 日次データを月次にロールアップした
スナップショット、または手入力された月次 KPI を保存する。F2 標準化スコア /
J2 罠件数の推移も同 store に乗せる。

設計方針:
    - decision_log_store.py の jsonl + S3 backend + lazy import パターンを踏襲
    - append-only。同一 year_month を再保存するときは追記し、load 時に
      recorded_at 最大のレコードを採用する（行を書き換えない）
    - jsonl 1 行 = MonthlyKpiSnapshot 1 件
    - S3 backend (LOGI_STORAGE_BACKEND=s3) のとき outputs/kpi_timeseries/<id>.jsonl
      を S3 に複製・取得
"""

from __future__ import annotations

import contextlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# ---------------------------------------------------------------------------
# データモデル
# ---------------------------------------------------------------------------


class MonthlyKpiSnapshot(BaseModel):
    """1 ヶ月分の KPI スナップショット。

    `OperationKpiSnapshot` 日次の月平均、または Excel `kpi_history` シート由来の
    月次入力値を統一形式で保持する。`source` で由来を区別する。
    """

    model_config = ConfigDict(frozen=True)

    company_id: str
    year_month: str = Field(
        description="ISO 年月 YYYY-MM",
    )

    # KPI 5 種（cockpit と同形）
    load_factor_pct: float | None = Field(default=None, ge=0, le=100)
    wait_time_avg_min: float | None = Field(default=None, ge=0)
    wait_time_max_min: float | None = Field(default=None, ge=0)
    handling_time_avg_min: float | None = Field(default=None, ge=0)
    co2_intensity_g_per_tonkm: float | None = Field(default=None, ge=0)

    # 物流コスト/売上比率（v1.1 追加・0-1 の比率。例: 0.048 が 4.8%）
    logistics_cost_ratio: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description=(
            "物流コスト/売上比率（0-1）。JILS 物流コスト調査の業種別平均と比較する。"
            "v1.1 では (a) 当月の月次物流コスト入力 / (b) profile.kpi_history の最新 fy "
            "値 / (c) None の優先順で埋まる。"
        ),
    )

    # F2 標準化スコア
    standardization_score: float | None = Field(default=None, ge=0, le=100)

    # J2 罠件数（severity 別）
    waste_trap_count_high: int = Field(default=0, ge=0)
    waste_trap_count_medium: int = Field(default=0, ge=0)
    waste_trap_count_low: int = Field(default=0, ge=0)

    # メタ
    source: Literal["rolled_up_from_daily", "manual_entry", "merged"] = Field(
        default="rolled_up_from_daily",
        description="由来: 日次ロールアップ / 手入力 / 合成",
    )
    daily_sample_count: int = Field(
        default=0,
        ge=0,
        description="ロールアップ元の日次サンプル数（manual_entry 時は 0）",
    )
    recorded_at: datetime = Field(
        description="スナップショット生成時刻（重複時の最新判定に使う）",
    )

    def model_post_init(self, __context: object) -> None:  # pragma: no cover - guard
        if not YEAR_MONTH_PATTERN.match(self.year_month):
            raise ValueError(f"year_month must match YYYY-MM: {self.year_month!r}")


# ---------------------------------------------------------------------------
# パス解決
# ---------------------------------------------------------------------------


def _outputs_root() -> Path:
    return Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs"))


def _kpi_timeseries_path(company_id: str) -> Path:
    return _outputs_root() / "kpi_timeseries" / f"{company_id}.jsonl"


def _s3_key(company_id: str) -> str:
    return f"kpi_timeseries/{company_id}.jsonl"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def append_monthly_snapshot(snapshot: MonthlyKpiSnapshot) -> Path:
    """月次スナップショットを jsonl に append する。

    同一 year_month の旧レコードは削除しない。load 時に recorded_at 最大が採用される。
    S3 backend 利用時は append 前に S3 既存を local に同期し、append 後に publish する
    （decision_log_store の Lambda コールドスタート対策と同じ）。
    """
    path = _kpi_timeseries_path(snapshot.company_id)
    _sync_local_from_s3_if_needed(path, s3_key=_s3_key(snapshot.company_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(snapshot.model_dump_json())
        fp.write("\n")
    _maybe_publish_to_s3(path)
    return path


def load_monthly_snapshots(
    company_id: str,
    *,
    from_year_month: str | None = None,
    to_year_month: str | None = None,
    limit_months: int | None = None,
) -> list[MonthlyKpiSnapshot]:
    """月次スナップショットを year_month 昇順で返す。

    同一 year_month が複数あれば recorded_at 最大の 1 件を採用する（append-only ログの解釈）。

    Args:
        company_id: 対象企業 ID
        from_year_month / to_year_month: YYYY-MM 範囲フィルタ（両端含む）
        limit_months: 末尾から N ヶ月分のみ返す（None 無制限。可視化の 24 ヶ月ウィンドウ用）
    """
    raw = _read_jsonl_text(
        _kpi_timeseries_path(company_id),
        s3_key=_s3_key(company_id),
    )
    if raw is None:
        return []

    latest_per_month: dict[str, MonthlyKpiSnapshot] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            snap = MonthlyKpiSnapshot.model_validate_json(line)
        except (ValueError, TypeError):
            continue
        existing = latest_per_month.get(snap.year_month)
        if existing is None or snap.recorded_at > existing.recorded_at:
            latest_per_month[snap.year_month] = snap

    snapshots = sorted(latest_per_month.values(), key=lambda s: s.year_month)

    if from_year_month is not None:
        snapshots = [s for s in snapshots if s.year_month >= from_year_month]
    if to_year_month is not None:
        snapshots = [s for s in snapshots if s.year_month <= to_year_month]
    if limit_months is not None and limit_months > 0:
        snapshots = snapshots[-limit_months:]
    return snapshots


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _read_jsonl_text(path: Path, *, s3_key: str) -> str | None:
    s3_data = _maybe_fetch_from_s3(s3_key)
    if s3_data is not None:
        return s3_data
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _sync_local_from_s3_if_needed(path: Path, *, s3_key: str) -> None:
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return
    remote = _maybe_fetch_from_s3(s3_key)
    if remote is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(remote, encoding="utf-8")


def _maybe_publish_to_s3(path: Path) -> None:
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return
    from core.storage import get_storage

    with contextlib.suppress(Exception):
        get_storage().publish(path)


def _maybe_fetch_from_s3(key: str) -> str | None:
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return None
    from core.storage import get_storage

    storage = get_storage()
    data = storage.read_bytes(key)
    return data.decode("utf-8") if data is not None else None


__all__ = [
    "MonthlyKpiSnapshot",
    "append_monthly_snapshot",
    "load_monthly_snapshots",
]
