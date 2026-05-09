"""Markdown 形式の成果物生成。

経営会議では PPT が主役だが、Claude → 人間レビュー → Word 整形のフローでは
Markdown が中継フォーマットとして使われる。CLO ドラフトを最も「読み流せる」
形で出力する。
"""

from __future__ import annotations

from pathlib import Path

from core.export.citation import Citation
from core.export.response import make_output_path


def write_macro_overview(
    prefecture: str,
    sections: list[tuple[str, str]],
    citations: list[Citation],
    company_id: str = "general",
    freshness_warnings: list[str] | None = None,
) -> Path:
    """都道府県マクロ概況の Markdown を生成する。

    Args:
        prefecture: 都道府県名
        sections: (見出し, 本文) のタプルリスト
        citations: 出典リスト
        company_id: ファイル名用の識別子
        freshness_warnings: 鮮度警告（None なら省略）

    Returns:
        生成ファイルのパス
    """
    path = make_output_path(
        file_type="markdown",
        purpose="macro_overview",
        company_id=company_id,
        extension="md",
    )

    lines: list[str] = []
    lines.append(f"# {prefecture} 物流業界マクロ概況")
    lines.append("")

    if freshness_warnings:
        lines.append("## ⚠️ データ鮮度警告")
        lines.extend(f"- {w}" for w in freshness_warnings)
        lines.append("")

    for heading, body in sections:
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(body)
        lines.append("")

    if citations:
        lines.append("## 出典")
        lines.append("")
        lines.extend(c.to_markdown() for c in citations)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_clo_plan_draft(
    company_name: str,
    company_id: str,
    plan_period: str,
    executive_summary: str,
    sections: list[tuple[str, str]],
    citations: list[Citation],
) -> Path:
    """CLO 中長期計画ドラフトの Markdown を生成する。

    Args:
        company_name: 会社名
        company_id: ファイル名用の識別子
        plan_period: 計画期間文字列（例: "2026年度〜2030年度"）
        executive_summary: エグゼクティブサマリー（経営層向け要約）
        sections: (見出し, 本文) のタプルリスト
        citations: 出典リスト

    Returns:
        生成ファイルのパス
    """
    path = make_output_path(
        file_type="markdown",
        purpose="clo_plan",
        company_id=company_id,
        extension="md",
    )

    lines: list[str] = []
    lines.append(f"# 中長期計画書ドラフト — {company_name}")
    lines.append("")
    lines.append(f"**計画期間**: {plan_period}")
    lines.append("")

    lines.append("## エグゼクティブサマリー")
    lines.append("")
    lines.append(executive_summary)
    lines.append("")

    for heading, body in sections:
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(body)
        lines.append("")

    lines.append("## 出典")
    lines.append("")
    lines.extend(c.to_markdown() for c in citations)
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
