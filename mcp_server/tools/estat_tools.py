"""e-Stat API 向け MCP ツール群。

ツール命名規則: logi_estat_* （docs/mcp_tools.md 参照）
"""
from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from core.clients.estat import EStatApiError, EStatClient


def _format_tables(tables: list[dict[str, Any]]) -> str:
    if not tables:
        return "該当する統計表が見つかりませんでした。"
    lines: list[str] = []
    for t in tables[:10]:
        tid = t.get("@id", "（不明）")
        stat = t.get("STAT_NAME", {})
        stat_str = stat.get("$", "") if isinstance(stat, dict) else str(stat)
        title = t.get("TITLE", {})
        title_str = title.get("$", str(title)) if isinstance(title, dict) else str(title)
        lines.append(f"statsDataId={tid}  統計={stat_str}  表題={title_str}")
    total = len(tables)
    result = "\n".join(lines)
    if total > 10:
        result += f"\n（他 {total - 10} 件。stats_code や survey_years で絞り込んでください）"
    return result


def _format_meta(meta: dict[str, Any]) -> str:
    class_objs = meta.get("CLASS_INF", {}).get("CLASS_OBJ", [])
    if isinstance(class_objs, dict):
        class_objs = [class_objs]
    if not class_objs:
        return "メタデータが見つかりませんでした。"
    lines: list[str] = []
    for obj in class_objs:
        obj_id = obj.get("@id", "")
        name = obj.get("@name", "")
        classes = obj.get("CLASS", [])
        if isinstance(classes, dict):
            classes = [classes]
        samples = [f"{c.get('@code', '')}={c.get('@name', '')}" for c in classes[:5]]
        suffix = "..." if len(classes) > 5 else ""
        lines.append(f"[{obj_id}] {name}: {', '.join(samples)}{suffix}")
    return "\n".join(lines)


def _format_values(stat_data: dict[str, Any], limit: int) -> str:
    values = stat_data.get("DATA_INF", {}).get("VALUE", [])
    if isinstance(values, dict):
        values = [values]
    if not values:
        return "データが見つかりませんでした。"
    lines: list[str] = []
    for v in values[:limit]:
        area = v.get("@area", "-")
        time_ = v.get("@time", "-")
        cat01 = v.get("@cat01", "-")
        value = v.get("$", v.get("@value", "-"))
        unit = v.get("@unit", "")
        lines.append(f"地域={area} 時間={time_} 分類={cat01} 値={value}{unit}")
    total_str = stat_data.get("RESULT_INF", {}).get("TOTAL_NUMBER", "")
    header = f"（全 {total_str} 件中 {min(len(values), limit)} 件表示）\n" if total_str else ""
    return header + "\n".join(lines)


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーに e-Stat ツールを登録する。"""

    @mcp.tool()
    async def logi_estat_search(
        search_word: str,
        stats_code: str = "",
        survey_years: str = "",
    ) -> str:
        """e-Stat の統計表をキーワードで検索します。

        使い方:
          1. search_word で検索 → statsDataId を取得
          2. logi_estat_get_meta で分類コード・地域コードを確認
          3. logi_estat_get_data で実数値を取得

        Args:
            search_word: 検索キーワード（例: "運輸業", "貨物運送", "トラック"）
            stats_code: 省庁コード（省略可。例: "00200552"=経済センサス）
            survey_years: 調査年（省略可。例: "2021"）

        Returns:
            statsDataId・統計名・表題の一覧（上位10件）
        """
        try:
            async with EStatClient() as client:
                tables = await client.search_stats(
                    search_word=search_word or None,
                    stats_code=stats_code or None,
                    survey_years=survey_years or None,
                )
            return _format_tables(tables)
        except EStatApiError as exc:
            return f"[e-Stat エラー] {exc}"

    @mcp.tool()
    async def logi_estat_get_meta(stats_data_id: str) -> str:
        """統計表のメタデータ（分類コード・地域コード・時間軸）を取得します。

        logi_estat_get_data でフィルタリングするために必要なコードを確認します。

        Args:
            stats_data_id: 統計表 ID（logi_estat_search で取得）

        Returns:
            分類事項・地域・時間軸のコード一覧
        """
        try:
            async with EStatClient() as client:
                meta = await client.get_meta_info(stats_data_id)
            return _format_meta(meta)
        except EStatApiError as exc:
            return f"[e-Stat エラー] {exc}"

    @mcp.tool()
    async def logi_estat_get_data(
        stats_data_id: str,
        cd_area: str = "",
        cd_cat01: str = "",
        cd_time: str = "",
        limit: int = 100,
    ) -> str:
        """e-Stat の統計表 ID を指定して実数値を取得します。

        Args:
            stats_data_id: 統計表 ID（logi_estat_search で取得）
            cd_area: 地域コード（例: "13000"=東京都, "00000"=全国。logi_estat_get_meta で確認）
            cd_cat01: 分類コード（例: "H"=運輸業。logi_estat_get_meta で確認）
            cd_time: 時間軸コード（例: "2021000000"。logi_estat_get_meta で確認）
            limit: 取得件数上限（デフォルト: 100）

        Returns:
            地域・分類・時間・値の一覧
        """
        try:
            async with EStatClient() as client:
                stat_data = await client.get_stats_data(
                    stats_data_id=stats_data_id,
                    cd_area=cd_area or None,
                    cd_cat01=cd_cat01 or None,
                    cd_time=cd_time or None,
                    limit=limit,
                )
            return _format_values(stat_data, limit)
        except EStatApiError as exc:
            return f"[e-Stat エラー] {exc}"
