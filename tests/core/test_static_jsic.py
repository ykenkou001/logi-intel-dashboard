"""core/static/jsic.py の単体テスト。"""
from __future__ import annotations

from core.static.jsic import (
    JSIC_ENTRIES,
    category_of,
    codes_in_category,
    lookup,
    name_of,
)


def test_lookup_known_code() -> None:
    """既知コードからエントリ取得。"""
    entry = lookup("5891")
    assert entry is not None
    assert entry.name.startswith("コンビニエンスストア")
    assert entry.category == "chain_franchise"


def test_lookup_unknown_code() -> None:
    """未収録コードは None。"""
    assert lookup("9999") is None


def test_name_of_returns_none_for_missing() -> None:
    """未収録は None。"""
    assert name_of("9999") is None


def test_category_of_manufacturing() -> None:
    """製造業コードのカテゴリが manufacturing。"""
    assert category_of("3159") == "manufacturing"


def test_codes_in_category_chain_franchise() -> None:
    """連鎖化事業者カテゴリにコンビニ（5891）が含まれる。"""
    chain_codes = codes_in_category("chain_franchise")
    assert "5891" in chain_codes


def test_all_entries_have_4digit_codes() -> None:
    """全エントリが4桁コード。"""
    for entry in JSIC_ENTRIES:
        assert len(entry.code) == 4
        assert entry.code.isdigit()


def test_codes_unique() -> None:
    """コードに重複がない。"""
    codes = [e.code for e in JSIC_ENTRIES]
    assert len(codes) == len(set(codes))
