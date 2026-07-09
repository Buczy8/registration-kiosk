param(
  [string]$OutputDir = "backups\db",
  [string]$FilePrefix = "kiosk",
  [switch]$PlainSql
)

$ErrorActionPreference = "Stop"

$dbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "kiosk" }
$dbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "kiosk" }
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

if ($PlainSql) {
  $filePath = Join-Path $OutputDir "$FilePrefix-$timestamp.sql"
  $command = "docker compose exec -T db pg_dump -U $dbUser -d $dbName --no-owner --no-privileges"
} else {
  $filePath = Join-Path $OutputDir "$FilePrefix-$timestamp.dump"
  $command = "docker compose exec -T db pg_dump -U $dbUser -d $dbName -Fc --no-owner --no-privileges"
}

Write-Host "Tworzenie backupu bazy do: $filePath"

Invoke-Expression "$command > `"$filePath`""

if (-not (Test-Path $filePath)) {
  throw "Backup nie zostal utworzony."
}

$sizeBytes = (Get-Item $filePath).Length
Write-Host "OK: backup gotowy ($sizeBytes B)"
Write-Host $filePath
