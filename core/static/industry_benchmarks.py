"""業界感覚レンジ（数値妥当性判定の基準値）。

CLO ツールの数値出力が業界感覚に照らして妥当か判定するための参照値。
verify-clo-step スキル + submission_validator が共通参照する。

新規セッションで「営業利益率 7% は妥当」等の暗黙判定が継承されないリスクを排し、
バリデータがロジックでチェックできる形に整備したもの。

出典:
    - JILS 2021年度物流コスト調査
    - 自動車輸送統計年報
    - 経済センサス活動調査 2021 / 基礎調査 2024
    - 厚労省告示第367号（改善基準告示）
    - 国交省「物流2024年問題」資料
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from core.static._freshness import Freshness, register


@dataclass(frozen=True)
class Range:
    """数値範囲（低位・中位・高位）。"""

    low: float
    median: float
    high: float

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high


# ---- 業界別レンジ ----------------------------------------------------------

OPERATING_PROFIT_MARGIN_PCT: dict[str, Range] = {
    "manufacturing": Range(low=5.0, median=7.0, high=10.0),
    "wholesale": Range(low=1.5, median=2.0, high=3.0),
    "retail": Range(low=2.0, median=3.0, high=5.0),
    "chain_franchise": Range(low=2.0, median=3.5, high=4.0),
    "transport": Range(low=2.0, median=3.0, high=4.0),
}
"""営業利益率レンジ（％）。経済センサス活動調査 + 各社決算公表値ベース。"""


LOGISTICS_COST_RATIO: dict[str, float | None] = {
    "manufacturing": 0.018,
    "wholesale": 0.048,
    "retail": 0.031,
    "chain_franchise": 0.035,
    "transport": None,
    "other": None,
}
"""業界平均 物流コスト/売上比率（JILS 2021年度物流コスト調査）。

    transport は荷主ではないため比較対象外。
    benchmark.py の INDUSTRY_AVG_LOGISTICS_RATIO と同値（順次統合）。
"""


# ---- 積載率（自動車輸送統計年報） ------------------------------------------

LOAD_FACTOR_INDUSTRY_AVG_PCT: float = 38.0
"""営業用普通貨物車の業界平均積載率。"""

LOAD_FACTOR_TARGET_PCT: float = 50.0
"""国交省「目指すべき水準」。"""

LOAD_FACTOR_ANNUAL_IMPROVEMENT_PP: float = 1.5
"""業界実績の年間改善ペース（pp/年・標準）。複数施策同時実施時は最大 3pp/年。"""


# ---- ドライバー需給（改善基準告示 + 国交省2030年試算） ---------------------

NATIONAL_DRIVER_WORKERS_RANGE: Range = Range(
    low=1_000_000, median=1_700_000, high=3_000_000,
)
"""全国 道路貨物運送業の従業者数レンジ。verify_driver_gap で異常値検出に使う。"""

DRIVER_CAPACITY_REDUCTION_FACTOR: float = 0.135
"""改善基準告示2024適用後の実効稼働減少係数（13.5%）。"""

MLIT_2030_DRIVER_SHORTAGE_PCT: float = 34.1
"""国交省2030年試算の輸送力不足率。"""


# ---- 国家目標 --------------------------------------------------------------

NATIONAL_CO2_INTENSITY_REDUCTION_PCT: float = 23.4
"""物流分野 CO2 原単位削減目標（2030年/2013年比）。"""


# ---- 業界平均比の信頼性しきい値 --------------------------------------------
# 業界平均は経済センサスの 1 事業所あたり推計値（小規模事業所中心の母集団）。
# 大企業を比較すると桁外れになりやすいため、信頼性区分のしきい値を一元管理する。

REVENUE_VS_AVG_LARGE_SCALE_THRESHOLD_PCT: float = 200.0
"""200% 超 → 規模優位企業として参考表示（200% 以下は normal）。"""

REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT: float = 1000.0
"""1000% 超 → 比較対象母集団との乖離大（経営会議では数値非表示）。"""


# ---- 数値妥当性判定しきい値（提出前バリデータ用） -------------------------

@dataclass(frozen=True)
class PlanDraftSanityThresholds:
    """提出前バリデータが「業界感覚から外れすぎた値」を検出するしきい値。

    過大評価（重複考慮不足）と過小評価（投資判断却下レベル）の両方を捕捉する。
    """

    operating_profit_increase_max_ratio: float = 0.30
    """営業利益増加額 / 現状営業利益 がこの倍率を超えたら過大評価の疑い（30%）。"""

    npv_to_investment_max_multiple: float = 100.0
    """5年累積 NPV / 必要投資額 がこの倍率を超えたら過大評価の疑い。"""

    npv_to_investment_min_multiple: float = 0.5
    """5年累積 NPV / 必要投資額 がこの倍率を下回ったら投資判断却下レベル。"""

    profit_margin_lift_max_pp: float = 3.0
    """利益率改善幅（pp）がこのしきい値を超えたら極端値の疑い。"""

    OK_GUARANTEED: ClassVar[None] = None


SANITY = PlanDraftSanityThresholds()


# ---- KPI 到達可能性のしきい値 ---------------------------------------------

@dataclass(frozen=True)
class KpiReachabilityThresholds:
    """feasibility_check が「目標年に届くか」判定する年次改善ペース基準。"""

    annual_improvement_pp_green: float = 1.5
    """残り年数 × 1.5pp/年 が目標達成幅以上なら green（業界実績ペース）。"""

    annual_improvement_pp_yellow: float = 3.0
    """残り年数 × 3.0pp/年 が目標達成幅以上なら yellow（複数施策同時実施で達成余地）。"""


KPI_REACHABILITY = KpiReachabilityThresholds()


# ---- 業界感覚チェックのヘルパー --------------------------------------------

def is_operating_profit_margin_in_range(
    category: str, margin_pct: float,
) -> tuple[bool, Range | None]:
    """営業利益率が業界レンジ内に収まっているかを判定する。

    Returns:
        (within_range, range_def) — レンジ未登録業種は (True, None) を返す
    """
    range_def = OPERATING_PROFIT_MARGIN_PCT.get(category)
    if range_def is None:
        return True, None
    return range_def.contains(margin_pct), range_def


FRESHNESS = Freshness(
    label="業界感覚レンジ（営業利益率・積載率・ドライバー需給・妥当性しきい値）",
    last_updated=date(2026, 5, 3),
    update_cadence="biennial",
    source_url="https://www.logistics.or.jp/survey/logistics_cost.html",
    notes=(
        "JILS物流コスト調査・自動車輸送統計年報・経済センサス活動調査の業界感覚レンジ。"
        "次回更新は JILS 2023年度調査公表時を想定。"
    ),
)
register("industry_benchmarks", FRESHNESS)
