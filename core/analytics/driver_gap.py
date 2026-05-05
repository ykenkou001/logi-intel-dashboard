"""ドライバー需給ギャップ分析。

改善基準告示（2024年4月施行）の年間時間外労働上限960h・年間拘束時間
3,300h により、トラック運転者の実効稼働力が業界推計で約13.5%減少する。
本モジュールは都道府県別の道路貨物運送業（中分類44）従業者数 ×
減少係数で需給ギャップを算出する。

設計方針:
    - e-Stat 経済センサス‐基礎調査 2024（statsDataId 0004040102）から
      産業中分類「44 道路貨物運送業」の従業者数を取得
    - 減少係数は core/static/improvement_standards.py の中央値（0.135）を使用
    - 国交省2030年試算（▲34.1%輸送力不足）も参考値として併記
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from core.clients.estat import EStatApiError, EStatClient
from core.export.citation import (
    Citation,
    estat_citation,
    improvement_standards_citation,
)
from core.static._freshness import all_warnings
from core.static.improvement_standards import (
    TRUCK_DRIVER_STANDARD,
    driver_capacity_reduction_factor,
)

# 経済センサス‐基礎調査 2024 産業(小分類)別 従業者数 - 全国、都道府県、市区町村
# 中分類「44 道路貨物運送業」も同表内に含まれる（level 4）
_FREIGHT_WORKERS_STATS_ID = "0004040102"
_TRANSPORT_MIDDLE_CATEGORY = "44"  # JSIC 中分類「道路貨物運送業」

# 国交省試算「物流の2024年問題」: 2030年度の輸送力不足見込み
# 出典: 国交省「持続可能な物流の実現に向けた検討会」最終とりまとめ（2023年8月）
_MLIT_2030_SHORTAGE_PCT = 34.1
_MLIT_2030_REPORT_URL = (
    "https://www.mlit.go.jp/seisakutokatsu/freight/seisakutokatsu_freight_fr_000172.html"
)

# 都道府県名 → e-Stat cdArea（5桁）
_PREF_ESTAT_CODE: dict[str, str] = {
    "北海道": "01000", "青森県": "02000", "岩手県": "03000",
    "宮城県": "04000", "秋田県": "05000", "山形県": "06000",
    "福島県": "07000", "茨城県": "08000", "栃木県": "09000",
    "群馬県": "10000", "埼玉県": "11000", "千葉県": "12000",
    "東京都": "13000", "神奈川県": "14000", "新潟県": "15000",
    "富山県": "16000", "石川県": "17000", "福井県": "18000",
    "山梨県": "19000", "長野県": "20000", "岐阜県": "21000",
    "静岡県": "22000", "愛知県": "23000", "三重県": "24000",
    "滋賀県": "25000", "京都府": "26000", "大阪府": "27000",
    "兵庫県": "28000", "奈良県": "29000", "和歌山県": "30000",
    "鳥取県": "31000", "島根県": "32000", "岡山県": "33000",
    "広島県": "34000", "山口県": "35000", "徳島県": "36000",
    "香川県": "37000", "愛媛県": "38000", "高知県": "39000",
    "福岡県": "40000", "佐賀県": "41000", "長崎県": "42000",
    "熊本県": "43000", "大分県": "44000", "宮崎県": "45000",
    "鹿児島県": "46000", "沖縄県": "47000",
}


@dataclass
class DriverGapResult:
    """ドライバー需給ギャップ分析結果。"""

    prefecture: str

    # 現状（経済センサス‐基礎調査 2024 中分類44）
    national_workers: int | None        # 全国 道路貨物運送業 従業者数
    regional_workers: int | None        # 都道府県内 同従業者数
    regional_share_pct: float | None    # 全国シェア（%）

    # 改善基準告示による実効稼働減少
    capacity_reduction_factor: float    # 0.135（業界推計中央値）
    national_capacity_loss: int | None  # 全国 実効稼働減（人相当）
    regional_capacity_loss: int | None  # 都道府県 実効稼働減（人相当）

    # 改善基準告示の主要数値（参照用）
    annual_overtime_limit_hours: int    # 年間時間外上限 960h
    annual_working_hours_principle: int  # 年間総拘束時間 原則 3,300h

    # 国家試算
    mlit_2030_shortage_pct: float       # 2030年 輸送力不足見込み

    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


async def _fetch_workers(cd_area: str) -> int | None:
    """経済センサスから道路貨物運送業（中分類44）の従業者数を取得する。失敗時は None。"""
    try:
        async with EStatClient() as client:
            data = await client.get_stats_data(
                stats_data_id=_FREIGHT_WORKERS_STATS_ID,
                cd_cat01=_TRANSPORT_MIDDLE_CATEGORY,
                cd_area=cd_area,
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


async def analyze_driver_gap(prefecture: str) -> DriverGapResult:
    """ドライバー需給ギャップを分析する。

    Args:
        prefecture: 都道府県名（例: "東京都"）

    Returns:
        DriverGapResult

    Raises:
        ValueError: 都道府県名が不正な場合
    """
    cd_area = _PREF_ESTAT_CODE.get(prefecture)
    if cd_area is None:
        pref_examples = "、".join(list(_PREF_ESTAT_CODE.keys())[:5]) + " …"
        raise ValueError(
            f"都道府県名 '{prefecture}' が認識できません。"
            f"正式名称で入力してください（例: {pref_examples}）"
        )

    # 全国（cd_area="00000"）と都道府県を並列取得
    national, regional = await asyncio.gather(
        _fetch_workers(cd_area="00000"),
        _fetch_workers(cd_area=cd_area),
    )

    factor = driver_capacity_reduction_factor()
    national_loss = int(national * factor) if national is not None else None
    regional_loss = int(regional * factor) if regional is not None else None
    regional_share = (
        regional / national * 100.0
        if national and regional and national > 0
        else None
    )

    citations = [
        estat_citation(
            "経済センサス‐基礎調査 2024 産業(小分類)別従業者数",
            _FREIGHT_WORKERS_STATS_ID,
        ),
        improvement_standards_citation(),
        Citation(
            label="国交省「持続可能な物流の実現に向けた検討会」最終とりまとめ（2023年8月）",
            url=_MLIT_2030_REPORT_URL,
            accessed_via="国交省ポータル（静的参照）",
        ),
    ]

    return DriverGapResult(
        prefecture=prefecture,
        national_workers=national,
        regional_workers=regional,
        regional_share_pct=regional_share,
        capacity_reduction_factor=factor,
        national_capacity_loss=national_loss,
        regional_capacity_loss=regional_loss,
        annual_overtime_limit_hours=TRUCK_DRIVER_STANDARD.max_annual_overtime_hours,
        annual_working_hours_principle=(
            TRUCK_DRIVER_STANDARD.max_annual_working_hours_principle
        ),
        mlit_2030_shortage_pct=_MLIT_2030_SHORTAGE_PCT,
        citations=citations,
        freshness_warnings=all_warnings(),
    )


def build_driver_gap_summary(r: DriverGapResult) -> str:
    """DriverGapResult から CLO 計画書サマリーテキストを生成する。"""
    lines: list[str] = [
        f"=== ドライバー需給ギャップ分析: {r.prefecture} ===",
        "基準: 改善基準告示（2024年4月施行・厚労省告示第367号）",
        f"  年間総拘束時間上限: 原則 {r.annual_working_hours_principle:,} 時間",
        f"  年間時間外労働上限: {r.annual_overtime_limit_hours:,} 時間",
        f"  実効稼働減少係数: {r.capacity_reduction_factor * 100:.1f}%（業界推計中央値）",
        "",
        "【道路貨物運送業 従業者数（経済センサス‐基礎調査 2024・中分類44）】",
    ]

    if r.national_workers is not None:
        lines.append(f"  全国: {r.national_workers:,} 人")
    else:
        lines.append("  全国: 取得失敗（e-Stat）")

    if r.regional_workers is not None:
        share = (
            f"（全国シェア {r.regional_share_pct:.1f}%）"
            if r.regional_share_pct is not None
            else ""
        )
        lines.append(f"  {r.prefecture}: {r.regional_workers:,} 人{share}")
    else:
        lines.append(f"  {r.prefecture}: 取得失敗（e-Stat）")

    lines += [
        "",
        "【2024年問題による実効稼働減（改善基準告示適用後）】",
    ]
    if r.national_capacity_loss is not None:
        lines.append(f"  全国: 約 {r.national_capacity_loss:,} 人分の実稼働減")
    if r.regional_capacity_loss is not None:
        lines.append(
            f"  {r.prefecture}: 約 {r.regional_capacity_loss:,} 人分の実稼働減"
        )

    lines += [
        "",
        "【業界参考値（国交省試算）】",
        f"  2030年 全国輸送力不足見込み: ▲{r.mlit_2030_shortage_pct:.1f}%",
        "  → 同等の効率化（積載率向上・モーダルシフト・共同配送等）が必要",
        "",
        "【CLO 計画書への反映必須事項】",
        "  対策措置として「ドライバー確保」「労働時間管理」「効率化施策」の記載が必要",
        "  → モーダルシフト・共同配送・中継輸送・積載率向上が主な選択肢"
        "（Step 5 で施策効果試算）",
        "",
        "  ※ 「従業者数」は事務員・整備士等を含む業界全体の数値。"
        "ドライバー比率（業界相場約75〜80%）を勘案して詳細試算する場合は、"
        "賃金構造基本統計調査の「貨物自動車運転者」を別途参照すること。",
    ]

    return "\n".join(lines)
