"""mcp_server/tools/macro_tools.py の単体テスト。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP

from mcp_server.tools import macro_tools


@pytest.mark.asyncio
async def test_with_source_timeout_returns_result() -> None:
    async def quick() -> str:
        return "ok"

    result = await macro_tools._with_source_timeout("テスト", quick())

    assert result == "ok"


@pytest.mark.asyncio
async def test_with_source_timeout_returns_timeout_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 実体は core.macro.sources にあるため、そちらを patch する
    from core.macro import sources as macro_sources

    monkeypatch.setattr(macro_sources, "SOURCE_TIMEOUT_SECONDS", 0.01)

    async def slow() -> str:
        await asyncio.sleep(1)
        return "late"

    result = await macro_tools._with_source_timeout("燃料価格", slow())

    assert result == "燃料価格: 取得タイムアウト（0秒）"


# ---- ToolResponse 構造化レスポンステスト ----


@pytest.mark.asyncio
async def test_logi_macro_overview_returns_structured_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """logi_macro_overview が ToolResponse の dict を返す。"""
    # 各サブ取得をモック（外部 API を叩かない）
    monkeypatch.setattr(
        macro_tools, "_fetch_estat",
        AsyncMock(return_value="運輸業事業所数: 15,234 事業所"),
    )
    monkeypatch.setattr(
        macro_tools, "_fetch_corp",
        AsyncMock(return_value="運送会社法人数: 5 件以上"),
    )
    monkeypatch.setattr(
        macro_tools, "_fetch_weather",
        AsyncMock(return_value="気象警報: なし"),
    )
    monkeypatch.setattr(
        macro_tools, "_fetch_fuel",
        AsyncMock(return_value="燃料価格: レギュラー 168 円/L"),
    )

    mcp = FastMCP("test")
    macro_tools.register_tools(mcp)
    tool = await mcp.get_tool("logi_macro_overview")
    result = await tool.run(arguments={"prefecture_name": "東京都"})
    payload = result.structured_content

    # ToolResponse の必須キー
    assert isinstance(payload, dict)
    assert "summary" in payload
    assert "citations" in payload
    assert "files" in payload
    assert "freshness_warnings" in payload

    # 内容検証
    assert "東京都" in str(payload["summary"])
    assert "15,234" in str(payload["summary"])
    citations = payload["citations"]
    assert isinstance(citations, list)
    assert len(citations) >= 4  # estat / corp / jma / fuel


@pytest.mark.asyncio
async def test_logi_macro_overview_unknown_prefecture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未知の都道府県名でも ToolResponse 構造で返す。"""
    mcp = FastMCP("test")
    macro_tools.register_tools(mcp)
    tool = await mcp.get_tool("logi_macro_overview")
    result = await tool.run(arguments={"prefecture_name": "存在しない県"})
    payload = result.structured_content

    assert isinstance(payload, dict)
    assert "summary" in payload
    assert "認識できません" in str(payload["summary"])
    # エラー時は citations なし
    assert payload["citations"] == []
