"""core/clients/corp_number.py の単体テスト。

NTA v4 API は CSV(UTF-8) を返すので、`get_html` をモックして CSV 文字列を渡す。
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.clients.corp_number import CorpNumberApiError, CorpNumberClient

# NTA v4 仕様の 30 列にダミー値を詰めた CSV（クォート・空欄含む）
SEARCH_CSV = (
    "2024-01-01,2,1,1\r\n"
    '1,1234567890123,01,0,2024-01-01,2024-01-01,"ヤマト運輸株式会社",,301,'
    '"東京都","中央区","XX",,13,102,1000001,,,,,,,2018-11-30,1,,,,,,\r\n'
    '2,9876543210987,01,0,2024-01-01,2024-01-01,"佐川急便株式会社",,301,'
    '"京都府","南区","YY",,26,109,6010001,,,,,,,2018-11-30,1,,,,,,\r\n'
)

SINGLE_CORP_CSV = (
    "2024-01-01,1,1,1\r\n"
    '1,1111111111111,01,0,2024-01-01,2024-01-01,"テスト運送株式会社",,301,'
    '"大阪府","北区","ZZ",,27,127,5300001,,,,,,,2018-11-30,1,,,,,,\r\n'
)

EMPTY_CSV = "2024-01-01,0,1,1\r\n"


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
    with patch.object(CorpNumberClient, "get_html", return_value=SEARCH_CSV):
        async with CorpNumberClient() as client:
            result = await client.search_by_name("運輸")
    assert len(result) == 2
    assert result[0]["name"] == "ヤマト運輸株式会社"
    assert result[0]["corporateNumber"] == "1234567890123"
    assert result[0]["prefectureName"] == "東京都"
    assert result[0]["cityName"] == "中央区"
    assert result[1]["name"] == "佐川急便株式会社"


@pytest.mark.asyncio
async def test_search_by_name_single_record(app_id: None) -> None:
    """単一ヒットでも list で返る。"""
    with patch.object(CorpNumberClient, "get_html", return_value=SINGLE_CORP_CSV):
        async with CorpNumberClient() as client:
            result = await client.search_by_name("テスト")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "テスト運送株式会社"


@pytest.mark.asyncio
async def test_search_empty_returns_empty_list(app_id: None) -> None:
    """ヒットゼロの CSV（ヘッダ行のみ）は空 list として返る。"""
    with patch.object(CorpNumberClient, "get_html", return_value=EMPTY_CSV):
        async with CorpNumberClient() as client:
            result = await client.search_by_name("該当なし")
    assert result == []


@pytest.mark.asyncio
async def test_search_with_prefecture_filter(app_id: None) -> None:
    with patch.object(CorpNumberClient, "get_html", return_value=SEARCH_CSV) as mock:
        async with CorpNumberClient() as client:
            await client.search_by_name("運輸", prefecture_code="13")
    call_params = mock.call_args[0][1]
    assert call_params.get("prefecture") == "13"
    assert call_params.get("type") == "02"


@pytest.mark.asyncio
async def test_count_slices_result(app_id: None) -> None:
    """count 引数は呼び出し側へ返す件数の上限として機能する。"""
    with patch.object(CorpNumberClient, "get_html", return_value=SEARCH_CSV):
        async with CorpNumberClient() as client:
            result = await client.search_by_name("運輸", count=1)
    assert len(result) == 1
    assert result[0]["name"] == "ヤマト運輸株式会社"


@pytest.mark.asyncio
async def test_endpoint_path_uses_name_without_extension(app_id: None) -> None:
    """NTA v4 は `/4/name`（拡張子なし）。`name.json` だと 404。"""
    with patch.object(CorpNumberClient, "get_html", return_value=SEARCH_CSV) as mock:
        async with CorpNumberClient() as client:
            await client.search_by_name("運輸")
    assert mock.call_args[0][0] == "name"
