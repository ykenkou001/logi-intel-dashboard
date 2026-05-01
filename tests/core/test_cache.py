"""core/cache.py の単体テスト。"""
import time

import pytest

from core import cache


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """テストごとに一時 DB を使用する。"""
    monkeypatch.setattr(cache, "_DB_PATH", tmp_path / "test_cache.db")  # type: ignore[attr-defined]


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
