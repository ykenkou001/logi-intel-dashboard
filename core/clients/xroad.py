"""xROAD 交通量 API（JARTIC）クライアント。

WFS（Web Feature Service）形式で GeoJSON を取得する。
認証不要（利用規約同意のみ）。
TTL: 1 分（5分値リアルタイムデータ）。

注意: 必ず CQL_FILTER で範囲を絞ること（過剰取得禁止）。
"""
from __future__ import annotations

from typing import Any, cast

from core import cache
from core.clients.base import AsyncHTTPClient, HttpClientError

_BASE_URL = "https://api.jartic-open-traffic.org/geoserver/"
_LAYER = "t_trafficvolume_5min"
_TTL_SECONDS = 60  # 1 分


class XRoadApiError(Exception):
    """xROAD API エラー。"""


class XRoadClient(AsyncHTTPClient):
    """xROAD 交通量 API（JARTIC）クライアント。

    WFS GetFeature リクエストで GeoJSON 形式のレスポンスを取得する。
    """

    def __init__(self) -> None:
        super().__init__(_BASE_URL)

    def _wfs_params(self, cql_filter: str, count: int = 100) -> dict[str, Any]:
        return {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": _LAYER,
            "outputFormat": "application/json",
            "count": str(count),
            "CQL_FILTER": cql_filter,
        }

    async def get_traffic_by_route(
        self,
        route_id: str,
        time_from: str | None = None,
    ) -> list[dict[str, Any]]:
        """路線コードで交通量データを取得する。

        Args:
            route_id: 路線コード（例: "0001"。JARTIC 仕様書を参照）
            time_from: 取得開始時刻（"YYYY-MM-DD HH:MM:SS"。省略時は最新データ）

        Returns:
            GeoJSON Feature リスト。各要素の properties に速度・交通量・混雑度が入る。
        """
        cql_filter = f"route_id='{route_id}'"
        if time_from:
            cql_filter += f" AND time_from>='{time_from}'"

        cache_key = cache.make_key(
            "xroad:route", {"route_id": route_id, "time_from": time_from or ""}
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

        try:
            data = await self.get_json("wfs", self._wfs_params(cql_filter))
        except HttpClientError as exc:
            raise XRoadApiError(f"xROAD 路線取得エラー (route_id={route_id}): {exc}") from exc

        features = data.get("features", [])
        cache.store(cache_key, features, _TTL_SECONDS)
        return cast(list[dict[str, Any]], features)

    async def get_traffic_by_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
    ) -> list[dict[str, Any]]:
        """バウンディングボックスで交通量データを取得する。

        範囲が広いと大量データになるため、狭い範囲（市区町村レベル）で使用すること。

        Args:
            min_lon: 最小経度
            min_lat: 最小緯度
            max_lon: 最大経度
            max_lat: 最大緯度

        Returns:
            GeoJSON Feature リスト。
        """
        cql_filter = (
            f"BBOX(geom,{min_lon},{min_lat},{max_lon},{max_lat},'EPSG:4326')"
        )
        cache_key = cache.make_key(
            "xroad:bbox",
            {"min_lon": min_lon, "min_lat": min_lat, "max_lon": max_lon, "max_lat": max_lat},
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

        try:
            data = await self.get_json("wfs", self._wfs_params(cql_filter))
        except HttpClientError as exc:
            raise XRoadApiError(f"xROAD バウンディングボックス取得エラー: {exc}") from exc

        features = data.get("features", [])
        cache.store(cache_key, features, _TTL_SECONDS)
        return cast(list[dict[str, Any]], features)
