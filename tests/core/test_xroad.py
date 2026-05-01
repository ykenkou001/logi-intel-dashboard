"""core/clients/xroad.py の単体テスト。"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from core.clients.xroad import XRoadClient

FEATURES_RESPONSE: dict[str, Any] = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "route_id": "0001",
                "speed": 60.0,
                "volume": 1200,
                "congestion_level": 1,
                "time_from": "2024-01-01 09:00:00",
            },
            "geometry": {"type": "Point", "coordinates": [139.7, 35.7]},
        }
    ],
}

EMPTY_RESPONSE: dict[str, Any] = {"type": "FeatureCollection", "features": []}


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_CACHE_BYPASS", "1")


@pytest.mark.asyncio
async def test_get_traffic_by_route_returns_features() -> None:
    with patch.object(XRoadClient, "get_json", return_value=FEATURES_RESPONSE):
        async with XRoadClient() as client:
            result = await client.get_traffic_by_route("0001")
    assert len(result) == 1
    assert result[0]["properties"]["route_id"] == "0001"


@pytest.mark.asyncio
async def test_get_traffic_by_route_with_time() -> None:
    with patch.object(XRoadClient, "get_json", return_value=EMPTY_RESPONSE) as mock:
        async with XRoadClient() as client:
            await client.get_traffic_by_route("0001", time_from="2024-01-01 09:00:00")
    cql = mock.call_args[0][1]["CQL_FILTER"]
    assert "time_from>=" in cql


@pytest.mark.asyncio
async def test_get_traffic_by_bbox_returns_features() -> None:
    with patch.object(XRoadClient, "get_json", return_value=FEATURES_RESPONSE):
        async with XRoadClient() as client:
            result = await client.get_traffic_by_bbox(139.6, 35.6, 139.8, 35.8)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_traffic_by_bbox_uses_bbox_filter() -> None:
    with patch.object(XRoadClient, "get_json", return_value=EMPTY_RESPONSE) as mock:
        async with XRoadClient() as client:
            await client.get_traffic_by_bbox(139.6, 35.6, 139.8, 35.8)
    cql = mock.call_args[0][1]["CQL_FILTER"]
    assert "BBOX" in cql
