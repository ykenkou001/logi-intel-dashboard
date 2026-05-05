"""ToolResponse を REST API で返すための Pydantic ラッパー。

`core/export/response.ToolResponse` の `to_dict()` 出力をそのまま検証・OpenAPI スキーマ化する。
MCP ツールと REST API でレスポンス構造を完全に一致させることで、
Web フロント・Claude 双方が同じパーサで処理できる。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CitationModel(BaseModel):
    """出典情報。経営会議で「出典は？」と聞かれて即答できるよう全数値に付与する。"""

    label: str = Field(description="表示用ラベル")
    url: str = Field(description="一次情報の URL")
    stats_data_id: str | None = Field(default=None, description="e-Stat の statsDataId")
    notice_number: str | None = Field(default=None, description="告示番号")
    ordinance_number: str | None = Field(default=None, description="省令番号")
    fetched_at: str = Field(description="ISO 8601 形式の取得時刻")
    accessed_via: str | None = Field(default=None, description="取得経路")


class ToolResponseModel(BaseModel):
    """MCP ツール／REST API 共通の戻り値構造。"""

    summary: str = Field(description="人間が読む要約テキスト")
    files: dict[str, str] = Field(
        default_factory=dict,
        description="成果物ファイルの種別キー → 相対パス（/api/v1/files でダウンロード可能）",
    )
    citations: list[CitationModel] = Field(default_factory=list, description="出典情報リスト")
    freshness_warnings: list[str] = Field(
        default_factory=list,
        description="静的データの鮮度警告メッセージ",
    )
    data_source: Literal["sample", "estimated", "actual"] = Field(
        default="estimated",
        description=(
            "入力データの出所。"
            "'sample' はデモ用架空企業（PoC のみ）、"
            "'estimated' はユーザー入力 + 業界統計推計、"
            "'actual' は自社実測データ。"
        ),
    )
    metadata: dict[str, object] | None = Field(
        default=None,
        description=(
            "テキスト要約以外の構造化データ（ヒートマップ cells、KPI snapshot など）。"
            "Web フロントで可視化する際の入力。MCP では summary 中心に表示。"
        ),
    )
