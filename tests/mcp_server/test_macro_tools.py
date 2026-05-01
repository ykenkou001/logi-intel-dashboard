"""mcp_server/tools/macro_tools.py の単体テスト。"""
from __future__ import annotations

import asyncio

import pytest

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
    monkeypatch.setattr(macro_tools, "_SOURCE_TIMEOUT_SECONDS", 0.01)

    async def slow() -> str:
        await asyncio.sleep(1)
        return "late"

    result = await macro_tools._with_source_timeout("燃料価格", slow())

    assert result == "燃料価格: 取得タイムアウト（0秒）"
