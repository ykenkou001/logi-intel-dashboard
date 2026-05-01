"""気象庁 bosai JSON 向け MCP ツール群。"""
from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from core.clients.weather import (
    _INACTIVE_STATUSES,
    WeatherApiError,
    WeatherClient,
    resolve_warning_name,
)


def _format_forecast(data: list[dict[str, Any]]) -> str:
    if not data:
        return "予報データがありません。"
    office = data[0].get("publishingOffice", "")
    lines = [f"発表元: {office}"]
    for period in data:
        series = period.get("timeSeries", [])
        if not series:
            continue
        time_defines = series[0].get("timeDefines", [])
        areas = series[0].get("areas", [])
        if not areas:
            continue
        weathers = areas[0].get("weathers", [])
        for t, w in zip(time_defines[:3], weathers[:3], strict=False):
            date = t[:10] if len(t) >= 10 else t
            lines.append(f"{date}: {w}")
        break
    return "\n".join(lines)


def _format_warning(data: dict[str, Any], area_code: str) -> str:
    area_types = data.get("areaTypes", [])
    warnings_found: set[str] = set()
    for at in area_types:
        for area in at.get("areas", []):
            for w in area.get("warnings", []):
                if w.get("status", "") not in _INACTIVE_STATUSES:
                    warnings_found.add(resolve_warning_name(w.get("code", "")))
    if not warnings_found:
        return f"エリアコード {area_code}: 現在発令中の警報・注意報はありません。"
    return f"エリアコード {area_code}: " + "、".join(sorted(warnings_found))


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーに気象庁ツールを登録する。"""

    @mcp.tool()
    async def logi_weather_forecast(area_code: str) -> str:
        """気象庁から7日間天気予報を取得します。

        Args:
            area_code: 気象庁エリアコード（例: "130000"=東京地方, "270000"=大阪府）

        Returns:
            発表元と直近3日間の天気予報
        """
        try:
            async with WeatherClient() as client:
                data = await client.get_forecast(area_code)
            return _format_forecast(data)
        except WeatherApiError as exc:
            return f"[気象庁エラー] {exc}"

    @mcp.tool()
    async def logi_weather_warning(area_code: str) -> str:
        """気象庁から現在の警報・注意報を取得します。

        Args:
            area_code: 気象庁エリアコード（例: "130000"=東京地方）

        Returns:
            発令中の警報・注意報の一覧（なければその旨）
        """
        try:
            async with WeatherClient() as client:
                data = await client.get_warning(area_code)
            return _format_warning(data, area_code)
        except WeatherApiError as exc:
            return f"[気象庁エラー] {exc}"
