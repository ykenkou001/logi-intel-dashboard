"""MCP ツール logi_clo_decision_log_record / logi_clo_decision_log_query のテスト。

Tier S1（フェーズ 5.5）。Claude Desktop / Claude Code から呼ばれる経路をシミュレートする。
"""
from __future__ import annotations

import asyncio

import pytest
from fastmcp import FastMCP

from mcp_server.tools.clo_tools import register_tools


@pytest.fixture(scope="module")
def mcp_with_clo_tools() -> FastMCP:
    m = FastMCP("test-clo")
    register_tools(m)
    return m


async def _call_tool(mcp_obj: FastMCP, name: str, args: dict) -> dict:
    result = await mcp_obj.call_tool(name, args)
    # FastMCP は ToolResult を返すので structured_content を取り出す
    if hasattr(result, "structured_content"):
        sc = result.structured_content
        if isinstance(sc, dict):
            return sc
    if hasattr(result, "data"):
        data = result.data
        if isinstance(data, dict):
            return data
    if isinstance(result, dict):
        return result
    raise AssertionError(f"unexpected tool result shape: {type(result)}")


# ---------------------------------------------------------------------------
# T11
# ---------------------------------------------------------------------------


def test_t11_mcp_decision_log_record_returns_entry_id(
    mcp_with_clo_tools, tmp_path, monkeypatch
):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    out = asyncio.run(
        _call_tool(
            mcp_with_clo_tools,
            "logi_clo_decision_log_record",
            {
                "company_id": "sample_wholesale_01",
                "decision_type": "measure_eval_topbottom",
                "decided_by": "CLO_A",
                "headline": "Top 3 採択",
                "rationale": "Top 推薦を採用",
                "selected_measures": ["load_factor_tms", "joint_delivery"],
                "rejected_measures": ["wms_3pl"],
                "snapshot_date": "2026-05-17",
                "snapshot_load_factor_pct": 42.0,
                "snapshot_compliance_overall": "compliant",
                "snapshot_feasibility_kpi_level": "green",
                "tags": ["board_review"],
            },
        )
    )
    assert "summary" in out
    assert "entry_id" in out
    assert out["decision_type"] == "measure_eval_topbottom"
    assert "DecisionLog 1 件を記録しました" in out["summary"]


# ---------------------------------------------------------------------------
# T12
# ---------------------------------------------------------------------------


def test_t12_mcp_decision_log_query_returns_entries_desc(
    mcp_with_clo_tools, tmp_path, monkeypatch
):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    # 2 件記録
    for headline in ("first", "second"):
        asyncio.run(
            _call_tool(
                mcp_with_clo_tools,
                "logi_clo_decision_log_record",
                {
                    "company_id": "sample_wholesale_01",
                    "decision_type": "free_form",
                    "decided_by": "CLO_A",
                    "headline": headline,
                },
            )
        )
    out = asyncio.run(
        _call_tool(
            mcp_with_clo_tools,
            "logi_clo_decision_log_query",
            {"company_id": "sample_wholesale_01", "limit": 10},
        )
    )
    # Codex 最終レビュー指摘 2: metadata.entries 構造で返る
    assert "metadata" in out
    assert "entries" in out["metadata"]
    entries = out["metadata"]["entries"]
    assert len(entries) == 2
    # decided_at 降順なので second が先頭
    assert entries[0]["headline"] == "second"
    assert entries[1]["headline"] == "first"


def test_mcp_decision_log_record_accepts_sources(
    mcp_with_clo_tools, tmp_path, monkeypatch
):
    """Codex 最終レビュー指摘 2: MCP record で sources 引数を渡せて、
    query 結果の citations / metadata に出典が保存される。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    asyncio.run(
        _call_tool(
            mcp_with_clo_tools,
            "logi_clo_decision_log_record",
            {
                "company_id": "sample_wholesale_01",
                "decision_type": "free_form",
                "decided_by": "CLO_A",
                "headline": "出典あり判断",
                "sources": [
                    {
                        "label": "改善基準告示",
                        "url": "https://www.mhlw.go.jp/test",
                        "notice_number": "厚生労働省告示第367号",
                    },
                ],
            },
        )
    )
    queried = asyncio.run(
        _call_tool(
            mcp_with_clo_tools,
            "logi_clo_decision_log_query",
            {"company_id": "sample_wholesale_01"},
        )
    )
    # citations に出典が集約される
    assert queried["citations"]
    assert queried["citations"][0]["label"] == "改善基準告示"
    # metadata.entries[0].sources にも保存
    saved_sources = queried["metadata"]["entries"][0]["sources"]
    assert len(saved_sources) == 1
    assert saved_sources[0]["url"] == "https://www.mhlw.go.jp/test"
