"""files ルーターのダウンロード／パストラバーサル防止テスト。"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.fixture
def sample_output() -> Iterator[Path]:
    """outputs/markdown/test_xxx.md を一時的に作って返す（テスト後削除）。"""
    outputs_dir = Path("outputs/markdown")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    target = outputs_dir / "_pytest_files_router_sample.md"
    target.write_text("# Sample\n\n本文", encoding="utf-8")
    yield target
    target.unlink(missing_ok=True)


def test_download_existing_markdown(sample_output: Path) -> None:
    resp = client.get(f"/api/v1/files/markdown/{sample_output.name}")
    assert resp.status_code == 200
    # MD はブラウザで直接表示されないよう octet-stream で配信される
    assert resp.headers["content-type"] == "application/octet-stream"
    assert "本文" in resp.text


def test_download_sets_attachment_disposition(sample_output: Path) -> None:
    """ブラウザがプレビュー表示せず即 DL するよう attachment を強制する。"""
    resp = client.get(f"/api/v1/files/markdown/{sample_output.name}")
    assert resp.status_code == 200
    assert resp.headers["content-disposition"].startswith("attachment;")
    assert sample_output.name in resp.headers["content-disposition"]


def test_download_missing_file_returns_404() -> None:
    resp = client.get("/api/v1/files/markdown/no_such_file.md")
    assert resp.status_code == 404


def test_path_traversal_is_blocked() -> None:
    """outputs/ の外を狙うパスは 400 で拒否される。"""
    resp = client.get("/api/v1/files/..%2F..%2Fpyproject.toml")
    # FastAPI は %2F をデコードしてくれないことがあるので、直接 ../ を含むケースも検証
    assert resp.status_code in (400, 404)


def test_path_traversal_dotdot_blocked() -> None:
    resp = client.get("/api/v1/files/../pyproject.toml")
    assert resp.status_code in (400, 404)
