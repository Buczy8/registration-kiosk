# KioskAPI — Kompleksowa Dokumentacja Systemu

KioskAPI to zlokalizowany system rejestracji uczestników, automatycznego generowania cyfrowych oświadczeń (PDF) z odręcznymi podpisami oraz drukowania na drukarce LAN. System jest przeznaczony do instalacji on-premise (serwer w sieci lokalnej + tablety w trybie kiosku), np. na torach kartingowych i obiektach sportowych.

---

## Spis treści

1. [Architektura systemu](#1-architektura-systemu)
2. [Struktura projektu](#2-struktura-projektu)
3. [Przepływy informacji](#3-przepływy-informacji)
4. [Uruchomienie produkcyjne](#4-uruchomienie-produkcyjne)
5. [Konfiguracja urządzeń zewnętrznych](#5-konfiguracja-urządzeń-zewnętrznych)
6. [Rozwój i testowanie](#6-rozwój-i-testowanie)
7. [Zasady bezpieczeństwa i RODO](#7-zasady-bezpieczeństwa-i-rodo)

---

## 1. Architektura systemu

System działa lokalnie w sieci LAN. Orkiestracja: **Docker Compose**.

```mermaid
graph TD
    subgraph Kiosk["Tablet (przeglądarka)"]
        SPA["React / Vite (statyczne pliki z Caddy)"]
    end

    subgraph Docker["Serwer — Docker Compose"]
        Proxy["Caddy reverse proxy :80 / :443"]
        API["FastAPI :8000"]
        DB[("PostgreSQL 15")]
        Sim["Printer simulator :9100 (tylko dev/test)"]
    end

    subgraph LAN["Sieć lokalna"]
        Printer["Drukarka RAW TCP :9100"]
    end

    SPA -->|"HTTPS"| Proxy
    Proxy -->|"X-Kiosk-Token + /api/*"| API
    Proxy -->|"pliki statyczne"| SPA
    API --> DB
    API -->|"auto-druk w tle (BackgroundTasks)"| Printer
    API -.->|"compose dev"| Sim
```

### Komponenty

| Usługa | Rola |
|--------|------|
| **reverse-proxy (Caddy)** | HTTPS (`tls internal`), serwowanie zbudowanego frontendu, proxy `/api/*` do API, **wstrzykiwanie nagłówka `X-Kiosk-Token`** (token nie trafia do bundla JS). |
| **api (FastAPI)** | REST API, JWT w HttpOnly cookie, generowanie PDF (PyMuPDF), zapis podpisów, kolejka druku w **FastAPI `BackgroundTasks`** (in-process, nie osobny worker). |
| **db (PostgreSQL)** | Użytkownicy, formularze, zgłoszenia, zadania druku (`print_jobs`). |
| **printer-simulator** | Opcjonalny symulator portu 9100 — zapisuje strumień RAW do `storage/printed_files`. W produkcji zwykle **wyłączony**; API kieruje się na fizyczną drukarkę. |

> **Uwaga:** W `app/core/config.py` są pola `redis_url` / `celery_*` — to **rezerwa na przyszłość**, obecnie **nie są używane** w runtime ani w `docker-compose.yml`.

---

## 2. Struktura projektu

```text
KioskAPI/
├── alembic/                 # Migracje bazy danych
├── app/
│   ├── api/v1/              # Routery HTTP (kiosk, auth, me, admin)
│   ├── core/                # Config, security, middleware, błędy
│   ├── models/              # SQLAlchemy
│   ├── schemas/             # Pydantic
│   └── services/            # PDF, drukarka, zgłoszenia, podpisy
├── documentation/           # Kontrakty API, backlog epików
├── frontend/                # React + Vite (JS/JSX)
├── infrastructure/
│   ├── caddy/               # Caddyfile + Dockerfile (build FE + proxy)
│   └── printer_simulator/   # Symulator drukarki TCP 9100
├── scripts/                 # docker-entrypoint.sh, seed formularza
├── storage/                 # Podpisy, wygenerowane pliki (wolumen)
├── templates/forms/         # Szablony PDF formularzy
├── tests/                   # pytest
├── Dockerfile               # Obraz API
├── docker-compose.yml
└── .env.example
```

---

## 3. Przepływy informacji

Wszystkie endpointy API są pod prefiksem **`/api/v1`**. Nagłówek **`X-Kiosk-Token`** jest wymagany na endpointach kiosku (w produkcji dokleja go Caddy).

### A. Gość (Guest)

1. Ekran startowy → formularz gościa.
2. Wybór roli i pojazdu, dane osobowe, zgody, podpis na `SignaturePad` (PNG → base64).
3. `POST /api/v1/kiosk/submissions` (bez JWT) — tryb `guest`.
4. Backend: walidacja, zapis podpisu, numer startowy, commit zgłoszenia.
5. Jeśli **`PRINT_ENABLED=true`** — auto-druk w tle (`BackgroundTasks`); jeśli `false` — status `submitted`, druk tylko z panelu admina.
6. Ekran wyniku: podgląd PDF (`GET /api/v1/kiosk/submissions/{id}/pdf`), status druku (kolejka / OK / błąd).

### B. Konto (Account)

1. Rejestracja `POST /api/v1/auth/register` lub logowanie `POST /api/v1/auth/login` (JWT w cookie).
2. Prefill: `GET /api/v1/me/form-prefill?role=...&vehicle_type=...`.
3. Weryfikacja danych, podpis, `POST /api/v1/kiosk/submissions` (z cookie JWT) — tryb `account`.
4. Profil użytkownika aktualizowany po zapisie; auto-druk jak wyżej, zależnie od `PRINT_ENABLED`.

### C. Opiekun prawny (Guardian)

1. Rola `legal_guardian`, lista podopiecznych `GET /api/v1/account/related-persons`.
2. Osobne zgłoszenie per podopieczny (`POST .../related-persons/{id}/submissions`) — każdy dostaje własny numer startowy i ewentualny wydruk.

### Druk — kto i kiedy

| Mechanizm | `PRINT_ENABLED=true` | `PRINT_ENABLED=false` |
|-----------|----------------------|------------------------|
| Auto-druk po submitcie użytkownika | Tak (w tle) | Nie |
| Druk z panelu admina | Tak (`force=true`) | Tak |
| Status „Drukarka” w panelu admina | TCP do `PRINTER_HOST:PORT` (niezależny od flagi) | j.w. |

Użytkownik **nie klika „Drukuj”** — przy włączonej fladze druk jest automatyczny po wysłaniu formularza.

---

## 4. Uruchomienie produkcyjne

### Wymagania

- Docker Engine lub Docker Desktop na serwerze LAN.
- Porty **80** i **443** dostępne dla tabletów (firewall).
- Statyczny IP serwera i (zalecane) drukarki w sieci lokalnej.

### Krok 1 — plik `.env`

```bash
cp .env.example .env
```

Uzupełnij **obowiązkowo** (aplikacja przy `APP_ENV=production` odrzuci start ze słabymi sekretami):

| Zmienna | Produkcja |
|---------|-----------|
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `KIOSK_TOKEN` | Losowy, min. 16 znaków, **inny niż placeholder** |
| `JWT_SECRET_KEY` | Losowy, min. 32 znaki, **inny niż placeholder** |
| `POSTGRES_PASSWORD` | Silne hasło (nie `kiosk`) |
| `AUTH_COOKIE_SECURE` | `true` (wymuszane też przez walidator produkcyjny) |
| `TRUSTED_HOSTS` | Konkretne hosty/IP serwera, **nie** `["*"]` |
| `START_NUMBER_TIMEZONE` | np. `Europe/Warsaw` |
| `PRINT_ENABLED` | `true` = użytkownik dostaje auto-druk; `false` = druk tylko admin |
| `PRINTER_HOST` / `PRINTER_PORT` | IP fizycznej drukarki, port **9100** (RAW) |
| `KIOSK_IDLE_LOGOUT_SECONDS` | Czas bezczynności (wbudowywany w obraz Caddy przy buildzie) |

Generowanie sekretów (przykład):

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Krok 2 — dostosuj `docker-compose.yml` pod produkcję

Domyślny plik jest nastawiony na **dev** (symulator drukarki, `DEBUG=true`, wystawiona baza). Przed produkcją:

1. **Drukarka** — w sekcji `api` ustaw realny host zamiast `printer-simulator`:
   ```yaml
   PRINTER_HOST: ${PRINTER_HOST:-192.168.1.100}
   PRINTER_PORT: ${PRINTER_PORT:-9100}
   ```
2. **Usuń lub zakomentuj usługę `printer-simulator`** i jej port `9100:9100` na hoście — nie powinien być publiczny w prod.
3. **PostgreSQL** — rozważ **usunięcie** mapowania `"5432:5432"` (baza tylko w sieci Docker), albo bind tylko do `127.0.0.1`.
4. **Sekrety** — nie polegaj na domyślnych wartościach w compose (`change-me-...`); wszystko z `.env`.
5. **Swagger** — FastAPI wyłącza `/docs` gdy `APP_ENV=production`, ale Caddy nadal może proxy’ować ścieżki dokumentacji; w razie potrzeby zablokuj `@api_docs` w `infrastructure/caddy/Caddyfile`.

### Krok 3 — szablony i wolumeny

- Plik **`templates/forms/guest-registration-v1.pdf`** musi istnieć (seed formularza wskazuje tę ścieżkę). Brak szablonu → błąd **500** przy generowaniu PDF (zgłoszenie w bazie już jest).
- Wolumeny `./storage` i `./templates` muszą być trwałe i objęte backupem (podpisy, ewentualne pliki druku testowych).

### Krok 4 — build i start

```bash
docker compose up -d --build
```

Przy starcie kontenera `api` (`scripts/docker-entrypoint.sh`):

1. `alembic upgrade head`
2. `scripts/seed_active_form.py` — aktywny formularz w bazie
3. `uvicorn main:app` (bez `--reload`)

### Krok 5 — weryfikacja

| Test | Oczekiwany wynik |
|------|------------------|
| `https://<IP-serwera>/` | Ekran startowy kiosku |
| `https://<IP-serwera>/api/v1/health` | JSON ze `status: ok`, `database: ok` |
| Panel admina po zalogowaniu | **Drukarka: OK/BŁĄD** = połączenie TCP; **Druk użytkownika** = wartość `PRINT_ENABLED` |
| Nowe zgłoszenie przy `PRINT_ENABLED=false` | Status `submitted`, bez auto-druku |
| Druk z admina | Działa niezależnie od `PRINT_ENABLED` |

### Krok 6 — pierwsze konto administratora

Rejestracja przez kiosk tworzy zwykłego użytkownika (`is_superuser=false`). Nadanie uprawnień admina — ręcznie w bazie:

```bash
docker compose exec db psql -U kiosk -d kiosk -c \
  "UPDATE users SET is_superuser = true WHERE email = 'admin@example.com';"
```

### Checklist bezpieczeństwa (produkcja)

- [ ] Zmienione `KIOSK_TOKEN` i `JWT_SECRET_KEY` (nie placeholdery z compose).
- [ ] `APP_ENV=production`, `DEBUG=false`.
- [ ] Silne hasło PostgreSQL; port 5432 nie wystawiony na LAN bez potrzeby.
- [ ] `TRUSTED_HOSTS` ograniczone do realnych hostów.
- [ ] `AUTH_COOKIE_SECURE=true` (HTTPS przez Caddy).
- [ ] Certyfikat Caddy (`tls internal`) zainstalowany na tabletach lub świadoma decyzja o HTTP (niezalecane).
- [ ] Symulator drukarki i port 9100 na hoście wyłączone w prod.
- [ ] Szablon PDF obecny w `templates/forms/`.
- [ ] Backup wolumenu `postgres_data` i `storage`.

### Typowe problemy

| Objaw | Przyczyna | Działanie |
|-------|-----------|-----------|
| **401** na API z tabletu | Brak / zły `X-Kiosk-Token` | Token w `.env` musi być zgodny z tym, co Caddy wstrzykuje (`KIOSK_TOKEN` w compose dla `reverse-proxy`). |
| **Drukarka: BŁĄD** w adminie | Brak TCP do `PRINTER_HOST:9100` | Sprawdź IP, firewall, kabel/sieć; to **nie** jest skutek `PRINT_ENABLED=false`. |
| Status **Błąd druku** na zgłoszeniu | Drukarka niedostępna przy `PRINT_ENABLED=true` | Napraw połączenie lub ustaw `PRINT_ENABLED=false` i drukuj z admina. |
| **500** przy PDF | Brak pliku szablonu | Dodaj `guest-registration-v1.pdf` lub popraw `pdf_template_path` w seedzie. |
| Aplikacja nie startuje | Słabe sekrety przy `APP_ENV=production` | Użyj losowych tokenów — walidator w `Settings.validate_production_safety`. |

---

## 5. Konfiguracja urządzeń zewnętrznych

### Drukarka LAN (RAW TCP, port 9100)

1. Statyczny IP drukarki (np. `192.168.1.100`).
2. W `.env`: `PRINTER_HOST`, `PRINTER_PORT=9100`.
3. `PRINT_ENABLED` — patrz sekcja [Druk — kto i kiedy](#druk--kto-i-kiedy).

Healthcheck w panelu admina to **test połączenia TCP**, nie diagnostyka „brak papieru” (wymagałoby protokołu producenta).

### Tablet (kiosk)

- Ta sama sieć Wi‑Fi/LAN co serwer.
- Adres: `https://<IP-serwera>` (Caddy).
- Certyfikat wewnętrzny Caddy: zainstaluj root CA z wolumenu `caddy_data` (`/data/caddy/pki/authorities/local/root.crt`) na tablecie, albo (niezalecane) HTTP + `AUTH_COOKIE_SECURE=false`.

---

## 6. Rozwój i testowanie

### Zalecany sposób — Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
```

- Aplikacja: `https://localhost` (Caddy) lub API wewnętrznie na porcie 8000 (tylko w sieci compose).
- Symulator drukarki: port **9100**, pliki w `storage/printed_files/`.
- **Redis nie jest wymagany.**

Logi API: `docker compose logs api -f`

### Backend lokalnie (bez Dockera)

1. `uv sync`
2. Działająca **PostgreSQL** (Redis **nie** jest potrzebny).
3. `.env` z `DATABASE_URL=postgresql+psycopg_async://...@localhost:5432/kiosk`
4. `uv run alembic upgrade head`
5. `uv run python scripts/seed_active_form.py`
6. `uv run uvicorn main:app --reload --port 8000`

Frontend w dev często przez osobny kontener Vite — patrz `.cursor/rules/docker-dev-environment.mdc` w repozytorium.

### Testy

```bash
uv run pytest
```

Testy obejmują m.in. auth, zgłoszenia, podpisy, PDF, drukarkę (mock / lokalny TCP server).

### Nowa migracja

```bash
uv run alembic revision --autogenerate -m "opis zmiany"
uv run alembic upgrade head
```

---

## 7. Zasady bezpieczeństwa i RODO

- **Idle logout:** po zalogowaniu sesja wygasa po bezczynności (domyślnie 30 s dla użytkownika, 5 min dla admina w UI; parametr `KIOSK_IDLE_LOGOUT_SECONDS` jest przekazywany przy buildzie obrazu Caddy).
- **Token kiosku:** tylko po stronie reverse proxy — nie umieszczaj `KIOSK_TOKEN` w frontendzie.
- **JWT:** HttpOnly cookie, `SameSite=strict`, Argon2id dla haseł.
- **Lockout:** 5 nieudanych logowań → blokada 15 min; rate limit na endpoint logowania.
- **RODO:** wymagane oświadczenia przed wysłaniem formularza; opcjonalna zgoda na publikację wizerunku.
- **Wersjonowanie formularza:** każde zgłoszenie wiązane z `form_version` w bazie.

Dalsze kontrakty API i backlog: katalog `documentation/` (m.in. `API_Contract_MVP.md`, `account-mode-tasks.md`).
