"""エネ庁 石油価格 向け MCP ツール群。"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from core.clients.energy import EnergyApiError, EnergyClient


def _format_prices(prices: dict[str, Any]) -> str:
    lines: list[str] = []
    if "date" in prices:
        lines.append(f"取得日: {prices['date']}")
    if "regular" in prices:
        lines.append(f"レギュラーガソリン: {prices['regular']:.1f} 円/L")
    if "diesel" in prices:
        lines.append(f"軽油: {prices['diesel']:.1f} 円/L")
    if "kerosene" in prices:
        lines.append(f"灯油（店頭）: {prices['kerosene']:.1f} 円/L")
    if not lines:
        return "燃料価格データが取得できませんでした。"
    source = prices.get("source", "gogo.gs")
    lines.append(f"出典: {source}")
    return "\n".join(lines)


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーにエネ庁燃料価格ツールを登録する。"""

    @mcp.tool()
    async def logi_fuel_price() -> str:
        """資源エネルギー庁から最新の燃料価格を取得します（週次更新、全国平均）。

        Returns:
            最新週のレギュラーガソリン・軽油・灯油価格（円/L）
        """
        try:
            async with EnergyClient() as client:
                prices = await client.get_fuel_prices()
            return _format_prices(prices)
        except EnergyApiError as exc:
            return f"[エネ庁エラー] {exc}"
