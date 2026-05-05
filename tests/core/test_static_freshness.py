"""core/static/_freshness.py の単体テスト。"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from core.static import _freshness
from core.static._freshness import Freshness, all_freshness, all_warnings, register


@pytest.fixture(autouse=True)
def isolate_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """テスト間でレジストリを分離する。"""
    monkeypatch.setattr(_freshness, "_REGISTRY", {})


def _make(last: date, cadence: str = "annual", label: str = "test") -> Freshness:
    return Freshness(
        label=label,
        last_updated=last,
        update_cadence=cadence,  # type: ignore[arg-type]
        source_url="https://example.com",
    )


def test_freshness_age_calculation() -> None:
    """age プロパティが正しく経過日数を返す。"""
    f = _make(date.today() - timedelta(days=100))
    assert f.age.days == 100


def test_freshness_is_stale_true_when_overdue() -> None:
    """推奨間隔を超えると is_stale=True。"""
    f = _make(date.today() - timedelta(days=400))  # 年次なら 365 日超で stale
    assert f.is_stale is True


def test_freshness_is_stale_false_when_fresh() -> None:
    """推奨間隔内なら is_stale=False。"""
    f = _make(date.today() - timedelta(days=100))
    assert f.is_stale is False


def test_freshness_warning_text_only_when_stale() -> None:
    """古いときだけ警告メッセージが返る。"""
    fresh = _make(date.today() - timedelta(days=10))
    stale = _make(date.today() - timedelta(days=400))
    assert fresh.warning_text() is None
    assert stale.warning_text() is not None
    assert "test" in stale.warning_text()  # type: ignore[operator]


def test_register_and_get() -> None:
    """register/get がレジストリに登録・取得できる。"""
    f = _make(date.today())
    register("k1", f)
    assert _freshness.get("k1") is f


def test_all_warnings_filters_only_stale() -> None:
    """all_warnings は古いものだけを返す。"""
    register("fresh", _make(date.today(), label="fresh-label"))
    register(
        "stale",
        _make(date.today() - timedelta(days=400), label="stale-label"),
    )
    warnings = all_warnings()
    assert len(warnings) == 1
    assert "stale-label" in warnings[0]


def test_all_freshness_returns_copy() -> None:
    """all_freshness が registry のコピーを返す（外部から書き換え不可）。"""
    register("k", _make(date.today()))
    result = all_freshness()
    result["new"] = _make(date.today())  # 戻り値を書き換えてもレジストリは不変
    assert "new" not in _freshness._REGISTRY


def test_quinquennial_cadence() -> None:
    """5年間隔（quinquennial）の閾値が 1825 日。"""
    f = _make(date.today() - timedelta(days=1900), cadence="quinquennial")
    assert f.is_stale is True
    f2 = _make(date.today() - timedelta(days=1000), cadence="quinquennial")
    assert f2.is_stale is False


def test_as_needed_cadence_almost_never_stale() -> None:
    """改正時のみ更新（as_needed）は数年経っても stale にならない。"""
    f = _make(date.today() - timedelta(days=1500), cadence="as_needed")
    assert f.is_stale is False
