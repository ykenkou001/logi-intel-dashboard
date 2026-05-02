"""業種別 物流原単位（売上→年間取扱量推計用）。

出典:
    - 国土交通省「物流調査結果」「物資流動調査」
    - 業種別の売上高あたり貨物量の業界推計値
    - 全国貨物純流動調査（物流センサス）2021

設計方針:
    - 9万トン基準（特定荷主判定）の概算用
    - 自社が**正確な取扱量を把握していない**場合の暫定推計に使う
    - **判定が9万トン近辺の場合は実測ベースで再確認することを推奨**

使用例:
    >>> # 売上 100億円の電子部品メーカーの推計取扱量
    >>> tons = estimate_freight_tons(jsic_code="2911", revenue_jpy=10_000_000_000)
    >>> tons
    1900.0  # 約 1,900 トン（電子部品は軽量・高単価のため少ない）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from core.static._freshness import Freshness, register
from core.static.jsic import category_of


@dataclass(frozen=True)
class FreightCoefficient:
    """業種カテゴリ別の売上高1億円あたり年間貨物量（トン）。

    値は概算範囲の中央値。実取扱量との乖離は ±50% 程度を想定。
    """

    # 業種別係数（トン/売上1億円）
    BY_CATEGORY: ClassVar[dict[str, float]] = {
        "manufacturing": 19.0,    # 製造業（電子部品・機械等の中位）
        "wholesale": 380.0,       # 卸売業（取扱量が大きい）
        "retail": 280.0,          # 小売業
        "chain_franchise": 320.0, # 連鎖化事業者（コンビニ等）
        "transport": 0.0,         # 運送業者は荷主ではないため対象外
        "other": 0.0,
    }

    # 細分類別の上書き値（より精緻な推計が必要な業種）
    BY_JSIC_CODE: ClassVar[dict[str, float]] = {
        "0911": 850.0,   # 食肉加工品（重量物・チルド配送多）
        "1041": 950.0,   # 清涼飲料（重量物・大量配送）
        "1631": 8.0,     # 医薬品（軽量・高単価）
        "2911": 19.0,    # 電子部品（軽量・高単価）
        "3211": 250.0,   # 自動車製造（重量物だが完成車は売上高い）
        "5311": 420.0,   # 農畜産物・水産物（重量物）
        "5411": 380.0,   # 食料・飲料卸（標準）
        "5891": 320.0,   # コンビニ
        "5611": 250.0,   # 百貨店・総合スーパー
    }


COEF = FreightCoefficient()


def estimate_freight_tons(jsic_code: str, revenue_jpy: int) -> float | None:
    """売上額から年間取扱量（トン）を推計する。

    Args:
        jsic_code: 4桁の JSIC 細分類コード
        revenue_jpy: 年間売上（円）

    Returns:
        推計年間取扱量（トン）。業種が登録されていない場合は None。
    """
    revenue_oku = revenue_jpy / 100_000_000  # 億円換算

    # 細分類別の上書きを優先
    if jsic_code in COEF.BY_JSIC_CODE:
        return revenue_oku * COEF.BY_JSIC_CODE[jsic_code]

    # カテゴリ別フォールバック
    category = category_of(jsic_code)
    if category and category in COEF.BY_CATEGORY:
        coef = COEF.BY_CATEGORY[category]
        if coef <= 0:
            return None
        return revenue_oku * coef

    return None


FRESHNESS = Freshness(
    label="業種別物流原単位（売上→取扱量推計）",
    last_updated=date(2024, 6, 1),  # 物流センサス2021 公表後の業界推計値
    update_cadence="quinquennial",  # 物流センサス（5年に1回）に追従
    source_url="https://www.mlit.go.jp/sogoseisaku/transport/butsuryu06100.html",
    notes="物流センサス2021に基づく業界推計値。次回更新は2026年センサス公表後。",
)
register("industry_freight_coef", FRESHNESS)
