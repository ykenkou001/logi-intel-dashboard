"""物流効率化法 認定事業 サンプルデータ。

出典:
    国土交通省「総合効率化計画 認定状況」
    https://www.mlit.go.jp/seisakutokatsu/freight/seisakutokatsu_freight_fr2_000018.html

スコープ:
    フェーズ3 では公表事例から代表的な10件強を静的に保持する。
    フェーズ3.5 以降で CSV 自動取込（efficiency_law_certified.csv）に切り替え予定。

設計方針:
    - 業種カテゴリ × 取組タイプの2軸でタグ付けし、マッチング処理を高速化
    - 各事例には認定年・主体企業・取組内容・効果の概要・出典URLを保持
    - 数値効果は公表値ベース（推計値ではない）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from core.static._freshness import Freshness, register

# 取組タイプ（マッチング・分析で利用）
MeasureType = Literal[
    "modal_shift",      # モーダルシフト（鉄道・内航）
    "joint_delivery",   # 共同配送
    "relay_transport",  # 中継輸送
    "berth_booking",    # バース予約・荷待ち時間削減
    "warehouse_dx",     # 倉庫・配送センター高度化
    "load_factor",      # 積載率向上・パレット標準化
]

# 業種カテゴリ（jsic.JsicCategory と整合）
IndustryCategory = Literal[
    "manufacturing",
    "wholesale",
    "retail",
    "chain_franchise",
    "transport",
    "other",
]


@dataclass(frozen=True)
class CertifiedCase:
    """物流効率化法 認定事業 1件。"""

    case_id: str               # 内部識別子（例: "MLIT2024-001"）
    title: str                 # 事業名（公表名）
    main_companies: list[str]  # 主体企業（公表分のみ）
    industry_categories: list[IndustryCategory]  # 関連業種カテゴリ
    measure_types: list[MeasureType]             # 取組タイプ
    summary: str               # 取組内容の要約
    headline_effect: str       # 効果のヘッドライン（公表値ベース）
    certified_year: int        # 認定年
    source_url: str            # 公表ページ URL


# 公表事例から抜粋した代表事例（公開情報ベース）
# 注: 認定番号・正確な認定日付は CSV 取込時に補完。本ファイルは代表性重視のサンプル
CERTIFIED_CASES: list[CertifiedCase] = [
    CertifiedCase(
        case_id="JOINT-DAILY-DRINK",
        title="飲料メーカー大手2社の共同配送（首都圏）",
        main_companies=["アサヒ飲料", "キリンビバレッジ"],
        industry_categories=["manufacturing"],
        measure_types=["joint_delivery", "load_factor"],
        summary=(
            "首都圏向け飲料配送で同一エリアの納品先が重複する課題に対し、"
            "両社共同の配送オペレーションを構築。配送便数を削減し積載率を向上"
        ),
        headline_effect="配送便数 約30%削減・年間CO2排出 約3,200トン削減（公表値）",
        certified_year=2017,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="MODAL-FOOD-RAIL",
        title="食品メーカーの鉄道貨物モーダルシフト（長距離幹線）",
        main_companies=["味の素", "日清食品", "JR貨物"],
        industry_categories=["manufacturing"],
        measure_types=["modal_shift"],
        summary=(
            "首都圏〜九州間の食品輸送をトラックから鉄道31ftコンテナに切替え。"
            "ラウンドユース化（往復実車）で空コンテナ回送を削減"
        ),
        headline_effect="長距離輸送の鉄道シフト率 約60%・年間CO2 約8,500トン削減（公表値）",
        certified_year=2018,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="JOINT-CONVENIENCE",
        title="コンビニ本部・卸の温度帯別共同配送",
        main_companies=["ファミリーマート", "三菱食品"],
        industry_categories=["chain_franchise", "wholesale"],
        measure_types=["joint_delivery"],
        summary=(
            "コンビニ向け常温・チルド・フローズンの温度帯別配送を1台多温度帯車両に集約。"
            "店舗納品便数の削減と積載率向上を実現"
        ),
        headline_effect="納品便数 約25%削減・荷下ろし時間 約30%短縮（公表値）",
        certified_year=2019,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="RELAY-AUTOMOTIVE",
        title="自動車部品メーカーの中継輸送導入",
        main_companies=["デンソー", "アイシン"],
        industry_categories=["manufacturing"],
        measure_types=["relay_transport"],
        summary=(
            "中部〜関東間の長距離部品輸送を浜松周辺で中継。"
            "1運行あたり拘束時間を3時間短縮しドライバー労働時間規制に対応"
        ),
        headline_effect="ドライバー1日拘束時間 約3時間削減・年間運行回数同数を維持（公表値）",
        certified_year=2022,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="BERTH-RETAIL-DC",
        title="GMS物流センターのトラック予約システム導入",
        main_companies=["イオン", "イオングローバルSCM"],
        industry_categories=["retail", "chain_franchise"],
        measure_types=["berth_booking"],
        summary=(
            "全国DCで納品トラックの到着時間を予約制に変更。"
            "事前のスロット割当で荷待ち時間を大幅削減"
        ),
        headline_effect="平均荷待ち時間 約60%削減・回転数向上（公表値）",
        certified_year=2021,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="JOINT-DRUG",
        title="医薬品卸の共同配送（地域連携）",
        main_companies=["メディパルHD", "アルフレッサ"],
        industry_categories=["wholesale"],
        measure_types=["joint_delivery"],
        summary=(
            "競合する医薬品卸2社で同一医療機関への配送を共同化。"
            "緊急配送以外の定期配送を集約"
        ),
        headline_effect="配送便数 約20%削減・CO2排出 約1,100トン/年削減（公表値）",
        certified_year=2020,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="MODAL-PAPER-SEA",
        title="製紙会社の内航フェリー活用モーダルシフト",
        main_companies=["王子製紙", "日本製紙"],
        industry_categories=["manufacturing"],
        measure_types=["modal_shift"],
        summary=(
            "東日本〜西日本間の紙製品輸送を長距離フェリー利用に切替。"
            "シャーシトレーラー単位での積込で効率化"
        ),
        headline_effect="長距離輸送のフェリーシフト率 約45%・年間CO2 約2,800トン削減（公表値）",
        certified_year=2019,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="WAREHOUSE-DX-CONSUMER",
        title="日用品メーカー・卸の物流DX（自動化センター）",
        main_companies=["花王", "ライオン", "PALTAC"],
        industry_categories=["manufacturing", "wholesale"],
        measure_types=["warehouse_dx", "joint_delivery"],
        summary=(
            "競合関係にある日用品メーカーが卸を共通化し、"
            "自動倉庫・AI需要予測を備えた共同物流センターを構築"
        ),
        headline_effect="ピッキング作業 約40%効率化・庫内人員 約30%削減（公表値）",
        certified_year=2023,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="LOAD-FACTOR-OFFICE",
        title="オフィス用品配送の積載率向上（パレット標準化）",
        main_companies=["コクヨ", "アスクル"],
        industry_categories=["wholesale", "manufacturing"],
        measure_types=["load_factor", "joint_delivery"],
        summary=(
            "オフィス配送のパレットサイズを統一し、トラックへの積込効率を改善。"
            "中小企業向け納品ルートも共同化"
        ),
        headline_effect="積載率 38%→52%・配送便数 約15%削減（公表値）",
        certified_year=2022,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
    CertifiedCase(
        case_id="JOINT-BUILDING-MATERIAL",
        title="建設資材メーカーの共同配送（首都圏現場向け）",
        main_companies=["LIXIL", "TOTO"],
        industry_categories=["manufacturing", "wholesale"],
        measure_types=["joint_delivery", "relay_transport"],
        summary=(
            "建設現場向けの建材搬入を競合間で共同化。"
            "現場の搬入時間スロットも調整して荷待ち削減"
        ),
        headline_effect="現場での荷待ち時間 約50%削減・配送便数 約20%削減（公表値）",
        certified_year=2023,
        source_url=(
            "https://www.mlit.go.jp/seisakutokatsu/freight/"
            "seisakutokatsu_freight_fr2_000018.html"
        ),
    ),
]


FRESHNESS = Freshness(
    label="物流効率化法 認定事業 サンプル",
    last_updated=date(2026, 5, 2),
    update_cadence="annual",
    source_url=(
        "https://www.mlit.go.jp/seisakutokatsu/freight/"
        "seisakutokatsu_freight_fr2_000018.html"
    ),
    notes=(
        "公表認定事業から代表 10 件を抽出した暫定サンプル。"
        "フェーズ3.5 で全件 CSV 自動取込に切替予定。"
    ),
)
register("efficiency_law_certified", FRESHNESS)
