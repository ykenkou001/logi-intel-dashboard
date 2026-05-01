"""資源エネルギー庁 石油価格情報スクレイパー。

HTML スクレイピングで最新週の燃料価格を取得する。
API は存在しないため BeautifulSoup4 を使用。
"""
from __future__ import annotations

import re
from typing import Any, cast

from bs4 import BeautifulSoup

from core import cache
from core.clients.base import AsyncHTTPClient, HttpClientError

_BASE_URL = "https://www.enecho.meti.go.jp/"
_PAGE_PATH = "statistics/petroleum_and_lpgas/pl007/results.html"
_TTL_SECONDS = 7 * 24 * 60 * 60   # 7 日（週次更新）

_CACHE_KEY = "energy:fuel_prices"


class EnergyApiError(Exception):
    """エネ庁スクレイピングエラー。HTML 構造変更の可能性がある。"""


class EnergyClient(AsyncHTTPClient):
    """資源エネルギー庁 石油価格情報スクレイパー。"""

    def __init__(self) -> None:
        super().__init__(_BASE_URL)

    async def get_fuel_prices(self) -> dict[str, Any]:
        """最新週の燃料価格（円/L）を取得する。

        Returns:
            {"date": "2025-01-01", "regular": 170.0, "diesel": 155.0, "kerosene": 100.0}

        Raises:
            EnergyApiError: HTML 構造変更等でパース失敗した場合
        """
        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            return cast(dict[str, Any], cached)

        try:
            html = await self.get_html(_PAGE_PATH)
        except HttpClientError as exc:
            raise EnergyApiError(f"エネ庁ページ取得エラー: {exc}") from exc

        result = _parse_fuel_prices(html)
        cache.store(_CACHE_KEY, result, _TTL_SECONDS)
        return result


def _parse_fuel_prices(html: str) -> dict[str, Any]:
    """HTML から最新週の燃料価格を抽出する。

    HTML 構造変更時は EnergyApiError を送出する。
    """
    soup = BeautifulSoup(html, "html.parser")

    # 価格テーブルを探す（「レギュラー」という列ヘッダを含む表）
    target_table = None
    for table in soup.find_all("table"):
        if "レギュラー" in table.get_text():
            target_table = table
            break

    if target_table is None:
        raise EnergyApiError(
            "エネ庁ページの価格テーブルが見つかりません。HTML 構造が変更された可能性があります。"
            "手動確認先: https://www.enecho.meti.go.jp/statistics/petroleum_and_lpgas/pl007/"
        )

    rows = target_table.find_all("tr")
    if len(rows) < 2:
        raise EnergyApiError("価格テーブルの行数が不足しています。")

    # ヘッダー行でカラム位置を特定
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    col_map: dict[str, int] = {}
    for i, h in enumerate(headers):
        if "レギュラー" in h:
            col_map["regular"] = i
        elif "軽油" in h:
            col_map["diesel"] = i
        elif "灯油" in h and "店頭" not in h:
            col_map["kerosene"] = i
        elif "調査" in h or "年月" in h or "週" in h:
            col_map["date"] = i

    if not col_map.get("regular"):
        raise EnergyApiError("レギュラーガソリン価格の列が見つかりません。")

    # 最新データ行（テーブルの最終行）を取得
    data_row = rows[-1].find_all(["th", "td"])
    if len(data_row) <= max(col_map.values()):
        raise EnergyApiError("最新行のセル数が不足しています。")

    def _to_float(text: str) -> float:
        m = re.search(r"[\d.]+", text.replace(",", ""))
        if not m:
            raise EnergyApiError(f"数値パースエラー: {text!r}")
        return float(m.group())

    result: dict[str, Any] = {}
    if "date" in col_map:
        result["date"] = data_row[col_map["date"]].get_text(strip=True)
    if "regular" in col_map:
        result["regular"] = _to_float(data_row[col_map["regular"]].get_text(strip=True))
    if "diesel" in col_map:
        result["diesel"] = _to_float(data_row[col_map["diesel"]].get_text(strip=True))
    if "kerosene" in col_map:
        result["kerosene"] = _to_float(data_row[col_map["kerosene"]].get_text(strip=True))

    return result
