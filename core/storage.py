"""ストレージ抽象層 — ローカルファイルシステム / S3 を `LOGI_STORAGE_BACKEND` で切替。

設計方針:
- PoC ではローカル（既存挙動）を既定にして本番（Lambda）では S3 に切替える。
- `make_output_path` で生成された Path をそのまま使い続けられるよう、書き込み先は
  常に **ローカル** とし、書き込み後に `publish` を呼ぶことで S3 にも複製する形を
  取る。Lambda は `/tmp/outputs` をローカルディレクトリとして利用する。
- ファイルダウンロードは `presigned_url(key)` で返し、`/api/v1/files/{path}` は
  S3 backend のときは 302 リダイレクトする。
- 既存呼出側はほぼ変更不要にし、AWS 知識のないコード（core/analytics 等）は触らない。

環境変数:
- `LOGI_STORAGE_BACKEND`: "local"（既定） or "s3"
- `LOGI_OUTPUTS_DIR`: ローカル書込先（既定 "outputs"・Lambda は "/tmp/outputs"）
- `LOGI_S3_BUCKET`: S3 backend で使うバケット名
- `LOGI_S3_PREFIX`: S3 オブジェクトキーのプレフィックス（既定 ""）
- `LOGI_S3_PRESIGNED_TTL`: プレサインド URL の有効期限秒（既定 300）
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Protocol

# boto3 は重いため、S3 backend が選ばれたときだけ遅延 import する。
# ローカル開発・テストでは boto3 を初期化しない。


class Storage(Protocol):
    """ストレージバックエンドのインターフェース。"""

    backend_name: str

    def publish(self, local_path: Path) -> str:
        """ローカル書き出し済みファイルをストレージに公開し、識別子を返す。

        - LocalStorage: ローカルパスを `outputs/` から見た相対パスで返す
        - S3Storage:   S3 にアップロードし、オブジェクトキーを返す

        戻り値は `download_url` の引数として使える識別子。
        """
        ...

    def download_url(self, key_or_path: str) -> str:
        """ダウンロード用 URL を返す。

        - LocalStorage: `/api/v1/files/{相対パス}` 形式の URL（FastAPI の files ルーター）
        - S3Storage:   プレサインド URL（5 分有効・既定）
        """
        ...

    def read_bytes(self, key_or_path: str) -> bytes | None:
        """識別子からバイト列を読む（FastAPI files ルーターのストリーム配信用）。"""
        ...


# ─── LocalStorage ────────────────────────────────────────────────────


class LocalStorage:
    """ローカルファイルシステム上の outputs/ を扱う。

    既存挙動を完全互換で保つ（ファイルパスをそのまま使い続けられる）。
    """

    backend_name = "local"

    def __init__(self, outputs_dir: Path) -> None:
        self.outputs_dir = outputs_dir.resolve()

    def publish(self, local_path: Path) -> str:
        """ローカル書出済みファイルの相対パスを返す。アップロードは不要。"""
        absolute = local_path.resolve()
        try:
            return str(absolute.relative_to(self.outputs_dir)).replace("\\", "/")
        except ValueError:
            # outputs_dir 外（テスト時など）はそのまま絶対パスを返す
            return str(absolute).replace("\\", "/")

    def download_url(self, key_or_path: str) -> str:
        # 既存挙動: フロントが組み立てる /api/v1/files/{path} を使う
        cleaned = key_or_path.replace("\\", "/").lstrip("/")
        return f"/api/v1/files/{cleaned}"

    def read_bytes(self, key_or_path: str) -> bytes | None:
        cleaned = key_or_path.replace("\\", "/").lstrip("/")
        path = (self.outputs_dir / cleaned).resolve()
        try:
            path.relative_to(self.outputs_dir)
        except ValueError:
            return None
        return path.read_bytes() if path.is_file() else None


# ─── S3Storage ──────────────────────────────────────────────────────


class S3Storage:
    """S3 バケットを outputs ストレージとして使う。

    `publish(local_path)` でアップロード後、ローカルファイルは Lambda の `/tmp` に
    残るため、Lambda 終了時に勝手に消える（明示削除は不要）。
    """

    backend_name = "s3"

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        outputs_dir: Path | None = None,
        presigned_ttl: int = 300,
    ) -> None:
        import boto3

        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        self.outputs_dir = (outputs_dir or Path("outputs")).resolve()
        self.presigned_ttl = presigned_ttl
        self._s3 = boto3.client("s3")

    def _key_from_local(self, local_path: Path) -> str:
        absolute = local_path.resolve()
        try:
            relative = absolute.relative_to(self.outputs_dir)
        except ValueError:
            relative = Path(absolute.name)
        return self.prefix + str(relative).replace("\\", "/")

    def publish(self, local_path: Path) -> str:
        key = self._key_from_local(local_path)
        self._s3.upload_file(
            Filename=str(local_path),
            Bucket=self.bucket,
            Key=key,
            ExtraArgs={"ContentType": _guess_content_type(local_path)},
        )
        return key

    def download_url(self, key_or_path: str) -> str:
        # 相対パスで渡された場合は prefix を付与
        if not key_or_path.startswith(self.prefix):
            key = self.prefix + key_or_path.lstrip("/")
        else:
            key = key_or_path
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=self.presigned_ttl,
        )

    def read_bytes(self, key_or_path: str) -> bytes | None:
        if not key_or_path.startswith(self.prefix):
            key = self.prefix + key_or_path.lstrip("/")
        else:
            key = key_or_path
        try:
            obj = self._s3.get_object(Bucket=self.bucket, Key=key)
            return bytes(obj["Body"].read())
        except self._s3.exceptions.NoSuchKey:
            return None


def _guess_content_type(path: Path) -> str:
    suffix_map = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
        ".md": "text/markdown; charset=utf-8",
        ".json": "application/json",
        ".html": "text/html; charset=utf-8",
    }
    return suffix_map.get(path.suffix.lower(), "application/octet-stream")


# ─── ファクトリ ────────────────────────────────────────────────────


def _outputs_dir_from_env() -> Path:
    return Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs"))


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    """環境変数 `LOGI_STORAGE_BACKEND` でバックエンドを切替。

    キャッシュするため起動中は単一インスタンス。テストで切り替える時は
    `get_storage.cache_clear()` を呼ぶこと。
    """
    backend = os.environ.get("LOGI_STORAGE_BACKEND", "local").lower()
    outputs_dir = _outputs_dir_from_env()
    if backend == "s3":
        bucket = os.environ.get("LOGI_S3_BUCKET")
        if not bucket:
            raise RuntimeError("LOGI_STORAGE_BACKEND=s3 のとき LOGI_S3_BUCKET 必須")
        prefix = os.environ.get("LOGI_S3_PREFIX", "")
        ttl_str = os.environ.get("LOGI_S3_PRESIGNED_TTL", "300")
        return S3Storage(
            bucket=bucket,
            prefix=prefix,
            outputs_dir=outputs_dir,
            presigned_ttl=int(ttl_str),
        )
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return LocalStorage(outputs_dir=outputs_dir)


__all__ = [
    "LocalStorage",
    "S3Storage",
    "Storage",
    "get_storage",
]
