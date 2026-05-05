"""会社区分から物流効率化法の該当条文ラベルを解決する純粋関数。

CLO 計画書出力（PPT / Word / Markdown / Excel）で会社区分（特定第一種荷主・
第二種荷主 / 特定連鎖化事業者）に応じて引用すべき条文を切替えるための共通ロジック。

法令区分対応:
    - 第46条: 特定第一種荷主 / 第二種荷主（中長期計画作成義務）
    - 第65条: 特定連鎖化事業者（中長期計画作成義務）
    - 第66条: CLO（物流統括管理者）の選任義務 — 上記いずれの区分にも横断的に適用

設計方針:
    - eligibility（既存ロジック）を入力に取り、文字列ラベルを返す純粋関数のみ
    - 連鎖化事業者と荷主の重複該当はあり得ないが、両方該当しても安全な順序で判定
"""
from __future__ import annotations

from core.legal.eligibility import EligibilityResult


def resolve_plan_law_article_label(eligibility: EligibilityResult) -> str:
    """会社区分に応じた中長期計画書の根拠条文ラベルを返す。

    Args:
        eligibility: 区分判定結果

    Returns:
        条文ラベル（例: "物流効率化法 第46条（特定荷主）"）。
        該当区分がない場合は CLO 選任義務なしを示す文言。
    """
    if "chain_franchise" in eligibility.categories:
        return "物流効率化法 第65条（特定連鎖化事業者の中長期計画作成義務）"
    if any(
        c in eligibility.categories
        for c in ("first_class_shipper", "second_class_shipper")
    ):
        return "物流効率化法 第46条（特定荷主の中長期計画作成義務）"
    return "物流効率化法（該当条文なし — CLO 選任義務なし）"


def resolve_clo_appointment_law_article_label(
    eligibility: EligibilityResult,
) -> str | None:
    """CLO 選任義務がある場合の第66条参照ラベルを返す。義務なしなら None。"""
    if eligibility.must_appoint_clo:
        return "物流効率化法 第66条（物流統括管理者（CLO）の選任義務）"
    return None


def expected_plan_article_number(eligibility: EligibilityResult) -> int | None:
    """中長期計画の根拠条文番号（46 or 65）を返す。CLO 選任不要なら None。

    submission_validator が「計画書の citations に当該条文番号が含まれているか」
    検査するために使用する。
    """
    if "chain_franchise" in eligibility.categories:
        return 65
    if any(
        c in eligibility.categories
        for c in ("first_class_shipper", "second_class_shipper")
    ):
        return 46
    return None
