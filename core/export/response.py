"""MCP ツール戻り値の統一構造とファイル名生成ヘルパー。

全 MCP ツールはこの `ToolResponse` 構造で返すことで、CLO 担当者・経営層が
「数字 → ファイル成果物 → 出典」を一貫して取得できる。

設計方針:
    - `summary`: Claude/人間に読ませる要約テキスト
    - `files`: 成果物ファイルの絶対 or 相対パス（種別キー → パス）
    - `citations`: 出典情報のリスト（必須）
    - `freshness_warnings`: 鮮度警告メッセージ
"""
from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from core.export.citation import Citation

# 環境変数 LOGI_OUTPUTS_DIR で書出先を切替（Lambda は "/tmp/outputs" 等）
OUTPUTS_DIR = Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs"))

DataSource = Literal["sample", "estimated", "actual"]
"""データの出所:
- "sample"   : デモ用架空企業のデータ（経営判断には使わない）
- "estimated": ユーザー入力 + 業界統計推計（一部実測なし）
- "actual"   : 自社実測データに基づく
"""


@dataclass
class ToolResponse:
    """MCP ツールの統一戻り値構造。"""

    summary: str
    citations: list[Citation] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    freshness_warnings: list[str] = field(default_factory=list)
    data_source: DataSource = "estimated"
    """入力データの出所。'estimated' は業界統計からの推計値（サンプル3社）、
    'actual' は自社実績データ。経営会議での defensibility 担保のため明示する。"""

    def to_dict(self) -> dict[str, object]:
        """MCP の戻り値として返す dict 形式。"""
        return {
            "summary": self.summary,
            "files": dict(self.files) if self.files else {},
            "citations": [c.to_dict() for c in self.citations],
            "freshness_warnings": list(self.freshness_warnings),
            "data_source": self.data_source,
        }

    def add_citation(self, citation: Citation) -> None:
        self.citations.append(citation)


def make_output_path(
    file_type: str,
    purpose: str,
    company_id: str,
    extension: str,
) -> Path:
    """成果物ファイルの衝突回避命名でパスを生成する。

    形式: outputs/{file_type}/{purpose}_{company_id}_{unix_ts}_{rand4}.{ext}

    Args:
        file_type: "ppt" / "pdf" / "excel" / "docx" / "markdown"
        purpose: 用途識別子（例: "clo_plan", "form3", "macro_overview"）
        company_id: 会社識別子（英数字推奨）
        extension: 拡張子（"pptx", "xlsx" 等。先頭ピリオドなし）

    Returns:
        outputs/ 配下の Path（親ディレクトリは事前作成）
    """
    safe_purpose = _sanitize(purpose)
    safe_company = _sanitize(company_id)
    unix_ts = int(time.time())
    rand4 = secrets.token_hex(2)  # 4 桁 hex（衝突確率十分低い）

    filename = f"{safe_purpose}_{safe_company}_{unix_ts}_{rand4}.{extension}"
    parent = OUTPUTS_DIR / file_type
    parent.mkdir(parents=True, exist_ok=True)
    return parent / filename


def _sanitize(value: str) -> str:
    """ファイル名に使えない文字を除去する。"""
    return "".join(c for c in value if c.isalnum() or c in "-_") or "x"
