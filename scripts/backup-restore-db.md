# Backup i restore bazy (Docker)

Ten projekt trzyma PostgreSQL w kontenerze `db` (`kiosk-postgres`).

## 1) Backup ręczny

Z katalogu repo:

```powershell
.\scripts\backup-db.ps1
```

Domyślnie powstaje plik:

- `backups\db\kiosk-YYYYMMDD-HHMMSS.dump`

Format domyślny to `custom` (`.dump`) - najlepszy do restore przez `pg_restore`.

Opcjonalnie SQL:

```powershell
.\scripts\backup-db.ps1 -PlainSql
```

## 2) Restore "na czysto"

Uwaga: to nadpisuje aktualne dane.

```powershell
.\scripts\restore-db.ps1 -BackupFile .\backups\db\kiosk-20260709-090000.dump -DropAndRecreateSchema
```

Skrypt:

- czyści `public schema` (gdy podasz `-DropAndRecreateSchema`)
- przywraca dane z:
  - `.dump` przez `pg_restore --clean --if-exists`
  - `.sql` przez `psql`

Po restore warto zrestartować API:

```powershell
docker compose restart api
```

## 3) Codzienny automatyczny backup (Windows Task Scheduler)

```powershell
schtasks /Create /TN "KioskAPI Daily DB Backup" /SC DAILY /ST 02:00 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\sciezka\do\pliku\przechowywania\backup-db.ps1\"" /F
```

Sprawdzenie:

```powershell
schtasks /Query /TN "KioskAPI Daily DB Backup" /V /FO LIST
```

Uruchomienie testowe:

```powershell
schtasks /Run /TN "KioskAPI Daily DB Backup"
```

## 4) Dobre praktyki

- Trzymaj backupy poza repo (np. dysk sieciowy / chmura).
- Dodaj retencję (np. 14-30 dni) osobnym taskiem czyszczącym stare pliki.
- Raz na tydzień zrób test restore na osobnej bazie/kontenerze.
