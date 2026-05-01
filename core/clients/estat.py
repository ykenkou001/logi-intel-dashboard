"""e-Stat API（政府統計ポータル）クライアント。

3 ステップで統計データを取得する:
  1. search_stats()  → statsDataId を取得
  2. get_meta_info() → 分類コード・地域コード・時間軸を把握
  3. get_stats_data() → 実際の統計数値を取得
"""
from __future__ import annotations

import os
from typing import Any, cast

from core import cache
from core.clients.base import AsyncHTTPClient, HttpClientError

_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/"
_TTL_SECONDS = 24 * 60 * 60  # 24 時間

_STATUS_MESSAGES: dict[int, str] = {
    100: "appId 認証失敗（ESTAT_APP_ID を確認してください）",
    101: "必須パラメータ不足",
    102: "パラメータ値不正",
    200: "DB アクセスエラー",
    201: "DB アクセスエラー",
    202: "DB アクセスエラー",
    203: "DB アクセスエラー",
}


class EStatApiError(Exception):
    """e-Stat API エラー。"""


class EStatClient(AsyncHTTPClient):
    """e-Stat API クライアント。

    環境変数 ESTAT_APP_ID からアプリケーション ID を読み込む。
    レスポンスは 24 時間 SQLite にキャッシュされる。
    """

    def __init__(self) -> None:
        super().__init__(_BASE_URL)
        app_id = os.environ.get("ESTAT_APP_ID", "")
        if not app_id:
            raise EStatApiError("環境変数 ESTAT_APP_ID が設定されていません")
        self._app_id = app_id

    def _base_params(self) -> dict[str, str]:
        return {"appId": self._app_id, "lang": "J"}

    def _check_result(self, result: dict[str, Any], endpoint: str) -> None:
        """e-Stat の RESULT ブロックを検査してエラーなら例外を送出する。

        STATUS 0 = 正常（データあり）、1 = 正常（データなし）、100以上 = エラー
        """
        status = int(result.get("STATUS", -1))
        if status not in (0, 1):
            msg = _STATUS_MESSAGES.get(status, result.get("ERROR_MSG", "不明なエラー"))
            raise EStatApiError(f"{endpoint} エラー (STATUS={status}): {msg}")

    async def search_stats(
        self,
        search_word: str | None = None,
        stats_code: str | None = None,
        survey_years: str | None = None,
    ) -> list[dict[str, Any]]:
        """統計表をキーワード検索し、テーブル情報リストを返す（Step 1）。

        Args:
            search_word: 検索キーワード（例: "運輸業"）
            stats_code: 省庁コード（例: "00200552"=経済センサス）
            survey_years: 調査年（例: "2021"）

        Returns:
            TABLE_INF の list。各要素に "@id" (statsDataId) が含まれる。
        """
        params: dict[str, Any] = {**self._base_params()}
        if search_word:
            params["searchWord"] = search_word
        if stats_code:
            params["statsCode"] = stats_code
        if survey_years:
            params["surveyYears"] = survey_years

        cache_key = cache.make_key("estat:list", params)
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

        try:
            data = await self.get_json("getStatsList", params)
        except HttpClientError as exc:
            raise EStatApiError(f"getStatsList 通信エラー: {exc}") from exc

        root = data.get("GET_STATS_LIST", {})
        self._check_result(root.get("RESULT", {}), "getStatsList")

        tables = root.get("DATALIST_INF", {}).get("TABLE_INF", [])
        if isinstance(tables, dict):
            tables = [tables]

        cache.store(cache_key, tables, _TTL_SECONDS)
        return cast(list[dict[str, Any]], tables)

    async def get_meta_info(self, stats_data_id: str) -> dict[str, Any]:
        """統計表のメタデータ（分類コード・地域コード・時間軸一覧）を取得する（Step 2）。

        Args:
            stats_data_id: 統計表 ID（search_stats の "@id" から取得）

        Returns:
            METADATA_INF ブロック。CLASS_INF.CLASS_OBJ にコード一覧が入る。
        """
        params = {**self._base_params(), "statsDataId": stats_data_id}
        cache_key = cache.make_key("estat:meta", {"statsDataId": stats_data_id})
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        try:
            data = await self.get_json("getMetaInfo", params)
        except HttpClientError as exc:
            raise EStatApiError(f"getMetaInfo 通信エラー: {exc}") from exc

        root = data.get("GET_META_INFO", {})
        self._check_result(root.get("RESULT", {}), "getMetaInfo")

        meta: dict[str, Any] = root.get("METADATA_INF", {})
        cache.store(cache_key, meta, _TTL_SECONDS)
        return meta

    async def get_stats_data(
        self,
        stats_data_id: str,
        cd_area: str | None = None,
        cd_cat01: str | None = None,
        cd_time: str | None = None,
        limit: int | None = None,
        start_position: int | None = None,
    ) -> dict[str, Any]:
        """統計データの実数値を取得する（Step 3）。

        Args:
            stats_data_id: 統計表 ID
            cd_area: 地域コード（例: "13000"=東京都, "00000"=全国）
            cd_cat01: 分類コード（get_meta_info の CLASS_OBJ で確認）
            cd_time: 時間軸コード（例: "2021000000"）
            limit: 取得件数上限
            start_position: 取得開始位置（ページネーション）

        Returns:
            STATISTICAL_DATA ブロック。DATA_INF.VALUE に数値リストが入る。
        """
        params: dict[str, Any] = {**self._base_params(), "statsDataId": stats_data_id}
        if cd_area:
            params["cdArea"] = cd_area
        if cd_cat01:
            params["cdCat01"] = cd_cat01
        if cd_time:
            params["cdTime"] = cd_time
        if limit is not None:
            params["limit"] = limit
        if start_position is not None:
            params["startPosition"] = start_position

        cache_key = cache.make_key(
            "estat:data",
            {k: v for k, v in params.items() if k != "appId"},
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        try:
            data = await self.get_json("getStatsData", params)
        except HttpClientError as exc:
            raise EStatApiError(f"getStatsData 通信エラー: {exc}") from exc

        root = data.get("GET_STATS_DATA", {})
        self._check_result(root.get("RESULT", {}), "getStatsData")

        stat_data: dict[str, Any] = root.get("STATISTICAL_DATA", {})
        cache.store(cache_key, stat_data, _TTL_SECONDS)
        return stat_data
