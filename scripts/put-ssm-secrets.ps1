# SSM Parameter Store にローカル .env のシークレットを投入する。
#
# 使い方（PowerShell）:
#   cd c:\Users\ykenk\repos\logi-intel-dashboard
#   .\scripts\put-ssm-secrets.ps1 -Env dev -Region ap-northeast-1
#
# このスクリプトは .env 内の ESTAT_APP_ID と CORP_NUMBER_APP_ID を
# /logi-intel/<env>/<NAME> として SecureString で投入する。
# 既存値は --overwrite で上書きされる（PoC 想定）。

param(
    [string]$Env = "dev",
    [string]$Region = "ap-northeast-1"
)

$envFile = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env が見つかりません: $envFile"
    exit 1
}

$prefix = "/logi-intel/$Env"
$targetNames = @("ESTAT_APP_ID", "CORP_NUMBER_APP_ID")

Get-Content $envFile | ForEach-Object {
    if ($_ -match "^([A-Z_]+)=(.+)$") {
        $name = $Matches[1].Trim()
        $value = $Matches[2].Trim()
        if ($targetNames -contains $name -and $value -ne "") {
            $param = "$prefix/$name"
            Write-Host "→ Putting $param ..." -NoNewline
            aws ssm put-parameter `
                --name $param `
                --value $value `
                --type "SecureString" `
                --region $Region `
                --overwrite `
                | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host " OK" -ForegroundColor Green
            } else {
                Write-Host " FAILED" -ForegroundColor Red
            }
        }
    }
}

Write-Host "`nDone. 確認:" -ForegroundColor Cyan
aws ssm get-parameters-by-path --path $prefix --region $Region --query "Parameters[].Name" --output table
