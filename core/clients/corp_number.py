"""国税庁 法人番号 API クライアント。

認証: クエリパラメータ id（環境変数 CORP_NUMBER_APP_ID）
エンドポイント: https://api.houjin-bangou.nta.go.jp/4/name
書式: type=02（CSV / UTF-8）で取得し、仕様書で定義された 30 列の項目順に従って
      dict 化する。v4 API は JSON 形式を提供しない（type=12 は XML）ため CSV を採用。
"""

from __future__ import annotations

import csv
import io
from typing import Any, cast

from core import cache
from core.clients.base import AsyncHTTPClient, HttpClientError
from core.secrets import get_secret

_BASE_URL = "https://api.houjin-bangou.nta.go.jp/4/"
_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 日

# 法人番号 Web-API v4 仕様 §3「提供データの内容」の corporation 行の項目順
_CORP_COLUMNS: tuple[str, ...] = (
    "sequenceNumber",
    "corporateNumber",
    "process",
    "correct",
    "updateDate",
    "changeDate",
    "name",
    "nameImageId",
    "kind",
    "prefectureName",
    "cityName",
    "streetNumber",
    "addressImageId",
    "prefectureCode",
    "cityCode",
    "postCode",
    "addressOutside",
    "addressOutsideImageId",
    "closeDate",
    "closeCause",
    "successorCorporateNumber",
    "changeCause",
    "assignmentDate",
    "latest",
    "enName",
    "enPrefectureName",
    "enCityName",
    "enAddressOutside",
    "furigana",
    "hihyoji",
)


class CorpNumberApiError(Exception):
    """国税庁法人番号 API エラー。"""


class CorpNumberClient(AsyncHTTPClient):
    """国税庁 法人番号 API クライアント。

    環境変数 CORP_NUMBER_APP_ID からアプリケーション ID を読み込む。
    レスポンスは 30 日 SQLite にキャッシュされる。
    """

    def __init__(self) -> None:
        super().__init__(_BASE_URL)
        app_id = get_secret("CORP_NUMBER_APP_ID") or ""
        if not app_id:
            raise CorpNumberApiError("環境変数 CORP_NUMBER_APP_ID が設定されていません")
        self._app_id = app_id

    def _mask_params(self, params: dict[str, Any]) -> dict[str, str]:
        """id（applicationID）も含めてマスクする。"""
        base = super()._mask_params(params)
        return {k: "***" if k == "id" else v for k, v in base.items()}

    def _base_params(self) -> dict[str, str]:
        # type=02: CSV UTF-8。v4 API には JSON 形式が存在しないため CSV を採用。
        return {"id": self._app_id, "type": "02"}

    async def search_by_name(
        self,
        name: str,
        prefecture_code: str | None = None,
        kind: str = "03",
        page: int = 1,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """法人名で検索する。

        Args:
            name: 法人名（前方一致）
            prefecture_code: 都道府県コード（"13"=東京, 省略可）
            kind: 法人種別（"01"=国の機関, "02"=地方公共団体, "03"=設立登記法人）
            page: 分割ページ番号（1 始まり / NTA API の `divide` に対応）
            count: 呼び出し側に返す件数の上限（API は最大 4000 件/ページ固定。
                クライアント側でスライスする）

        Returns:
            corporation 情報の dict リスト。各要素は _CORP_COLUMNS の項目名をキーに持つ。
        """
        params: dict[str, Any] = {
            **self._base_params(),
            "name": name,
            "kind": kind,
            "divide": str(page),
        }
        if prefecture_code:
            params["prefecture"] = prefecture_code

        cache_key = cache.make_key("corp:name", {k: v for k, v in params.items() if k != "id"})
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)[:count]

        try:
            text = await self.get_html("name", params)
        except HttpClientError as exc:
            raise CorpNumberApiError(f"法人名検索エラー: {exc}") from exc

        corporations = _parse_csv(text)
        cache.store(cache_key, corporations, _TTL_SECONDS)
        return corporations[:count]


def _parse_csv(text: str) -> list[dict[str, Any]]:
    """NTA v4 法人番号 API の CSV レスポンスを dict のリストへ変換する。

    1 行目は `lastUpdateDate, count, divideNumber, divideSize` のサマリヘッダ。
    2 行目以降が 法人情報レコード（_CORP_COLUMNS の項目順）。
    """
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if len(rows) <= 1:
        return []
    corporations: list[dict[str, Any]] = []
    for row in rows[1:]:
        if not row:
            continue
        record: dict[str, Any] = {
            col: (row[i] if i < len(row) else "") for i, col in enumerate(_CORP_COLUMNS)
        }
        corporations.append(record)
    return corporations
