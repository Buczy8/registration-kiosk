param(
  [Parameter(Mandatory = $true)]
  [string]$BackupFile,
  [switch]$DropAndRecreateSchema
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
  throw "Plik backupu nie istnieje: $BackupFile"
}

$dbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "kiosk" }
$dbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "kiosk" }
$resolvedBackup = (Resolve-Path $BackupFile).Path

if ($DropAndRecreateSchema) {
  Write-Host "Czyszczenie schematu public..."
  docker compose exec -T db psql -U $dbUser -d $dbName -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
}

$extension = [System.IO.Path]::GetExtension($resolvedBackup).ToLowerInvariant()

if ($extension -eq ".sql") {
  Write-Host "Przywracanie z SQL: $resolvedBackup"
  docker compose exec -T db psql -U $dbUser -d $dbName < $resolvedBackup
} else {
  Write-Host "Przywracanie z DUMP: $resolvedBackup"
  docker compose exec -T db pg_restore -U $dbUser -d $dbName --clean --if-exists --no-owner --no-privileges < $resolvedBackup
}

Write-Host "OK: restore zakończony."
