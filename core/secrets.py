"""シークレット取得ラッパー — env / AWS SSM Parameter Store を切替。

設計方針:
- ローカル開発・テストでは `os.environ` 経由（既存挙動・無料）。
- Lambda 上では SSM Parameter Store SecureString から取得（無料枠）。
- 一度取得した値はプロセス内でキャッシュし、Lambda 同一コンテナでの再呼び出し時の
  重複 API call を抑える。

環境変数:
- `LOGI_SECRETS_BACKEND`: "env"（既定） or "ssm"
- `LOGI_SSM_PREFIX`     : SSM パスのプレフィックス（既定 "/logi-intel/dev"）

使い方:
    from core.secrets import get_secret
    estat_app_id = get_secret("ESTAT_APP_ID")  # env か SSM から取得
"""
from __future__ import annotations

import os
from functools import cache


def get_secret(name: str) -> str | None:
    """シークレット値を取得する（env or SSM）。

    Args:
        name: 環境変数名 / SSM パラメータ末端名。例: "ESTAT_APP_ID"

    Returns:
        値（取得できなければ None）
    """
    backend = os.environ.get("LOGI_SECRETS_BACKEND", "env").lower()
    if backend == "ssm":
        return _get_from_ssm(name)
    # env バックエンドでは毎回 os.environ を読む（テストの monkeypatch を反映するため）
    return os.environ.get(name)


@cache
def _get_from_ssm(name: str) -> str | None:
    """AWS SSM Parameter Store SecureString から取得。

    SSM パスは `${LOGI_SSM_PREFIX}/${name}`。例: "/logi-intel/dev/ESTAT_APP_ID"。
    取得後は `os.environ` にも反映し、既存の `os.environ.get(...)` 呼出も透過動作させる。
    """
    import boto3

    prefix = os.environ.get("LOGI_SSM_PREFIX", "/logi-intel/dev").rstrip("/")
    full_name = f"{prefix}/{name}"
    client = boto3.client("ssm")
    try:
        response = client.get_parameter(Name=full_name, WithDecryption=True)
    except client.exceptions.ParameterNotFound:
        return None
    value = response["Parameter"]["Value"]
    os.environ.setdefault(name, value)
    return value


__all__ = ["get_secret"]
