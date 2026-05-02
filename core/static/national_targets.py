"""物流分野固有の国家目標（CO2 削減目標等）。

出典:
    - 経済産業省・国土交通省・環境省「物流分野における CO2 排出削減のための取組」
    - 「2030年度におけるエネルギー需給の見通し」関連資料
    - パリ協定整合の地球温暖化対策計画（令和3年10月閣議決定）

注意:
    - 「日本全体の温室効果ガス▲46%（2030/2013比）」とは別物
    - 物流分野は「輸送量当たりCO2排出原単位」で個別目標が設定されている
    - 計画書に数値目標を書く際は、必ず**物流分野固有目標**を参照する
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.static._freshness import Freshness, register


@dataclass(frozen=True)
class LogisticsCo2Target:
    """物流分野の CO2 削減国家目標。"""

    # 物流分野（輸送量当たり CO2 排出原単位）
    target_year: int = 2030                          # 目標年
    base_year: int = 2013                            # 基準年
    intensity_reduction_pct: float = 23.4            # 輸送量当たり原単位 ▲23.4%（2030/2013比）

    # 参考: 国全体（物流以外も含む）
    national_ghg_reduction_pct: float = 46.0         # 日本全体の温室効果ガス ▲46%
    national_ghg_stretch_pct: float = 50.0           # ストレッチ目標 ▲50%


LOGISTICS_CO2_TARGET = LogisticsCo2Target()


@dataclass(frozen=True)
class ModalShiftTarget:
    """モーダルシフト推進目標（鉄道・内航海運）。

    出典: 第3次交通政策基本計画 (令和5年8月閣議決定)
    """

    # 鉄道貨物の輸送量（トンキロベース）の目標
    rail_freight_tonkm_target_2030: float = 220.0    # 億トンキロ（2030年度目標）
    rail_freight_tonkm_base_2019: float = 190.0      # 億トンキロ（2019年度実績）

    # 内航海運（モーダルシフト分の輸送量）目標
    coastal_shift_tonkm_target_2030: float = 410.0   # 億トンキロ（2030年度目標）
    coastal_shift_tonkm_base_2019: float = 340.0     # 億トンキロ（2019年度実績）


MODAL_SHIFT_TARGET = ModalShiftTarget()


FRESHNESS = Freshness(
    label="物流分野 国家目標（CO2・モーダルシフト）",
    last_updated=date(2023, 8, 25),  # 第3次交通政策基本計画 閣議決定日
    update_cadence="biennial",
    source_url=(
        "https://www.mlit.go.jp/sogoseisaku/transport/sosei_transport_tk_000146.html"
    ),
    notes="計画見直しのタイミングで last_updated を更新。",
)
register("national_targets", FRESHNESS)
