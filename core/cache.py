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

# Lambda の /var/task は read-only。LOGI_CACHE_DB_PATH で /tmp 等に上書きできるようにする。
_DB_PATH = Path(os.environ.get("LOGI_CACHE_DB_PATH", ".logi_cache.db"))

_DDL = """
CREATE TABLE IF NOT EXISTS api_cache (
    cache_key    TEXT    PRIMARY KEY,
    response_json TEXT   NOT NULL,
    fetched_at   REAL    NOT NULL,
    ttl_seconds  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fetched_at ON api_cache(fetched_at);

CREATE TABLE IF NOT EXISTS fuel_price_history (
    date         TEXT    NOT NULL,
    source       TEXT    NOT NULL,
    regular      REAL,
    diesel       REAL,
    kerosene     REAL,
    inserted_at  REAL    NOT NULL,
    PRIMARY KEY (date, source)
);
CREATE INDEX IF NOT EXISTS idx_fuel_date ON fuel_price_history(date);
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


def get_stale(key: str, max_age_seconds: int) -> Any:
    """期限切れを許容してキャッシュを取得する。

    LOGI_CACHE_BYPASS=1 が設定されている場合は常に None を返す。
    max_age_seconds より古い行、または fresh な行は None を返す。
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
    age_seconds = time.time() - fetched_at
    if age_seconds <= ttl_seconds or age_seconds > max_age_seconds:
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


def insert_fuel_price_record(
    date_str: str,
    source: str,
    regular: float | None,
    diesel: float | None,
    kerosene: float | None,
) -> None:
    """燃料価格履歴に1日分を追記する。重複は INSERT OR IGNORE。

    Args:
        date_str: ISO 日付文字列（"2026-04-30"）。空文字列なら何もしない。
        source: ソース識別子（例: "gogo.gs"）
        regular/diesel/kerosene: 円/L 価格（取得できなかったものは None 可）
    """
    if not date_str:
        return
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO fuel_price_history "
            "(date, source, regular, diesel, kerosene, inserted_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (date_str, source, regular, diesel, kerosene, time.time()),
        )
        conn.commit()


def get_fuel_price_history(
    source: str | None = None,
    days: int | None = None,
) -> list[dict[str, Any]]:
    """燃料価格履歴を取得する（古い順）。

    Args:
        source: ソース識別子で絞り込み（例: "gogo.gs"）
        days: 直近 N 日分のみ取得（None なら全件）

    Returns:
        辞書のリスト: {date, source, regular, diesel, kerosene}
    """
    sql = "SELECT date, source, regular, diesel, kerosene FROM fuel_price_history"
    conditions: list[str] = []
    params: list[Any] = []
    if source:
        conditions.append("source = ?")
        params.append(source)
    if days is not None:
        # ISO 日付文字列の比較で直近 N 日
        from datetime import date as _date
        from datetime import timedelta as _timedelta

        cutoff = (_date.today() - _timedelta(days=days)).isoformat()
        conditions.append("date >= ?")
        params.append(cutoff)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY date ASC, source ASC"
    with closing(_connect()) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {"date": r[0], "source": r[1], "regular": r[2], "diesel": r[3], "kerosene": r[4]}
        for r in rows
    ]
