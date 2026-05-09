"""出典 URL の統一管理。

経営会議で「この数字の出典は？」と聞かれて即答できる状態を担保する。
全ての成果物（PPT スライド・Excel セル・Markdown 数値・MCP レスポンス）に
本モジュール経由で出典を付与する。

設計方針:
    - データソースごとに `Citation` インスタンスを生成
    - フォーマッタ（PPT 脚注・Excel シート行・Markdown 引用）を分離
    - `fetched_at` は取得時刻を ISO 8601 文字列で記録
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Citation:
    """単一の出典情報。

    Attributes:
        label: 表示用ラベル（例: "経済センサス‐活動調査 2021"）
        url: 一次情報の URL（必須・経営会議の説明責任を果たすため）
        stats_data_id: e-Stat の statsDataId（該当時のみ）
        notice_number: 告示番号（該当時のみ／例: "厚生労働省告示第367号"）
        ordinance_number: 省令番号（該当時のみ）
        fetched_at: ISO 8601 形式の取得時刻
        accessed_via: 取得経路（"e-Stat API", "gogo.gs", "手動DL" 等）
    """

    label: str
    url: str
    stats_data_id: str | None = None
    notice_number: str | None = None
    ordinance_number: str | None = None
    fetched_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"),
    )
    accessed_via: str = ""

    def to_dict(self) -> dict[str, str | None]:
        """MCP ツールの戻り値構造（citations 配列の要素）に流し込む形式。"""
        return {
            "label": self.label,
            "url": self.url,
            "stats_data_id": self.stats_data_id,
            "notice_number": self.notice_number,
            "ordinance_number": self.ordinance_number,
            "fetched_at": self.fetched_at,
            "accessed_via": self.accessed_via or None,
        }

    def to_footnote(self) -> str:
        """PPT スライド脚注向けの 1 行表示。"""
        parts = [self.label]
        if self.stats_data_id:
            parts.append(f"statsDataId={self.stats_data_id}")
        if self.notice_number:
            parts.append(self.notice_number)
        if self.ordinance_number:
            parts.append(self.ordinance_number)
        parts.append(self.url)
        return "出典: " + " / ".join(parts)

    def to_markdown(self) -> str:
        """Markdown 引用形式（脚注リスト用）。"""
        return f"- [{self.label}]({self.url})" + (
            f" — statsDataId={self.stats_data_id}" if self.stats_data_id else ""
        )


# 主要データソースのテンプレート
def estat_citation(
    table_label: str,
    stats_data_id: str,
    accessed_via: str = "e-Stat API",
) -> Citation:
    """e-Stat 経由の引用テンプレート。"""
    return Citation(
        label=table_label,
        url=f"https://www.e-stat.go.jp/dbview?sid={stats_data_id}",
        stats_data_id=stats_data_id,
        accessed_via=accessed_via,
    )


def fuel_price_citation(source_label: str = "gogo.gs 全国平均") -> Citation:
    """燃料価格の引用テンプレート。"""
    return Citation(
        label=source_label,
        url="https://gogo.gs/",
        accessed_via="gogo.gs HTML スクレイピング",
    )


def jma_warning_citation() -> Citation:
    """気象庁警報の引用テンプレート。"""
    return Citation(
        label="気象庁 防災情報 XML / JSON",
        url="https://www.jma.go.jp/bosai/",
        accessed_via="気象庁 bosai JSON",
    )


def improvement_standards_citation() -> Citation:
    """改善基準告示の引用テンプレート。"""
    return Citation(
        label="自動車運転者の労働時間等の改善のための基準（2024年4月施行）",
        url=(
            "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/"
            "roudoukijun/jidousha/index.html"
        ),
        notice_number="厚生労働省告示第367号（令和4年12月23日改正）",
        accessed_via="厚生労働省ポータル",
    )


def logistics_efficiency_law_citation() -> Citation:
    """物流効率化法の包括的引用テンプレート（条文非特定）。"""
    return Citation(
        label="物資の流通の効率化に関する法律（改正物流効率化法）",
        url="https://www.revised-logistics-act-portal.mlit.go.jp/",
        accessed_via="国土交通省ポータル",
    )


def logistics_efficiency_law_article46_citation() -> Citation:
    """物流効率化法 第46条 — 特定荷主の中長期計画作成義務。

    特定第一種荷主（発荷主）/ 第二種荷主（着荷主）に適用。
    年間取扱貨物量 9 万トン以上の事業者が対象。
    """
    return Citation(
        label="物流効率化法 第46条（特定荷主の中長期計画作成義務）",
        url="https://www.revised-logistics-act-portal.mlit.go.jp/",
        ordinance_number="物流効率化法 第46条",
        accessed_via="国土交通省ポータル",
    )


def logistics_efficiency_law_article65_citation() -> Citation:
    """物流効率化法 第65条 — 特定連鎖化事業者の中長期計画作成義務。

    フランチャイズ本部等。記載項目は荷待ち時間短縮 + 積載率向上の2 領域。
    様式第3 の「第5条関係」で出力する点が荷主向けと異なる。
    """
    return Citation(
        label="物流効率化法 第65条（特定連鎖化事業者の中長期計画作成義務）",
        url="https://www.revised-logistics-act-portal.mlit.go.jp/",
        ordinance_number="物流効率化法 第65条",
        accessed_via="国土交通省ポータル",
    )


def logistics_efficiency_law_article66_citation() -> Citation:
    """物流効率化法 第66条 — CLO（物流統括管理者）の選任義務。

    特定荷主・特定連鎖化事業者に横断的に適用。役員級の選任が義務付けられる。
    """
    return Citation(
        label="物流効率化法 第66条（物流統括管理者（CLO）の選任義務）",
        url="https://www.revised-logistics-act-portal.mlit.go.jp/",
        ordinance_number="物流効率化法 第66条",
        accessed_via="国土交通省ポータル",
    )


def corp_number_citation() -> Citation:
    """国税庁法人番号 API の引用テンプレート。"""
    return Citation(
        label="国税庁 法人番号公表サイト",
        url="https://www.houjin-bangou.nta.go.jp/",
        accessed_via="国税庁 法人番号 API v4",
    )


def xroad_citation() -> Citation:
    """xROAD 交通量 API の引用テンプレート。"""
    return Citation(
        label="JARTIC 道路交通情報 API（xROAD）",
        url="https://www.jartic.or.jp/",
        accessed_via="JARTIC オープン API（WFS）",
    )


def co2_factors_citation() -> Citation:
    """CO2 排出原単位の引用テンプレート。"""
    return Citation(
        label="ロジスティクス分野におけるCO2排出量算定方法 共同ガイドライン Ver.3.2",
        url="https://www.greenpartnership.jp/guideline_ver3_2.pdf",
        accessed_via="経産省・国交省共同ガイドライン（令和5年6月）",
    )
