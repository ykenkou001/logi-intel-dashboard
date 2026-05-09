"""提出実務チェックリスト（Codex 1 取込）。

中長期計画書（様式第3）/ 定期報告書（様式第5）の提出時に必要となる
実務情報（提出経路・指定通知書番号・法人番号・代表者情報・連絡先）を
機械的に列挙し、提出物の最終ページに統合できる形で提供する。

設計方針:
    - 自動補完できる項目（会社名・CLO名・JSIC コード）は流し込む
    - 自社固有の項目（法人番号・指定通知書番号・代表者氏名）は placeholder
    - 様式第3 / 様式第4 / 様式第5 の使い分けを固定テキストで提示
    - Markdown / プレーンテキスト / 行リストの 3 形式で出力可能
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChecklistItem:
    """提出実務チェックリストの 1 項目。"""

    label: str
    """項目名（例: '指定通知書番号'）。"""

    guidance: str
    """記載内容のガイダンス（例: '特定事業者指定の証跡を記載'）。"""

    auto_value: str | None = None
    """自動補完できる値。None なら自社確認が必要。"""

    required: bool = True
    """提出に必須か（False なら任意）。"""


@dataclass(frozen=True)
class SubmissionChecklist:
    """提出実務チェックリスト（form3 / form5 共通）。"""

    submission_method: str
    """提出経路（e-Gov / GビズID）。"""

    items: list[ChecklistItem]
    """個別チェック項目。"""

    form_usage_notes: list[str] = field(default_factory=list)
    """様式第3 / 第4 / 第5 の使い分けに関する注釈。"""

    def to_markdown_lines(self) -> list[str]:
        """Markdown 形式の行リスト。"""
        lines: list[str] = [
            "## 提出準備チェックリスト（実務）",
            "",
            f"**提出経路**: {self.submission_method}",
            "",
            "### 必要情報",
            "",
        ]
        for item in self.items:
            check = "✅" if item.auto_value else "☐"
            value_part = f"`{item.auto_value}`" if item.auto_value else "（自社で記載）"
            req_mark = " (必須)" if item.required else " (任意)"
            lines.append(f"- {check} **{item.label}**{req_mark}: {item.guidance} → {value_part}")
        if self.form_usage_notes:
            lines += ["", "### 様式の使い分け", ""]
            lines.extend(f"- {note}" for note in self.form_usage_notes)
        return lines

    def to_text_lines(self) -> list[str]:
        """プレーンテキスト形式の行リスト（PPT・サマリー埋込み用）。"""
        lines: list[str] = [
            "【提出準備チェックリスト（実務）】",
            f"  提出経路: {self.submission_method}",
            "",
            "  必要情報:",
        ]
        for item in self.items:
            check = "✅" if item.auto_value else "☐"
            value_part = item.auto_value if item.auto_value else "（自社で記載）"
            req_mark = "必須" if item.required else "任意"
            lines.append(f"  {check} {item.label} [{req_mark}]: {item.guidance} → {value_part}")
        if self.form_usage_notes:
            lines += ["", "  様式の使い分け:"]
            lines.extend(f"  ・{note}" for note in self.form_usage_notes)
        return lines


_FORM_USAGE_NOTES: list[str] = [
    "様式第3別紙（中長期計画書）: 5 年に 1 度作成・改定。初回は 2026 年 10 月末まで",
    "様式第4（変更届出書）: 計画期間中の事業内容・体制変更時に随時提出",
    "様式第5（定期報告書）: 毎年 7 月末までに前年度実績を報告",
]


def build_submission_checklist(
    *,
    company_name: str | None = None,
    main_business: str | None = None,
    jsic_code: str | None = None,
    clo_name: str | None = None,
    is_chain_franchise: bool = False,
    must_appoint_clo: bool = True,
) -> SubmissionChecklist:
    """会社プロフィールから提出実務チェックリストを生成する。

    自動補完できる項目（会社名・CLO 名・主たる事業・JSIC コード）は流し込み、
    自社固有の項目（法人番号・指定通知書番号・代表者氏名・連絡先）は
    placeholder として提示する。

    Args:
        company_name: 事業者の名称（auto 補完）
        main_business: 主たる事業の名称（auto 補完）
        jsic_code: JSIC 細分類4桁（auto 補完）
        clo_name: CLO 役職・氏名（auto 補完・must_appoint_clo=True なら必須）
        is_chain_franchise: 連鎖化事業者か
        must_appoint_clo: CLO 選任義務がある会社区分か

    Returns:
        SubmissionChecklist
    """
    items: list[ChecklistItem] = [
        ChecklistItem(
            label="事業者の名称",
            guidance="登記名称を記載",
            auto_value=company_name,
        ),
        ChecklistItem(
            label="主たる事業",
            guidance="主たる事業の名称（業種）を記載",
            auto_value=main_business,
        ),
        ChecklistItem(
            label="主たる事業の細分類番号",
            guidance="JSIC 細分類4桁",
            auto_value=jsic_code,
        ),
        ChecklistItem(
            label="法人番号",
            guidance=(
                "13 桁の法人番号を記載（国税庁 法人番号公表サイト houjin-bangou.nta.go.jp で確認）"
            ),
            auto_value=None,
        ),
        ChecklistItem(
            label="指定通知書番号",
            guidance=(
                "特定第一種荷主／第二種荷主／連鎖化事業者の指定通知書番号を記載"
                "（国交省より受領済の指定通知書を確認）"
            ),
            auto_value=None,
            required=not is_chain_franchise or True,
        ),
        ChecklistItem(
            label="代表者情報",
            guidance="代表者氏名・役職を記載",
            auto_value=None,
        ),
        ChecklistItem(
            label="作成担当者連絡先",
            guidance="氏名・所属部署・電話番号・メールアドレス",
            auto_value=None,
        ),
    ]

    if must_appoint_clo:
        items.append(
            ChecklistItem(
                label="CLO 役職・氏名",
                guidance="物流統括管理者（役員級）の役職・氏名を記載",
                auto_value=clo_name,
            )
        )

    submission_method = "e-Gov 電子申請（GビズID プライム または GビズID メンバー）"

    return SubmissionChecklist(
        submission_method=submission_method,
        items=items,
        form_usage_notes=list(_FORM_USAGE_NOTES),
    )


__all__ = [
    "ChecklistItem",
    "SubmissionChecklist",
    "build_submission_checklist",
]
