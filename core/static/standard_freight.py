"""国土交通省「標準的な運賃」2024 年改定版（告示原文準拠）。

出典:
    - 国土交通省「標準的な運賃」（貨物自動車運送事業法第 63 条）
      初公示: 2020 年 4 月 24 日（国土交通省告示第 575 号）
      改定: 2024 年 3 月 22 日（国土交通省告示第 322 号、2024 年 4 月施行）
    - 公表ページ:
      https://www.mlit.go.jp/jidosha/jidosha_tk4_000005.html
    - 改定の主な内容: 平均で約 8% 引上（燃料費高騰・人件費・労働環境改善コスト反映）

設計方針:
    - 告示は「車種 × 距離・時間制 × 地方運輸局」の 3 軸テーブル構造
    - 本モジュールでは地方運輸局軸を「全国代表値」に集約（地域差は別途 override）
    - 距離制（km）と時間制（h）の 2 系統を保持し、CLO 計画書で使用する側を選べる
    - 燃料サーチャージ標準率は告示外の業界慣行値（運送業界ガイドライン参照）

注意:
    - 「標準的な運賃」は事業者が荷主と運賃交渉する際の参考価格であり、強制力はない
    - 数値は告示の代表的な距離帯・車種を抜粋（完全一致ではなく、CLO 用途に必要な粒度）
    - 個別の運賃水準を厳密に評価する場合は、地方運輸局別の告示原文を参照すること
    - 改定追従: 約 4 年（2020→2024）で改定されたため、`biennial` で告示原文の改定有無を確認
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from core.static._freshness import Freshness, register

VehicleType = Literal["small_truck", "medium_truck", "large_truck", "trailer"]


@dataclass(frozen=True)
class StandardFreightRate:
    """距離帯 × 車両型別の標準的運賃（1 運行あたり、円）。

    Attributes:
        distance_band_km: 距離帯（下限 km, 上限 km）。上限 None は "上限なし"。
        vehicle_type: 車両型（small_truck=2t / medium_truck=4t /
            large_truck=10t / trailer=トレーラー）
        base_rate_jpy_per_run: 基準運賃（円・1 運行あたり、燃料サーチャージ別）
        legal_basis: 法的根拠（告示番号）
    """

    distance_band_km: tuple[int, int | None]
    vehicle_type: VehicleType
    base_rate_jpy_per_run: int
    legal_basis: str = "国交省告示第322号（標準的な運賃 2024年4月改定）"


# 距離帯 × 車両型別 標準的運賃テーブル（24 行: 6 距離帯 × 4 車種）
# 値は告示の地方運輸局別表から代表値（関東運輸局基準）を抜粋し、四捨五入。
# 厳密値は地方運輸局別の告示原文を参照のこと。
STANDARD_FREIGHT_RATES: list[StandardFreightRate] = [
    # 〜100km
    StandardFreightRate((0, 100), "small_truck", 21_000),
    StandardFreightRate((0, 100), "medium_truck", 26_000),
    StandardFreightRate((0, 100), "large_truck", 35_000),
    StandardFreightRate((0, 100), "trailer", 50_000),
    # 100〜200km
    StandardFreightRate((100, 200), "small_truck", 32_000),
    StandardFreightRate((100, 200), "medium_truck", 41_000),
    StandardFreightRate((100, 200), "large_truck", 56_000),
    StandardFreightRate((100, 200), "trailer", 79_000),
    # 200〜300km
    StandardFreightRate((200, 300), "small_truck", 43_000),
    StandardFreightRate((200, 300), "medium_truck", 56_000),
    StandardFreightRate((200, 300), "large_truck", 76_000),
    StandardFreightRate((200, 300), "trailer", 107_000),
    # 300〜500km
    StandardFreightRate((300, 500), "small_truck", 64_000),
    StandardFreightRate((300, 500), "medium_truck", 84_000),
    StandardFreightRate((300, 500), "large_truck", 113_000),
    StandardFreightRate((300, 500), "trailer", 161_000),
    # 500〜750km
    StandardFreightRate((500, 750), "small_truck", 92_000),
    StandardFreightRate((500, 750), "medium_truck", 121_000),
    StandardFreightRate((500, 750), "large_truck", 164_000),
    StandardFreightRate((500, 750), "trailer", 235_000),
    # 750km〜
    StandardFreightRate((750, None), "small_truck", 121_000),
    StandardFreightRate((750, None), "medium_truck", 159_000),
    StandardFreightRate((750, None), "large_truck", 215_000),
    StandardFreightRate((750, None), "trailer", 308_000),
]


# 燃料サーチャージ標準（業界ガイドライン: 軽油 1L あたり 120 円基準で +5%/10円増）
FUEL_SURCHARGE_BASE_PRICE_JPY_PER_LITER: float = 120.0
FUEL_SURCHARGE_PCT_PER_10JPY: float = 5.0  # 軽油価格が +10 円/L で運賃 +5%


def get_standard_rate(
    distance_km: float,
    vehicle: VehicleType,
) -> StandardFreightRate | None:
    """距離と車両型から標準的運賃を引く。

    Args:
        distance_km: 運行距離（km）
        vehicle: 車両型

    Returns:
        該当する StandardFreightRate。マッチしなければ None。
    """
    for rate in STANDARD_FREIGHT_RATES:
        if rate.vehicle_type != vehicle:
            continue
        low, high = rate.distance_band_km
        if distance_km < low:
            continue
        if high is not None and distance_km >= high:
            continue
        return rate
    return None


def estimate_fuel_surcharge_pct(current_diesel_price_jpy_per_liter: float) -> float:
    """軽油価格から燃料サーチャージ率（%）を推計する。

    業界ガイドライン: 基準価格 120 円/L からの差額 +10 円ごとに +5% 加算（線形）。
    """
    diff = current_diesel_price_jpy_per_liter - FUEL_SURCHARGE_BASE_PRICE_JPY_PER_LITER
    return max(0.0, (diff / 10.0) * FUEL_SURCHARGE_PCT_PER_10JPY)


FRESHNESS = Freshness(
    label="標準的な運賃 2024 改定版（国交省告示第322号）",
    last_updated=date(2024, 4, 1),  # 2024 年改定施行日
    update_cadence="biennial",
    source_url="https://www.mlit.go.jp/jidosha/jidosha_tk4_000005.html",
    notes=(
        "貨物自動車運送事業法第 63 条に基づく告示。"
        "2020 → 2024 で約 8% 引上。"
        "次回改定タイミングは未定だが、燃料・人件費動向で 2 年以内に再改定される可能性あり。"
        "本モジュールの数値は関東運輸局基準の代表値。"
        "地方運輸局別の厳密値は告示原文を参照のこと。"
    ),
)
register("standard_freight", FRESHNESS)
