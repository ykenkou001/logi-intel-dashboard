"""成果物ファイルダウンロードエンドポイント。

`outputs/` 配下の成果物（PPT/Word/Excel/Markdown/PDF/JSON）を HTTPS でダウンロード可能にする。

backend 切替（`LOGI_STORAGE_BACKEND` 環境変数）:
- "local"（既定）: ローカルファイルを直接配信（パストラバーサル防止あり）
- "s3"          : S3 プレサインド URL を生成して 302 リダイレクト
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from core.storage import get_storage

router = APIRouter(prefix="/api/v1/files", tags=["files"])

_OUTPUTS_DIR = Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs")).resolve()

_MEDIA_TYPES = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
    # MD はブラウザが直接表示しがちなので octet-stream で DL を強制する
    ".md": "application/octet-stream",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json",
}


@router.get("/{file_path:path}", response_model=None)
async def download(file_path: str) -> FileResponse | RedirectResponse:
    """outputs/ 配下のファイルをダウンロード配信する。

    パスは `outputs/` から見た相対パスで指定する（例: `ppt/clo_plan_xxx.pptx`）。
    S3 backend では 302 リダイレクトでプレサインド URL を返す。
    """
    # Office アプリのロックファイル（"~$..." / ".~lock..."）は配信しない。
    base_name = file_path.rsplit("/", 1)[-1]
    if base_name.startswith(("~$", ".~lock")):
        raise HTTPException(
            status_code=404,
            detail="Office ロックファイルはダウンロード対象外",
        )

    storage = get_storage()
    if storage.backend_name == "s3":
        # S3 backend: プレサインド URL を生成して 302 リダイレクト
        url = storage.download_url(file_path)
        return RedirectResponse(url=url, status_code=302)

    # Local backend: 既存挙動（パストラバーサル防止 + 直接配信）
    candidate = (_OUTPUTS_DIR / file_path).resolve()
    try:
        candidate.relative_to(_OUTPUTS_DIR)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="outputs/ 配下のファイルのみダウンロード可能",
        ) from exc

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"ファイルが見つかりません: {file_path}")

    media_type = _MEDIA_TYPES.get(candidate.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path=candidate,
        media_type=media_type,
        filename=candidate.name,
        content_disposition_type="attachment",
    )
