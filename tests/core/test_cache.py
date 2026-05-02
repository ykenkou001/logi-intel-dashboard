"""core/cache.py の単体テスト。"""
import time
from pathlib import Path

import pytest

from core import cache


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """テストごとに一時 DB を使用する。"""
    monkeypatch.setattr(cache, "_DB_PATH", tmp_path / "test_cache.db")


def test_store_and_get() -> None:
    """保存したデータを取得できる。"""
    cache.store("test:key", {"value": 42}, ttl_seconds=60)
    result = cache.get("test:key")
    assert result == {"value": 42}


def test_get_missing_key() -> None:
    """存在しないキーは None を返す。"""
    assert cache.get("nonexistent") is None


def test_get_expired() -> None:
    """TTL 切れのエントリは None を返す。"""
    cache.store("test:expired", {"value": 1}, ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get("test:expired") is None


def test_get_stale_returns_expired_entry_within_max_age() -> None:
    """get_stale は期限切れだが最大経過時間内のエントリを返す。"""
    cache.store("test:stale", {"value": 1}, ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get_stale("test:stale", max_age_seconds=60) == {"value": 1}


def test_get_stale_ignores_fresh_entry() -> None:
    """get_stale は fresh なエントリを返さない。"""
    cache.store("test:fresh", {"value": 1}, ttl_seconds=60)
    assert cache.get_stale("test:fresh", max_age_seconds=60) is None


def test_get_stale_ignores_too_old_entry() -> None:
    """get_stale は最大経過時間を超えたエントリを返さない。"""
    cache.store("test:too_old", {"value": 1}, ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get_stale("test:too_old", max_age_seconds=1) is None


def test_store_overwrites() -> None:
    """同じキーに書き込むと上書きされる。"""
    cache.store("test:overwrite", {"v": 1}, ttl_seconds=60)
    cache.store("test:overwrite", {"v": 2}, ttl_seconds=60)
    assert cache.get("test:overwrite") == {"v": 2}


def test_cache_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    """LOGI_CACHE_BYPASS=1 では常に None を返す。"""
    cache.store("test:bypass", {"v": 1}, ttl_seconds=60)
    monkeypatch.setenv("LOGI_CACHE_BYPASS", "1")
    assert cache.get("test:bypass") is None


def test_make_key_excludes_app_id() -> None:
    """appId の違いはキーに影響しない（シークレット除外の確認）。"""
    key1 = cache.make_key("prefix", {"appId": "secret1", "param": "val"})
    key2 = cache.make_key("prefix", {"appId": "secret2", "param": "val"})
    assert key1 == key2


def test_make_key_differs_by_params() -> None:
    """パラメータが異なればキーも異なる。"""
    key1 = cache.make_key("prefix", {"param": "val1"})
    key2 = cache.make_key("prefix", {"param": "val2"})
    assert key1 != key2


def test_store_list() -> None:
    """list データも保存・取得できる。"""
    data = [{"id": "001", "name": "運輸業"}, {"id": "002", "name": "倉庫業"}]
    cache.store("test:list", data, ttl_seconds=60)
    assert cache.get("test:list") == data


# ---- 燃料価格履歴テーブル ----


def test_insert_and_get_fuel_price_history() -> None:
    """履歴に追記して取得できる。"""
    cache.insert_fuel_price_record(
        date_str="2026-04-30",
        source="gogo.gs",
        regular=168.5,
        diesel=148.0,
        kerosene=110.0,
    )
    history = cache.get_fuel_price_history()
    assert len(history) == 1
    row = history[0]
    assert row["date"] == "2026-04-30"
    assert row["regular"] == 168.5


def test_insert_fuel_price_dedup_on_same_date_source() -> None:
    """同じ date+source の重複は INSERT OR IGNORE で 1 行のまま。"""
    cache.insert_fuel_price_record("2026-04-30", "gogo.gs", 168.0, 148.0, 110.0)
    cache.insert_fuel_price_record("2026-04-30", "gogo.gs", 999.0, 999.0, 999.0)
    history = cache.get_fuel_price_history()
    assert len(history) == 1
    # 最初のレコードが残る
    assert history[0]["regular"] == 168.0


def test_insert_fuel_price_empty_date_no_op() -> None:
    """date 空文字なら何も挿入しない。"""
    cache.insert_fuel_price_record("", "gogo.gs", 100.0, 100.0, 100.0)
    history = cache.get_fuel_price_history()
    assert len(history) == 0


def test_get_fuel_price_history_filter_by_source() -> None:
    """source で絞り込める。"""
    cache.insert_fuel_price_record("2026-04-30", "gogo.gs", 168.0, 148.0, 110.0)
    cache.insert_fuel_price_record("2026-04-30", "other", 200.0, 180.0, 130.0)
    gogogs_only = cache.get_fuel_price_history(source="gogo.gs")
    assert len(gogogs_only) == 1
    assert gogogs_only[0]["source"] == "gogo.gs"


def test_get_fuel_price_history_orders_by_date_asc() -> None:
    """日付昇順で並ぶ。"""
    cache.insert_fuel_price_record("2026-05-01", "gogo.gs", 169.0, 149.0, 111.0)
    cache.insert_fuel_price_record("2026-04-29", "gogo.gs", 168.0, 148.0, 110.0)
    cache.insert_fuel_price_record("2026-04-30", "gogo.gs", 168.5, 148.5, 110.5)
    history = cache.get_fuel_price_history()
    assert [r["date"] for r in history] == ["2026-04-29", "2026-04-30", "2026-05-01"]
