"""自社プロフィール入力／取込エンドポイント。

フェーズ4.0 で追加した `logi_clo_generate_template` / `logi_clo_load_company` の REST 版。
Web UI からは「テンプレート DL → 記入 → アップロード → JSON 永続化」のフローで
使用する。
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api.routers.clo import _publish_files
from api.schemas.responses import ToolResponseModel
from core.export.response import ToolResponse
from core.io.company_loader import load_company_profile_from_excel
from core.io.company_store import save_company_profile
from core.io.template_writer import (
    DEFAULT_TEMPLATE_PATH,
    TemplatePurpose,
    write_company_template,
)

router = APIRouter(prefix="/api/v1/company", tags=["company"])

_LOAD_FILE_DESCRIPTION = (
    "記入済み Excel ファイル（.xlsx）。CSV ディレクトリは MCP ツール経由でのみ対応"
)
_UPLOAD_FILE = File(..., description=_LOAD_FILE_DESCRIPTION)


def _to_model(response: ToolResponse) -> ToolResponseModel:
    _publish_files(response)
    return ToolResponseModel.model_validate(response.to_dict())


_PURPOSE_QUERY = Query(
    "annual",
    description=(
        "テンプレ用途。'annual'（既定・計画策定の網羅版）/"
        " 'monthly'（月次レビュー・KPI 中心）/"
        " 'daily'（日次運用入力・wait_time 軽量版）。"
    ),
)

_PURPOSE_LABEL: dict[TemplatePurpose, str] = {
    "annual": "計画策定用（年 1 回・網羅版）",
    "monthly": "月次集計用（月次レビュー）",
    "daily": "日次運用入力用（コックピット／ヒートマップ）",
}

_PURPOSE_SHEETS: dict[TemplatePurpose, str] = {
    "annual": (
        "profile / sites / wait_time(年集計) / handling_time / "
        "kpi_history / _jsic_reference"
    ),
    "monthly": (
        "profile / sites / wait_time(月集計) / handling_time / "
        "kpi_history / _jsic_reference"
    ),
    "daily": "profile / sites / wait_time(日次・site×slot) / _jsic_reference",
}


@router.post("/template", response_model=ToolResponseModel)
async def generate_template(
    purpose: TemplatePurpose = _PURPOSE_QUERY,
) -> ToolResponseModel:
    """自社プロフィール入力 Excel テンプレートを生成し、相対パスを返す。

    フェーズ4.5 B 軸で **用途別 3 種類** に拡張。``purpose`` 未指定時は
    ``annual``（現行互換・6 シート構成）を返すので、既存呼び出しは破壊しない。

    生成された Excel は `/api/v1/files/{path}` 経由でダウンロード可能。
    """
    try:
        written = write_company_template(DEFAULT_TEMPLATE_PATH, purpose=purpose)
    except ValueError as exc:
        # purpose が想定外の値だった場合（FastAPI Literal で防げるはずだが多重安全）
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"テンプレ生成失敗: {exc}") from exc

    summary = (
        "=== 自社プロフィール入力テンプレ生成完了 ===\n"
        f"用途: {purpose}（{_PURPOSE_LABEL[purpose]}）\n"
        f"出力先: {written}\n"
        f"含まれるシート: {_PURPOSE_SHEETS[purpose]}\n\n"
        "次の手順:\n"
        "  1. このファイルを開き、各シートを記入\n"
        "  2. 必須項目（[必須] と表記）はすべて埋める\n"
        "  3. 連鎖化事業者は handling_time シートを空にしてよい\n"
        "  4. POST /api/v1/company/load にファイルを multipart/form-data でアップロード\n"
        "  5. 取込が成功すると POST /api/v1/clo/plan-draft/{company_id} で計画書を生成可能"
    )
    response = ToolResponse(
        summary=summary,
        files={"template_xlsx": str(written)},
        data_source="actual",
    )
    return _to_model(response)


@router.post("/load", response_model=ToolResponseModel)
async def load_company(file: UploadFile = _UPLOAD_FILE) -> ToolResponseModel:
    """記入済み Excel をアップロードして CompanyProfile を構築・JSON 永続化する。

    取込後、生成された company_id は `/api/v1/clo/plan-draft/{company_id}` 等で参照可能。
    """
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Excel ファイル（.xlsx）をアップロードしてください。CSV ディレクトリ取込は "
                "MCP ツール `logi_clo_load_company` を利用してください"
            ),
        )

    suffix = Path(file.filename).suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(file.file, tmp)

    try:
        try:
            profile = load_company_profile_from_excel(tmp_path)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"取込失敗: {exc}") from exc

        try:
            json_path = save_company_profile(profile)
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"JSON 永続化失敗: {exc}",
            ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    summary = (
        f"=== 自社プロフィール取込完了 ===\n"
        f"company_id: {profile.company_id}\n"
        f"会社名: {profile.name}\n"
        f"業種: {profile.main_business} (JSIC {profile.jsic_code})\n"
        f"年間売上: {profile.annual_revenue_jpy / 1e8:.1f} 億円\n"
        f"年間取扱量: {profile.annual_freight_tons_total:,.0f} トン\n"
        f"連鎖化事業者: {'はい' if profile.is_chain_franchise else 'いいえ'}\n"
        f"拠点数: {len(profile.sites)} 件\n"
        f"data_source: {profile.data_source}\n\n"
        f"永続化先: {json_path}"
    )
    response = ToolResponse(
        summary=summary,
        files={"profile_json": str(json_path)},
        data_source=profile.data_source,
    )
    return _to_model(response)


@router.get("/samples", response_model=list[dict[str, str]])
async def list_samples() -> list[dict[str, str]]:
    """利用可能なサンプル企業 ID 一覧を返す。

    実データを取込済みの場合は outputs/profiles/ にも JSON が存在するが、
    本エンドポイントはサンプル3社のみを返す（実データ列挙は別エンドポイントで対応）。
    """
    return [
        {
            "company_id": "sample_mfg_01",
            "name": "電子部品製造（架空）",
            "industry": "manufacturing",
            "data_source": "sample",
        },
        {
            "company_id": "sample_wholesale_01",
            "name": "インテリア卸売（架空）",
            "industry": "wholesale",
            "data_source": "sample",
        },
        {
            "company_id": "sample_chain_01",
            "name": "コンビニ本部（架空）",
            "industry": "chain_franchise",
            "data_source": "sample",
        },
    ]
