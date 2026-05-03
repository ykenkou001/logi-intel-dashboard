"""core/export/citation.py の単体テスト。"""
from __future__ import annotations

from core.export.citation import (
    Citation,
    co2_factors_citation,
    estat_citation,
    fuel_price_citation,
    improvement_standards_citation,
    jma_warning_citation,
    logistics_efficiency_law_citation,
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
