# ローカル開発用 FastAPI 起動ヘルパー（Windows / PowerShell）
#
# 役割:
#   1. 同 port を listen している既存 uvicorn を強制停止
#   2. --reload モードで再起動（core/ への変更を即時反映）
#
# 経緯:
#   2026-05-05 に「古い uvicorn が core/ をメモリにロードしたまま動き続け、
#   修正反映が確認できない」事故が発生（コミット 069b2d6 検証中）。
#   多重起動と reload なし起動が原因。本スクリプトはそれを root cause で抑止する。
#
# 使い方:
#   pwsh scripts/dev_api.ps1            # port 8000 (default)
#   pwsh scripts/dev_api.ps1 -Port 8765 # 別ポート

param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

# ── 1. 同 port を listen している全プロセスを kill ────────────────────
# 古い uvicorn 多重起動だけでなく、Zenn CLI (port 8000 デフォルト) など別アプリの
# 占有も問題になるため、port を listen している全 PID を一律で停止する。
# 2026-05-17: zenn preview が port 8000 を占有して FastAPI のリクエストを横取りする
# 事故が発生。同じ落とし穴を踏まないよう listener ベースの停止に変更した。
$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -gt 0) {
    $pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($targetPid in $pids) {
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$targetPid" -ErrorAction SilentlyContinue).CommandLine
        Write-Host ("[dev_api] port {0} を占有中のプロセスを停止: PID={1} Name={2}" -f $Port, $targetPid, $proc.ProcessName)
        if ($cmd) { Write-Host ("           cmd: {0}" -f $cmd) }
        Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host ("[dev_api] port {0} 占有プロセスなし" -f $Port)
}

# ── 2. ローカル開発時の CORS を localhost:3000 に開放 ────────────────
# 本番（CloudFront 同居）では同一 origin なので CORS 不要。
# ローカルは Next.js 3000 → FastAPI 8000 のクロスオリジンになるため明示する。
# `.env` の LOGI_API_CORS_ORIGINS より process 環境変数が優先される（load_dotenv は既存値を上書きしない）。
$env:LOGI_API_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"

# ── 3. --reload で起動 ─────────────────────────────────────────────
Write-Host ("[dev_api] uvicorn 起動: port={0} reload=on cors={1}" -f $Port, $env:LOGI_API_CORS_ORIGINS)
Set-Location $repoRoot
uv run uvicorn api.main:app --host 127.0.0.1 --port $Port --reload --log-level info
