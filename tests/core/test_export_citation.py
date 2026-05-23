"""core/export/citation.py の単体テスト。"""
from __future__ import annotations

from core.export.citation import (
    Citation,
    co2_factors_citation,
    estat_citation,
    form5_iv4_iv5_consigned_citation,
    fuel_price_citation,
    improvement_standards_citation,
    improvement_standards_notice_pdf_citation,
    jma_warning_citation,
    logistics_efficiency_law_article57_citation,
    logistics_efficiency_law_citation,
    mlit_shipper_handbook_consigned_citation,
)


def test_citation_to_dict_includes_all_keys() -> None:
    """to_dict が必須キーを含む。"""
    c = Citation(label="test", url="https://example.com")
    d = c.to_dict()
    assert d["label"] == "test"
    assert d["url"] == "https://example.com"
    assert "fetched_at" in d


def test_citation_to_footnote_includes_url_and_label() -> None:
    """to_footnote 出力に URL とラベルが含まれる。"""
    c = Citation(label="経済センサス2021", url="https://example.com",
                 stats_data_id="0004005642")
    fn = c.to_footnote()
    assert "経済センサス2021" in fn
    assert "0004005642" in fn
    assert "https://example.com" in fn
    assert fn.startswith("出典:")


def test_citation_to_markdown() -> None:
    """to_markdown が Markdown 引用形式で出力。"""
    c = Citation(label="A", url="https://a.example.com", stats_data_id="X1")
    md = c.to_markdown()
    assert "[A](https://a.example.com)" in md
    assert "X1" in md


def test_estat_citation_template() -> None:
    """e-Stat テンプレートが statsDataId を URL に埋め込む。"""
    c = estat_citation("経済センサス", "0004005642")
    assert c.stats_data_id == "0004005642"
    assert "0004005642" in c.url


def test_fuel_price_citation_template() -> None:
    c = fuel_price_citation()
    assert "gogo.gs" in c.url


def test_jma_warning_citation_template() -> None:
    c = jma_warning_citation()
    assert "jma.go.jp" in c.url


def test_improvement_standards_citation_has_notice_number() -> None:
    c = improvement_standards_citation()
    assert c.notice_number is not None
    assert "厚生労働省告示" in c.notice_number


def test_logistics_efficiency_law_citation() -> None:
    c = logistics_efficiency_law_citation()
    assert "mlit" in c.url


def test_co2_factors_citation() -> None:
    c = co2_factors_citation()
    assert "Ver.3.2" in c.label
    assert c.url.startswith("https://")


# ---------------------------------------------------------------------------
# Tier S3 フォロー Codex 二次調査 2026-05-23
# ---------------------------------------------------------------------------


def test_form5_iv4_iv5_consigned_citation_uses_meti_pdf() -> None:
    """様式第5 IV-4/IV-5 は経産省 PDF を一次出典として参照する。"""
    c = form5_iv4_iv5_consigned_citation()
    assert c.url == "https://www.meti.go.jp/policy/economy/distribution/250829_ninushi.pdf"
    assert c.ordinance_number == "様式第5 IV-4/IV-5"
    assert "経済産業省" in c.accessed_via
    # 推測値「3-5-3」が混入していないこと
    assert "3-5-3" not in c.label
    assert "3-5-3" not in (c.ordinance_number or "")


def test_mlit_shipper_handbook_consigned_citation_uses_mlit_pdf() -> None:
    """国交省 特定荷主手引書 第1.1版 PDF を一次出典として参照する。"""
    c = mlit_shipper_handbook_consigned_citation()
    assert c.url == "https://www.mlit.go.jp/seisakutokatsu/freight/content/001984872.pdf"
    assert "第1.1版" in c.label
    assert "国土交通省" in c.accessed_via


def test_logistics_efficiency_law_article57_citation_uses_egov() -> None:
    """第57条（特定倉庫業者の定期報告）は e-Gov 法令検索を恒久 URL とする。"""
    c = logistics_efficiency_law_article57_citation()
    assert c.url == "https://laws.e-gov.go.jp/law/417AC0000000085"
    assert "第57条" in c.label
    assert "第65条" not in c.label  # 連鎖化事業者用と混同しないこと
    assert "e-Gov" in c.accessed_via


def test_improvement_standards_notice_pdf_citation_has_both_notices() -> None:
    """原告示（平成元年）と改正告示（令和4年）の双方を notice_number に含む。"""
    c = improvement_standards_notice_pdf_citation()
    assert c.url == "https://www.mhlw.go.jp/content/001035032.pdf"
    assert c.notice_number is not None
    assert "平成元年労働省告示第7号" in c.notice_number
    assert "令和4年厚生労働省告示第367号" in c.notice_number
