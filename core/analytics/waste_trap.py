"""J2 罠スコア — 投資が回っていない施策を 6 軸セーフガード付きで検出する。

CLO の中長期計画書では「実施した施策」だけでなく「効果が出ていない施策」を
率直に経営会議に出す必要がある（物流効率化法の継続運用責任）。本モジュールは
施策の投資額・期待効果・実績を比較し、罠（waste trap）を検出する。

設計方針（plans/b-c-flickering-pixel.md §段階 c.6 J2 完全反映）:
    - 6 軸セーフガード（Codex 勧告④・誤検知抑止）:
        ① 立ち上げ期間が短い (months_since_start < 6)
        ② データ欠損 (data_completeness < 0.5)
        ③ サンプル数不足 (measured_count < min_sample_size)
        ④ 季節性影響中
        ⑤ 外部要因（燃料急騰等）
        ⑥ 投資回収前 (months_since_start < payback_months_estimated)
      → これらが当てはまる場合は trap_severity="low" 固定
    - root cause 分類は 9 種（Codex 勧告⑤で 3 種追加: data_quality /
      adoption_resistance / implementation_quality）
    - investment_freeze 推奨は high severity かつ
      root_cause in {scale_misfit, wrong_kpi, implementation_quality}

「actual_effect_jpy が None の場合」の扱い (Claude 単独判断):
    - 実績未計測なら detect 側で trap 判定をしない（severity=None で返す）
    - kpi_history からの自動逆算は次 PR の課題（複雑性回避のため初版では未実装）

入力ソース:
    - profile: CompanyProfile
    - measure_runs: list[MeasureExecutionRecord]（投資額・経過月数・実績効果等）
        MeasureExecutionRecord は core/io/measure_run_store.py で定義・永続化される。
        後方互換性のためここでも re-export する。
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from core.export.citation import Citation, logistics_efficiency_law_citation

# MeasureExecutionRecord / RootCause / TrapSeverity は I/O 層に昇格（フェーズ5.5 #0）。
# 後方互換性のため re-export する（既存 import を壊さない）。
from core.io.measure_run_store import (
    MeasureExecutionRecord,
    RootCause,
    TrapSeverity,
)
from core.playbook.measures import get_measure
from core.static._freshness import all_warnings
from core.static.sample_company import CompanyProfile

# ---------------------------------------------------------------------------
# 6 軸セーフガード閾値（Codex 議論で確定）
# ---------------------------------------------------------------------------

MIN_MONTHS_SINCE_START_FOR_JUDGMENT: int = 6
"""① 立ち上げ期間が短い場合のしきい値。<6 ヶ月は判定保留。"""

MIN_DATA_COMPLETENESS: float = 0.5
"""② データ欠損割合のしきい値。完全度 50% 未満は判定保留。"""

MIN_MEASURED_COUNT: int = 30
"""③ サンプル数のしきい値。<30 サンプルは統計的に判定不能。"""

# ---------------------------------------------------------------------------
# 効果判定の閾値
# ---------------------------------------------------------------------------

LOW_RATIO_HIGH_SEVERITY: float = 0.3
"""actual / invested が <= 0.3 で high severity。"""

MID_RATIO_MEDIUM_SEVERITY: float = 0.7
"""actual / invested が 0.3 < r < 0.7 で medium severity。"""

HIGH_EXPECTATION_RATIO: float = 2.0
"""high severity 確定の前提となる expected/invested しきい値。"""


# ---------------------------------------------------------------------------
# 戻り値モデル
# ---------------------------------------------------------------------------


class WasteTrapItem(BaseModel):
    """1 件の罠検出結果。"""

    model_config = ConfigDict(frozen=True)

    measure_id: str
    measure_name: str = Field(description="表示用名称（ALL_MEASURES から）")
    invested_jpy: int | None
    expected_effect_jpy: int | None
    actual_effect_jpy: int | None
    months_since_start: int | None
    trap_severity: TrapSeverity
    suspected_root_cause: RootCause
    suggested_remediation: str = Field(
        description="経営会議で次のアクションを決めるための推奨対応",
    )
    investment_freeze_recommended: bool = Field(
        description="高 severity かつ root_cause が要因型の場合 True",
    )
    safeguard_triggered: list[str] = Field(
        default_factory=list,
        description="6 軸セーフガードのうち発火した識別子（rationale 表示用）",
    )


class WasteTrapResult(BaseModel):
    """J2 罠スコア全体結果。"""

    model_config = ConfigDict(frozen=True)

    company_id: str
    items: list[WasteTrapItem]
    high_count: int
    medium_count: int
    low_count: int
    investment_freeze_count: int
    citations: list[Citation] = Field(default_factory=list)
    freshness_warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_waste_traps(
    profile: CompanyProfile,
    measure_runs: list[MeasureExecutionRecord],
    *,
    today: date | None = None,
) -> WasteTrapResult:
    """施策実行記録から罠を検出する。

    Args:
        profile: 自社プロフィール（将来の業種別調整・拡張のため受け取る）
        measure_runs: 施策実行記録一覧
        today: 経過月数計算の基準日（None なら今日）

    Returns:
        WasteTrapResult: 検出結果（severity 別件数 + items）
    """
    today_d = today or date.today()
    items: list[WasteTrapItem] = []
    for run in measure_runs:
        items.append(_evaluate_run(run, today_d))

    high = sum(1 for i in items if i.trap_severity == "high")
    medium = sum(1 for i in items if i.trap_severity == "medium")
    low = sum(1 for i in items if i.trap_severity == "low")
    freeze = sum(1 for i in items if i.investment_freeze_recommended)

    return WasteTrapResult(
        company_id=profile.company_id,
        items=items,
        high_count=high,
        medium_count=medium,
        low_count=low,
        investment_freeze_count=freeze,
        citations=[logistics_efficiency_law_citation()],
        freshness_warnings=all_warnings(),
    )


def build_waste_trap_summary(result: WasteTrapResult) -> str:
    """経営層向けの 1 段落サマリー。"""
    if not result.items:
        return "罠候補なし: 監視対象施策が未登録"
    lines = [
        f"罠候補: high {result.high_count} / medium {result.medium_count} "
        f"/ low {result.low_count} 件",
    ]
    if result.investment_freeze_count > 0:
        lines.append(
            f"投資凍結推奨: {result.investment_freeze_count} 件 (経営会議で再評価)",
        )
    high_items = [i for i in result.items if i.trap_severity == "high"]
    if high_items:
        ids = [i.measure_id for i in high_items[:3]]
        lines.append(f"high 例: {', '.join(ids)}")
    return " / ".join(lines)


# ---------------------------------------------------------------------------
# 評価ロジック
# ---------------------------------------------------------------------------


def _evaluate_run(
    run: MeasureExecutionRecord,
    today: date,
) -> WasteTrapItem:
    """単一施策実行記録の severity と推奨対応を判定する。"""
    measure = get_measure(run.measure_id)
    measure_name = measure.name if measure else run.measure_id
    months = _months_since(run.started_on, today)

    safeguards = _check_safeguards(run, months)
    if safeguards:
        # セーフガード発火 → low 固定 (Codex 勧告④)
        return WasteTrapItem(
            measure_id=run.measure_id,
            measure_name=measure_name,
            invested_jpy=run.invested_jpy,
            expected_effect_jpy=run.expected_effect_jpy,
            actual_effect_jpy=run.actual_effect_jpy,
            months_since_start=months,
            trap_severity="low",
            suspected_root_cause=run.suspected_root_cause,
            suggested_remediation=_remediation_for_safeguard(safeguards),
            investment_freeze_recommended=False,
            safeguard_triggered=safeguards,
        )

    severity = _calc_severity(run)
    freeze = _should_freeze_investment(severity, run.suspected_root_cause)
    remediation = _remediation_for_severity(
        severity=severity,
        root_cause=run.suspected_root_cause,
        measure_name=measure_name,
    )

    return WasteTrapItem(
        measure_id=run.measure_id,
        measure_name=measure_name,
        invested_jpy=run.invested_jpy,
        expected_effect_jpy=run.expected_effect_jpy,
        actual_effect_jpy=run.actual_effect_jpy,
        months_since_start=months,
        trap_severity=severity,
        suspected_root_cause=run.suspected_root_cause,
        suggested_remediation=remediation,
        investment_freeze_recommended=freeze,
        safeguard_triggered=[],
    )


def _check_safeguards(
    run: MeasureExecutionRecord,
    months: int | None,
) -> list[str]:
    """6 軸セーフガード（Codex 勧告④）。発火した識別子のリストを返す。

    1 つでも発火したら trap_severity を low 固定にする。
    """
    triggered: list[str] = []
    # ① 立ち上げ期間が短い (months 未指定もここに含む — 不明なら判定保留)
    if months is None or months < MIN_MONTHS_SINCE_START_FOR_JUDGMENT:
        triggered.append("ramp_up_period")
    # ② データ欠損
    if run.data_completeness is not None and run.data_completeness < MIN_DATA_COMPLETENESS:
        triggered.append("data_incomplete")
    # ③ サンプル数不足
    if run.measured_count is not None and run.measured_count < MIN_MEASURED_COUNT:
        triggered.append("insufficient_samples")
    # ④ 季節性
    if run.seasonal_factor_active:
        triggered.append("seasonal_factor")
    # ⑤ 外部要因
    if run.external_event_active:
        triggered.append("external_event")
    # ⑥ 投資回収前
    if (
        run.payback_months_estimated is not None
        and months is not None
        and months < run.payback_months_estimated
    ):
        triggered.append("before_payback")
    # actual 未計測 → 判定保留 (Claude 単独判断: kpi_history 逆算は次 PR)
    if run.actual_effect_jpy is None:
        triggered.append("actual_not_measured")
    return triggered


def _calc_severity(run: MeasureExecutionRecord) -> TrapSeverity:
    """セーフガード発火後の severity 計算。

    actual/invested 比 <= 0.3 かつ expected/invested >= 2.0 → high
    0.3 < ratio < 0.7 → medium
    それ以外 → low
    """
    invested = run.invested_jpy or 0
    actual = run.actual_effect_jpy or 0
    expected = run.expected_effect_jpy or 0
    if invested <= 0:
        return "low"
    actual_ratio = actual / invested
    expected_ratio = expected / invested
    if actual_ratio <= LOW_RATIO_HIGH_SEVERITY and expected_ratio >= HIGH_EXPECTATION_RATIO:
        return "high"
    if LOW_RATIO_HIGH_SEVERITY < actual_ratio < MID_RATIO_MEDIUM_SEVERITY:
        return "medium"
    return "low"


def _should_freeze_investment(
    severity: TrapSeverity,
    root_cause: RootCause,
) -> bool:
    """投資凍結推奨の判定。high かつ要因型 root cause のみ True。"""
    if severity != "high":
        return False
    return root_cause in {"scale_misfit", "wrong_kpi", "implementation_quality"}


def _remediation_for_safeguard(triggered: list[str]) -> str:
    """セーフガード発火時の推奨対応。"""
    if "actual_not_measured" in triggered:
        return "実績計測の整備を優先 (PoC データ取込・KPI モニタリング体制)"
    if "ramp_up_period" in triggered:
        return "立ち上げ期間中（6 ヶ月未満）— 評価は再計測後"
    if "data_incomplete" in triggered:
        return "データ欠損 50% 超 — 計測体制を整備してから再評価"
    if "insufficient_samples" in triggered:
        return "サンプル不足 (<30) — 計測継続"
    if "seasonal_factor" in triggered:
        return "季節性影響中 — 通常期データで再評価"
    if "external_event" in triggered:
        return "外部要因 (燃料急騰等) の影響中 — 環境正常化後に再評価"
    if "before_payback" in triggered:
        return "想定回収期間内 — 経過観察"
    return "判定保留"


def _remediation_for_severity(
    *,
    severity: TrapSeverity,
    root_cause: RootCause,
    measure_name: str,
) -> str:
    """severity と root_cause に応じた推奨対応。"""
    if severity == "high":
        if root_cause == "scale_misfit":
            return f"{measure_name}: 規模不適合のため施策中止を経営会議に上程"
        if root_cause == "wrong_kpi":
            return f"{measure_name}: KPI 設計を見直し、再立案"
        if root_cause == "implementation_quality":
            return f"{measure_name}: 実装品質を再点検 (PoC からやり直し検討)"
        if root_cause == "resource_missing":
            return f"{measure_name}: 必要リソースを補強した上で再評価"
        if root_cause == "governance_gap":
            return f"{measure_name}: 月次会議体・進捗ガバナンスを設計"
        if root_cause == "external_factor":
            return f"{measure_name}: 外部要因の影響を切り分け、定期見直し"
        if root_cause == "data_quality":
            return f"{measure_name}: 計測データの品質改善を優先"
        if root_cause == "adoption_resistance":
            return f"{measure_name}: 現場説明会・運用負荷軽減の打ち手"
        return f"{measure_name}: 経営会議で原因分析と方針決定"
    if severity == "medium":
        return f"{measure_name}: 効果が伸びていない — 月次レビューで原因特定"
    return f"{measure_name}: 監視継続"


def _months_since(started_on: date | None, today: date) -> int | None:
    """開始日から today までの経過月数（カレンダーベース・ざっくり）。"""
    if started_on is None:
        return None
    delta = today - started_on
    return max(0, delta.days // 30)


__all__ = [
    "HIGH_EXPECTATION_RATIO",
    "LOW_RATIO_HIGH_SEVERITY",
    "MID_RATIO_MEDIUM_SEVERITY",
    "MIN_DATA_COMPLETENESS",
    "MIN_MEASURED_COUNT",
    "MIN_MONTHS_SINCE_START_FOR_JUDGMENT",
    "MeasureExecutionRecord",
    "RootCause",
    "TrapSeverity",
    "WasteTrapItem",
    "WasteTrapResult",
    "build_waste_trap_summary",
    "detect_waste_traps",
]
