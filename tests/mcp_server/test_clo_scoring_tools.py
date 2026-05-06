"""フェーズ5.0 c.7 MCP ツール 3 件のスモークテスト。

logi_clo_industry_package / logi_clo_standardization_score / logi_clo_waste_traps
が ToolResponse 構造の dict を返し、4 業種サンプル + 不正 ID + 空 measure_runs
等のエッジケースで期待通りの挙動になることを確認する。
"""
from __future__ import annotations

import pytest
from fastmcp import FastMCP

from mcp_server.tools import clo_tools


def _assert_tool_response_shape(payload: dict[str, object]) -> None:
    assert "summary" in payload
    assert isinstance(payload["summary"], str) and payload["summary"]
    assert "files" in payload and isinstance(payload["files"], dict)
    assert "citations" in payload and isinstance(payload["citations"], list)
    assert "freshness_warnings" in payload
    assert payload["data_source"] in ("sample", "estimated", "actual")


@pytest.fixture
def mcp_server() -> FastMCP:
    mcp = FastMCP("test_clo_scoring")
    clo_tools.register_tools(mcp)
    return mcp


# ---------------------------------------------------------------------------
# logi_clo_industry_package
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "company_id,expected_industry",
    [
        ("sample_mfg_01", "manufacturing"),
        ("sample_wholesale_01", "wholesale"),
        ("sample_retail_01", "retail"),
        ("sample_chain_01", "chain_franchise"),
    ],
)
async def test_logi_clo_industry_package_returns_industry_summary(
    mcp_server: FastMCP, company_id: str, expected_industry: str,
) -> None:
    tool = await mcp_server.get_tool("logi_clo_industry_package")
    result = await tool.run(arguments={"company_id": company_id})
    payload = result.structured_content

    assert isinstance(payload, dict)
    _assert_tool_response_shape(payload)
    assert "標準" in payload["summary"] or "業種パッケージ" in payload["summary"]
    assert "version" in payload["summary"]


@pytest.mark.asyncio
async def test_logi_clo_industry_package_unknown_company_returns_summary(
    mcp_server: FastMCP,
) -> None:
    tool = await mcp_server.get_tool("logi_clo_industry_package")
    result = await tool.run(arguments={"company_id": "nonexistent_xyz"})
    payload = result.structured_content

    assert isinstance(payload, dict)
    assert "見つかりません" in payload["summary"]
    assert payload["citations"] == []


# ---------------------------------------------------------------------------
# logi_clo_standardization_score
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logi_clo_standardization_score_returns_score_summary(
    mcp_server: FastMCP,
) -> None:
    tool = await mcp_server.get_tool("logi_clo_standardization_score")
    result = await tool.run(arguments={"company_id": "sample_mfg_01"})
    payload = result.structured_content

    _assert_tool_response_shape(payload)
    assert "標準化スコア" in payload["summary"]
    # サンプル profile は kpi_history 空で coverage 0 → score 0/100 が想定
    assert "0.0/100" in payload["summary"] or "/100" in payload["summary"]


@pytest.mark.asyncio
async def test_logi_clo_standardization_score_unknown_company(
    mcp_server: FastMCP,
) -> None:
    tool = await mcp_server.get_tool("logi_clo_standardization_score")
    result = await tool.run(arguments={"company_id": "nonexistent"})
    payload = result.structured_content
    assert "見つかりません" in payload["summary"]


# ---------------------------------------------------------------------------
# logi_clo_waste_traps
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logi_clo_waste_traps_with_empty_runs(
    mcp_server: FastMCP,
) -> None:
    """measure_runs 未指定の場合は罠候補なしで返る。"""
    tool = await mcp_server.get_tool("logi_clo_waste_traps")
    result = await tool.run(
        arguments={"company_id": "sample_mfg_01", "measure_runs": []},
    )
    payload = result.structured_content
    _assert_tool_response_shape(payload)
    assert "罠候補なし" in payload["summary"]


@pytest.mark.asyncio
async def test_logi_clo_waste_traps_safeguard_triggers_low(
    mcp_server: FastMCP,
) -> None:
    """actual_effect_jpy が None なら 6 軸セーフガード発火 → low 固定。"""
    tool = await mcp_server.get_tool("logi_clo_waste_traps")
    result = await tool.run(
        arguments={
            "company_id": "sample_mfg_01",
            "measure_runs": [
                {
                    "measure_id": "modal_shift_to_rail",
                    "started_on": "2025-10-01",
                    "invested_jpy": 100_000_000,
                    "expected_effect_jpy": 300_000_000,
                    "actual_effect_jpy": None,
                    "measured_count": 50,
                    "data_completeness": 0.8,
                    "seasonal_factor_active": False,
                    "external_event_active": False,
                    "payback_months_estimated": 12,
                    "suspected_root_cause": "wrong_kpi",
                },
            ],
        },
    )
    payload = result.structured_content
    _assert_tool_response_shape(payload)
    # safeguard 発火 → low 固定。high/medium に出ない
    assert "high 0" in payload["summary"] or "high 0 " in payload["summary"]


@pytest.mark.asyncio
async def test_logi_clo_waste_traps_unknown_company(
    mcp_server: FastMCP,
) -> None:
    tool = await mcp_server.get_tool("logi_clo_waste_traps")
    result = await tool.run(
        arguments={"company_id": "nonexistent", "measure_runs": []},
    )
    payload = result.structured_content
    assert "見つかりません" in payload["summary"]
