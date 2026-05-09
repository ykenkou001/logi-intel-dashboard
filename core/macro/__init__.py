"""都道府県マクロ概況のコアロジック。

MCP ツール（mcp_server/tools/macro_tools.py）と REST API ルーター（api/routers/macro.py）
の両方が共有する、外部 API へのフェッチヘルパー群。

Lambda パッケージは fastmcp を含まないため、ここに切り出して両系統で再利用する。
"""

from core.macro.sources import (
    ESTAT_STATS_ID,
    PREF_CODES,
    SOURCE_TIMEOUT_SECONDS,
    fetch_corp,
    fetch_estat,
    fetch_fuel,
    fetch_weather,
    with_source_timeout,
)

__all__ = [
    "ESTAT_STATS_ID",
    "PREF_CODES",
    "SOURCE_TIMEOUT_SECONDS",
    "fetch_corp",
    "fetch_estat",
    "fetch_fuel",
    "fetch_weather",
    "with_source_timeout",
]
