"""KPI 時系列トラッキング（Tier S2 / フェーズ5.5）。

CLO 月次レビューで「悪化中か / 計画線に乗っているか」を一目で判定するための
時系列ビュー。日次 `OperationKpiSnapshot` を月次にロールアップし、F2 標準化
スコア / J2 罠件数を月次スナップショットに保存・取得する。

設計方針:
    - 月次粒度のスナップショットは core/io/kpi_timeseries_store.py に保存
    - 既存 outputs/cockpit_snapshots/<id>/<yyyymmdd>.json を読みに行って月平均を計算
    - F2 / J2 はオプションでスナップショット時刻に再計算
    - 悪化判定は「3 ヶ月前との比較」と「3 ヶ月連続悪化」の二段構え
    - baseline 未確定（履歴 < 3 ヶ月）の場合は最古スナップショットを baseline に
"""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.export.citation import Citation, logistics_efficiency_law_citation
from core.io.kpi_timeseries_store import (
    MonthlyKpiSnapshot,
    append_monthly_snapshot,
    load_monthly_snapshots,
)
from core.io.measure_run_store import MeasureExecutionRecord
from core.playbook.industry_packages import CompanyPackageOverride
from core.static._freshness import all_warnings
from core.static.sample_company import CompanyProfile

# ---------------------------------------------------------------------------
# 結果型
# ---------------------------------------------------------------------------


DeteriorationSeverity = Literal["watch", "warn", "critical"]
DeteriorationDirection = Literal["down", "up"]
BaselineSource = Literal["three_months_ago", "oldest_snapshot"]


class KpiDeteriorationAlert(BaseModel):
    """悪化アラート 1 件分。CLO 月次レビューで「ここ悪化中」を提示するための単位。"""

    model_config = ConfigDict(frozen=True)

    metric: str = Field(description="指標 ID（load_factor_pct 等）")
    metric_label: str = Field(description="日本語ラベル")
    severity: DeteriorationSeverity
    direction: DeteriorationDirection = Field(
        description="悪化方向: load_factor は down, wait_time は up",
    )
    consecutive_months: int = Field(
        ge=0,
        description="連続して悪化方向に推移している月数",
    )
    latest_value: float | None = None
    baseline_value: float | None = Field(
        default=None,
        description="比較基準（3 ヶ月前 or 最古スナップショット）",
    )
    baseline_source: BaselineSource = Field(
        default="three_months_ago",
        description=(
            "baseline の由来（v1.1 追加）。Codex 観点 5 対応。"
            "v1.2 以降で 'planned_value'（計画値線）を追加予定。"
        ),
    )
    delta_pct: float | None = Field(
        default=None,
        description="baseline 比 %（baseline が 0 の場合は None）",
    )
    message: str = Field(description="CLO 説明文（経営会議資料に貼れる長さ）")


class KpiTimeSeriesResult(BaseModel):
    """KPI 時系列の照会結果（Web / MCP / REST 共通）。"""

    model_config = ConfigDict(frozen=True)

    company_id: str
    months: list[MonthlyKpiSnapshot] = Field(
        description="year_month 昇順（古→新）。最大 24 ヶ月",
    )
    deteriorations: list[KpiDeteriorationAlert] = Field(
        default_factory=list,
        description="severity 重い順 (critical > warn > watch)",
    )
    industry_benchmark_logistics_cost_ratio: float | None = Field(
        default=None,
        description=(
            "v1.1 追加: 業界平均 物流コスト/売上比率（JILS 2021）。"
            "profile.jsic_code から解決した業種の平均値。Web で ReferenceLine 表示用。"
        ),
    )
    industry_category: str | None = Field(
        default=None,
        description=(
            "業種カテゴリ"
            "（manufacturing / wholesale / retail / chain_franchise / transport）"
        ),
    )
    citations: list[Citation] = Field(default_factory=list)
    freshness_warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 指標メタ
# ---------------------------------------------------------------------------


_METRIC_LABELS: dict[str, str] = {
    "load_factor_pct": "積載率(%)",
    "wait_time_avg_min": "荷待ち平均(分)",
    "wait_time_max_min": "荷待ち最大(分)",
    "handling_time_avg_min": "荷役等時間(分)",
    "co2_intensity_g_per_tonkm": "CO2原単位(g/t-km)",
    "logistics_cost_ratio": "物流コスト/売上比率(%)",
    "standardization_score": "F2標準化スコア",
    "waste_trap_count_high": "J2罠(high)",
}

_METRIC_DIRECTIONS: dict[str, DeteriorationDirection] = {
    "load_factor_pct": "down",  # 下がる方が悪
    "wait_time_avg_min": "up",
    "wait_time_max_min": "up",
    "handling_time_avg_min": "up",
    "co2_intensity_g_per_tonkm": "up",
    "logistics_cost_ratio": "up",
    "standardization_score": "down",
    "waste_trap_count_high": "up",
}

# 閾値テーブル: (watch, warn, critical) はそれぞれ baseline 比 % 絶対値 or 絶対差分。
#
# logistics_cost_ratio は Codex 観点 4 を反映し相対率ベース（業種別平均
# 1.8%〜4.8% の幅を吸収）。当初案の固定 pp は製造業 1.8% → 卸 4.8% で意味が
# 大きく変わるため、baseline 比 +15% / +30% / +50% を採用する。
_THRESHOLDS: dict[str, dict[str, float]] = {
    "load_factor_pct": {"watch_pt": 2, "warn_pt": 5, "critical_pt": 10},
    "wait_time_avg_min": {"watch_pct": 10, "warn_pct": 25, "critical_pct": 50},
    "wait_time_max_min": {"watch_pct": 10, "warn_pct": 25, "critical_pct": 50},
    "handling_time_avg_min": {"watch_pct": 10, "warn_pct": 25, "critical_pct": 50},
    "co2_intensity_g_per_tonkm": {"watch_pct": 5, "warn_pct": 10, "critical_pct": 20},
    "logistics_cost_ratio": {"watch_pct": 15, "warn_pct": 30, "critical_pct": 50},
    "standardization_score": {"watch_pt": 3, "warn_pt": 10, "critical_pt": 20},
    "waste_trap_count_high": {"watch_abs": 1, "warn_abs": 3, "critical_abs": 5},
}


# ---------------------------------------------------------------------------
# 日次 → 月次ロールアップ
# ---------------------------------------------------------------------------


def _outputs_root() -> Path:
    return Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs"))


def roll_up_daily_to_monthly(
    company_id: str,
    *,
    target_year_month: str,
) -> MonthlyKpiSnapshot | None:
    """outputs/cockpit_snapshots/<id>/*.json から target_year_month の月平均を計算する。

    指定月の日次 snapshot が 1 件もなければ None を返す。

    Returns:
        MonthlyKpiSnapshot (source="rolled_up_from_daily") or None
    """
    base = _outputs_root() / "cockpit_snapshots" / company_id
    if not base.is_dir():
        return None

    bucket: dict[str, list[float]] = defaultdict(list)
    over_2h_sum = 0
    sample_count = 0
    for p in sorted(base.glob("*.json")):
        try:
            d = datetime.strptime(p.stem, "%Y%m%d").date()
        except ValueError:
            continue
        ym = f"{d.year:04d}-{d.month:02d}"
        if ym != target_year_month:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        sample_count += 1
        for key in (
            "load_factor_pct",
            "wait_time_avg_min",
            "wait_time_max_min",
            "handling_time_avg_min",
            "co2_intensity_g_per_tonkm",
        ):
            val = data.get(key)
            if isinstance(val, (int, float)):
                bucket[key].append(float(val))
        if isinstance(data.get("over_2h_count_total"), int):
            over_2h_sum += data["over_2h_count_total"]

    if sample_count == 0:
        return None

    def _mean(key: str) -> float | None:
        vals = bucket.get(key)
        return statistics.fmean(vals) if vals else None

    return MonthlyKpiSnapshot(
        company_id=company_id,
        year_month=target_year_month,
        load_factor_pct=_mean("load_factor_pct"),
        wait_time_avg_min=_mean("wait_time_avg_min"),
        wait_time_max_min=_mean("wait_time_max_min"),
        handling_time_avg_min=_mean("handling_time_avg_min"),
        co2_intensity_g_per_tonkm=_mean("co2_intensity_g_per_tonkm"),
        source="rolled_up_from_daily",
        daily_sample_count=sample_count,
        recorded_at=datetime.now(),
    )


# ---------------------------------------------------------------------------
# スナップショット記録（F2/J2 込み）
# ---------------------------------------------------------------------------


_LOGISTICS_COST_KPI_METRIC = "logistics_cost_revenue_ratio_pct"


def _resolve_logistics_cost_ratio(
    profile: CompanyProfile,
    monthly_logistics_cost_jpy: int | None,
) -> float | None:
    """v1.1: 物流コスト/売上比率を入力 source の優先順で解決する。

    優先順:
        1. monthly_logistics_cost_jpy（当月物流コスト円・REST/MCP 引数）が与えられたら
           当月推計売上（年間売上 / 12）で割って当月比率を計算
        2. profile.kpi_history の `logistics_cost_revenue_ratio_pct` 最新 fy 値
           （Excel kpi_history シート / KpiHistoryEntry 経由・年次粒度）
        3. いずれも無ければ None

    Codex 観点 1（入力ソース）への対応。Excel 月次拡張は v2 持ち越し。
    """
    if monthly_logistics_cost_jpy is not None and profile.annual_revenue_jpy > 0:
        monthly_revenue = profile.annual_revenue_jpy / 12
        if monthly_revenue > 0:
            ratio = monthly_logistics_cost_jpy / monthly_revenue
            return min(max(ratio, 0.0), 1.0)

    # fallback: profile.kpi_history（年次）
    entries = [
        e for e in profile.kpi_history
        if e.metric == _LOGISTICS_COST_KPI_METRIC
    ]
    if entries:
        latest = max(entries, key=lambda e: e.fy)
        # unit が "%" なら 0-100 → 0-1 比率に変換
        return latest.value / 100 if latest.unit == "%" else latest.value
    return None


def record_monthly_snapshot(
    profile: CompanyProfile,
    year_month: str,
    *,
    override: CompanyPackageOverride | None = None,
    measure_runs: list[MeasureExecutionRecord] | None = None,
    monthly_logistics_cost_jpy: int | None = None,
    today: date | None = None,
    persist: bool = True,
) -> MonthlyKpiSnapshot:
    """profile + measure_runs から月次スナップショットを作成・保存する。

    F2 標準化スコア・J2 罠件数・v1.1 で追加した物流コスト比率を同時に計算して埋める。
    日次 cockpit_snapshots が存在すれば KPI 5 種は月平均で上書き、なければ None。

    Args:
        profile: 自社プロフィール
        year_month: YYYY-MM
        override: F2 計算用の個社差分
        measure_runs: J2 計算用の施策実行記録（None なら罠件数 0）
        monthly_logistics_cost_jpy: v1.1 追加・当月の物流コスト実績（円）。
            given なら年間売上 / 12 で割って当月比率を計算。未指定なら
            profile.kpi_history の最新 fy 値にフォールバック
        today: F2 期限切れ判定の基準日
        persist: True なら store に append。False は計算だけ返す
    """
    # 1. 日次ロールアップ（あれば）
    rolled = roll_up_daily_to_monthly(profile.company_id, target_year_month=year_month)

    # 2. F2 標準化スコア
    f2_score: float | None = None
    try:
        from core.analytics.standardization_score import compute_standardization_score

        f2_result = compute_standardization_score(profile, override, today=today)
        f2_score = f2_result.score
    except Exception:
        # 業種未解決 / IndustryPackage 未定義などは None で続行
        f2_score = None

    # 3. J2 罠件数
    high = medium = low = 0
    if measure_runs:
        from core.analytics.waste_trap import detect_waste_traps

        try:
            j2_result = detect_waste_traps(profile, measure_runs, today=today)
            high = j2_result.high_count
            medium = j2_result.medium_count
            low = j2_result.low_count
        except Exception:
            # measure_id 未解決等は 0 で続行
            high = medium = low = 0

    # 4. v1.1: 物流コスト/売上比率
    cost_ratio = _resolve_logistics_cost_ratio(profile, monthly_logistics_cost_jpy)

    snapshot = MonthlyKpiSnapshot(
        company_id=profile.company_id,
        year_month=year_month,
        load_factor_pct=rolled.load_factor_pct if rolled else None,
        wait_time_avg_min=rolled.wait_time_avg_min if rolled else None,
        wait_time_max_min=rolled.wait_time_max_min if rolled else None,
        handling_time_avg_min=rolled.handling_time_avg_min if rolled else None,
        co2_intensity_g_per_tonkm=rolled.co2_intensity_g_per_tonkm if rolled else None,
        logistics_cost_ratio=cost_ratio,
        standardization_score=f2_score,
        waste_trap_count_high=high,
        waste_trap_count_medium=medium,
        waste_trap_count_low=low,
        source="rolled_up_from_daily" if rolled else "manual_entry",
        daily_sample_count=rolled.daily_sample_count if rolled else 0,
        recorded_at=datetime.now(),
    )

    if persist:
        append_monthly_snapshot(snapshot)
    return snapshot


# ---------------------------------------------------------------------------
# 悪化検出
# ---------------------------------------------------------------------------


def _get_metric_value(snapshot: MonthlyKpiSnapshot, metric: str) -> float | None:
    val = getattr(snapshot, metric, None)
    if val is None:
        return None
    return float(val)


def _is_worsening(metric: str, current: float, previous: float) -> bool:
    """direction に応じて current が previous より悪化しているか判定。"""
    direction = _METRIC_DIRECTIONS[metric]
    return current < previous if direction == "down" else current > previous


def _count_consecutive_worsening(
    months: list[MonthlyKpiSnapshot],
    metric: str,
) -> int:
    """末尾から遡って何ヶ月連続で悪化方向にあるかを返す。"""
    values = [(_get_metric_value(m, metric)) for m in months]
    consecutive = 0
    # 末尾から 2 連続で値があるペアを比較
    for i in range(len(values) - 1, 0, -1):
        cur = values[i]
        prev = values[i - 1]
        if cur is None or prev is None:
            break
        if _is_worsening(metric, cur, prev):
            consecutive += 1
        else:
            break
    return consecutive


def _classify_severity(
    metric: str,
    latest: float,
    baseline: float,
    consecutive: int,
) -> DeteriorationSeverity | None:
    """閾値に従い severity を返す。悪化していなければ None。"""
    th = _THRESHOLDS.get(metric)
    if th is None:
        return None
    direction = _METRIC_DIRECTIONS[metric]
    diff = latest - baseline if direction == "up" else baseline - latest
    if diff <= 0:
        # 悪化していない
        if consecutive >= 3:
            return "watch"  # 連続悪化のみ拾う安全網
        return None

    # 1. ポイント差分閾値（pp）
    if "critical_pt" in th and diff >= th["critical_pt"]:
        return "critical"
    if "warn_pt" in th and diff >= th["warn_pt"]:
        return "warn"
    if "watch_pt" in th and diff >= th["watch_pt"]:
        return "watch"

    # 2. % 差分閾値
    if "critical_pct" in th and baseline > 0:
        pct = diff / baseline * 100
        if pct >= th["critical_pct"]:
            return "critical"
        if pct >= th["warn_pct"]:
            return "warn"
        if pct >= th["watch_pct"]:
            return "watch"

    # 3. 絶対差分閾値（罠件数）
    if "critical_abs" in th:
        if diff >= th["critical_abs"]:
            return "critical"
        if diff >= th["warn_abs"]:
            return "warn"
        if diff >= th["watch_abs"]:
            return "watch"

    # 4. 連続悪化救済（閾値未満でも 3 ヶ月続けば critical）
    if consecutive >= 3:
        return "critical"
    return None


def _build_message(
    metric: str,
    severity: DeteriorationSeverity,
    consecutive: int,
    latest: float | None,
    baseline: float | None,
    delta_pct: float | None,
) -> str:
    label = _METRIC_LABELS.get(metric, metric)
    parts: list[str] = []
    if latest is not None:
        parts.append(f"最新: {latest:.2f}")
    if baseline is not None:
        parts.append(f"基準: {baseline:.2f}")
    if delta_pct is not None:
        parts.append(f"差分: {delta_pct:+.1f}%")
    if consecutive >= 1:
        parts.append(f"連続悪化 {consecutive} ヶ月")
    detail = " / ".join(parts) if parts else "詳細不明"
    severity_label = {"watch": "注意", "warn": "警告", "critical": "重大"}[severity]
    return f"[{severity_label}] {label} が悪化しています — {detail}"


def detect_kpi_deterioration(
    months: list[MonthlyKpiSnapshot],
) -> list[KpiDeteriorationAlert]:
    """月次スナップショットから悪化アラートを生成する。

    判定ルール:
        - baseline = 3 ヶ月前のスナップショット（無ければ最古）
        - latest = 最新（末尾）スナップショット
        - 3 ヶ月連続で悪化方向に推移している場合は閾値未満でも critical 扱い

    v1.1（Codex 観点 5 対応）: baseline 由来を `baseline_source` で返し、UI で
    「3 ヶ月前比」or「最古比」を経営会議向けに明示できるようにする。計画値線
    （planned_value）は v1.2 で追加予定。
    """
    if len(months) < 2:
        return []

    sorted_months = sorted(months, key=lambda m: m.year_month)
    latest = sorted_months[-1]
    has_three_months_back = len(sorted_months) >= 4
    baseline = sorted_months[-4] if has_three_months_back else sorted_months[0]
    baseline_source: BaselineSource = (
        "three_months_ago" if has_three_months_back else "oldest_snapshot"
    )

    alerts: list[KpiDeteriorationAlert] = []
    for metric in _METRIC_LABELS:
        latest_val = _get_metric_value(latest, metric)
        baseline_val = _get_metric_value(baseline, metric)
        if latest_val is None or baseline_val is None:
            continue
        consecutive = _count_consecutive_worsening(sorted_months, metric)
        severity = _classify_severity(metric, latest_val, baseline_val, consecutive)
        if severity is None:
            continue
        delta_pct: float | None = None
        if baseline_val != 0:
            delta_pct = (latest_val - baseline_val) / baseline_val * 100
        alerts.append(
            KpiDeteriorationAlert(
                metric=metric,
                metric_label=_METRIC_LABELS[metric],
                severity=severity,
                direction=_METRIC_DIRECTIONS[metric],
                consecutive_months=consecutive,
                latest_value=latest_val,
                baseline_value=baseline_val,
                baseline_source=baseline_source,
                delta_pct=delta_pct,
                message=_build_message(
                    metric, severity, consecutive, latest_val, baseline_val, delta_pct,
                ),
            ),
        )

    severity_order = {"critical": 0, "warn": 1, "watch": 2}
    alerts.sort(key=lambda a: (severity_order[a.severity], a.metric))
    return alerts


# ---------------------------------------------------------------------------
# Public API（Result 統合）
# ---------------------------------------------------------------------------


def _resolve_industry_benchmark(
    profile: CompanyProfile | None,
) -> tuple[str | None, float | None]:
    """v1.1: profile.jsic_code から業種カテゴリと業界平均物流コスト比率を解決する。

    Returns:
        (industry_category, logistics_cost_ratio) のタプル。解決失敗時は (None, None)。
    """
    if profile is None:
        return None, None
    try:
        from core.static.industry_benchmarks import LOGISTICS_COST_RATIO
        from core.static.jsic import category_of

        category = category_of(profile.jsic_code)
        if category is None:
            return None, None
        return category, LOGISTICS_COST_RATIO.get(category)
    except Exception:
        return None, None


def build_kpi_timeseries(
    company_id: str,
    *,
    profile: CompanyProfile | None = None,
    limit_months: int = 24,
    from_year_month: str | None = None,
    to_year_month: str | None = None,
) -> KpiTimeSeriesResult:
    """KPI 時系列の照会 API（Web / MCP / REST 共通の戻り値）。

    Args:
        company_id: 対象企業 ID
        profile: v1.1 追加。業界平均物流コスト比率の解決に使う。未指定なら
            industry_benchmark_* フィールドは None
        limit_months: 末尾から何ヶ月分を返すか（既定 24）
        from_year_month / to_year_month: YYYY-MM 範囲フィルタ
    """
    months = load_monthly_snapshots(
        company_id,
        from_year_month=from_year_month,
        to_year_month=to_year_month,
        limit_months=limit_months,
    )
    deteriorations = detect_kpi_deterioration(months)
    industry_category, benchmark_ratio = _resolve_industry_benchmark(profile)
    return KpiTimeSeriesResult(
        company_id=company_id,
        months=months,
        deteriorations=deteriorations,
        industry_benchmark_logistics_cost_ratio=benchmark_ratio,
        industry_category=industry_category,
        citations=[logistics_efficiency_law_citation()],
        freshness_warnings=all_warnings(),
    )


def build_kpi_timeseries_summary(result: KpiTimeSeriesResult) -> str:
    """経営層向けの 1 段落サマリー。"""
    if not result.months:
        return "KPI 時系列データ未登録: 月次スナップショットを記録すると推移が見えるようになります"
    span = f"{result.months[0].year_month} 〜 {result.months[-1].year_month}"
    lines = [f"KPI 時系列: {len(result.months)} ヶ月分 ({span})"]
    if result.deteriorations:
        critical = sum(1 for a in result.deteriorations if a.severity == "critical")
        warn = sum(1 for a in result.deteriorations if a.severity == "warn")
        watch = sum(1 for a in result.deteriorations if a.severity == "watch")
        lines.append(
            f"悪化アラート: 重大 {critical} / 警告 {warn} / 注意 {watch} 件",
        )
    else:
        lines.append("悪化アラート: なし（計画線上 or 改善傾向）")
    return " | ".join(lines)


__all__ = [
    "KpiDeteriorationAlert",
    "KpiTimeSeriesResult",
    "build_kpi_timeseries",
    "build_kpi_timeseries_summary",
    "detect_kpi_deterioration",
    "record_monthly_snapshot",
    "roll_up_daily_to_monthly",
]
