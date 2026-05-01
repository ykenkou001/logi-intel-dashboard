"""core/clients/corp_number.py の単体テスト。"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from core.clients.corp_number import CorpNumberApiError, CorpNumberClient

SEARCH_RESPONSE: dict[str, Any] = {
    "lastUpdateDate": "2024-01-01",
    "count": 2,
    "divideNumber": 1,
    "divideSize": 1,
    "corporation": [
        {
            "sequenceNumber": "1",
            "corporateNumber": "1234567890123",
            "name": "ヤマト運輸株式会社",
            "prefectureName": "東京都",
            "cityName": "中央区",
            "addressOutside": "",
            "kind": "301",
        },
        {
            "sequenceNumber": "2",
            "corporateNumber": "9876543210987",
            "name": "佐川急便株式会社",
            "prefectureName": "京都府",
            "cityName": "南区",
            "addressOutside": "",
            "kind": "301",
        },
    ],
}

SINGLE_CORP_RESPONSE: dict[str, Any] = {
    "count": 1,
    "corporation": {
        "corporateNumber": "1111111111111",
        "name": "テスト運送株式会社",
        "prefectureName": "大阪府",
    },
}


@pytest.fixture
def app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORP_NUMBER_APP_ID", "test_corp_app_id")


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_CACHE_BYPASS", "1")


def test_client_requires_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORP_NUMBER_APP_ID", raising=False)
    with pytest.raises(CorpNumberApiError, match="CORP_NUMBER_APP_ID"):
        CorpNumberClient()


@pytest.mark.asyncio
async def test_search_by_name_returns_list(app_id: None) -> None:
    with patch.object(CorpNumberClient, "get_json", return_value=SEARCH_RESPONSE):
        async with CorpNumberClient() as client:
            result = await client.search_by_name("運輸")
    assert len(result) == 2
    assert result[0]["name"] == "ヤマト運輸株式会社"


@pytest.mark.asyncio
async def test_search_by_name_single_as_list(app_id: None) -> None:
    """corporation が dict 単体の場合も list に変換される。"""
    with patch.object(CorpNumberClient, "get_json", return_value=SINGLE_CORP_RESPONSE):
        async with CorpNumberClient() as client:
            result = await client.search_by_name("テスト")
    assert isinstance(result, list)
    assert result[0]["name"] == "テスト運送株式会社"


@pytest.mark.asyncio
async def test_search_with_prefecture_filter(app_id: None) -> None:
    with patch.object(CorpNumberClient, "get_json", return_value=SEARCH_RESPONSE) as mock:
        async with CorpNumberClient() as client:
            await client.search_by_name("運輸", prefecture_code="13")
    call_params = mock.call_args[0][1]
    assert call_params.get("prefecture") == "13"
