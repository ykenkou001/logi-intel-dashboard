"""輸送機関別 CO2 排出原単位（環境省・国土交通省公表値）。

出典:
    - 国土交通省「ロジスティクス分野におけるCO2排出量算定方法 共同ガイドライン Ver.3.1」
      https://www.mlit.go.jp/seisakutokatsu/freight/seisakutokatsu_freight_tk1_000131.html
    - グリーン物流パートナーシップ会議 公表値

単位:
    g-CO2 / トンキロ（貨物 1 トンを 1 km 運ぶ際の CO2 排出量）

注意:
    - 営業用と自家用、車格（小型/普通/大型）で大きく異なる
    - モーダルシフト試算で使用するため、各モードの典型値を保持
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.static._freshness import Freshness, register


@dataclass(frozen=True)
class Co2EmissionFactors:
    """輸送機関別 CO2 排出原単位（g-CO2/トンキロ）。"""

    # 自動車（営業用）
    truck_small_commercial: float = 388     # 小型トラック 営業用（〜2t）
    truck_medium_commercial: float = 196    # 普通トラック 営業用（2-10t）
    truck_large_commercial: float = 76      # 大型トラック 営業用（10t〜）

    # 鉄道
    rail_freight: float = 21                # 鉄道貨物

    # 海運
    coastal_shipping: float = 39            # 内航海運（フェリー含む）

    # 航空
    air_freight: float = 1490               # 航空貨物（参考）


CO2_FACTORS = Co2EmissionFactors()

FRESHNESS = Freshness(
    label="CO2 排出原単位（輸送機関別）",
    last_updated=date(2024, 3, 31),  # 2024年度版ガイドライン
    update_cadence="annual",
    source_url=(
        "https://www.mlit.go.jp/seisakutokatsu/freight/"
        "seisakutokatsu_freight_tk1_000131.html"
    ),
    notes="国交省・経産省共同ガイドライン Ver.3.1。年次で改訂チェック。",
)
register("co2_factors", FRESHNESS)
