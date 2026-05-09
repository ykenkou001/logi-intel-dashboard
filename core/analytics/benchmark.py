"""業界ベンチマーク位置づけ分析。

CLO 計画書の「業界平均比」「全国・地域別事業所数」算出を担う。
e-Stat 経済センサスから同業種の全国・都道府県別事業所数を取得し、
業界平均物流コスト比率（静的データ）と自社を比較する。

設計方針:
    - e-Stat 取得失敗は許容。事業所数が取れなくても物流コスト比較は出力する
    - 「業界平均売上」は経済センサス公表値から算出した推計値
    - 全数値に出典を付与（経営会議「出典は？」即答用）
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal

from core.clients.estat import EStatApiError, EStatClient
from core.export.citation import Citation, estat_citation
from core.export.formatter import format_jpy
from core.static._freshness import all_warnings
from core.static.industry_benchmarks import (
    REVENUE_VS_AVG_LARGE_SCALE_THRESHOLD_PCT,
    REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT,
)
from core.static.jsic import lookup
from core.static.national_targets import LOGISTICS_CO2_TARGET

ReliabilityLevel = Literal["normal", "large_scale", "low_reliability"]

# 経済センサス‐基礎調査 2024（産業小分類別 民営事業所数 — 全国・都道府県・市区町村）
# JSIC 細分類4桁の上3桁（小分類）を cd_cat01 に渡すと絞り込める。
# e-Stat の最細粒度は小分類3桁（細分類4桁の集計表は提供されていない）。
_ECONOMIC_CENSUS_ID = "0004040101"

# 都道府県名 → e-Stat cdArea（5桁）
_PREF_ESTAT_CODE: dict[str, str] = {
    "北海道": "01000",
    "青森県": "02000",
    "岩手県": "03000",
    "宮城県": "04000",
    "秋田県": "05000",
    "山形県": "06000",
    "福島県": "07000",
    "茨城県": "08000",
    "栃木県": "09000",
    "群馬県": "10000",
    "埼玉県": "11000",
    "千葉県": "12000",
    "東京都": "13000",
    "神奈川県": "14000",
    "新潟県": "15000",
    "富山県": "16000",
    "石川県": "17000",
    "福井県": "18000",
    "山梨県": "19000",
    "長野県": "20000",
    "岐阜県": "21000",
    "静岡県": "22000",
    "愛知県": "23000",
    "三重県": "24000",
    "滋賀県": "25000",
    "京都府": "26000",
    "大阪府": "27000",
    "兵庫県": "28000",
    "奈良県": "29000",
    "和歌山県": "30000",
    "鳥取県": "31000",
    "島根県": "32000",
    "岡山県": "33000",
    "広島県": "34000",
    "山口県": "35000",
    "徳島県": "36000",
    "香川県": "37000",
    "愛媛県": "38000",
    "高知県": "39000",
    "福岡県": "40000",
    "佐賀県": "41000",
    "長崎県": "42000",
    "熊本県": "43000",
    "大分県": "44000",
    "宮崎県": "45000",
    "鹿児島県": "46000",
    "沖縄県": "47000",
}

# 業界平均 物流コスト/売上比率（日本ロジスティクスシステム協会 2021年度物流コスト調査報告書）
INDUSTRY_AVG_LOGISTICS_RATIO: dict[str, float | None] = {
    "manufacturing": 0.018,  # 1.8%
    "wholesale": 0.048,  # 4.8%
    "retail": 0.031,  # 3.1%
    "chain_franchise": 0.035,  # 3.5%（推計）
    "transport": None,  # 荷主ではないため比較不可
    "other": None,
}

# 業種別 1事業所あたり推計平均年間売上（億円）
# 経済センサス活動調査 2021 の業種別売上合計 ÷ 事業所数から算出した概算値
_INDUSTRY_AVG_REVENUE_PER_EST_OKUYEN: dict[str, float] = {
    "manufacturing": 12.5,
    "wholesale": 8.0,
    "retail": 2.5,
    "chain_franchise": 5.0,
    "transport": 3.0,
}

_JILS_URL = "https://www.logistics.or.jp/survey/logistics_cost.html"


@dataclass
class BenchmarkResult:
    """業界ベンチマーク分析結果。CLO 計画書「業界平均比」セクションへの入力に使う。"""

    # 入力情報
    jsic_code: str
    jsic_name: str
    category: str
    prefecture: str
    revenue_jpy: int
    logistics_cost_jpy: int | None

    # 業界規模（e-Stat 取得値。取得失敗時は None。JSIC 上3桁=小分類で絞り込み）
    estat_minor_code: str  # 絞り込みに使った小分類コード（JSIC 上3桁）
    national_peer_count: int | None  # 全国同業種（小分類）事業所数
    regional_peer_count: int | None  # 都道府県内同業種事業所数

    # 売上相対位置（推計値）
    industry_avg_revenue_jpy: float | None  # 業界推計平均売上（円）
    revenue_vs_avg_pct: float | None  # 自社売上 / 業界平均 × 100

    # 物流コスト比較
    logistics_cost_ratio: float | None  # 自社 物流コスト/売上比率
    industry_avg_logistics_ratio: float | None  # 業界平均比率（JILS調査）
    logistics_cost_gap_pct: float | None  # 業界平均比差分（% 正=割高 負=割安）

    # 国家目標
    co2_intensity_target_pct: float  # 物流分野 CO2 原単位削減目標

    # 業界平均比の信頼性区分（経営会議で参照する場合の信頼度を示す）
    # 業界統計の母集団が小規模事業所中心のため、大企業の比較は桁外れになりやすい。
    revenue_ratio_reliability: ReliabilityLevel = "normal"
    revenue_ratio_warning: str | None = None

    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


async def _fetch_peer_count(cd_cat01: str, cd_area: str | None) -> int | None:
    """e-Stat 経済センサスから同業種の事業所数を取得する。失敗時は None を返す。"""
    try:
        async with EStatClient() as client:
            data = await client.get_stats_data(
                stats_data_id=_ECONOMIC_CENSUS_ID,
                cd_area=cd_area,
                cd_cat01=cd_cat01,
                limit=1,
            )
        values = data.get("DATA_INF", {}).get("VALUE", [])
        if isinstance(values, dict):
            values = [values]
        if values:
            try:
                return int(float(str(values[0].get("$", ""))))
            except (ValueError, TypeError):
                return None
    except (EStatApiError, Exception):
        return None
    return None


async def analyze_benchmark(
    jsic_code: str,
    prefecture: str,
    revenue_jpy: int,
    logistics_cost_jpy: int | None = None,
) -> BenchmarkResult:
    """業界ベンチマーク位置づけを分析する。

    Args:
        jsic_code: JSIC 細分類4桁コード（例: "5411"）
        prefecture: 主たる拠点の都道府県名（例: "東京都"）
        revenue_jpy: 年間売上（円）
        logistics_cost_jpy: 年間物流コスト（円）。省略時は比率比較不可

    Returns:
        BenchmarkResult

    Raises:
        ValueError: jsic_code が未収録の場合
    """
    entry = lookup(jsic_code)
    if entry is None:
        raise ValueError(
            f"JSIC コード '{jsic_code}' は未収録です。"
            "収録済みコードの例: 5411（食料・飲料卸売業）、4411（一般貨物自動車運送業）"
        )

    category = entry.category
    # JSIC 細分類4桁の上3桁が e-Stat 経済センサスの小分類コードに対応する
    estat_minor_code = jsic_code[:3]
    cd_area = _PREF_ESTAT_CODE.get(prefecture)

    # e-Stat から事業所数を取得（失敗許容）
    if cd_area:
        national_count, regional_count = await asyncio.gather(
            _fetch_peer_count(estat_minor_code, cd_area=None),
            _fetch_peer_count(estat_minor_code, cd_area=cd_area),
        )
    else:
        national_count = await _fetch_peer_count(estat_minor_code, cd_area=None)
        regional_count = None

    # 業界平均売上との比較（推計）
    avg_revenue_okuyen = _INDUSTRY_AVG_REVENUE_PER_EST_OKUYEN.get(category)
    industry_avg_revenue_jpy = avg_revenue_okuyen * 1e8 if avg_revenue_okuyen else None
    revenue_vs_avg_pct = (
        revenue_jpy / industry_avg_revenue_jpy * 100.0
        if industry_avg_revenue_jpy and industry_avg_revenue_jpy > 0
        else None
    )
    revenue_ratio_reliability, revenue_ratio_warning = _classify_revenue_ratio_reliability(
        revenue_vs_avg_pct,
    )

    # 物流コスト比率
    logistics_cost_ratio = (
        logistics_cost_jpy / revenue_jpy
        if logistics_cost_jpy is not None and revenue_jpy > 0
        else None
    )
    industry_avg_logistics_ratio = INDUSTRY_AVG_LOGISTICS_RATIO.get(category)
    logistics_cost_gap_pct = (
        (logistics_cost_ratio - industry_avg_logistics_ratio) / industry_avg_logistics_ratio * 100.0
        if logistics_cost_ratio is not None and industry_avg_logistics_ratio
        else None
    )

    citations = [
        estat_citation(
            "経済センサス‐基礎調査 2024 産業（小分類）別民営事業所数",
            _ECONOMIC_CENSUS_ID,
        ),
        Citation(
            label="物流コスト実態調査 2021年度（日本ロジスティクスシステム協会）",
            url=_JILS_URL,
            accessed_via="公開報告書（静的参照）",
        ),
    ]

    return BenchmarkResult(
        jsic_code=jsic_code,
        jsic_name=entry.name,
        category=category,
        prefecture=prefecture,
        revenue_jpy=revenue_jpy,
        logistics_cost_jpy=logistics_cost_jpy,
        estat_minor_code=estat_minor_code,
        national_peer_count=national_count,
        regional_peer_count=regional_count,
        industry_avg_revenue_jpy=industry_avg_revenue_jpy,
        revenue_vs_avg_pct=revenue_vs_avg_pct,
        revenue_ratio_reliability=revenue_ratio_reliability,
        revenue_ratio_warning=revenue_ratio_warning,
        logistics_cost_ratio=logistics_cost_ratio,
        industry_avg_logistics_ratio=industry_avg_logistics_ratio,
        logistics_cost_gap_pct=logistics_cost_gap_pct,
        co2_intensity_target_pct=LOGISTICS_CO2_TARGET.intensity_reduction_pct,
        citations=citations,
        freshness_warnings=all_warnings(),
    )


def _classify_revenue_ratio_reliability(
    revenue_vs_avg_pct: float | None,
) -> tuple[ReliabilityLevel, str | None]:
    """業界平均売上比から信頼性区分とユーザー警告を導出する。

    業界平均は経済センサスの 1 事業所あたり推計値（小規模事業所中心の母集団）。
    大企業を比較すると桁外れになりやすく、経営会議でそのまま提示すると defensibility が損なわれる。
    """
    if revenue_vs_avg_pct is None:
        return "normal", None
    if revenue_vs_avg_pct > REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT:
        warning = (
            f"業界平均売上比 {revenue_vs_avg_pct:.0f}% は信頼性しきい値 "
            f"{REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT:.0f}% を超過。"
            "業界統計の母集団（小規模事業所中心）と自社規模の乖離が大きく、"
            "経営会議では参考値として扱い、相対参照（規模優位企業として上位帯）に留めてください。"
        )
        return "low_reliability", warning
    if revenue_vs_avg_pct > REVENUE_VS_AVG_LARGE_SCALE_THRESHOLD_PCT:
        return "large_scale", None
    return "normal", None


def build_benchmark_summary(r: BenchmarkResult) -> str:
    """BenchmarkResult から CLO 計画書サマリーテキストを生成する。"""
    lines: list[str] = [
        "=== 業界ベンチマーク分析 ===",
        f"業種: {r.jsic_name}（{r.jsic_code}）/ {_category_label(r.category)}",
        f"都道府県: {r.prefecture}",
        f"年間売上: {format_jpy(r.revenue_jpy)}",
        "",
        "【業界規模（経済センサス‐基礎調査 2024）】",
        (f"  ※ 産業小分類 {r.estat_minor_code}（JSIC 細分類 {r.jsic_code} の上3桁）で絞り込み"),
    ]

    if r.national_peer_count is not None:
        lines.append(f"  全国同業種事業所数（小分類）: {r.national_peer_count:,} 件")
    else:
        lines.append("  全国同業種事業所数（小分類）: 取得失敗（e-Stat）")

    if r.regional_peer_count is not None:
        share = (
            f"（全国シェア {r.regional_peer_count / r.national_peer_count * 100:.1f}%）"
            if r.national_peer_count
            else ""
        )
        lines.append(
            f"  {r.prefecture}内同業種事業所数（小分類）: {r.regional_peer_count:,} 件{share}"
        )
    else:
        lines.append(f"  {r.prefecture}内同業種事業所数（小分類）: 取得失敗（e-Stat）")

    lines += [
        "",
        "【売上規模比較（推計）】",
    ]
    if r.industry_avg_revenue_jpy is not None:
        lines.append(
            f"  業界推計平均売上: {format_jpy(r.industry_avg_revenue_jpy)} / 事業所"
            "（経済センサス2021公表値から算出）"
        )
    if r.revenue_vs_avg_pct is not None:
        position = "上位水準" if r.revenue_vs_avg_pct >= 100 else "平均以下"
        lines.append(
            f"  自社売上: {format_jpy(r.revenue_jpy)} → 業界平均の {r.revenue_vs_avg_pct:.0f}%"
            f"（{position}）"
        )
        if r.revenue_ratio_warning:
            lines.append(f"  ⚠️ {r.revenue_ratio_warning}")

    lines += [
        "",
        "【物流コスト比較（JILS 2021年度調査）】",
    ]
    if r.industry_avg_logistics_ratio is not None:
        lines.append(f"  業界平均比率: {r.industry_avg_logistics_ratio * 100:.1f}%")
    if r.logistics_cost_ratio is not None and r.logistics_cost_gap_pct is not None:
        sign = "▲" if r.logistics_cost_gap_pct < 0 else "+"
        eval_label = "コスト優位（改善済み）" if r.logistics_cost_gap_pct < 0 else "要改善"
        lines.append(
            f"  自社比率: {r.logistics_cost_ratio * 100:.1f}%"
            f" → 業界平均比 {sign}{abs(r.logistics_cost_gap_pct):.1f}%（{eval_label}）"
        )
    else:
        lines.append(
            "  自社比率: 物流コスト未入力のため比較不可（logistics_cost_jpy を指定してください）"
        )

    co2_line = (
        f"  物流分野CO2削減目標: ▲{r.co2_intensity_target_pct:.1f}%"
        "（2030年/2013年比・輸送量当たり原単位）"
    )
    lines += [
        "",
        "【CLO 計画書への反映必須事項】",
        co2_line,
        (
            "  → 中長期計画に CO2 原単位削減目標の記載が必要"
            "（物流効率化法 第46条 特定荷主 / 第65条 特定連鎖化事業者）"
        ),
    ]

    return "\n".join(lines)


def _category_label(category: str) -> str:
    labels = {
        "manufacturing": "製造業",
        "wholesale": "卸売業",
        "retail": "小売業",
        "chain_franchise": "連鎖化事業者",
        "transport": "運輸業",
        "other": "その他",
    }
    return labels.get(category, category)
