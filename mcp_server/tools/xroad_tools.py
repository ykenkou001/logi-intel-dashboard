"""xROAD 交通量 API（JARTIC）向け MCP ツール群。"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from core.clients.xroad import XRoadApiError, XRoadClient


def _format_features(features: list[dict[str, Any]]) -> str:
    if not features:
        return (
            "交通量データが見つかりませんでした。"
            "常時観測点コード、地理範囲、時間帯を確認してください。"
        )
    lines: list[str] = []
    for f in features[:10]:
        props = f.get("properties", {})
        station = props.get("常時観測点コード", "-")
        time_ = props.get("時間コード", props.get("時間帯", "-"))
        up = _sum_volume(props, "上り")
        down = _sum_volume(props, "下り")
        total = up + down
        lines.append(
            f"観測点={station} 時間コード={time_} 交通量={total}台/5分（上り {up} / 下り {down}）"
        )
    total = len(features)
    result = "\n".join(lines)
    if total > 10:
        result += f"\n（全 {total} 件中10件表示）"
    return result


def _sum_volume(props: dict[str, Any], direction: str) -> int:
    total = 0
    for key in (
        f"{direction}・小型交通量",
        f"{direction}・大型交通量",
        f"{direction}・車種判別不能交通量",
    ):
        value = props.get(key) or 0
        total += int(value)
    return total


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーに xROAD 交通量ツールを登録する。"""

    @mcp.tool()
    async def logi_traffic_realtime(route_id: str, time_from: str = "") -> str:
        """xROAD から常時観測点別リアルタイム交通量を取得します（5分値データ、TTL=1分）。

        Args:
            route_id: 常時観測点コード（例: "3110010"）
            time_from: 取得開始時刻（省略可。"YYYY-MM-DD HH:MM:SS" または YYYYMMDDHHMM 形式）

        Returns:
            5分値交通量の一覧
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
            直近1時間の5分値交通量の一覧
        """
        try:
            async with XRoadClient() as client:
                features = await client.get_traffic_by_bbox(min_lon, min_lat, max_lon, max_lat)
            return _format_features(features)
        except XRoadApiError as exc:
            return f"[xROAD エラー] {exc}"
