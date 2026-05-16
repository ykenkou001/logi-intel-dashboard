"""CLO 義務対象スクリーニング判定エンドポイント（`/check` Web 画面用）。

`api/routers/clo.py` の `eligibility` は荷主3区分の細分化判定であるのに対し、
本エンドポイントは初見ユーザー向けの **30 秒スクリーニング** に特化する。

設計方針:
    - 入力はバンド（範囲）選択で受ける（実測値を強要しない）
    - 結果は ToolResponseModel + metadata（CategoryFinding[]）で返す
    - 全数値・条文に出典 URL を付与
    - Web 画面の Result コンポーネントが metadata を直接描画する想定
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from api.routers._helpers import to_model
from api.schemas.responses import ToolResponseModel
from core.export.citation import Citation, logistics_efficiency_law_citation
from core.export.response import ToolResponse
from core.legal.screening import (
    CategoryFinding,
    CloStatus,
    FreightTonsBand,
    IndustryHint,
    ScreeningInput,
    ScreeningResult,
    VehiclesBand,
    Verdict,
    WarehouseTonsBand,
    screen,
)

router = APIRouter(prefix="/api/v1/check", tags=["check"])


# ─── Pydantic 入力 ────────────────────────────────────────────────────


class CheckRequest(BaseModel):
    """`/check` 画面からのスクリーニング入力。"""

    industry: IndustryHint = Field(description="業種カテゴリ")
    freight_tons_band: FreightTonsBand = Field(description="年間取扱貨物量バンド")
    vehicles_band: VehiclesBand = Field(description="保有車両台数バンド")
    warehouse_tons_band: WarehouseTonsBand = Field(description="営業倉庫の年間入庫貨物量バンド")
    annual_revenue_jpy: int | None = Field(
        default=None,
        ge=0,
        description="年間売上（円・参考表示用・連鎖化判定に使用）",
    )
    clo_status: CloStatus = Field(
        default="not_considered",
        description="物流統括管理者の選任状況",
    )
    is_chain_franchise: bool = Field(
        default=False,
        description="連鎖化事業者（フランチャイズ本部）として運営しているか",
    )


# ─── Pydantic 出力（metadata 用）─────────────────────────────────────


class CategoryFindingModel(BaseModel):
    """1 区分の判定結果。Web フロントが直接描画する。"""

    category: str
    verdict: Verdict
    reason: str
    legal_article: str
    threshold_label: str


class CheckMetadata(BaseModel):
    """ToolResponse.metadata の構造。"""

    overall_verdict: Verdict
    findings: list[CategoryFindingModel]
    notes: list[str]
    days_until_deadline: int
    submission_deadline: str = "2026-10-31"
    enforcement_date: str = "2026-04-01"
    penalty: dict[str, str] = Field(
        default_factory=lambda: {
            "未選任": "100 万円以下の罰金",
            "届出懈怠": "20 万円以下の過料",
        },
    )


# ─── 表示ラベル ────────────────────────────────────────────────────


_CATEGORY_LABEL: dict[str, str] = {
    "shipper": "特定荷主",
    "chain_franchise": "特定連鎖化事業者",
    "warehouse": "特定倉庫業者",
    "freight_transport": "特定貨物自動車運送事業者等",
}

_VERDICT_LABEL: dict[Verdict, str] = {
    "applies": "✅ 対象",
    "gray_zone": "⚠️ グレーゾーン（要詳細確認）",
    "not_applies": "❌ 対象外",
}


def _build_summary(result: ScreeningResult) -> str:
    """Markdown 風サマリーテキスト（MCP / 経営会議の即答用）。"""
    lines: list[str] = ["=== CLO 義務対象 スクリーニング判定 ==="]
    lines.append("")
    lines.append(f"【総合判定】{_VERDICT_LABEL[result.overall_verdict]}")
    lines.append(f"【初回提出期限まで】残り {result.days_until_deadline} 日（2026-10-31）")
    lines.append("")
    lines.append("【区分別判定】")
    for f in result.findings:
        label = _CATEGORY_LABEL.get(f.category, f.category)
        lines.append(f"  ・{label}: {_VERDICT_LABEL[f.verdict]}")
        lines.append(f"      閾値: {f.threshold_label}")
        lines.append(f"      根拠: {f.reason}")
        lines.append(f"      法令: {f.legal_article}")
    if result.notes:
        lines.append("")
        lines.append("【注意事項】")
        for n in result.notes:
            lines.append(f"  ・{n}")
    lines.append("")
    lines.append("【罰則】")
    lines.append("  ・CLO 未選任: 100 万円以下の罰金")
    lines.append("  ・届出懈怠: 20 万円以下の過料")
    lines.append("")
    lines.append("【出典】国土交通省「物資の流通の効率化に関する法律」ポータル")
    lines.append("  https://www.revised-logistics-act-portal.mlit.go.jp/designation/")
    return "\n".join(lines)


def _to_finding_model(f: CategoryFinding) -> CategoryFindingModel:
    return CategoryFindingModel(
        category=f.category,
        verdict=f.verdict,
        reason=f.reason,
        legal_article=f.legal_article,
        threshold_label=f.threshold_label,
    )


@router.post("", response_model=ToolResponseModel)
async def run_check(
    payload: Annotated[CheckRequest, Body(...)],
) -> ToolResponseModel:
    """CLO 義務対象スクリーニングを実行する。

    `/check` Web 画面からの POST を受け、4 区分（荷主・連鎖化・倉庫・運送）の
    粗粒度判定を返す。Web フロントは ``metadata.findings`` を直接描画する。
    """
    result = screen(
        ScreeningInput(
            industry=payload.industry,
            freight_tons_band=payload.freight_tons_band,
            vehicles_band=payload.vehicles_band,
            warehouse_tons_band=payload.warehouse_tons_band,
            annual_revenue_jpy=payload.annual_revenue_jpy,
            clo_status=payload.clo_status,
            is_chain_franchise=payload.is_chain_franchise,
        ),
    )

    metadata = CheckMetadata(
        overall_verdict=result.overall_verdict,
        findings=[_to_finding_model(f) for f in result.findings],
        notes=result.notes,
        days_until_deadline=result.days_until_deadline,
    )

    citations: list[Citation] = [
        logistics_efficiency_law_citation(),
        Citation(
            label="特定事業者の指定（物流効率化法ポータル）",
            url="https://www.revised-logistics-act-portal.mlit.go.jp/designation/",
            accessed_via="国土交通省ポータル",
        ),
    ]

    response = ToolResponse(
        summary=_build_summary(result),
        citations=citations,
        data_source="estimated",
    )
    model = to_model(response)
    model.metadata = metadata.model_dump()
    return model
