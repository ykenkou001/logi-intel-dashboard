"""core/static/standard_freight.py の単体テスト。

国交省告示「標準的な運賃 2024 改定版」のテーブルが構造的に正しく、
距離 × 車種のルックアップが期待通り動作することを確認する。
"""
from __future__ import annotations

import pytest

from core.static.standard_freight import (
    FRESHNESS,
    FUEL_SURCHARGE_BASE_PRICE_JPY_PER_LITER,
    STANDARD_FREIGHT_RATES,
    estimate_fuel_surcharge_pct,
    get_standard_rate,
)


def test_table_has_24_rows() -> None:
    """4 車種 × 6 距離帯 = 24 行。"""
    assert len(STANDARD_FREIGHT_RATES) == 24


def test_table_covers_4_vehicle_types() -> None:
    """全車種が 6 行ずつ存在する。"""
    vehicles = {r.vehicle_type for r in STANDARD_FREIGHT_RATES}
    assert vehicles == {"small_truck", "medium_truck", "large_truck", "trailer"}
    for v in vehicles:
        rows = [r for r in STANDARD_FREIGHT_RATES if r.vehicle_type == v]
        assert len(rows) == 6


def test_table_distance_bands_cover_known_ranges() -> None:
    """主要距離帯（〜100, 100-200, 200-300, 300-500, 500-750, 750〜）を網羅。"""
    bands = {r.distance_band_km for r in STANDARD_FREIGHT_RATES}
    assert (0, 100) in bands
    assert (100, 200) in bands
    assert (200, 300) in bands
    assert (300, 500) in bands
    assert (500, 750) in bands
    assert (750, None) in bands


def test_rates_are_monotonic_within_vehicle() -> None:
    """同一車種で距離帯が長いほど運賃が高い（単調増加）。"""
    for vehicle in ("small_truck", "medium_truck", "large_truck", "trailer"):
        rows = [r for r in STANDARD_FREIGHT_RATES if r.vehicle_type == vehicle]
        rows_sorted = sorted(rows, key=lambda r: r.distance_band_km[0])
        rates = [r.base_rate_jpy_per_run for r in rows_sorted]
        for i in range(1, len(rates)):
            assert rates[i] > rates[i - 1], f"{vehicle} の距離帯運賃が単調増加でない"


def test_rates_are_monotonic_across_vehicles() -> None:
    """同一距離帯で車種が大きいほど運賃が高い。"""
    order = ["small_truck", "medium_truck", "large_truck", "trailer"]
    by_band: dict[tuple[int, int | None], dict[str, int]] = {}
    for r in STANDARD_FREIGHT_RATES:
        by_band.setdefault(r.distance_band_km, {})[r.vehicle_type] = r.base_rate_jpy_per_run
    for band, rates in by_band.items():
        for i in range(1, len(order)):
            assert rates[order[i]] > rates[order[i - 1]], (
                f"距離帯 {band} で {order[i - 1]} < {order[i]} になっていない"
            )


@pytest.mark.parametrize(
    "distance_km,vehicle,expected_band",
    [
        (50, "small_truck", (0, 100)),
        (100, "medium_truck", (100, 200)),
        (250, "large_truck", (200, 300)),
        (450, "trailer", (300, 500)),
        (600, "medium_truck", (500, 750)),
        (1000, "large_truck", (750, None)),
    ],
)
def test_get_standard_rate_returns_correct_band(
    distance_km: float,
    vehicle: str,
    expected_band: tuple[int, int | None],
) -> None:
    rate = get_standard_rate(distance_km, vehicle)  # type: ignore[arg-type]
    assert rate is not None
    assert rate.distance_band_km == expected_band
    assert rate.vehicle_type == vehicle


def test_get_standard_rate_returns_none_for_negative_distance() -> None:
    """負の距離はマッチしない。"""
    assert get_standard_rate(-1, "medium_truck") is None


def test_fuel_surcharge_at_base_price_is_zero() -> None:
    """基準価格 120 円/L ではサーチャージ 0%。"""
    pct = estimate_fuel_surcharge_pct(FUEL_SURCHARGE_BASE_PRICE_JPY_PER_LITER)
    assert pct == 0.0


def test_fuel_surcharge_increases_with_price() -> None:
    """軽油価格が +20 円で +10%、+40 円で +20%（線形）。"""
    pct_plus20 = estimate_fuel_surcharge_pct(140.0)
    pct_plus40 = estimate_fuel_surcharge_pct(160.0)
    assert pct_plus20 == pytest.approx(10.0)
    assert pct_plus40 == pytest.approx(20.0)


def test_fuel_surcharge_below_base_is_zero() -> None:
    """基準価格を下回ってもマイナスにはならない（0% にクランプ）。"""
    assert estimate_fuel_surcharge_pct(100.0) == 0.0


def test_freshness_label_and_url() -> None:
    """鮮度メタデータが正しく登録されている。"""
    assert "標準的な運賃" in FRESHNESS.label
    assert "mlit.go.jp" in FRESHNESS.source_url
    assert FRESHNESS.update_cadence == "biennial"


def test_legal_basis_references_2024_revision() -> None:
    """全レコードの legal_basis に 2024 改定が明示されている。"""
    for r in STANDARD_FREIGHT_RATES:
        assert "2024" in r.legal_basis
