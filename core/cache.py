"""SQLite ベースの API レスポンスキャッシュ。"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

_DB_PATH = Path(".logi_cache.db")

_DDL = """
CREATE TABLE IF NOT EXISTS api_cache (
    cache_key    TEXT    PRIMARY KEY,
    response_json TEXT   NOT NULL,
    fetched_at   REAL    NOT NULL,
    ttl_seconds  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fetched_at ON api_cache(fetched_at);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.executescript(_DDL)
    return conn


def make_key(prefix: str, params: dict[str, Any]) -> str:
    """プレフィックスとパラメータ辞書からキャッシュキーを生成する。

    appId 等のシークレット値はキー生成対象から除外する。
    """
    safe = {k: v for k, v in params.items() if k not in ("appId", "applicationID", "apiKey")}
    digest = hashlib.sha256(json.dumps(safe, sort_keys=True).encode()).hexdigest()[:16]
    return f"{prefix}:{digest}"


def get(key: str) -> Any:
    """キャッシュから取得する。期限切れまたは未存在なら None。

    LOGI_CACHE_BYPASS=1 が設定されている場合は常に None を返す。
    """
    if os.environ.get("LOGI_CACHE_BYPASS") == "1":
        return None
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT response_json, fetched_at, ttl_seconds FROM api_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
    if row is None:
        return None
    response_json, fetched_at, ttl_seconds = row
    if time.time() - fetched_at > ttl_seconds:
        return None
    return json.loads(response_json)


def store(key: str, data: Any, ttl_seconds: int) -> None:
    """データをキャッシュに保存する。"""
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO api_cache VALUES (?, ?, ?, ?)",
            (key, json.dumps(data, ensure_ascii=False), time.time(), ttl_seconds),
        )
        conn.commit()
