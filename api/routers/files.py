"""成果物ファイルダウンロードエンドポイント。

`outputs/` 配下の成果物（PPT/Word/Excel/Markdown/PDF/JSON）を HTTPS でダウンロード可能にする。
パストラバーサル防止のため、ファイル パスを `outputs/` の解決済み絶対パス内に
留まることを検証する。

フェーズ4.5 で AWS S3 + プレサインド URL 方式に置き換える予定。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/v1/files", tags=["files"])

_OUTPUTS_DIR = Path("outputs").resolve()

_MEDIA_TYPES = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
    ".md": "text/markdown; charset=utf-8",
    ".json": "application/json",
}


@router.get("/{file_path:path}")
async def download(file_path: str) -> FileResponse:
    """outputs/ 配下のファイルをダウンロード配信する。

    パスは `outputs/` から見た相対パスで指定する（例: `ppt/clo_plan_xxx.pptx`）。
    """
    candidate = (_OUTPUTS_DIR / file_path).resolve()
    try:
        candidate.relative_to(_OUTPUTS_DIR)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="outputs/ 配下のファイルのみダウンロード可能",
        ) from exc

    # Office アプリのロックファイル（"~$..." / ".~lock..."）は配信しない。
    # Word/Excel が開かれている間に生成され、成果物としては不要かつ Open XML パーサが
    # 壊れた MIME を返すため、明示的に 404 にする。
    if candidate.name.startswith(("~$", ".~lock")):
        raise HTTPException(
            status_code=404,
            detail="Office ロックファイルはダウンロード対象外",
        )

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"ファイルが見つかりません: {file_path}")

    media_type = _MEDIA_TYPES.get(candidate.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path=candidate,
        media_type=media_type,
        filename=candidate.name,
    )
