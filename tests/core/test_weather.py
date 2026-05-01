"""core/clients/weather.py の単体テスト。"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from core.clients.weather import WeatherApiError, WeatherClient

FORECAST_RESPONSE: list[dict[str, Any]] = [
    {
        "publishingOffice": "気象庁",
        "reportDatetime": "2024-01-01T05:00:00+09:00",
        "timeSeries": [
            {
                "timeDefines": ["2024-01-01T00:00:00+09:00"],
                "areas": [{"area": {"name": "東京地方", "code": "130010"}, "weathers": ["晴れ"]}],
            }
        ],
    }
]

WARNING_RESPONSE: dict[str, Any] = {
    "areaTypes": [
        {
            "areas": [
                {
                    "code": "130010",
                    "name": "東京地方",
                    "warnings": [],
                }
            ]
        }
    ]
}


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_CACHE_BYPASS", "1")


@pytest.mark.asyncio
async def test_get_forecast_returns_list() -> None:
    with patch.object(WeatherClient, "get_json", return_value=FORECAST_RESPONSE):
        async with WeatherClient() as client:
            result = await client.get_forecast("130000")
    assert isinstance(result, list)
    assert result[0]["publishingOffice"] == "気象庁"


@pytest.mark.asyncio
async def test_get_forecast_non_list_raises() -> None:
    with patch.object(WeatherClient, "get_json", return_value={"error": "not a list"}):
        async with WeatherClient() as client:
            with pytest.raises(WeatherApiError, match="予期しないレスポンス形式"):
                await client.get_forecast("999999")


@pytest.mark.asyncio
async def test_get_warning_returns_dict() -> None:
    with patch.object(WeatherClient, "get_json", return_value=WARNING_RESPONSE):
        async with WeatherClient() as client:
            result = await client.get_warning("130000")
    assert "areaTypes" in result
