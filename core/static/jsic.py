"""日本標準産業分類（JSIC）細分類4桁コードの主要マスタ。

出典:
    総務省「日本標準産業分類」（令和5年7月総務省告示第265号、2024年4月施行）
    https://www.soumu.go.jp/toukei_toukatsu/index/seido/sangyo/index.htm

スコープ:
    CLO 計画書で記載が必要な「主たる事業の細分類番号」用に、
    物流関連業種・主要荷主業種を網羅する。完全な全コードは収録しない。

設計方針:
    - コード（4桁文字列）→ 名称、業種カテゴリの双方向マッピング
    - 業種カテゴリ（manufacturing/wholesale/retail/transport/chain_franchise）で
      ベンチマーク分析の対象業種選択や記載事例集の選択に利用
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from core.static._freshness import Freshness, register

# 業種カテゴリ
JsicCategory = Literal[
    "manufacturing",     # 製造業（D）
    "wholesale",         # 卸売業（I 51）
    "retail",            # 小売業（I 56-60）
    "transport",         # 運輸業（H）
    "chain_franchise",   # フランチャイズ本部（連鎖化事業者の典型）
    "other",
]


@dataclass(frozen=True)
class JsicEntry:
    """JSIC 細分類1件分。"""

    code: str            # 4桁コード（文字列。先頭ゼロ保持）
    name: str            # 細分類名
    category: JsicCategory


# CLO 関連の主要細分類カタログ（全業種を網羅しない）
JSIC_ENTRIES: list[JsicEntry] = [
    # 製造業（D 大分類）— 主要メーカー業種
    JsicEntry("0911", "食肉加工品製造業", "manufacturing"),
    JsicEntry("1041", "清涼飲料製造業", "manufacturing"),
    JsicEntry("1611", "化学肥料製造業", "manufacturing"),
    JsicEntry("1631", "医薬品製造業", "manufacturing"),
    JsicEntry("2521", "建設用金属製品製造業", "manufacturing"),
    JsicEntry("2911", "電子部品製造業", "manufacturing"),
    JsicEntry("3011", "電子計算機製造業", "manufacturing"),
    JsicEntry("3111", "通信機械器具製造業", "manufacturing"),
    JsicEntry("3159", "その他の電子部品・デバイス製造業", "manufacturing"),
    JsicEntry("3211", "自動車製造業", "manufacturing"),

    # 卸売業（I 51）
    JsicEntry("5121", "繊維品卸売業", "wholesale"),
    JsicEntry("5141", "建築材料卸売業", "wholesale"),
    JsicEntry("5161", "化学製品卸売業", "wholesale"),
    JsicEntry("5211", "自動車卸売業", "wholesale"),
    JsicEntry("5311", "農畜産物・水産物卸売業", "wholesale"),
    JsicEntry("5411", "食料・飲料卸売業", "wholesale"),
    JsicEntry("5514", "室内装飾繊維品卸売業", "wholesale"),

    # 小売業（I 56〜60）
    JsicEntry("5611", "百貨店、総合スーパー", "retail"),
    JsicEntry("5811", "各種食料品小売業", "retail"),
    JsicEntry("5891", "コンビニエンスストア（飲食料品を中心とするものに限る）", "chain_franchise"),
    JsicEntry("5911", "自動車小売業", "retail"),
    JsicEntry("6011", "ドラッグストア", "retail"),

    # 運輸業（H 大分類）— 運送業者
    JsicEntry("4411", "一般貨物自動車運送業", "transport"),
    JsicEntry("4441", "宅配便事業", "transport"),
    JsicEntry("4521", "外航貨物海運業", "transport"),
    JsicEntry("4531", "内航貨物海運業", "transport"),
    JsicEntry("4581", "鉄道貨物運送業", "transport"),
    JsicEntry("4711", "倉庫業", "transport"),
]

# 高速ルックアップ用 dict
_BY_CODE: dict[str, JsicEntry] = {e.code: e for e in JSIC_ENTRIES}


def lookup(code: str) -> JsicEntry | None:
    """4桁コードから JsicEntry を取得する。"""
    return _BY_CODE.get(code)


def name_of(code: str) -> str | None:
    """4桁コードから細分類名を返す。未収録なら None。"""
    entry = _BY_CODE.get(code)
    return entry.name if entry else None


def category_of(code: str) -> JsicCategory | None:
    """4桁コードから業種カテゴリを返す。未収録なら None。"""
    entry = _BY_CODE.get(code)
    return entry.category if entry else None


def codes_in_category(category: JsicCategory) -> list[str]:
    """指定カテゴリに属するコード一覧を返す。"""
    return [e.code for e in JSIC_ENTRIES if e.category == category]


FRESHNESS = Freshness(
    label="日本標準産業分類（細分類）",
    last_updated=date(2023, 7, 1),  # 令和5年7月告示
    update_cadence="as_needed",
    source_url="https://www.soumu.go.jp/toukei_toukatsu/index/seido/sangyo/index.htm",
    notes="改正告示時に追加収録。本ファイルは CLO 関連業種に絞った抜粋。",
)
register("jsic", FRESHNESS)
