"""企業プロフィール解決の単一エントリポイント。

`get_sample()` の呼び出しと「未登録時の統一エラー文言」を REST / MCP の
両系統で同じ実装にするためのヘルパー。

REST 側は `ProfileNotFoundError` を `HTTPException(404)` にラップする。
MCP 側は `try/except` で受けて `ToolResponse(summary=...)` に流す。
"""

from __future__ import annotations

from core.static.sample_company import (
    CompanyProfile,
    format_sample_ids,
    get_sample,
)


class ProfileNotFoundError(Exception):
    """指定 ID の企業プロフィールが見つからない場合に送出される。"""

    def __init__(self, company_id: str) -> None:
        self.company_id = company_id
        super().__init__(
            f"会社 ID '{company_id}' が見つかりません。"
            f"サンプルは {format_sample_ids(separator=', ')}、"
            "または POST /api/v1/company/load で取込済みの ID が利用可能"
        )


def resolve_profile(company_id: str) -> CompanyProfile:
    """企業プロフィールを取得する。未登録なら ``ProfileNotFoundError`` を送出。"""
    profile = get_sample(company_id)
    if profile is None:
        raise ProfileNotFoundError(company_id)
    return profile
