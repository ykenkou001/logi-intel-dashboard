"""core/export/formatter.format_jpy のテスト。"""

from __future__ import annotations

import pytest

from core.export.formatter import format_jpy


class TestFormatJpy:
    def test_oku_default(self) -> None:
        assert format_jpy(1_200_000_000) == "12.0億円"

    def test_oku_two_digits(self) -> None:
        assert format_jpy(1_234_500_000, digits=2) == "12.35億円"

    def test_million(self) -> None:
        assert format_jpy(15_000_000, unit="million", digits=0) == "15百万円"

    def test_man(self) -> None:
        assert format_jpy(50_000, unit="man", digits=0) == "5万円"

    def test_yen_thousand_sep(self) -> None:
        assert format_jpy(1_234_567, unit="yen", thousand_sep=True) == "1,234,567円"

    def test_negative(self) -> None:
        assert format_jpy(-500_000_000) == "-5.0億円"

    def test_with_sign_positive(self) -> None:
        assert format_jpy(800_000_000, with_sign=True) == "+8.0億円"

    def test_with_sign_negative_unchanged(self) -> None:
        assert format_jpy(-800_000_000, with_sign=True) == "-8.0億円"

    def test_none_returns_dash(self) -> None:
        assert format_jpy(None) == "—"

    def test_zero(self) -> None:
        assert format_jpy(0) == "0.0億円"

    def test_thousand_sep_oku(self) -> None:
        assert format_jpy(123_456_700_000_000, digits=0, thousand_sep=True) == "1,234,567億円"

    @pytest.mark.parametrize(
        "amount,unit,digits,expected",
        [
            (100_000_000, "oku", 1, "1.0億円"),
            (10_000_000, "million", 0, "10百万円"),
            (10_000, "man", 0, "1万円"),
            (1234, "yen", 0, "1234円"),
        ],
    )
    def test_units(self, amount: int, unit: str, digits: int, expected: str) -> None:
        assert format_jpy(amount, unit=unit, digits=digits) == expected  # type: ignore[arg-type]
