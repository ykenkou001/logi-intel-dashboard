"""gogo.gs 全国平均燃料価格スクレイパー。"""
from __future__ import annotations

import re
from typing import Any, cast

from bs4 import BeautifulSoup

from core import cache
from core.clients.base import AsyncHTTPClient, HttpClientError

_BASE_URL = "https://gogo.gs/"
_SOURCE_NAME = "gogo.gs（全国平均・ユーザー申告集計）"
_CACHE_KEY = "energy:fuel_prices:gogogs:v1"
_TTL_SECONDS = 24 * 60 * 60


class EnergyApiError(Exception):
    """燃料価格の取得・解析エラー。"""


class GoGoGsClient(AsyncHTTPClient):
    """gogo.gs から全国平均燃料価格をスクレイピングする。"""

    def __init__(self) -> None:
        super().__init__(_BASE_URL, max_retries=2, timeout=10.0)

    async def get_fuel_prices(self) -> dict[str, Any]:
        """全国平均燃料価格（円/L）を取得する。キャッシュあれば返す。

        副作用として、取得した日付・価格を `fuel_price_history` テーブルに
        自動追記する。同一日付・ソースの重複は INSERT OR IGNORE。
        蓄積を早く始めるほど傾向分析の価値が出るため、本フェーズで先行実装。
        """
        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            self._record_history(cast(dict[str, Any], cached))
            return cast(dict[str, Any], cached)

        try:
            html = await self.get_html("")
        except HttpClientError as exc:
            raise EnergyApiError(f"gogo.gs 取得エラー: {exc}") from exc

        result = _parse_gogogs_prices(html)
        cache.store(_CACHE_KEY, result, _TTL_SECONDS)
        self._record_history(result)
        return result

    @staticmethod
    def _record_history(prices: dict[str, Any]) -> None:
        """履歴テーブルに 1 行追記する（重複 INSERT OR IGNORE）。"""
        date_str = str(prices.get("date") or "")
        if not date_str:
            return  # 日付が抽出できなかった場合は履歴化しない
        cache.insert_fuel_price_record(
            date_str=date_str,
            source="gogo.gs",
            regular=prices.get("regular"),
            diesel=prices.get("diesel"),
            kerosene=prices.get("kerosene"),
        )


# 後方互換エイリアス（energy_tools.py / macro_tools.py のインポートを変えない）
EnergyClient = GoGoGsClient


def _parse_gogogs_prices(html: str) -> dict[str, Any]:
    """gogo.gs トップページ HTML から全国平均価格を抽出する。"""
    soup = BeautifulSoup(html, "html.parser")
    panel = soup.find(class_="pref-price-panel")
    if panel is None:
        raise EnergyApiError(
            "gogo.gs: .pref-price-panel が見つかりません。ページ構造が変わった可能性があります。"
        )

    prices: dict[str, float] = {}
    for avg in panel.find_all(class_="average"):
        label_tag = avg.find("label")
        price_tag = avg.find(class_="price")
        if label_tag is None or price_tag is None:
            continue
        label = label_tag.get_text(strip=True)
        price_text = price_tag.get_text(strip=True).replace(",", "")
        match = re.search(r"\d+(?:\.\d+)?", price_text)
        if match is None:
            continue
        value = float(match.group())
        if "レギュラー" in label:
            prices["regular"] = value
        elif "軽油" in label:
            prices["diesel"] = value
        elif "灯油" in label:
            prices["kerosene"] = value

    if "regular" not in prices or "diesel" not in prices:
        raise EnergyApiError("gogo.gs: レギュラー・軽油の価格を取得できませんでした。")

    date_str = _parse_date(soup)

    result: dict[str, Any] = {"source": _SOURCE_NAME, "date": date_str}
    result.update(prices)
    return result


def _parse_date(soup: BeautifulSoup) -> str:
    """「2026年4月30日（木）時点...」のようなテキストから ISO 日付を返す。"""
    for tag in soup.find_all(class_="help"):
        text = tag.get_text(" ", strip=True)
        match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", text)
        if match:
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return f"{y:04d}-{m:02d}-{d:02d}"
    return ""
