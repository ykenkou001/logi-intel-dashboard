"""xROAD 交通量 API（JARTIC）向け MCP ツール群。"""
from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from core.clients.xroad import XRoadApiError, XRoadClient


def _format_features(features: list[dict[str, Any]]) -> str:
    if not features:
        return "交通量データが見つかりませんでした。route_id または地理範囲を確認してください。"
    lines: list[str] = []
    for f in features[:10]:
        props = f.get("properties", {})
        route = props.get("route_id", "-")
        speed = props.get("speed", "-")
        volume = props.get("volume", "-")
        level = props.get("congestion_level", "-")
        time_ = props.get("time_from", "-")
        lines.append(f"路線={route} 時刻={time_} 速度={speed}km/h 交通量={volume}台/h 混雑={level}")
    total = len(features)
    result = "\n".join(lines)
    if total > 10:
        result += f"\n（全 {total} 件中10件表示）"
    return result


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーに xROAD 交通量ツールを登録する。"""

    @mcp.tool()
    async def logi_traffic_realtime(route_id: str, time_from: str = "") -> str:
        """xROAD から路線別リアルタイム交通量を取得します（5分値データ、TTL=1分）。

        Args:
            route_id: 路線コード（JARTIC 仕様書を参照。例: "0001"）
            time_from: 取得開始時刻（省略可。"YYYY-MM-DD HH:MM:SS" 形式）

        Returns:
            速度・交通量・混雑度の一覧
        """
        try:
            async with XRoadClient() as client:
                features = await client.get_traffic_by_route(
                    route_id=route_id,
                    time_from=time_from or None,
                )
            return _format_features(features)
        except XRoadApiError as exc:
            return f"[xROAD エラー] {exc}"

    @mcp.tool()
    async def logi_traffic_by_bbox(
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
    ) -> str:
        """xROAD から地理範囲（バウンディングボックス）で交通量を取得します。

        範囲が広すぎると大量データになるため、市区町村レベルの範囲で使用してください。

        Args:
            min_lon: 最小経度（例: 139.6）
            min_lat: 最小緯度（例: 35.6）
            max_lon: 最大経度（例: 139.8）
            max_lat: 最大緯度（例: 35.8）

        Returns:
            速度・交通量・混雑度の一覧
        """
        try:
            async with XRoadClient() as client:
                features = await client.get_traffic_by_bbox(min_lon, min_lat, max_lon, max_lat)
            return _format_features(features)
        except XRoadApiError as exc:
            return f"[xROAD エラー] {exc}"
