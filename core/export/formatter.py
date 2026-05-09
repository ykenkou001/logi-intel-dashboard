"""通貨フォーマット共通関数。

CLO 計画書・経営会議資料で頻出する「億円 / 百万円 / 万円」表示を統一する。
散在していた ``revenue / 1e8`` ``revenue / 1e6`` ``revenue / 1e4`` を
本モジュール経由に置換することで、丸め桁の不揃い・単位ラベルの揺れを排除する。
"""

from __future__ import annotations

from typing import Final, Literal

JpyUnit = Literal["oku", "million", "man", "yen"]

_DIVISORS: Final[dict[JpyUnit, float]] = {
    "oku": 1e8,
    "million": 1e6,
    "man": 1e4,
    "yen": 1.0,
}

_LABELS: Final[dict[JpyUnit, str]] = {
    "oku": "億円",
    "million": "百万円",
    "man": "万円",
    "yen": "円",
}


def format_jpy(
    amount: float | int | None,
    unit: JpyUnit = "oku",
    digits: int = 1,
    *,
    with_sign: bool = False,
    thousand_sep: bool = False,
) -> str:
    """日本円の金額を指定単位の文字列に整形する。

    Args:
        amount: 円単位の金額。``None`` の場合は ``"—"`` を返す。
        unit: 表示単位（``"oku"`` 億円 / ``"million"`` 百万円 / ``"man"`` 万円 /
            ``"yen"`` 円）。デフォルトは ``"oku"``。
        digits: 小数点以下桁数。``unit="yen"`` の時は無視され整数表示。
        with_sign: ``True`` の場合は正の値に ``+`` を付ける。
        thousand_sep: ``True`` の場合はカンマ区切りで表示する。

    Returns:
        ``"+1.2 億円"`` のような表示文字列。``amount`` が ``None`` のときは ``"—"``。
    """
    if amount is None:
        return "—"

    value = float(amount) / _DIVISORS[unit]

    if unit == "yen":
        fmt = ",.0f" if thousand_sep else ".0f"
    elif thousand_sep:
        fmt = f",.{digits}f"
    else:
        fmt = f".{digits}f"

    body = format(value, fmt)
    if with_sign and value > 0:
        body = f"+{body}"

    return f"{body}{_LABELS[unit]}"
