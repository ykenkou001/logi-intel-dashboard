"""改善基準告示の数値定数（自動車運転者の労働時間等の改善のための基準）。

出典:
    厚生労働省告示「自動車運転者の労働時間等の改善のための基準」
    (昭和 64 年労働省告示第 7 号、最終改正 令和 4 年 12 月 23 日厚生労働省告示第 367 号)
    2024 年 4 月 1 日施行（いわゆる 2024 年問題）

URL:
    https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/roudoukijun/jidousha/index.html

注意:
    - ここで定義する数値は **告示原文に準拠**する
    - 一般によく言及される「年 960h」は時間外労働の上限であって、拘束時間とは別概念
    - 計画書・経営会議で使用する場合は、必ず本モジュールから引用する（独自数値を書かない）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.static._freshness import Freshness, register


@dataclass(frozen=True)
class WaitTimeStandard:
    """荷待ち時間の運用目標値（改善基準告示の定量化補助）。

    告示原文に直接書かれている数値（2 時間超で「健康障害を生ずるおそれ」相当）に加え、
    国交省ガイドライン・JILS 物流コスト調査の業界ベンチマークから設定した運用目標。
    `wait_time_heatmap` の severity 判定および J3 デイリーコックピットの違反検知で使用する。

    出典:
        - 改善基準告示（2024 年 4 月施行版）
        - 国交省「物流効率化に向けた荷主・物流事業者の取組事例集」
        - JILS 2021 年度物流コスト調査報告書
    """

    threshold_minutes: int = 120          # 2 時間基準（改善基準告示で「過度な拘束」相当）
    over_threshold_max_pct: float = 5.0   # 2 時間超過率の運用目標（5% 以下）
    avg_target_minutes: int = 30          # 平均荷待ち時間の運用目標（30 分以下）
    measurement_minimum_runs: int = 100   # 統計的有意性のための最低計測便数


WAIT_TIME_STANDARD = WaitTimeStandard()


@dataclass(frozen=True)
class TruckDriverStandard:
    """トラック運転者の改善基準告示（2024 年 4 月施行版）。

    告示原文に基づく数値のみを定義する。実装側で独自に解釈した派生値は持たせない。
    """

    # 1 日の拘束時間
    max_daily_working_hours_principle: int = 13     # 1日の拘束時間 原則 13 時間以内
    max_daily_working_hours_max: int = 15           # 1日の拘束時間 最大 15 時間（例外時 16 時間）
    max_daily_working_hours_exception: int = 16     # 例外時の1日拘束時間上限
    daily_over_14h_max_count_per_week: int = 3      # 1日14時間超は週2回までが目安（運用上）

    # 連続休息期間（2024 年改正で上方修正）
    min_rest_hours_principle: int = 11              # 連続休息 原則 11 時間以上
    min_rest_hours_floor: int = 9                   # 連続休息 下限 9 時間

    # 年間・月間の拘束時間
    max_annual_working_hours_principle: int = 3300  # 年間総拘束時間 原則 3,300 時間
    max_annual_working_hours_exception: int = 3400  # 労使協定で 3,400 時間まで延長可
    max_monthly_working_hours_principle: int = 284  # 1ヶ月の拘束時間 原則 284 時間
    max_monthly_working_hours_exception: int = 310  # 例外で 310 時間まで延長可

    # 時間外労働（働き方改革関連法 / 同時施行）
    max_annual_overtime_hours: int = 960            # 時間外労働 年間上限 960 時間（運送業の特例）

    # 1 回の運転時間（4 時間ごとに 30 分以上の休憩を合算で必要）
    max_continuous_driving_hours: int = 4           # 連続運転 4 時間
    min_break_per_4h_continuous_minutes: int = 30   # 4 時間運転毎に必要な休憩

    # 2 日平均の運転時間
    max_avg_driving_hours_per_2days: int = 9        # 2 日平均 1 日 9 時間以内


# シングルトン定数として公開
TRUCK_DRIVER_STANDARD = TruckDriverStandard()

# 鮮度メタデータ
FRESHNESS = Freshness(
    label="改善基準告示（トラック運転者）",
    last_updated=date(2022, 12, 23),  # 最終改正告示日
    update_cadence="as_needed",        # 改正時のみ更新
    source_url=(
        "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/"
        "roudoukijun/jidousha/index.html"
    ),
    notes="2024 年 4 月施行版。改正時は本ファイルと last_updated を更新する。",
)
register("improvement_standards", FRESHNESS)


def driver_capacity_reduction_factor() -> float:
    """2024 年問題による運転者実効稼働力の減少係数。

    年間時間外上限 960h により、規制前と比較して約 13〜14% の実稼働時間減と
    業界団体が推計している。本値は分析モジュール（driver_gap）で使用する。

    Returns:
        0.13〜0.14 の中央値 0.135（変動を保守的に見積もる場合は上限 0.14 を使う）
    """
    return 0.135
