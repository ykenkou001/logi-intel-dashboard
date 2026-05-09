"""輸送機関別 CO2 排出原単位（経産省・国交省共同ガイドライン公表値）。

出典:
    - 経済産業省・国土交通省「ロジスティクス分野におけるCO2排出量算定方法
      共同ガイドライン Ver.3.2」（令和5年6月）
      https://www.greenpartnership.jp/guideline_ver3_2.pdf
    - グリーン物流パートナーシップ会議 公表値
      https://www.greenpartnership.jp/co2

単位:
    g-CO2 / トンキロ（貨物 1 トンを 1 km 運ぶ際の CO2 排出量）

注意:
    - 営業用と自家用、車格（小型/普通/大型）で大きく異なる
    - モーダルシフト試算で使用するため、各モードの典型値を保持
    - Ver.3.1 → Ver.3.2 では「改良トンキロ法」の燃費基準達成考慮が主な変更点で、
      輸送機関別の典型値（モーダル比較用）は据え置き
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.static._freshness import Freshness, register


@dataclass(frozen=True)
class Co2EmissionFactors:
    """輸送機関別 CO2 排出原単位（g-CO2/トンキロ）。"""

    # 自動車（営業用）
    truck_small_commercial: float = 388  # 小型トラック 営業用（〜2t）
    truck_medium_commercial: float = 196  # 普通トラック 営業用（2-10t）
    truck_large_commercial: float = 76  # 大型トラック 営業用（10t〜）

    # 鉄道
    rail_freight: float = 21  # 鉄道貨物

    # 海運
    coastal_shipping: float = 39  # 内航海運（フェリー含む）

    # 航空
    air_freight: float = 1490  # 航空貨物（参考）


CO2_FACTORS = Co2EmissionFactors()

FRESHNESS = Freshness(
    label="CO2 排出原単位（共同ガイドライン Ver.3.2）",
    last_updated=date(2023, 6, 1),  # 共同ガイドライン Ver.3.2 発行月
    update_cadence="biennial",
    source_url="https://www.greenpartnership.jp/guideline_ver3_2.pdf",
    notes=(
        "経産省・国交省共同ガイドライン Ver.3.2（2023年6月）。"
        "Ver.3.0→3.1→3.2 のリリース実績から概ね 2 年間隔で改訂チェック。"
    ),
)
register("co2_factors", FRESHNESS)
