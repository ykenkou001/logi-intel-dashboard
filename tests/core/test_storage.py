"""storage 層のテスト — LocalStorage の挙動と S3Storage のプレサインド URL 生成。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.storage import LocalStorage, S3Storage

# ─── LocalStorage ────────────────────────────────────────────────────


def test_local_publish_returns_relative_path(tmp_path: Path) -> None:
    storage = LocalStorage(outputs_dir=tmp_path)
    target = tmp_path / "ppt" / "sample.pptx"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")
    assert storage.publish(target) == "ppt/sample.pptx"


def test_local_download_url_format(tmp_path: Path) -> None:
    storage = LocalStorage(outputs_dir=tmp_path)
    assert storage.download_url("ppt/sample.pptx") == "/api/v1/files/ppt/sample.pptx"


# ─── S3Storage ──────────────────────────────────────────────────────


@pytest.fixture
def s3_storage(tmp_path: Path) -> S3Storage:
    """boto3 client をモック化した S3Storage を返す。"""
    with patch("boto3.client") as mock_client:
        mock_client.return_value = MagicMock()
        storage = S3Storage(
            bucket="test-bucket",
            prefix="poc/",
            outputs_dir=tmp_path,
            presigned_ttl=300,
        )
    return storage


def test_s3_download_url_includes_attachment_disposition(s3_storage: S3Storage) -> None:
    """プレサインド URL 生成時に ResponseContentDisposition=attachment が指定される。

    これがないと Office ファイル等がブラウザで直接開かれてしまう。
    """
    s3_storage._s3.generate_presigned_url.return_value = "https://example.com/signed"

    s3_storage.download_url("ppt/clo_plan_sample.pptx")

    call = s3_storage._s3.generate_presigned_url.call_args
    assert call.args[0] == "get_object"
    params = call.kwargs["Params"]
    assert params["Bucket"] == "test-bucket"
    assert params["Key"] == "poc/ppt/clo_plan_sample.pptx"
    disposition = params["ResponseContentDisposition"]
    assert disposition.startswith("attachment;")
    assert 'filename="clo_plan_sample.pptx"' in disposition


def test_s3_download_url_handles_full_key(s3_storage: S3Storage) -> None:
    """既に prefix を含むキーが渡された場合は二重付与しない。"""
    s3_storage._s3.generate_presigned_url.return_value = "https://example.com/signed"

    s3_storage.download_url("poc/markdown/plan.md")

    params = s3_storage._s3.generate_presigned_url.call_args.kwargs["Params"]
    assert params["Key"] == "poc/markdown/plan.md"
    assert 'filename="plan.md"' in params["ResponseContentDisposition"]
