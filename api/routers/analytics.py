"""GA4 Measurement Protocol プロキシエンドポイント。

ブラウザのアドブロッカー（uBlock Origin / Brave 等）は
`www.google-analytics.com` への送信を弾くため、同一 origin の
`/api/v1/analytics/collect` で一度受けてからサーバー側で GA4 に転送する。

設計方針:
    - URL の query string は PII（法人番号・会社名等）が含まれる可能性があるため
      サーバー側で除去してから GA4 に送る
    - 環境変数 `GA4_MEASUREMENT_ID` / `GA4_API_SECRET` が未設定なら 204 を返し
      クライアント側のロジックを壊さない（PoC で計測オフのまま開発できるようにする）
    - GA4 Measurement Protocol はサーバー経由送信で IP/UA を保持できない仕様のため、
      地理情報の精度は犠牲にして `client_id` ベースの識別のみ行う
    - 改正電気通信事業法（外部送信規律）への対応として、Web フロント側の
      フッターに「外部送信先: Google Analytics」を明示している
"""

from __future__ import annotations

import logging
import os
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Body, Response, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# GA4 Measurement Protocol。
# `GA4_DEBUG=1` で validation errors を返す debug エンドポイントに切り替え。
GA4_ENDPOINT = "https://www.google-analytics.com/mp/collect"
GA4_DEBUG_ENDPOINT = "https://www.google-analytics.com/debug/mp/collect"


class AnalyticsEventParams(BaseModel):
    """GA4 イベントのパラメータ。

    GA4 Measurement Protocol の `events[].params` に対応する。
    `page_location` は query string がサーバー側で除去される。
    """

    page_location: str | None = Field(default=None, description="絶対 URL（query は除去される）")
    page_title: str | None = Field(default=None, max_length=300)
    page_referrer: str | None = Field(default=None)
    engagement_time_msec: int | None = Field(default=None, ge=0, le=60 * 60 * 1000)
    session_id: str | None = Field(default=None, max_length=64)


class AnalyticsEvent(BaseModel):
    """GA4 に送る単一イベント。"""

    name: str = Field(min_length=1, max_length=40, description="イベント名（例: page_view）")
    params: AnalyticsEventParams = Field(default_factory=AnalyticsEventParams)


class AnalyticsPayload(BaseModel):
    """ブラウザから受け取る計測ペイロード。"""

    client_id: str = Field(min_length=1, max_length=128, description="ブラウザ単位の永続 UUID")
    events: list[AnalyticsEvent] = Field(min_length=1, max_length=25)


def _strip_query(url: str | None) -> str | None:
    """URL から query string と fragment を除去する（PII 漏洩防止）。"""
    if not url:
        return url
    try:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except ValueError:
        return None


@router.post(
    "/collect",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="GA4 Measurement Protocol プロキシ",
)
async def collect(
    payload: Annotated[AnalyticsPayload, Body()],
) -> Response:
    """ブラウザから受けた計測イベントを GA4 に転送する。

    GA4 設定が無い場合でも 204 を返し、クライアント側の処理を妨げない。
    """
    measurement_id = os.environ.get("GA4_MEASUREMENT_ID")
    api_secret = os.environ.get("GA4_API_SECRET")
    if not measurement_id or not api_secret:
        logger.warning(
            "[analytics] GA4 disabled (measurement_id=%s api_secret=%s)",
            "set" if measurement_id else "MISSING",
            "set" if api_secret else "MISSING",
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    sanitized_events: list[dict[str, object]] = []
    for event in payload.events:
        params: dict[str, object] = {}
        if event.params.page_location:
            params["page_location"] = _strip_query(event.params.page_location)
        if event.params.page_title:
            params["page_title"] = event.params.page_title
        if event.params.page_referrer:
            params["page_referrer"] = _strip_query(event.params.page_referrer)
        if event.params.engagement_time_msec is not None:
            params["engagement_time_msec"] = event.params.engagement_time_msec
        if event.params.session_id:
            params["session_id"] = event.params.session_id
        sanitized_events.append({"name": event.name, "params": params})

    # GA4 Measurement Protocol のトップレベルで許可されるフィールドは
    # client_id / user_id / timestamp_micros / user_properties / consent /
    # non_personalized_ads / events のみ。Measurement Protocol は HTTP の IP/UA を
    # 自動取得しないため、サーバー経由送信では IP/UA は失われる（PoC では許容）。
    ga_body: dict[str, object] = {
        "client_id": payload.client_id,
        "events": sanitized_events,
    }

    endpoint = GA4_DEBUG_ENDPOINT if os.environ.get("GA4_DEBUG") == "1" else GA4_ENDPOINT
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            ga_resp = await client.post(
                endpoint,
                params={"measurement_id": measurement_id, "api_secret": api_secret},
                json=ga_body,
            )
            logger.warning(
                "[analytics] GA4 status=%s events=%s body=%s",
                ga_resp.status_code,
                [e["name"] for e in sanitized_events],
                ga_resp.text[:500] if ga_resp.text else "(empty)",
            )
    except httpx.HTTPError as exc:
        logger.warning("[analytics] GA4 forward failed: %s", exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
