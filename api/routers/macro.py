"""都道府県マクロ概況エンドポイント。

`mcp_server/tools/macro_tools.py` と同じ並列フェッチロジックを呼び出す。
e-Stat / 国税庁 / 気象庁 / エネ庁を並列で叩き、部分失敗を許容する。
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from api.schemas.responses import ToolResponseModel
from core.export.citation import (
    corp_number_citation,
    estat_citation,
    fuel_price_citation,
    jma_warning_citation,
)
from core.export.response import ToolResponse
from core.macro.sources import (
    ESTAT_STATS_ID,
    PREF_CODES,
    fetch_corp,
    fetch_estat,
    fetch_fuel,
    fetch_weather,
    with_source_timeout,
)
from core.static._freshness import all_warnings

router = APIRouter(prefix="/api/v1/macro", tags=["macro"])


@router.get("/overview", response_model=ToolResponseModel)
async def macro_overview(
    prefecture: Annotated[str, Query(description="都道府県名（例: '東京都', '大阪府'）")],
) -> ToolResponseModel:
    """都道府県の物流業界マクロ概況を全データソースから集約。"""
    codes = PREF_CODES.get(prefecture)
    if codes is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"都道府県名 '{prefecture}' が認識できません。"
                "正式名称で入力してください（例: '東京都'）"
            ),
        )

    estat_result, corp_result, weather_result, fuel_result = await asyncio.gather(
        with_source_timeout("運輸業事業所数", fetch_estat(codes["estat"])),
        with_source_timeout("運送会社法人数", fetch_corp(codes["corp"], prefecture)),
        with_source_timeout("気象警報", fetch_weather(codes["jma"])),
        with_source_timeout("燃料価格", fetch_fuel()),
    )

    summary = "\n".join(
        [
            f"=== {prefecture} 物流業界マクロ概況 ===",
            estat_result,
            corp_result,
            weather_result,
            fuel_result,
        ]
    )

    response = ToolResponse(summary=summary)
    response.add_citation(
        estat_citation(
            "経済センサス‐活動調査 2021 産業（大分類）別事業所数",
            ESTAT_STATS_ID,
        )
    )
    response.add_citation(corp_number_citation())
    response.add_citation(jma_warning_citation())
    response.add_citation(fuel_price_citation())
    response.freshness_warnings = all_warnings()

    return ToolResponseModel.model_validate(response.to_dict())
