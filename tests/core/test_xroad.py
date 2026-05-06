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
                "常時観測点コード": 3110010,
                "時間コード": 202605061600,
                "上り・小型交通量": 64,
                "上り・大型交通量": 2,
                "上り・車種判別不能交通量": 2,
                "下り・小型交通量": 76,
                "下り・大型交通量": 1,
                "下り・車種判別不能交通量": 7,
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
            result = await client.get_traffic_by_route("3110010")
    assert len(result) == 1
    assert result[0]["properties"]["常時観測点コード"] == 3110010


@pytest.mark.asyncio
async def test_get_traffic_by_route_with_time() -> None:
    with patch.object(XRoadClient, "get_json", return_value=EMPTY_RESPONSE) as mock:
        async with XRoadClient() as client:
            await client.get_traffic_by_route("3110010", time_from="2026-05-06 16:00:00")
    cql = mock.call_args[0][1]["cql_filter"]
    assert "常時観測点コード = 3110010" in cql
    assert "時間コード >= 202605061600" in cql


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
    assert mock.call_args[0][0] == "geoserver"
    params = mock.call_args[0][1]
    cql = params["cql_filter"]
    assert params["typeNames"] == "t_travospublic_measure_5m"
    assert "BBOX" in cql
    assert "ジオメトリ" in cql
    assert "時間コード >=" in cql
