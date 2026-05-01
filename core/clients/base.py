"""httpx ベースの非同期 HTTP クライアント基底クラス。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)

_SECRET_PARAMS = frozenset({"appId", "app_id", "apiKey", "api_key", "applicationID"})


class HttpClientError(Exception):
    """HTTP クライアントの通信エラー。"""


class AsyncHTTPClient:
    """リトライ・バックオフ付き非同期 HTTP クライアント。

    サブクラスは __aenter__/__aexit__ を経由して使う。
    API キーはログにマスクされる。
    """

    def __init__(
        self,
        base_url: str,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _mask_params(self, params: dict[str, Any]) -> dict[str, str]:
        """ログ出力用にシークレット値を *** に置換する。"""
        return {k: "***" if k in _SECRET_PARAMS else str(v) for k, v in params.items()}

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """リトライ・バックオフ付き GET リクエスト。レスポンスを JSON で返す。"""
        if self._client is None:
            raise HttpClientError("async with 経由で使用してください")

        params = params or {}
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                logger.debug("GET %s params=%s", path, self._mask_params(params))
                resp = await self._client.get(path, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                # 4xx はリトライしても無意味
                if exc.response.status_code < 500:
                    raise HttpClientError(
                        f"HTTP {exc.response.status_code}: {path}"
                    ) from exc
                last_exc = exc
            except httpx.RequestError as exc:
                last_exc = exc

            wait = self._backoff_factor * (2**attempt)
            logger.warning(
                "リトライ %d/%d: %.1f 秒待機 (%s)", attempt + 1, self._max_retries, wait, last_exc
            )
            await asyncio.sleep(wait)

        raise HttpClientError(
            f"{self._max_retries} 回リトライ後も失敗: {path}"
        ) from last_exc
