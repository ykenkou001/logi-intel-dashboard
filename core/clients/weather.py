"""気象庁 bosai JSON クライアント。認証不要。

エリアコード（6桁）は都道府県コードとは別体系。
例: 東京地方="130000", 大阪府="270000"
"""
from __future__ import annotations

from typing import Any, cast

from core import cache
from core.clients.base import AsyncHTTPClient, HttpClientError

_BASE_URL = "https://www.jma.go.jp/bosai/"
_FORECAST_TTL = 30 * 60   # 30 分
_WARNING_TTL = 30 * 60    # 30 分


class WeatherApiError(Exception):
    """気象庁 API エラー。"""


class WeatherClient(AsyncHTTPClient):
    """気象庁 bosai JSON クライアント。認証不要。"""

    def __init__(self) -> None:
        super().__init__(_BASE_URL)

    async def get_forecast(self, area_code: str) -> list[dict[str, Any]]:
        """7日間天気予報を取得する。

        Args:
            area_code: 気象庁エリアコード（例: "130000"=東京地方）

        Returns:
            予報データリスト。各要素に publishingOffice・reportDatetime・timeSeries が入る。
        """
        cache_key = cache.make_key("weather:forecast", {"area": area_code})
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

        try:
            data = await self.get_json(f"forecast/data/forecast/{area_code}.json")
        except HttpClientError as exc:
            raise WeatherApiError(
                f"天気予報取得エラー (area_code={area_code}): {exc}"
            ) from exc

        if not isinstance(data, list):
            raise WeatherApiError(f"予期しないレスポンス形式 (area_code={area_code})")

        cache.store(cache_key, data, _FORECAST_TTL)
        return cast(list[dict[str, Any]], data)

    async def get_warning(self, area_code: str) -> dict[str, Any]:
        """現在の警報・注意報情報を取得する。

        Args:
            area_code: 気象庁エリアコード（例: "130000"=東京地方）

        Returns:
            警報・注意報データ。areaTypes → areas → warnings が主要フィールド。
        """
        cache_key = cache.make_key("weather:warning", {"area": area_code})
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        try:
            data = await self.get_json(f"warning/data/warning/{area_code}.json")
        except HttpClientError as exc:
            raise WeatherApiError(
                f"警報情報取得エラー (area_code={area_code}): {exc}"
            ) from exc

        result = cast(dict[str, Any], data)
        cache.store(cache_key, result, _WARNING_TTL)
        return result
