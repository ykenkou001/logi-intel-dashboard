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

# ── 1. 同 port を listen している既存プロセスを kill ──────────────────
$existing = Get-CimInstance Win32_Process -Filter "Name='uvicorn.exe' OR Name='python.exe'" |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match "uvicorn" -and
        $_.CommandLine -match "--port\s+$Port\b"
    }

if ($existing) {
    Write-Host ("[dev_api] 既存 uvicorn (port {0}) を停止: {1}" -f $Port, ($existing.ProcessId -join ", "))
    foreach ($p in $existing) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host "[dev_api] 既存 uvicorn なし"
}

# ── 2. --reload で起動 ─────────────────────────────────────────────
Write-Host ("[dev_api] uvicorn 起動: port={0} reload=on" -f $Port)
Set-Location $repoRoot
uv run uvicorn api.main:app --host 127.0.0.1 --port $Port --reload --log-level info
