"""core/export/response.py の単体テスト。"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.export.citation import Citation
from core.export.response import OUTPUTS_DIR, ToolResponse, make_output_path


def test_tool_response_to_dict_basic() -> None:
    """ToolResponse.to_dict が必須キーを返す。"""
    resp = ToolResponse(summary="ok")
    d = resp.to_dict()
    assert d["summary"] == "ok"
    assert d["files"] == {}
    assert d["citations"] == []
    assert d["freshness_warnings"] == []


def test_tool_response_with_citations() -> None:
    """citation を含む to_dict 出力。"""
    resp = ToolResponse(summary="x")
    resp.add_citation(Citation(label="A", url="https://a.example.com"))
    d = resp.to_dict()
    citations = d["citations"]
    assert isinstance(citations, list)
    assert len(citations) == 1
    assert citations[0]["label"] == "A"


def test_make_output_path_creates_parent_dir(tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """make_output_path が親ディレクトリを作成する。"""
    # OUTPUTS_DIR を tmp_path に差し替え
    monkeypatch.setattr("core.export.response.OUTPUTS_DIR", tmp_path)
    p = make_output_path("ppt", "test", "co1", "pptx")
    assert p.parent.exists()
    assert p.parent == tmp_path / "ppt"


def test_make_output_path_filename_format(tmp_path: Path,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    """ファイル名が `{purpose}_{company}_{ts}_{rand4}.{ext}` パターン。"""
    monkeypatch.setattr("core.export.response.OUTPUTS_DIR", tmp_path)
    p = make_output_path("excel", "macro", "co1", "xlsx")
    pattern = re.compile(r"^macro_co1_\d{10}_[0-9a-f]{4}\.xlsx$")
    assert pattern.match(p.name), p.name


def test_make_output_path_sanitizes_unsafe_chars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """purpose と company_id の不正文字が除去される。"""
    monkeypatch.setattr("core.export.response.OUTPUTS_DIR", tmp_path)
    p = make_output_path("ppt", "my/plan", "co<1>", "pptx")
    assert "/" not in p.name
    assert "<" not in p.name


def test_make_output_path_uniqueness(tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    """連続呼出でファイル名が衝突しない。"""
    monkeypatch.setattr("core.export.response.OUTPUTS_DIR", tmp_path)
    p1 = make_output_path("ppt", "x", "co", "pptx")
    p2 = make_output_path("ppt", "x", "co", "pptx")
    assert p1.name != p2.name


def test_outputs_dir_default() -> None:
    """OUTPUTS_DIR デフォルトが outputs/。"""
    assert Path("outputs") == OUTPUTS_DIR
