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

# JMA 警報・注意報コード → 名称マッピング（bosai warning API は type フィールドを持たない）
_WARNING_CODE_NAMES: dict[str, str] = {
    "02": "大雨特別警報",
    "03": "暴風特別警報",
    "04": "暴風雪特別警報",
    "05": "大雪特別警報",
    "06": "波浪特別警報",
    "07": "高潮特別警報",
    "10": "大雨警報",
    "12": "洪水警報",
    "13": "暴風警報",
    "15": "波浪警報",
    "16": "高潮警報",
    "17": "大雪警報",
    "18": "暴風雪警報",
    "14": "強風注意報",
    "19": "波浪注意報",
    "20": "雷注意報",
    "21": "風雪注意報",
    "22": "大雨注意報",
    "23": "洪水注意報",
    "24": "高波注意報",
    "25": "高潮注意報",
    "26": "大雪注意報",
    "27": "融雪注意報",
    "28": "霧注意報",
    "29": "低温注意報",
    "30": "霜注意報",
    "31": "乾燥注意報",
    "32": "なだれ注意報",
    "33": "着氷注意報",
    "34": "着雪注意報",
}

# 発令中とみなさないステータス値
_INACTIVE_STATUSES = {"", "解除", "平常"}


def resolve_warning_name(code: str) -> str:
    """警報コードから名称を返す。未知コードは「警報(コード)」形式。"""
    return _WARNING_CODE_NAMES.get(code, f"警報({code})")


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
