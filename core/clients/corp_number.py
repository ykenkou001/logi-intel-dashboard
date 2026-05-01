"""国税庁 法人番号 API クライアント。

認証: クエリパラメータ id（環境変数 CORP_NUMBER_APP_ID）
エンドポイント: https://api.houjin-bangou.nta.go.jp/4/
"""
from __future__ import annotations

import os
from typing import Any, cast

from core import cache
from core.clients.base import AsyncHTTPClient, HttpClientError

_BASE_URL = "https://api.houjin-bangou.nta.go.jp/4/"
_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 日


class CorpNumberApiError(Exception):
    """国税庁法人番号 API エラー。"""


class CorpNumberClient(AsyncHTTPClient):
    """国税庁 法人番号 API クライアント。

    環境変数 CORP_NUMBER_APP_ID からアプリケーション ID を読み込む。
    レスポンスは 30 日 SQLite にキャッシュされる。
    """

    def __init__(self) -> None:
        super().__init__(_BASE_URL)
        app_id = os.environ.get("CORP_NUMBER_APP_ID", "")
        if not app_id:
            raise CorpNumberApiError("環境変数 CORP_NUMBER_APP_ID が設定されていません")
        self._app_id = app_id

    def _mask_params(self, params: dict[str, Any]) -> dict[str, str]:
        """id（applicationID）も含めてマスクする。"""
        base = super()._mask_params(params)
        return {k: "***" if k == "id" else v for k, v in base.items()}

    def _base_params(self) -> dict[str, str]:
        return {"id": self._app_id, "type": "12"}  # type=12 は JSON 形式

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
            name: 法人名（部分一致）
            prefecture_code: 都道府県コード（"13"=東京, 省略可）
            kind: 法人種別（"01"=国の機関, "02"=地方公共団体, "03"=設立登記法人）
            page: ページ番号（1 始まり）
            count: 1ページあたりの件数（最大 2000）

        Returns:
            corporation リスト。各要素に corporateNumber・name・prefectureName 等が入る。
        """
        params: dict[str, Any] = {
            **self._base_params(),
            "name": name,
            "kind": kind,
            "from": str((page - 1) * count + 1),
            "count": str(count),
            "close": "0",
        }
        if prefecture_code:
            params["prefecture"] = prefecture_code

        cache_key = cache.make_key("corp:name", {k: v for k, v in params.items() if k != "id"})
        cached = cache.get(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached)

        try:
            data = await self.get_json("name.json", params)
        except HttpClientError as exc:
            raise CorpNumberApiError(f"法人名検索エラー: {exc}") from exc

        corporations = data.get("corporation", [])
        if isinstance(corporations, dict):
            corporations = [corporations]

        cache.store(cache_key, corporations, _TTL_SECONDS)
        return cast(list[dict[str, Any]], corporations)
