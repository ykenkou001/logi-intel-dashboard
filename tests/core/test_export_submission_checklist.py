"""core/export/submission_checklist.py の単体テスト。

Codex 1 取込（提出実務チェックリスト）の構造と出力フォーマットを検証する。
"""
from __future__ import annotations

from core.export.submission_checklist import (
    ChecklistItem,
    SubmissionChecklist,
    build_submission_checklist,
)


def test_checklist_item_construct() -> None:
    item = ChecklistItem(
        label="法人番号",
        guidance="13桁を記載",
        auto_value="1234567890123",
        required=True,
    )
    assert item.label == "法人番号"
    assert item.auto_value == "1234567890123"
    assert item.required is True


def test_build_submission_checklist_auto_fills_company_info() -> None:
    """会社情報を渡すと auto_value に流し込まれる。"""
    checklist = build_submission_checklist(
        company_name="テクノパーツ製造株式会社",
        main_business="電子部品製造業",
        jsic_code="3159",
        clo_name="専務執行役員 田中 雄一",
        is_chain_franchise=False,
        must_appoint_clo=True,
    )
    assert isinstance(checklist, SubmissionChecklist)
    labels = {item.label: item.auto_value for item in checklist.items}
    assert labels["事業者の名称"] == "テクノパーツ製造株式会社"
    assert labels["主たる事業"] == "電子部品製造業"
    assert labels["主たる事業の細分類番号"] == "3159"
    assert labels["CLO 役職・氏名"] == "専務執行役員 田中 雄一"


def test_build_submission_checklist_placeholder_for_self_managed_fields() -> None:
    """法人番号・指定通知書番号・代表者情報は自社で記載（auto_value=None）。"""
    checklist = build_submission_checklist(
        company_name="テスト株式会社",
        main_business="x",
        jsic_code="1234",
        clo_name="テストCLO",
    )
    self_managed = ["法人番号", "指定通知書番号", "代表者情報", "作成担当者連絡先"]
    for label in self_managed:
        item = next(i for i in checklist.items if i.label == label)
        assert item.auto_value is None


def test_clo_item_omitted_when_no_appointment_obligation() -> None:
    checklist = build_submission_checklist(
        company_name="x",
        main_business="x",
        jsic_code="1234",
        clo_name="x",
        must_appoint_clo=False,
    )
    labels = [item.label for item in checklist.items]
    assert "CLO 役職・氏名" not in labels


def test_submission_method_is_e_gov() -> None:
    checklist = build_submission_checklist(company_name="x")
    assert "e-Gov" in checklist.submission_method
    assert "GビズID" in checklist.submission_method


def test_form_usage_notes_include_three_forms() -> None:
    checklist = build_submission_checklist(company_name="x")
    notes = " ".join(checklist.form_usage_notes)
    assert "様式第3" in notes
    assert "様式第4" in notes
    assert "様式第5" in notes


def test_to_markdown_lines_includes_submission_path() -> None:
    checklist = build_submission_checklist(
        company_name="テスト",
        main_business="x",
        jsic_code="1234",
    )
    lines = checklist.to_markdown_lines()
    text = "\n".join(lines)
    assert "提出準備チェックリスト" in text
    assert "提出経路" in text
    assert "事業者の名称" in text


def test_to_text_lines_returns_plaintext() -> None:
    """PPT 埋込み・サマリー用にプレーンテキストを返す（Markdown 構文を含まない）。"""
    checklist = build_submission_checklist(company_name="x")
    lines = checklist.to_text_lines()
    text = "\n".join(lines)
    assert "提出準備チェックリスト" in text
    # Markdown のヘッダ・リスト記法は含まない
    assert "##" not in text
    assert not any(line.startswith("- ") for line in lines)
