"""都道府県マクロ概況 統合ツール。

全データソースを asyncio.gather で並列呼び出しし、
一部が失敗しても他のデータは返す（部分失敗許容）。
"""
from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from core.clients.corp_number import CorpNumberApiError, CorpNumberClient
from core.clients.energy import EnergyApiError, EnergyClient
from core.clients.estat import EStatApiError, EStatClient
from core.clients.weather import (
    _INACTIVE_STATUSES,
    WeatherApiError,
    WeatherClient,
    resolve_warning_name,
)

# 都道府県名 → 各 API コードのマッピング
# estat: e-Stat cdArea（5桁）, corp: 国税庁都道府県コード（2桁）
# jma: 気象庁エリアコード（6桁・代表地方）
_PREF_CODES: dict[str, dict[str, str]] = {
    "北海道": {"estat": "01000", "corp": "01", "jma": "016000"},
    "青森県": {"estat": "02000", "corp": "02", "jma": "020000"},
    "岩手県": {"estat": "03000", "corp": "03", "jma": "030000"},
    "宮城県": {"estat": "04000", "corp": "04", "jma": "040000"},
    "秋田県": {"estat": "05000", "corp": "05", "jma": "050000"},
    "山形県": {"estat": "06000", "corp": "06", "jma": "060000"},
    "福島県": {"estat": "07000", "corp": "07", "jma": "070000"},
    "茨城県": {"estat": "08000", "corp": "08", "jma": "080000"},
    "栃木県": {"estat": "09000", "corp": "09", "jma": "090000"},
    "群馬県": {"estat": "10000", "corp": "10", "jma": "100000"},
    "埼玉県": {"estat": "11000", "corp": "11", "jma": "110000"},
    "千葉県": {"estat": "12000", "corp": "12", "jma": "120000"},
    "東京都": {"estat": "13000", "corp": "13", "jma": "130000"},
    "神奈川県": {"estat": "14000", "corp": "14", "jma": "140000"},
    "新潟県": {"estat": "15000", "corp": "15", "jma": "150000"},
    "富山県": {"estat": "16000", "corp": "16", "jma": "160000"},
    "石川県": {"estat": "17000", "corp": "17", "jma": "170000"},
    "福井県": {"estat": "18000", "corp": "18", "jma": "180000"},
    "山梨県": {"estat": "19000", "corp": "19", "jma": "190000"},
    "長野県": {"estat": "20000", "corp": "20", "jma": "200000"},
    "岐阜県": {"estat": "21000", "corp": "21", "jma": "210000"},
    "静岡県": {"estat": "22000", "corp": "22", "jma": "220000"},
    "愛知県": {"estat": "23000", "corp": "23", "jma": "230000"},
    "三重県": {"estat": "24000", "corp": "24", "jma": "240000"},
    "滋賀県": {"estat": "25000", "corp": "25", "jma": "250000"},
    "京都府": {"estat": "26000", "corp": "26", "jma": "260000"},
    "大阪府": {"estat": "27000", "corp": "27", "jma": "270000"},
    "兵庫県": {"estat": "28000", "corp": "28", "jma": "280000"},
    "奈良県": {"estat": "29000", "corp": "29", "jma": "290000"},
    "和歌山県": {"estat": "30000", "corp": "30", "jma": "300000"},
    "鳥取県": {"estat": "31000", "corp": "31", "jma": "310000"},
    "島根県": {"estat": "32000", "corp": "32", "jma": "320000"},
    "岡山県": {"estat": "33000", "corp": "33", "jma": "330000"},
    "広島県": {"estat": "34000", "corp": "34", "jma": "340000"},
    "山口県": {"estat": "35000", "corp": "35", "jma": "350000"},
    "徳島県": {"estat": "36000", "corp": "36", "jma": "360000"},
    "香川県": {"estat": "37000", "corp": "37", "jma": "370000"},
    "愛媛県": {"estat": "38000", "corp": "38", "jma": "380000"},
    "高知県": {"estat": "39000", "corp": "39", "jma": "390000"},
    "福岡県": {"estat": "40000", "corp": "40", "jma": "400000"},
    "佐賀県": {"estat": "41000", "corp": "41", "jma": "410000"},
    "長崎県": {"estat": "42000", "corp": "42", "jma": "420000"},
    "熊本県": {"estat": "43000", "corp": "43", "jma": "430000"},
    "大分県": {"estat": "44000", "corp": "44", "jma": "440000"},
    "宮崎県": {"estat": "45000", "corp": "45", "jma": "450000"},
    "鹿児島県": {"estat": "46000", "corp": "46", "jma": "460100"},
    "沖縄県": {"estat": "47000", "corp": "47", "jma": "471000"},
}

# e-Stat 経済センサス活動調査 産業（大分類）別事業所数（2021年）の統計表 ID
_ESTAT_STATS_ID = "0004005642"


async def _fetch_estat(cd_area: str) -> str:
    try:
        async with EStatClient() as client:
            data = await client.get_stats_data(
                stats_data_id=_ESTAT_STATS_ID,
                cd_area=cd_area,
                cd_cat01="H",   # 運輸業，郵便業
                limit=1,
            )
        values = data.get("DATA_INF", {}).get("VALUE", [])
        if isinstance(values, dict):
            values = [values]
        if values:
            v = values[0]
            unit = v.get("@unit", "事業所")
            return f"運輸業事業所数: {v.get('$', '不明')} {unit}（経済センサス2021）"
        return "運輸業事業所数: データなし（e-Stat）"
    except EStatApiError as exc:
        return f"運輸業事業所数: 取得失敗（{exc}）"


async def _fetch_corp(corp_code: str, pref_name: str) -> str:
    try:
        async with CorpNumberClient() as client:
            corps = await client.search_by_name("運送", prefecture_code=corp_code, count=5)
        count = len(corps)
        return f"運送会社法人数（「運送」で検索）: {count} 件以上（国税庁法人番号 サンプル）"
    except CorpNumberApiError as exc:
        return f"運送会社法人数: 取得失敗（{exc}）"


async def _fetch_weather(jma_code: str) -> str:
    try:
        async with WeatherClient() as client:
            warnings = await client.get_warning(jma_code)
        area_types = warnings.get("areaTypes", [])
        active: set[str] = set()
        for at in area_types:
            for area in at.get("areas", []):
                for w in area.get("warnings", []):
                    if w.get("status", "") not in _INACTIVE_STATUSES:
                        active.add(resolve_warning_name(w.get("code", "")))
        if active:
            return f"気象警報: 発令中 — {', '.join(sorted(active))}"
        return "気象警報: なし（気象庁）"
    except WeatherApiError as exc:
        return f"気象警報: 取得失敗（{exc}）"


async def _fetch_fuel() -> str:
    try:
        async with EnergyClient() as client:
            prices = await client.get_fuel_prices()
        regular = prices.get("regular", "不明")
        diesel = prices.get("diesel", "不明")
        date = prices.get("date", "")
        return f"燃料価格（{date}）: レギュラー {regular} 円/L・軽油 {diesel} 円/L（全国平均）"
    except EnergyApiError as exc:
        return f"燃料価格: 取得失敗（{exc}）"


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーに統合マクロ概況ツールを登録する。"""

    @mcp.tool()
    async def logi_macro_overview(prefecture_name: str) -> str:
        """都道府県の物流業界マクロ概況を全データソースから集約して返します。

        e-Stat・国税庁・気象庁・エネ庁を並列呼び出しし、
        一部のソースが失敗しても他のデータは返します。

        Args:
            prefecture_name: 都道府県名（例: "東京都", "大阪府", "神奈川県"）

        Returns:
            運輸業事業所数・運送会社法人数・気象警報・燃料価格のサマリー
        """
        codes = _PREF_CODES.get(prefecture_name)
        if codes is None:
            pref_list = "、".join(list(_PREF_CODES.keys())[:5]) + " …"
            return (
                f"都道府県名 '{prefecture_name}' が認識できません。"
                f"正式名称で入力してください（例: {pref_list}）"
            )

        estat_result, corp_result, weather_result, fuel_result = await asyncio.gather(
            _fetch_estat(codes["estat"]),
            _fetch_corp(codes["corp"], prefecture_name),
            _fetch_weather(codes["jma"]),
            _fetch_fuel(),
        )

        return "\n".join([
            f"=== {prefecture_name} 物流業界マクロ概況 ===",
            estat_result,
            corp_result,
            weather_result,
            fuel_result,
        ])
