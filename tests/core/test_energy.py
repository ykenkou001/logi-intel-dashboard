"""core/clients/energy.py の単体テスト（gogo.gs スクレイパー）。"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core import cache
from core.clients.energy import (
    EnergyApiError,
    EnergyClient,
    _is_data_fresh_enough,
    _parse_gogogs_prices,
)


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """履歴 INSERT が実 DB に書かれないよう、テストごとに一時 DB を使う。"""
    monkeypatch.setattr(cache, "_DB_PATH", tmp_path / "test_cache.db")

_SAMPLE_HTML = """
<html><body>
  <div class="pref-price-panel">
    <div class="average"><label>レギュラー</label><div class="price">166.1</div></div>
    <div class="average"><label>軽油</label><div class="price">155.8</div></div>
    <div class="average"><label>灯油</label><div class="price">2,456.6</div></div>
    <span class="help">2026年4月30日（木）時点の平均価格</span>
  </div>
</body></html>
"""

_HTML_NO_PANEL = "<html><body><p>no panel here</p></body></html>"

_HTML_NO_PRICE = """
<html><body>
  <div class="pref-price-panel">
    <div class="average"><label>レギュラー</label><div class="price">---</div></div>
    <span class="help">2026年4月30日（木）時点</span>
  </div>
</body></html>
"""


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_CACHE_BYPASS", "1")


def test_parse_success() -> None:
    result = _parse_gogogs_prices(_SAMPLE_HTML)

    assert result["regular"] == pytest.approx(166.1)
    assert result["diesel"] == pytest.approx(155.8)
    assert result["kerosene"] == pytest.approx(2456.6)


def test_parse_date_format() -> None:
    result = _parse_gogogs_prices(_SAMPLE_HTML)

    assert result["date"] == "2026-04-30"


def test_parse_no_panel_raises() -> None:
    with pytest.raises(EnergyApiError, match="pref-price-panel"):
        _parse_gogogs_prices(_HTML_NO_PANEL)


def test_parse_missing_required_price_raises() -> None:
    with pytest.raises(EnergyApiError, match="レギュラー・軽油"):
        _parse_gogogs_prices(_HTML_NO_PRICE)


@pytest.mark.asyncio
async def test_get_fuel_prices_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("core.clients.energy.cache.get", lambda _key: None)
    monkeypatch.setattr("core.clients.energy.cache.store", lambda *_args: None)

    with patch(
        "core.clients.base.AsyncHTTPClient.get_html",
        new_callable=AsyncMock,
        return_value=_SAMPLE_HTML,
    ):
        async with EnergyClient() as client:
            result = await client.get_fuel_prices()

    assert result["regular"] == pytest.approx(166.1)
    assert result["date"] == "2026-04-30"
    assert result["source"] == "gogo.gs（全国平均・ユーザー申告集計）"


@pytest.mark.asyncio
async def test_get_fuel_prices_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """date が前日のフレッシュなキャッシュはそのまま返される。"""
    yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
    cached = {"regular": 160.0, "diesel": 150.0, "date": yesterday, "source": "gogo.gs"}
    monkeypatch.setattr("core.clients.energy.cache.get", lambda _key: cached)

    async with EnergyClient() as client:
        result = await client.get_fuel_prices()

    assert result is cached


@pytest.mark.asyncio
async def test_get_fuel_prices_records_history(monkeypatch: pytest.MonkeyPatch) -> None:
    """ライブ取得時に履歴テーブルへ自動 INSERT される。"""
    monkeypatch.setattr("core.clients.energy.cache.get", lambda _key: None)
    monkeypatch.setattr("core.clients.energy.cache.store", lambda *_args: None)

    with patch(
        "core.clients.base.AsyncHTTPClient.get_html",
        new_callable=AsyncMock,
        return_value=_SAMPLE_HTML,
    ):
        async with EnergyClient() as client:
            await client.get_fuel_prices()

    history = cache.get_fuel_price_history()
    assert len(history) == 1
    assert history[0]["date"] == "2026-04-30"
    assert history[0]["regular"] == pytest.approx(166.1)
    assert history[0]["source"] == "gogo.gs"


@pytest.mark.asyncio
async def test_get_fuel_prices_no_date_skips_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """日付が抽出できない HTML では履歴に追記しない。"""
    monkeypatch.setattr("core.clients.energy.cache.get", lambda _key: None)
    monkeypatch.setattr("core.clients.energy.cache.store", lambda *_args: None)

    no_date_html = """
    <html><body>
      <div class="pref-price-panel">
        <div class="average"><label>レギュラー</label><div class="price">166.1</div></div>
        <div class="average"><label>軽油</label><div class="price">155.8</div></div>
      </div>
    </body></html>
    """

    with patch(
        "core.clients.base.AsyncHTTPClient.get_html",
        new_callable=AsyncMock,
        return_value=no_date_html,
    ):
        async with EnergyClient() as client:
            await client.get_fuel_prices()

    assert cache.get_fuel_price_history() == []


# ---- データ鮮度チェック ----


def test_is_data_fresh_today() -> None:
    """date が今日 → fresh。"""
    today = _dt.date.today().isoformat()
    assert _is_data_fresh_enough({"date": today}) is True


def test_is_data_fresh_yesterday() -> None:
    """date が前日 → fresh（要件: 前日 or 前々日まで許容）。"""
    yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
    assert _is_data_fresh_enough({"date": yesterday}) is True


def test_is_data_fresh_day_before_yesterday() -> None:
    """date が前々日 → fresh（要件の境界値）。"""
    dby = (_dt.date.today() - _dt.timedelta(days=2)).isoformat()
    assert _is_data_fresh_enough({"date": dby}) is True


def test_is_data_fresh_three_days_old_is_stale() -> None:
    """date が 3 日前 → stale（要件超過）。"""
    three_ago = (_dt.date.today() - _dt.timedelta(days=3)).isoformat()
    assert _is_data_fresh_enough({"date": three_ago}) is False


def test_is_data_fresh_empty_date_is_stale() -> None:
    """date 空 → stale（再取得を強制）。"""
    assert _is_data_fresh_enough({"date": ""}) is False
    assert _is_data_fresh_enough({}) is False


def test_is_data_fresh_invalid_date_is_stale() -> None:
    """date 形式不正 → stale。"""
    assert _is_data_fresh_enough({"date": "invalid"}) is False


def test_is_data_fresh_future_date_is_stale() -> None:
    """date が未来日付（システム時刻ずれ等の異常値）→ stale。"""
    future = (_dt.date.today() + _dt.timedelta(days=1)).isoformat()
    assert _is_data_fresh_enough({"date": future}) is False


@pytest.mark.asyncio
async def test_get_fuel_prices_stale_cache_triggers_refetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """キャッシュ済 date が 3 日以上前なら破棄して再取得。"""
    stale_date = (_dt.date.today() - _dt.timedelta(days=5)).isoformat()
    stale_cache = {
        "date": stale_date,
        "regular": 100.0,
        "diesel": 90.0,
        "source": "gogo.gs",
    }
    monkeypatch.setattr("core.clients.energy.cache.get", lambda _key: stale_cache)
    monkeypatch.setattr("core.clients.energy.cache.store", lambda *_args: None)

    with patch(
        "core.clients.base.AsyncHTTPClient.get_html",
        new_callable=AsyncMock,
        return_value=_SAMPLE_HTML,
    ) as mock_get_html:
        async with EnergyClient() as client:
            result = await client.get_fuel_prices()

    # キャッシュではなくライブから取得されている
    assert result["date"] == "2026-04-30"
    assert result["regular"] == pytest.approx(166.1)
    mock_get_html.assert_called_once()


@pytest.mark.asyncio
async def test_get_fuel_prices_fresh_cache_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """キャッシュ済 date が前日 → ライブ取得をスキップ。"""
    yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
    fresh_cache = {
        "date": yesterday,
        "regular": 168.0,
        "diesel": 158.0,
        "source": "gogo.gs",
    }
    monkeypatch.setattr("core.clients.energy.cache.get", lambda _key: fresh_cache)
    monkeypatch.setattr("core.clients.energy.cache.store", lambda *_args: None)

    with patch(
        "core.clients.base.AsyncHTTPClient.get_html",
        new_callable=AsyncMock,
    ) as mock_get_html:
        async with EnergyClient() as client:
            result = await client.get_fuel_prices()

    assert result is fresh_cache
    mock_get_html.assert_not_called()
