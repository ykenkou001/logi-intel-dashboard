"""都道府県マクロ概況 統合ツール（MCP 登録ラッパー）。

全データソースを asyncio.gather で並列呼び出しし、
一部が失敗しても他のデータは返す（部分失敗許容）。

戻り値は ToolResponse 構造（summary/files/citations/freshness_warnings）。

実 fetch ロジックは Lambda zip でも共有するため `core/macro/sources.py` に切り出してある。
このモジュールは fastmcp に依存するため、Lambda パッケージには含めない。
"""
from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from core.export.citation import (
    corp_number_citation,
    estat_citation,
    fuel_price_citation,
    jma_warning_citation,
)
from core.export.response import ToolResponse
from core.macro.sources import (
    ESTAT_STATS_ID,
    PREF_CODES,
    fetch_corp,
    fetch_estat,
    fetch_fuel,
    fetch_weather,
    with_source_timeout,
)
from core.static._freshness import all_warnings

# 後方互換: 旧テストが参照するアンダースコア名。新規コードは core/macro/sources を使う。
_PREF_CODES = PREF_CODES
_ESTAT_STATS_ID = ESTAT_STATS_ID
_SOURCE_TIMEOUT_SECONDS = 18.0
_with_source_timeout = with_source_timeout
_fetch_estat = fetch_estat
_fetch_corp = fetch_corp
_fetch_weather = fetch_weather
_fetch_fuel = fetch_fuel


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーに統合マクロ概況ツールを登録する。"""

    @mcp.tool()
    async def logi_macro_overview(prefecture_name: str) -> dict[str, object]:
        """都道府県の物流業界マクロ概況を全データソースから集約して返します。

        e-Stat・国税庁・気象庁・エネ庁を並列呼び出しし、
        一部のソースが失敗しても他のデータは返します。

        Args:
            prefecture_name: 都道府県名（例: "東京都", "大阪府", "神奈川県"）

        Returns:
            ToolResponse 構造（summary/files/citations/freshness_warnings）の dict。
            - summary: 運輸業事業所数・運送会社法人数・気象警報・燃料価格のサマリー
            - citations: 各データソースの出典情報（経営会議で「出典は？」即答用）
            - freshness_warnings: 静的データ（CO2係数・告示等）の鮮度警告
        """
        codes = _PREF_CODES.get(prefecture_name)
        if codes is None:
            pref_list = "、".join(list(_PREF_CODES.keys())[:5]) + " …"
            return ToolResponse(
                summary=(
                    f"都道府県名 '{prefecture_name}' が認識できません。"
                    f"正式名称で入力してください（例: {pref_list}）"
                ),
            ).to_dict()

        estat_result, corp_result, weather_result, fuel_result = await asyncio.gather(
            _with_source_timeout("運輸業事業所数", _fetch_estat(codes["estat"])),
            _with_source_timeout("運送会社法人数", _fetch_corp(codes["corp"], prefecture_name)),
            _with_source_timeout("気象警報", _fetch_weather(codes["jma"])),
            _with_source_timeout("燃料価格", _fetch_fuel()),
        )

        summary = "\n".join([
            f"=== {prefecture_name} 物流業界マクロ概況 ===",
            estat_result,
            corp_result,
            weather_result,
            fuel_result,
        ])

        response = ToolResponse(summary=summary)
        response.add_citation(estat_citation(
            "経済センサス‐活動調査 2021 産業（大分類）別事業所数",
            _ESTAT_STATS_ID,
        ))
        response.add_citation(corp_number_citation())
        response.add_citation(jma_warning_citation())
        response.add_citation(fuel_price_citation())
        response.freshness_warnings = all_warnings()

        return response.to_dict()
