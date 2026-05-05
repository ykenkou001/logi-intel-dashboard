"""静的データの鮮度メタデータ管理。

各静的データソース（CO2 排出原単位・改善基準告示・標準的運賃 等）について
最終更新日と推奨更新間隔を一元管理し、古いデータを Claude の応答に警告として
含められるようにする。

使い方:
    >>> warnings = check_all_freshness()
    >>> for w in warnings:
    ...     print(w.label, w.is_stale)

設計方針:
    - 静的データ各モジュールは `Freshness` インスタンスを `FRESHNESS` 変数で公開
    - 本モジュールで全モジュールを集約し、起動時/MCP 呼出時に一括チェック
    - 鮮度警告は MCP ツールの戻り値 `freshness_warnings` フィールドに含める
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

# 推奨更新間隔のプリセット
_DEFAULT_INTERVALS: dict[str, timedelta] = {
    "annual": timedelta(days=365),       # 年次データ
    "biennial": timedelta(days=730),     # 2年ごと
    "quinquennial": timedelta(days=1825),  # 5年ごと（物流センサス等）
    "as_needed": timedelta(days=10000),  # 改正時のみ更新（告示・省令等）
}


@dataclass(frozen=True)
class Freshness:
    """静的データソースの鮮度メタデータ。

    Attributes:
        label: 表示用ラベル（例: "改善基準告示"）
        last_updated: 最終更新日（データそのものの更新日。コミット日ではない）
        update_cadence: 推奨更新間隔のキー（_DEFAULT_INTERVALS のキー or 任意 timedelta）
        source_url: 一次情報の URL
        notes: 補足（例: "毎年4月に告示改訂チェック"）
    """

    label: str
    last_updated: date
    update_cadence: Literal["annual", "biennial", "quinquennial", "as_needed"]
    source_url: str
    notes: str = ""

    @property
    def recommended_interval(self) -> timedelta:
        return _DEFAULT_INTERVALS[self.update_cadence]

    @property
    def age(self) -> timedelta:
        return date.today() - self.last_updated

    @property
    def is_stale(self) -> bool:
        return self.age > self.recommended_interval

    def warning_text(self) -> str | None:
        """古い場合の警告メッセージ。最新なら None。"""
        if not self.is_stale:
            return None
        days_overdue = (self.age - self.recommended_interval).days
        return (
            f"⚠️ {self.label}: データが {self.age.days} 日経過（推奨間隔超過 +{days_overdue} 日）。"
            f"最新化を検討してください: {self.source_url}"
        )


# 全静的データソースの鮮度レジストリ
# 各 core/static/*.py モジュールがロードされた際に register() で登録する
_REGISTRY: dict[str, Freshness] = {}


def register(key: str, freshness: Freshness) -> None:
    """静的データソースの鮮度を登録する。"""
    _REGISTRY[key] = freshness


def get(key: str) -> Freshness | None:
    return _REGISTRY.get(key)


def all_warnings() -> list[str]:
    """全登録済みデータの鮮度警告（古いものだけ）を返す。"""
    return [w for f in _REGISTRY.values() if (w := f.warning_text()) is not None]


def all_freshness() -> dict[str, Freshness]:
    """全登録済み鮮度メタデータを返す（テスト用）。"""
    return dict(_REGISTRY)
