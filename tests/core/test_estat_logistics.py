"""core/clients/estat_logistics.py の単体テスト。HTTP 通信はモックする。"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from core.clients.estat import EStatApiError, EStatClient
from core.clients.estat_logistics import EStatLogisticsClient

# ---- フィクスチャ: 自動車輸送統計年報の検索レスポンス ----

AUTO_TRANSPORT_LIST_RESPONSE: dict[str, Any] = {
    "GET_STATS_LIST": {
        "RESULT": {"STATUS": 0},
        "DATALIST_INF": {
            "NUMBER": 3,
            "TABLE_INF": [
                {
                    "@id": "0003480000",
                    "STAT_NAME": {"@code": "00600340", "$": "自動車輸送統計年報"},
                    "TITLE": {"$": "営業用貨物自動車 積載率"},
                    "OPEN_DATE": "2023-12-25",
                    "SURVEY_DATE": "2022",
                },
                {
                    "@id": "0003490000",
                    "STAT_NAME": {"@code": "00600340", "$": "自動車輸送統計年報"},
                    "TITLE": {"$": "営業用貨物自動車 積載率"},
                    "OPEN_DATE": "2024-12-25",
                    "SURVEY_DATE": "2023",
                },
                {
                    "@id": "0003495000",
                    "STAT_NAME": {"@code": "00600340", "$": "自動車輸送統計年報"},
                    "TITLE": {"$": "車種別走行距離"},
                    "OPEN_DATE": "2024-12-25",
                    "SURVEY_DATE": "2023",
                },
            ],
        },
    }
}

EMPTY_LIST_RESPONSE: dict[str, Any] = {
    "GET_STATS_LIST": {
        "RESULT": {"STATUS": 1, "ERROR_MSG": "該当データなし"},
        "DATALIST_INF": {"NUMBER": 0, "TABLE_INF": []},
    }
}

DATA_RESPONSE: dict[str, Any] = {
    "GET_STATS_DATA": {
        "RESULT": {"STATUS": 0},
        "STATISTICAL_DATA": {
            "DATA_INF": {
                "VALUE": [
                    {"@area": "00000", "@unit": "%", "$": "39.2"},
                ]
            }
        },
    }
}


# ---- ヘルパー ----


def make_mock_get_json(*responses: dict[str, Any]) -> AsyncMock:
    """get_json をモックする。複数渡すと呼出毎に順番に返す。"""
    if len(responses) == 1:
        return AsyncMock(return_value=responses[0])
    return AsyncMock(side_effect=list(responses))


# ---- フィクスチャ ----


@pytest.fixture
def app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ESTAT_APP_ID", "test_app_id_12345")


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_CACHE_BYPASS", "1")


# ---- テスト ----


def test_resolve_stats_code_known_dataset(app_id: None) -> None:
    """既知のデータセット名から正しい statsCode を返す。"""
    client = EStatLogisticsClient()
    assert client._resolve_stats_code("auto_transport") == "00600340"
    assert client._resolve_stats_code("freight_census") == "00600370"
    assert client._resolve_stats_code("population_census") == "00200521"


def test_resolve_stats_code_unknown_dataset(app_id: None) -> None:
    """未知のデータセット名で EStatApiError を送出する。"""
    client = EStatLogisticsClient()
    with pytest.raises(EStatApiError, match="未知のデータセット"):
        client._resolve_stats_code("unknown_dataset")


@pytest.mark.asyncio
async def test_search_logistics_tables_returns_list(app_id: None) -> None:
    """物流統計表の検索結果が返る。"""
    with patch.object(
        EStatClient, "get_json", make_mock_get_json(AUTO_TRANSPORT_LIST_RESPONSE)
    ):
        async with EStatLogisticsClient() as client:
            tables = await client.search_logistics_tables("auto_transport")
    assert len(tables) == 3
    assert all(t["STAT_NAME"]["@code"] == "00600340" for t in tables)


@pytest.mark.asyncio
async def test_find_latest_stats_data_id_picks_newest(app_id: None) -> None:
    """OPEN_DATE 最新の statsDataId が返る。"""
    with patch.object(
        EStatClient, "get_json", make_mock_get_json(AUTO_TRANSPORT_LIST_RESPONSE)
    ):
        async with EStatLogisticsClient() as client:
            stats_id = await client.find_latest_stats_data_id("auto_transport")
    # 2024-12-25 公開のうち @id 降順で先頭
    assert stats_id == "0003495000"


@pytest.mark.asyncio
async def test_find_latest_stats_data_id_with_title_keyword(app_id: None) -> None:
    """title_keyword で絞り込んでから最新を選ぶ。"""
    with patch.object(
        EStatClient, "get_json", make_mock_get_json(AUTO_TRANSPORT_LIST_RESPONSE)
    ):
        async with EStatLogisticsClient() as client:
            stats_id = await client.find_latest_stats_data_id(
                "auto_transport",
                title_keyword="積載率",
            )
    # 「積載率」表のうち最新（2024-12-25）
    assert stats_id == "0003490000"


@pytest.mark.asyncio
async def test_find_latest_stats_data_id_no_match_raises(app_id: None) -> None:
    """該当表がない場合 EStatApiError を送出する。"""
    with patch.object(EStatClient, "get_json", make_mock_get_json(EMPTY_LIST_RESPONSE)):
        async with EStatLogisticsClient() as client:
            with pytest.raises(EStatApiError, match="該当する統計表が見つかりません"):
                await client.find_latest_stats_data_id("auto_transport")


@pytest.mark.asyncio
async def test_get_stats_data_by_dataset_resolves_and_fetches(app_id: None) -> None:
    """データセット指定で statsDataId 解決 → getStatsData まで一気通貫で動く。"""
    # 1回目: getStatsList、2回目: getStatsData
    mock = make_mock_get_json(AUTO_TRANSPORT_LIST_RESPONSE, DATA_RESPONSE)
    with patch.object(EStatClient, "get_json", mock):
        async with EStatLogisticsClient() as client:
            data = await client.get_stats_data_by_dataset(
                "auto_transport",
                title_keyword="積載率",
                cd_area="00000",
            )
    values = data["DATA_INF"]["VALUE"]
    assert values[0]["$"] == "39.2"
    # getStatsList と getStatsData の2回呼ばれている
    assert mock.call_count == 2


def test_stats_codes_catalog_is_complete(app_id: None) -> None:
    """物流必修統計の statsCode カタログに必要な項目が含まれる。"""
    expected = {
        "auto_transport",
        "freight_census",
        "port",
        "rail_freight",
        "economic_census",
        "wage_structure",
        "population_census",
    }
    assert set(EStatLogisticsClient.STATS_CODES.keys()) >= expected
