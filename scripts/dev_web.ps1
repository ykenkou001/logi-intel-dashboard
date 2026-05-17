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

# ── 1. 同 port を listen している全プロセスを kill ────────────────────
# 古い next dev だけでなく、別アプリ（Zenn CLI 等）が port を占有しているケースも
# 同じ症状（リクエストが届かない）になるため、listener ベースで一律停止する。
# 2026-05-17: dev_api.ps1 と同じ方針に揃えた。
$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -gt 0) {
    $pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($targetPid in $pids) {
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$targetPid" -ErrorAction SilentlyContinue).CommandLine
        Write-Host ("[dev_web] port {0} を占有中のプロセスを停止: PID={1} Name={2}" -f $Port, $targetPid, $proc.ProcessName)
        if ($cmd) { Write-Host ("           cmd: {0}" -f $cmd) }
        Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host ("[dev_web] port {0} 占有プロセスなし" -f $Port)
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
