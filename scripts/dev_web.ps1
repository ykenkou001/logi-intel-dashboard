# ローカル開発用 Next.js 起動ヘルパー（Windows / PowerShell）
#
# 役割:
#   1. 同 port を listen している既存 next dev を停止
#   2. NEXT_PUBLIC_API_BASE_URL を localhost に固定して起動
#
# 経緯:
#   2026-05-05 に「ローカル Next.js dev が古い localhost:8000 を叩き続け、
#   本番修正が見えない」事故が発生（dev_api.ps1 と対）。
#
# 使い方:
#   pwsh scripts/dev_web.ps1                                    # port 3000 / API 8000
#   pwsh scripts/dev_web.ps1 -Port 3001 -ApiPort 8765           # 別ポート

param(
    [int]$Port = 3000,
    [int]$ApiPort = 8000
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$webDir = Join-Path $repoRoot "web"

# ── 1. 同 port を listen している既存 next dev を kill ──────────────
$existing = Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match "next" -and
        $_.CommandLine -match "dev" -and
        ($_.CommandLine -match "--port\s+$Port\b" -or
         ($Port -eq 3000 -and $_.CommandLine -notmatch "--port"))
    }

if ($existing) {
    Write-Host ("[dev_web] 既存 next dev (port {0}) を停止: {1}" -f $Port, ($existing.ProcessId -join ", "))
    foreach ($p in $existing) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host "[dev_web] 既存 next dev なし"
}

# ── 2. API_BASE をローカル uvicorn に向けて起動 ─────────────────────
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:$ApiPort"
Write-Host ("[dev_web] next dev 起動: port={0} API_BASE={1}" -f $Port, $env:NEXT_PUBLIC_API_BASE_URL)
Set-Location $webDir
if ($Port -eq 3000) {
    npm run dev
} else {
    npx next dev --turbopack --port $Port
}
