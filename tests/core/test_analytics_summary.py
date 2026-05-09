"""SummaryResult のテスト。"""

from __future__ import annotations

import json

from core.analytics._summary import SummaryResult


class TestSummaryResult:
    def test_str_compat(self) -> None:
        s = SummaryResult("=== ヘッダー ===", ["line1", "line2"])
        # SummaryResult は str を継承する
        assert isinstance(s, str)
        assert s == "=== ヘッダー ===\nline1\nline2"

    def test_attributes(self) -> None:
        s = SummaryResult("=== ヘッダー ===", ["line1", "line2"])
        assert s.title == "=== ヘッダー ==="
        assert s.body == ("line1", "line2")

    def test_empty_body(self) -> None:
        s = SummaryResult("=== タイトルだけ ===", [])
        assert s == "=== タイトルだけ ==="
        assert s.body == ()

    def test_f_string_works(self) -> None:
        s = SummaryResult("=== T ===", ["a"])
        assert f"prefix: {s}" == "prefix: === T ===\na"

    def test_join_works(self) -> None:
        s = SummaryResult("=== T ===", ["a", "b"])
        assert "\n---\n".join([s, "extra"]) == "=== T ===\na\nb\n---\nextra"

    def test_json_serialization(self) -> None:
        # ToolResponse.to_dict() は summary を文字列のまま JSON 化する経路で使う
        s = SummaryResult("=== T ===", ["a"])
        payload = {"summary": s}
        encoded = json.dumps(payload, ensure_ascii=False)
        assert json.loads(encoded) == {"summary": "=== T ===\na"}

    def test_iter_body_lines(self) -> None:
        # plan_draft.py が `.split("\n")[N:]` の代わりに使うパターン
        s = SummaryResult("=== T ===", ["a", "b", "c"])
        assert list(s.body[1:]) == ["b", "c"]

    def test_body_is_tuple(self) -> None:
        # body は immutable
        s = SummaryResult("=== T ===", ["a"])
        assert isinstance(s.body, tuple)

    def test_accepts_iterable(self) -> None:
        # list/tuple/generator どれでも受け付ける
        gen = (f"line{i}" for i in range(3))
        s = SummaryResult("=== T ===", gen)
        assert s.body == ("line0", "line1", "line2")
