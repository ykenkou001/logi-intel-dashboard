"""core/legal/screening.py の単体テスト。

判定対象:
    - 特定荷主（年間取扱貨物 9 万トン以上）
    - 特定連鎖化事業者（売上 1,000 億円以上）
    - 特定倉庫業者（年間入庫貨物 70 万トン以上）
    - 特定貨物自動車運送事業者等（保有車両 150 台以上）
"""

from __future__ import annotations

from datetime import date

from core.legal.screening import (
    CHAIN_FRANCHISE_THRESHOLD_JPY,
    SUBMISSION_DEADLINE,
    ScreeningInput,
    screen,
)


def _base_input(**overrides: object) -> ScreeningInput:
    """3 区分すべて該当なしのベース入力。"""
    base: dict[str, object] = {
        "industry": "other",
        "freight_tons_band": "lt_10k",
        "vehicles_band": "none",
        "warehouse_tons_band": "none",
        "annual_revenue_jpy": None,
        "clo_status": "not_considered",
        "is_chain_franchise": False,
    }
    base.update(overrides)
    return ScreeningInput(**base)  # type: ignore[arg-type]


# ─── 特定荷主の判定 ──────────────────────────────────────────


def test_shipper_applies_when_freight_ge_90k() -> None:
    """年間取扱貨物 9 万トン以上 → applies。"""
    result = screen(_base_input(industry="food", freight_tons_band="ge_90k"))
    shipper = next(f for f in result.findings if f.category == "shipper")
    assert shipper.verdict == "applies"
    assert result.applies_any is True
    assert result.overall_verdict == "applies"


def test_shipper_gray_zone_when_50k_90k() -> None:
    """5〜9 万トン帯 → gray_zone。"""
    result = screen(_base_input(industry="food", freight_tons_band="50k_90k"))
    shipper = next(f for f in result.findings if f.category == "shipper")
    assert shipper.verdict == "gray_zone"
    assert result.overall_verdict == "gray_zone"


def test_shipper_gray_zone_when_unknown() -> None:
    """貨物量不明 → gray_zone。"""
    result = screen(_base_input(industry="food", freight_tons_band="unknown"))
    shipper = next(f for f in result.findings if f.category == "shipper")
    assert shipper.verdict == "gray_zone"


def test_shipper_not_applies_when_lt_10k() -> None:
    """1 万トン未満 → not_applies。"""
    result = screen(_base_input(industry="food", freight_tons_band="lt_10k"))
    shipper = next(f for f in result.findings if f.category == "shipper")
    assert shipper.verdict == "not_applies"


def test_shipper_not_applies_for_transport_industry() -> None:
    """運送業を主たる業種とする企業は荷主区分の対象外。"""
    result = screen(_base_input(industry="transport", freight_tons_band="ge_90k"))
    shipper = next(f for f in result.findings if f.category == "shipper")
    assert shipper.verdict == "not_applies"


def test_shipper_not_applies_for_warehouse_industry() -> None:
    """倉庫業を主たる業種とする企業も荷主区分の対象外。"""
    result = screen(
        _base_input(industry="warehouse", freight_tons_band="ge_90k"),
    )
    shipper = next(f for f in result.findings if f.category == "shipper")
    assert shipper.verdict == "not_applies"


# ─── 特定連鎖化事業者の判定 ─────────────────────────────


def test_chain_franchise_not_included_when_flag_off() -> None:
    """連鎖化フラグ OFF → 連鎖化区分は findings に含まれない。"""
    result = screen(_base_input(is_chain_franchise=False))
    assert all(f.category != "chain_franchise" for f in result.findings)


def test_chain_franchise_applies_when_revenue_ge_threshold() -> None:
    """連鎖化フラグ ON + 売上 ≥ 閾値 → applies。"""
    result = screen(
        _base_input(
            industry="chain_franchise",
            is_chain_franchise=True,
            annual_revenue_jpy=CHAIN_FRANCHISE_THRESHOLD_JPY,
        ),
    )
    chain = next(f for f in result.findings if f.category == "chain_franchise")
    assert chain.verdict == "applies"


def test_chain_franchise_gray_zone_near_threshold() -> None:
    """連鎖化フラグ ON + 売上が閾値の 70〜100% → gray_zone。"""
    result = screen(
        _base_input(
            industry="chain_franchise",
            is_chain_franchise=True,
            annual_revenue_jpy=int(CHAIN_FRANCHISE_THRESHOLD_JPY * 0.8),
        ),
    )
    chain = next(f for f in result.findings if f.category == "chain_franchise")
    assert chain.verdict == "gray_zone"


def test_chain_franchise_gray_zone_when_revenue_missing() -> None:
    """連鎖化フラグ ON + 売上未入力 → gray_zone（精査必要）。"""
    result = screen(
        _base_input(
            industry="chain_franchise",
            is_chain_franchise=True,
            annual_revenue_jpy=None,
        ),
    )
    chain = next(f for f in result.findings if f.category == "chain_franchise")
    assert chain.verdict == "gray_zone"


def test_chain_franchise_not_applies_when_revenue_far_below_threshold() -> None:
    """連鎖化フラグ ON + 売上が閾値の 50% 未満 → not_applies。"""
    result = screen(
        _base_input(
            industry="chain_franchise",
            is_chain_franchise=True,
            annual_revenue_jpy=int(CHAIN_FRANCHISE_THRESHOLD_JPY * 0.3),
        ),
    )
    chain = next(f for f in result.findings if f.category == "chain_franchise")
    assert chain.verdict == "not_applies"


# ─── 特定倉庫業者の判定 ─────────────────────────────────


def test_warehouse_not_included_when_none() -> None:
    """営業倉庫なし → 倉庫区分は findings に含まれない。"""
    result = screen(_base_input(warehouse_tons_band="none"))
    assert all(f.category != "warehouse" for f in result.findings)


def test_warehouse_applies_when_ge_700k() -> None:
    """営業倉庫の年間入庫 70 万トン以上 → applies。"""
    result = screen(_base_input(warehouse_tons_band="ge_700k"))
    warehouse = next(f for f in result.findings if f.category == "warehouse")
    assert warehouse.verdict == "applies"
    assert result.overall_verdict == "applies"


def test_warehouse_gray_zone_when_100k_700k() -> None:
    """10〜70 万トン帯 → gray_zone。"""
    result = screen(_base_input(warehouse_tons_band="100k_700k"))
    warehouse = next(f for f in result.findings if f.category == "warehouse")
    assert warehouse.verdict == "gray_zone"


def test_warehouse_not_applies_when_lt_100k() -> None:
    """10 万トン未満 → not_applies。"""
    result = screen(_base_input(warehouse_tons_band="lt_100k"))
    warehouse = next(f for f in result.findings if f.category == "warehouse")
    assert warehouse.verdict == "not_applies"


# ─── 特定貨物自動車運送事業者等の判定 ─────────────────


def test_freight_transport_not_included_when_none() -> None:
    """車両保有なし → 運送区分は findings に含まれない。"""
    result = screen(_base_input(vehicles_band="none"))
    assert all(f.category != "freight_transport" for f in result.findings)


def test_freight_transport_applies_when_ge_150() -> None:
    """保有車両 150 台以上 → applies。"""
    result = screen(_base_input(vehicles_band="ge_150"))
    transport = next(
        f for f in result.findings if f.category == "freight_transport"
    )
    assert transport.verdict == "applies"


def test_freight_transport_gray_zone_when_50_150() -> None:
    """50〜150 台帯 → gray_zone。"""
    result = screen(_base_input(vehicles_band="50_150"))
    transport = next(
        f for f in result.findings if f.category == "freight_transport"
    )
    assert transport.verdict == "gray_zone"


def test_freight_transport_not_applies_when_lt_50() -> None:
    """50 台未満 → not_applies。"""
    result = screen(_base_input(vehicles_band="lt_50"))
    transport = next(
        f for f in result.findings if f.category == "freight_transport"
    )
    assert transport.verdict == "not_applies"


# ─── 複数該当 + 注意事項 ────────────────────────────────────


def test_multi_category_applies() -> None:
    """大手小売 + 自社倉庫 + 自社配送 → 3 区分すべて該当。"""
    result = screen(
        _base_input(
            industry="retail",
            freight_tons_band="ge_90k",
            vehicles_band="ge_150",
            warehouse_tons_band="ge_700k",
        ),
    )
    applies_cats = {f.category for f in result.findings if f.verdict == "applies"}
    assert applies_cats == {"shipper", "warehouse", "freight_transport"}
    assert result.overall_verdict == "applies"


def test_note_added_when_applies_but_clo_not_considered() -> None:
    """対象に該当するが CLO 未検討 → 警告ノートが追加される。"""
    result = screen(
        _base_input(
            industry="food",
            freight_tons_band="ge_90k",
            clo_status="not_considered",
        ),
    )
    assert any("未検討" in n for n in result.notes)


def test_no_warning_note_when_clo_appointed() -> None:
    """CLO 既選任 → 「未検討」警告ノートは出ない。"""
    result = screen(
        _base_input(
            industry="food",
            freight_tons_band="ge_90k",
            clo_status="appointed",
        ),
    )
    assert all("未検討" not in n for n in result.notes)


# ─── カウントダウン ────────────────────────────────────────


def test_days_until_deadline_uses_injected_today() -> None:
    """today 注入時、`SUBMISSION_DEADLINE - today` の日数が返る。"""
    today = date(2026, 1, 1)
    result = screen(_base_input(), today=today)
    assert result.days_until_deadline == (SUBMISSION_DEADLINE - today).days


def test_days_until_deadline_can_be_negative_after_deadline() -> None:
    """期限後は負数を返す（UI 側で表示制御する想定）。"""
    today = date(2027, 1, 1)
    result = screen(_base_input(), today=today)
    assert result.days_until_deadline < 0


# ─── overall_verdict の集約 ────────────────────────────────


def test_overall_verdict_not_applies_when_all_negative() -> None:
    """すべて not_applies → overall も not_applies。"""
    result = screen(_base_input())  # 全て none/閾値未満
    assert result.overall_verdict == "not_applies"


def test_overall_verdict_gray_zone_when_only_gray() -> None:
    """gray_zone のみ → overall は gray_zone。"""
    result = screen(_base_input(industry="food", freight_tons_band="50k_90k"))
    assert result.overall_verdict == "gray_zone"
