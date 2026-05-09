"""物流関連 e-Stat 統計表への特化アクセサ。

設計方針:
    - 既存 `EStatClient` を内部で使う薄いラッパー
    - **statsDataId をハードコードしない**: `statsCode` から動的に最新の
      `statsDataId` を取得する（年次更新に追従するため）
    - 物流必修統計の `statsCode` を一箇所にカタログ化

参考: docs/api_endpoints.md の「statsCode と statsDataId の区別」セクション
"""

from __future__ import annotations

from typing import Any, ClassVar, Self

from core.clients.estat import EStatApiError, EStatClient


class EStatLogisticsClient:
    """物流関連の e-Stat 統計表アクセスを集約するヘルパー。

    用途: 業界ベンチマーク・モーダルシフト試算・ドライバー需給ギャップ等の
    分析モジュールから呼び出すことを想定。
    """

    # 物流関連の主要統計の statsCode（省庁コード）
    # 注: ここは固定 ID。statsDataId は毎年新しい ID が発行されるため動的取得する
    STATS_CODES: ClassVar[dict[str, str]] = {
        "auto_transport": "00600340",  # 自動車輸送統計年報（積載率・実車率）
        "freight_census": "00600370",  # 全国貨物純流動調査（物流センサス／5年に1回）
        "port": "00600460",  # 港湾統計（内航海運キャパ）
        "rail_freight": "00600420",  # 鉄道輸送統計（鉄道貨物キャパ）
        "economic_census": "00200552",  # 経済センサス‐活動調査（事業所数・売上）
        "wage_structure": "00600310",  # 賃金構造基本統計（ドライバー賃金）
        "population_census": "00200521",  # 国勢調査（道路貨物運送業 就業者数）
    }

    def __init__(self) -> None:
        self._estat = EStatClient()

    async def __aenter__(self) -> Self:
        await self._estat.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._estat.__aexit__(*args)

    @property
    def estat(self) -> EStatClient:
        """内部の EStatClient（getMetaInfo / getStatsData の直接呼出用）。"""
        return self._estat

    def _resolve_stats_code(self, dataset: str) -> str:
        """データセット識別子を statsCode に変換する。"""
        if dataset not in self.STATS_CODES:
            raise EStatApiError(
                f"未知のデータセット: '{dataset}'. 利用可能: {sorted(self.STATS_CODES.keys())}"
            )
        return self.STATS_CODES[dataset]

    async def search_logistics_tables(
        self,
        dataset: str,
        survey_year: str | None = None,
    ) -> list[dict[str, Any]]:
        """物流必修統計の表一覧を取得する。

        Args:
            dataset: STATS_CODES のキー（例: "auto_transport", "freight_census"）
            survey_year: 調査年で絞り込み（省略時は全年度）

        Returns:
            statsDataId と表メタデータのリスト
        """
        return await self._estat.search_stats(
            stats_code=self._resolve_stats_code(dataset),
            survey_years=survey_year,
        )

    async def find_latest_stats_data_id(
        self,
        dataset: str,
        title_keyword: str | None = None,
        survey_year: str | None = None,
    ) -> str:
        """データセットから最新（OPEN_DATE 降順 1位）の statsDataId を取得する。

        年次更新で statsDataId が変わる統計でも、本メソッド経由で取得することで
        コードを変更せずに最新データを参照できる。

        Args:
            dataset: STATS_CODES のキー（例: "auto_transport"）
            title_keyword: 表タイトルでの絞り込み（例: "積載率"）
            survey_year: 調査年で絞り込み（例: "2024"）

        Returns:
            最新の statsDataId

        Raises:
            EStatApiError: 該当する統計表が見つからない場合
        """
        tables = await self.search_logistics_tables(dataset, survey_year=survey_year)
        if not tables:
            raise EStatApiError(
                f"dataset='{dataset}' に該当する統計表が見つかりません"
                f"{f' (survey_year={survey_year})' if survey_year else ''}"
            )

        if title_keyword:
            filtered = [t for t in tables if self._matches_title(t, title_keyword)]
            if filtered:
                tables = filtered

        # OPEN_DATE 降順で最新を選ぶ。OPEN_DATE がなければ @id 降順
        tables.sort(
            key=lambda t: (str(t.get("OPEN_DATE", "")), str(t.get("@id", ""))),
            reverse=True,
        )
        return str(tables[0]["@id"])

    @staticmethod
    def _matches_title(table: dict[str, Any], keyword: str) -> bool:
        """統計表のタイトル系フィールドにキーワードが含まれるか判定する。"""
        title = table.get("TITLE")
        title_text = title.get("$", "") if isinstance(title, dict) else str(title or "")
        stat_name = table.get("STAT_NAME")
        stat_name_text = (
            stat_name.get("$", "") if isinstance(stat_name, dict) else str(stat_name or "")
        )
        return keyword in title_text or keyword in stat_name_text

    async def get_stats_data_by_dataset(
        self,
        dataset: str,
        title_keyword: str | None = None,
        survey_year: str | None = None,
        cd_area: str | None = None,
        cd_cat01: str | None = None,
        cd_time: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """データセット指定で統計データを取得する（statsDataId 解決を内蔵）。

        `find_latest_stats_data_id` で最新の表 ID を解決し、`getStatsData` を呼ぶ
        ヘルパー。年次更新を意識せずに最新データを取得できる。

        Args:
            dataset: STATS_CODES のキー
            title_keyword: 表タイトルでの絞り込み
            survey_year: 調査年（特定年度を固定したい場合）
            cd_area: 地域コード（例: "13000"）
            cd_cat01: 分類コード
            cd_time: 時間軸コード
            limit: 取得件数上限

        Returns:
            STATISTICAL_DATA ブロック
        """
        stats_data_id = await self.find_latest_stats_data_id(
            dataset=dataset,
            title_keyword=title_keyword,
            survey_year=survey_year,
        )
        return await self._estat.get_stats_data(
            stats_data_id=stats_data_id,
            cd_area=cd_area,
            cd_cat01=cd_cat01,
            cd_time=cd_time,
            limit=limit,
        )
