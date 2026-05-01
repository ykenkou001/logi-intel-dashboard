"""core/clients/estat.py の単体テスト。HTTP 通信はモックする。"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from core.clients.estat import EStatApiError, EStatClient

# ---- フィクスチャ: e-Stat API レスポンスサンプル ----

SEARCH_RESPONSE: dict[str, Any] = {
    "GET_STATS_LIST": {
        "RESULT": {"STATUS": 0, "ERROR_MSG": "正常終了", "DATE": "2024-01-01"},
        "DATALIST_INF": {
            "NUMBER": 1,
            "TABLE_INF": [
                {
                    "@id": "0003410379",
                    "STAT_NAME": {"@code": "00200552", "$": "経済センサス－活動調査"},
                    "TITLE": {"@no": "001", "$": "産業別事業所数－都道府県"},
                }
            ],
        },
    }
}

META_RESPONSE: dict[str, Any] = {
    "GET_META_INFO": {
        "RESULT": {"STATUS": 0, "ERROR_MSG": "正常終了"},
        "METADATA_INF": {
            "CLASS_INF": {
                "CLASS_OBJ": [
                    {
                        "@id": "cat01",
                        "@name": "産業",
                        "CLASS": [
                            {"@code": "H", "@name": "運輸業，郵便業", "@level": "1"},
                            {"@code": "H44", "@name": "道路貨物運送業", "@level": "2"},
                        ],
                    },
                    {
                        "@id": "area",
                        "@name": "地域",
                        "CLASS": [
                            {"@code": "00000", "@name": "全国"},
                            {"@code": "13000", "@name": "東京都"},
                        ],
                    },
                ]
            }
        },
    }
}

DATA_RESPONSE: dict[str, Any] = {
    "GET_STATS_DATA": {
        "RESULT": {"STATUS": 0, "ERROR_MSG": "正常終了"},
        "STATISTICAL_DATA": {
            "RESULT_INF": {"TOTAL_NUMBER": 2, "FROM_NUMBER": 1, "TO_NUMBER": 2},
            "DATA_INF": {
                "VALUE": [
                    {"@cat01": "H", "@area": "13000", "@time": "2021000000",
                     "@unit": "事業所", "$": "15234"},
                    {"@cat01": "H44", "@area": "13000", "@time": "2021000000",
                     "@unit": "事業所", "$": "8921"},
                ]
            },
        },
    }
}

ERROR_RESPONSE: dict[str, Any] = {
    "GET_STATS_LIST": {
        "RESULT": {"STATUS": 100, "ERROR_MSG": "appId が不正です"},
        "DATALIST_INF": {},
    }
}

# ---- ヘルパー ----


def make_mock_get_json(response: dict[str, Any]) -> Any:
    """get_json をモックする AsyncMock を作る。"""
    mock = AsyncMock(return_value=response)
    return mock


# ---- テスト ----


@pytest.fixture
def app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ESTAT_APP_ID", "test_app_id_12345")


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """テスト時はキャッシュを無効化する。"""
    monkeypatch.setenv("LOGI_CACHE_BYPASS", "1")


def test_estat_client_requires_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """ESTAT_APP_ID 未設定で EStatApiError を送出する。"""
    monkeypatch.delenv("ESTAT_APP_ID", raising=False)
    with pytest.raises(EStatApiError, match="ESTAT_APP_ID"):
        EStatClient()


@pytest.mark.asyncio
async def test_search_stats_returns_tables(app_id: None) -> None:
    """正常レスポンスからテーブルリストを返す。"""
    with patch.object(EStatClient, "get_json", make_mock_get_json(SEARCH_RESPONSE)):
        async with EStatClient() as client:
            tables = await client.search_stats(search_word="運輸業")
    assert len(tables) == 1
    assert tables[0]["@id"] == "0003410379"


@pytest.mark.asyncio
async def test_search_stats_single_table_as_list(app_id: None) -> None:
    """TABLE_INF が dict 単体の場合も list に変換される。"""
    response: dict[str, Any] = {
        "GET_STATS_LIST": {
            "RESULT": {"STATUS": 0},
            "DATALIST_INF": {
                "NUMBER": 1,
                "TABLE_INF": {"@id": "single", "TITLE": {"$": "1件のみ"}},
            },
        }
    }
    with patch.object(EStatClient, "get_json", make_mock_get_json(response)):
        async with EStatClient() as client:
            tables = await client.search_stats(search_word="test")
    assert isinstance(tables, list)
    assert tables[0]["@id"] == "single"


@pytest.mark.asyncio
async def test_search_stats_api_error(app_id: None) -> None:
    """STATUS=100（認証エラー）で EStatApiError を送出する。"""
    with patch.object(EStatClient, "get_json", make_mock_get_json(ERROR_RESPONSE)):
        async with EStatClient() as client:
            with pytest.raises(EStatApiError, match="STATUS=100"):
                await client.search_stats(search_word="運輸業")


@pytest.mark.asyncio
async def test_get_meta_info(app_id: None) -> None:
    """getMetaInfo のレスポンスから CLASS_INF を返す。"""
    with patch.object(EStatClient, "get_json", make_mock_get_json(META_RESPONSE)):
        async with EStatClient() as client:
            meta = await client.get_meta_info("0003410379")
    class_objs = meta["CLASS_INF"]["CLASS_OBJ"]
    assert len(class_objs) == 2
    assert class_objs[0]["@id"] == "cat01"


@pytest.mark.asyncio
async def test_get_stats_data_returns_values(app_id: None) -> None:
    """getStatsData のレスポンスから STATISTICAL_DATA を返す。"""
    with patch.object(EStatClient, "get_json", make_mock_get_json(DATA_RESPONSE)):
        async with EStatClient() as client:
            data = await client.get_stats_data("0003410379", cd_area="13000")
    values = data["DATA_INF"]["VALUE"]
    assert len(values) == 2
    assert values[0]["$"] == "15234"


@pytest.mark.asyncio
async def test_get_stats_data_status_1_ok(app_id: None) -> None:
    """STATUS=1（データなし・正常）でエラーにならない。"""
    response: dict[str, Any] = {
        "GET_STATS_DATA": {
            "RESULT": {"STATUS": 1, "ERROR_MSG": "該当データなし"},
            "STATISTICAL_DATA": {"DATA_INF": {"VALUE": []}},
        }
    }
    with patch.object(EStatClient, "get_json", make_mock_get_json(response)):
        async with EStatClient() as client:
            data = await client.get_stats_data("0003410379")
    assert data["DATA_INF"]["VALUE"] == []
