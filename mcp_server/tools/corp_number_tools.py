"""国税庁 法人番号 API 向け MCP ツール群。"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from core.clients.corp_number import CorpNumberApiError, CorpNumberClient


def _format_corps(corps: list[dict[str, Any]]) -> str:
    if not corps:
        return "該当する法人が見つかりませんでした。"
    lines: list[str] = []
    for c in corps[:10]:
        corp_num = c.get("corporateNumber", "")
        name = c.get("name", "")
        pref = c.get("prefectureName", "")
        city = c.get("cityName", "")
        lines.append(f"法人番号={corp_num}  {name}  所在: {pref}{city}")
    total = len(corps)
    result = "\n".join(lines)
    if total > 10:
        result += "\n（上位10件表示。count パラメータで件数を変更できます）"
    return result


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーに国税庁法人番号ツールを登録する。"""

    @mcp.tool()
    async def logi_corp_search(
        name: str,
        prefecture_code: str = "",
        count: int = 10,
    ) -> str:
        """国税庁法人番号 API で法人名を検索します。

        Args:
            name: 法人名（部分一致。例: "ヤマト運輸", "佐川", "運送"）
            prefecture_code: 都道府県コード（省略可。"13"=東京都, "27"=大阪府）
            count: 取得件数（デフォルト: 10、最大: 2000）

        Returns:
            法人番号・法人名・所在地の一覧（上位10件）
        """
        try:
            async with CorpNumberClient() as client:
                corps = await client.search_by_name(
                    name=name,
                    prefecture_code=prefecture_code or None,
                    count=count,
                )
            return _format_corps(corps)
        except CorpNumberApiError as exc:
            return f"[国税庁法人番号エラー] {exc}"
