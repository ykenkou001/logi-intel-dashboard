"""ルーター共通ヘルパー（ToolResponse → JSON モデル変換 / ファイル公開）。

`clo` / `company` ルーターで重複していた `_publish_files` と `_to_model` を
集約する。`storage` の `publish()` はローカルでは outputs/ 相対パス、
S3 では S3 オブジェクトキーに置換する。
"""

from __future__ import annotations

from pathlib import Path

from api.schemas.responses import ToolResponseModel
from core.export.response import ToolResponse
from core.storage import get_storage


def publish_files(response: ToolResponse) -> None:
    """``ToolResponse.files`` の各値をストレージに公開しキーで上書きする。"""
    if not response.files:
        return
    storage = get_storage()
    new_files: dict[str, str] = {}
    for key, value in response.files.items():
        try:
            new_files[key] = storage.publish(Path(value))
        except Exception:
            new_files[key] = value
    response.files = new_files


def to_model(response: ToolResponse) -> ToolResponseModel:
    """``ToolResponse`` を ``ToolResponseModel`` に変換し ``files`` を公開する。"""
    publish_files(response)
    return ToolResponseModel.model_validate(response.to_dict())
