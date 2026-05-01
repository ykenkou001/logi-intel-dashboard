"""core/clients/energy.py の単体テスト。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.clients.energy import EnergyApiError, EnergyClient, _parse_fuel_prices

SAMPLE_HTML = """
<html><body>
<table>
  <tr>
    <th>調査週</th>
    <th>レギュラー</th>
    <th>ハイオク</th>
    <th>軽油</th>
    <th>灯油（配達）</th>
    <th>灯油</th>
  </tr>
  <tr>
    <td>2025/01/06</td>
    <td>175.4</td>
    <td>186.3</td>
    <td>153.2</td>
    <td>104.3</td>
    <td>98.5</td>
  </tr>
</table>
</body></html>
"""

NO_TABLE_HTML = "<html><body><p>テーブルなし</p></body></html>"


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_CACHE_BYPASS", "1")


def test_parse_fuel_prices_success() -> None:
    result = _parse_fuel_prices(SAMPLE_HTML)
    assert result["regular"] == pytest.approx(175.4)
    assert result["diesel"] == pytest.approx(153.2)


def test_parse_fuel_prices_no_table_raises() -> None:
    with pytest.raises(EnergyApiError, match="価格テーブルが見つかりません"):
        _parse_fuel_prices(NO_TABLE_HTML)


@pytest.mark.asyncio
async def test_get_fuel_prices_returns_dict() -> None:
    with patch.object(EnergyClient, "get_html", return_value=SAMPLE_HTML):
        async with EnergyClient() as client:
            result = await client.get_fuel_prices()
    assert "regular" in result
    assert isinstance(result["regular"], float)
