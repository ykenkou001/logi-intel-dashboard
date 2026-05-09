"""build_*_summary 関数の戻り値構造。

`title`(=== ヘッダー ===) と `body` 行の構造化アクセスを提供しつつ、
``str`` を継承して既存呼出側との互換性を維持する。

主な利点:
    1. `result.body[N:]` で本文行に直接アクセス可能になり、
       `plan_draft.py` で見られた ``result.split("\n")[N:]`` のような
       見出し行数に依存する脆弱なスライスを排除できる。
    2. ``ToolResponse(summary=result)`` などの既存呼び出しは ``SummaryResult``
       が ``str`` のサブクラスのため変更不要。
    3. ``str(result)`` ``f"{result}"`` ``result == "..."`` といった文字列
       としての挙動も維持される。
"""

from __future__ import annotations

from collections.abc import Iterable


class SummaryResult(str):
    """``build_*_summary`` の戻り値。``str`` を継承する。

    ``title`` と ``body`` を構造的に保持しつつ、文字列としての挙動も維持する。
    """

    __slots__ = ("body", "title")

    title: str
    body: tuple[str, ...]

    def __new__(cls, title: str, body: Iterable[str]) -> SummaryResult:
        body_tuple = tuple(body)
        joined = "\n".join((title, *body_tuple))
        instance = super().__new__(cls, joined)
        instance.title = title
        instance.body = body_tuple
        return instance

    def __reduce__(self) -> tuple[object, tuple[object, ...]]:  # pragma: no cover
        # pickle 等でインスタンスを再構築できるようにする
        return (self.__class__, (self.title, self.body))


def join_lines(lines: Iterable[str]) -> str:
    """``"\\n".join(lines)`` のショートカット。
    既存 ``"\\n".join(...)`` パターンと結果は同じ。
    """
    return "\n".join(lines)
