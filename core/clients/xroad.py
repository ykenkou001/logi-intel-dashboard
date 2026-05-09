"""xROAD 交通量 API（JARTIC）クライアント。

WFS（Web Feature Service）形式で GeoJSON を取得する。
認証不要（利用規約同意のみ）。
TTL: 1 分（5分値リアルタイムデータ）。

注意: 必ず CQL_FILTER で範囲を絞ること（過剰取得禁止）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from core import cache
from core.clients.base import AsyncHTTPClient, HttpClientError

_BASE_URL = "https://api.jartic-open-traffic.org/"
_LAYER = "t_travospublic_measure_5m"
_TTL_SECONDS = 60  # 1 分
_JST = timezone(timedelta(hours=9))


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
            "typeNames": _LAYER,
            "srsName": "EPSG:4326",
            "outputFormat": "application/json",
            "exceptions": "application/json",
            "count": str(count),
            "cql_filter": cql_filter,
        }

    async def get_traffic_by_route(
        self,
        route_id: str,
        time_from: str | None = None,
    ) -> list[dict[str, Any]]:
        """常時観測点コードで交通量データを取得する。

        Args:
            route_id: JARTIC の常時観測点コード（例: "3110010"）
            time_from: 取得開始時刻（"YYYY-MM-DD HH:MM:SS" または YYYYMMDDHHMM）。
                省略時は現在時刻の直近1時間。

        Returns:
            GeoJSON Feature リスト。各要素の properties に5分値交通量が入る。
        """
        start_code, end_code = _time_code_range(time_from)
        cql_filter = (
            f"常時観測点コード = {int(route_id)} "
            f"AND 時間コード >= {start_code} AND 時間コード <= {end_code}"
        )

        cache_key = cache.make_key(
            "xroad:route",
            {"route_id": route_id, "start_code": start_code, "end_code": end_code},
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

        try:
            data = await self.get_json("geoserver", self._wfs_params(cql_filter))
        except HttpClientError as exc:
            raise XRoadApiError(f"xROAD 観測点取得エラー (route_id={route_id}): {exc}") from exc

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
        start_code, end_code = _time_code_range(None)
        cql_filter = (
            f"道路種別 = 3 "
            f"AND 時間コード >= {start_code} AND 時間コード <= {end_code} "
            f"AND BBOX(ジオメトリ,{min_lon},{min_lat},{max_lon},{max_lat},'EPSG:4326')"
        )
        cache_key = cache.make_key(
            "xroad:bbox",
            {
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
                "start_code": start_code,
                "end_code": end_code,
            },
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

        try:
            data = await self.get_json("geoserver", self._wfs_params(cql_filter))
        except HttpClientError as exc:
            raise XRoadApiError(f"xROAD バウンディングボックス取得エラー: {exc}") from exc

        features = data.get("features", [])
        cache.store(cache_key, features, _TTL_SECONDS)
        return cast(list[dict[str, Any]], features)


def _time_code_range(time_from: str | None) -> tuple[int, int]:
    """xROAD の時間コード（YYYYMMDDHHMM）範囲を返す。

    time_from 省略時は、リアルタイム配信の取得負荷を抑えるため直近1時間だけを
    対象にする。
    """
    if time_from:
        start = _parse_time_code(time_from)
    else:
        now = datetime.now(_JST).replace(second=0, microsecond=0)
        start = now.replace(minute=0)
    end = start + timedelta(minutes=59)
    return _to_time_code(start), _to_time_code(end)


def _parse_time_code(value: str) -> datetime:
    if value.isdigit() and len(value) == 12:
        return datetime.strptime(value, "%Y%m%d%H%M").replace(tzinfo=_JST)
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_JST)


def _to_time_code(dt: datetime) -> int:
    return int(dt.strftime("%Y%m%d%H%M"))
