# KioskAPI — Kompleksowa Dokumentacja Systemu

KioskAPI to zlokalizowany system rejestracji uczestników, automatycznego generowania cyfrowych oświadczeń (PDF) z odręcznymi podpisami oraz ich bezobsługowego drukowania. System został zaprojektowany z myślą o instalacji na lokalnym serwerze (on-premise) obsługującym stanowiska samoobsługowe (tablety w trybie kiosku) na torach kartingowych, obiektach sportowych i szkoleniowych (np. Autodrom Biłgoraj).

---

## Spis Treści
1. [Architektura Systemu](#1-architektura-systemu)
2. [Struktura Projektu](#2-struktura-projektu)
3. [Przepływy Informacji (Flows)](#3-przepływy-informacji-flows)
4. [Dokumentacja Uruchomieniowa (Deployment)](#4-dokumentacja-uruchomieniowa-deployment)
5. [Konfiguracja Urządzeń Zewnętrznych](#5-konfiguracja-urządzeń-zewnętrznych)
6. [Rozwój i Testowanie (Development)](#6-rozwój-i-testowanie-development)
7. [Zasady Bezpieczeństwa i RODO](#7-zasady-bezpieczeństwa-i-rodo)

---

## 1. Architektura Systemu

System działa w pełni lokalnie (offline) w obrębie sieci LAN, eliminując zależność od połączenia z internetem. Do komunikacji i izolacji wykorzystuje zestaw kontenerów Docker Compose.

```mermaid
graph TD
    subgraph Kiosk (Tablet)
        SPA[React / Vite Application]
    end

    subgraph Serwer Lokalny (Docker Compose)
        Proxy[Caddy Reverse Proxy: port 80/443]
        API[FastAPI Backend: port 8000]
        DB[(PostgreSQL 15)]
        Redis[(Redis)]
        Worker[Celery / Background Workers]
        Sim[Printer Simulator: port 9100]
    end

    subgraph Urządzenia Sieciowe
        RealPrinter[Fizyczna Drukarka LAN: port 9100]
    end

    SPA -- "HTTPS (Lokalne IP)" --> Proxy
    Proxy -- "Wstrzykuje X-Kiosk-Token & Serwuje Front" --> API
    API -- "Odczyt/Zapis (Asyncpg)" --> DB
    API -- "Kolejkowanie Zadań" --> Redis
    Worker -- "Obsługa Zadań Druku" --> Redis
    Worker -- "RAW Socket TCP (Wydruk)" --> RealPrinter
    Worker -- "Opcjonalna Symulacja" --> Sim
```

### Opis komponentów systemu:
* **Caddy (Reverse Proxy):** Działa jako brama wejściowa. Obsługuje ruch HTTPS (generując wewnętrzny certyfikat SSL za pomocą `tls internal`), serwuje skompilowane pliki statyczne frontendu React oraz przekazuje zapytania API do backendu. Dodatkowo wstrzykuje nagłówek `X-Kiosk-Token` do zapytań API (szczegóły w pliku [Caddyfile](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/infrastructure/caddy/Caddyfile)).
* **FastAPI Backend:** Asynchroniczna aplikacja Python obsługująca punkty końcowe REST API. Odpowiada za walidację danych, zarządzanie użytkownikami, uwierzytelnianie (JWT) oraz generowanie dokumentów PDF.
* **PostgreSQL:** Lokalna baza danych przechowująca informacje o użytkownikach, podopiecznych, szablonach formularzy i historii zgłoszeń.
* **Redis & Celery:** Kolejka zadań asynchronicznych dedykowana do obsługi zadań drukowania. Zapobiega blokowaniu interfejsu klienta podczas fizycznego przetwarzania dokumentu przez drukarkę.
* **Printer Simulator:** Skrypt Python nasłuchujący na porcie 9100, który przechwytuje strumień wydruku RAW i zapisuje go w formacie PDF w celach testowych (szczegóły w pliku [printer_server.py](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/infrastructure/printer_simulator/printer_server.py)).

---

## 2. Struktura Projektu

Układ katalogów i kluczowych plików w repozytorium:

```text
KioskAPI/
├── alembic/                       # Migracje bazy danych (Alembic)
├── app/                           # Kod źródłowy backendu FastAPI
│   ├── api/v1/                    # Punkty końcowe API (kiosk, auth, me, admin)
│   ├── core/                      # Konfiguracja, zabezpieczenia, middleware
│   ├── db/                        # Inicjalizacja sesji bazy danych
│   ├── models/                    # Modele bazodanowe SQLAlchemy
│   ├── schemas/                   # Schematy walidacyjne Pydantic
│   └── services/                  # Logika biznesowa (PDF, drukarka, podpisy)
├── documentation/                 # Wewnętrzne dokumenty analityczne i backlog
├── frontend/                      # Aplikacja kliencka React + Vite
│   ├── src/
│   │   ├── api/                   # Klient HTTP i integracja z API
│   │   ├── components/            # Komponenty UI (SignaturePad, PdfPreview, itp.)
│   │   ├── context/               # Kontekst uwierzytelniania (AuthContext)
│   │   ├── routes/                # Definicje tras (AppRouter)
│   │   └── styles.css             # Stylowanie interfejsu (Vanilla CSS)
├── infrastructure/                # Konfiguracja Docker, Caddy i symulatora druku
├── scripts/                       # Skrypty pomocnicze (baza danych, entrypoint)
├── tests/                         # Testy automatyczne (pytest)
├── Dockerfile                     # Definicja kontenera backendu
├── docker-compose.yml             # Orkiestracja usług Docker
├── pyproject.toml                 # Definicja zależności Pythona (uv)
└── .env.example                   # Szablon zmiennych środowiskowych
```

---

## 3. Przepływy Informacji (Flows)

### A. Przepływ Rejestracji Gościa (Guest Flow)
1. Klient na ekranie startowym klika **"Wypełnij jako Gość"**.
2. Wybiera rolę (`kierowca`, `pasażer` lub `opiekun prawny`) oraz typ pojazdu.
3. Wypełnia formularz osobowy, dane pojazdu oraz zaznacza wymagane zgody prawne.
4. Składa odręczny podpis na ekranie dotykowym (generowany jako obraz PNG w formacie Base64).
5. Frontend wysyła żądanie `POST /api/v1/submissions` (lub odpowiednio `POST /api/v1/submissions/guest`).
6. Backend:
   * Dekoduje podpis Base64 i zapisuje go w wolumenie dyskowym jako plik `.png`.
   * Nadaje unikalny, atomowy **numer startowy** dla danego dnia (resetowany o północy).
   * Generuje PDF oświadczenia na bazie szablonu, wstrzykując dane tekstowe oraz obraz podpisu.
   * Zapisuje zgłoszenie w bazie danych.
   * Tworzy zadanie wydruku `PrintJob` i wysyła je do kolejki.
7. Klient widzi ekran sukcesu, a drukarka LAN automatycznie drukuje podpisane oświadczenie.

### B. Przepływ Użytkownika Zarejestrowanego (Account Flow)
1. Klient zakłada konto (`POST /api/v1/auth/register`) lub loguje się (`POST /api/v1/auth/login`).
2. Przy kolejnej wizycie na torze, po zalogowaniu, backend pobiera dane z jego ostatniego zatwierdzonego formularza (`GET /api/v1/me/form-prefill`).
3. Klient wybiera rolę i pojazd na dany dzień. System automatycznie uzupełnia jego dane osobowe i dane wybranego pojazdu (np. marka, model, nr rejestracyjny).
4. Klient weryfikuje poprawność, składa podpis i klika "Wyślij i Drukuj".
5. Backend generuje PDF, wysyła zadanie na drukarkę oraz **aktualizuje profil klienta** (zapisując ostatnio używane pojazdy oraz rolę, co przyspieszy logowanie przy kolejnej wizycie).

### C. Przepływ Opiekuna Prawnego (Guardian Flow)
1. Zalogowany opiekun wybiera rolę `legal_guardian`.
2. System wyświetla listę powiązanych z nim podopiecznych (np. dzieci) pobraną z `GET /api/v1/account/related-persons`.
3. Opiekun może wybrać istniejącego podopiecznego lub dodać nowego (`POST /api/v1/account/related-persons`).
4. Przy każdym podopiecznym wyświetlany jest szybki podgląd jego ostatnio wypełnionego formularza.
5. Zaznaczenie podopiecznego generuje dedykowane oświadczenie, które opiekun podpisuje swoim imieniem i nazwiskiem w sekcji reprezentanta prawnego.
6. **Zasada 1 podopieczny = 1 certyfikat:** System generuje i drukuje osobny dokument dla każdego wybranego podopiecznego z unikalnym numerem startowym.

---

## 4. Dokumentacja Uruchomieniowa (Deployment)

### Wymagania Wstępne
* **Docker Desktop** lub **Docker Engine** zainstalowany na lokalnym serwerze.
* Odblokowane porty systemowe **80** (HTTP) i **443** (HTTPS) na serwerze (np. w Zaporze Windows Defender).

### Krok po kroku: Uruchomienie Produkcyjne

1. **Skopiuj szablon konfiguracji:**
   ```bash
   cp .env.example .env
   ```

2. **Skonfiguruj plik [.env](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/.env):**
   Edytuj plik za pomocą edytora tekstowego i uzupełnij kluczowe zmienne:
   * Ustaw `APP_ENV=production` oraz `DEBUG=false`.
   * Wpisz silne, losowe klucze dla `KIOSK_TOKEN` (min. 16 znaków) oraz `JWT_SECRET_KEY` (min. 32 znaki).
   * Zmień domyślne hasła bazy danych `POSTGRES_PASSWORD`.
   * Ustaw strefę czasową `START_NUMBER_TIMEZONE=Europe/Warsaw` (odpowiada za poprawny reset numeru startowego o północy).

3. **Uruchom kontenery w tle:**
   ```bash
   docker compose up -d --build
   ```

4. **Co dzieje się podczas startu kontenera backendowego (`api`):**
   Uruchamiany jest skrypt [docker-entrypoint.sh](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/scripts/docker-entrypoint.sh), który automatycznie:
   * Wykonuje migracje bazy danych (Alembic) do najnowszej wersji.
   * Uruchamia skrypt [seed_active_form.py](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/scripts/seed_active_form.py), sprawdzając czy w bazie jest zaimportowany domyślny, aktywny szablon oświadczenia z pliku [guest-registration-v1.pdf](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/templates/forms/guest-registration-v1.pdf).
   * Startuje serwer produkcyjny Uvicorn.

---

## 5. Konfiguracja Urządzeń Zewnętrznych

### Fizyczna Drukarka LAN
Aplikacja komunikuje się bezpośrednio z drukarką sieciową przy użyciu protokołu RAW TCP na porcie 9100.
1. Przypisz drukarce statyczny adres IP w sieci lokalnej (np. `192.168.1.100`).
2. Otwórz plik [docker-compose.yml](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/docker-compose.yml#L63-L64) i zmień parametry podłączenia drukarki w sekcji `api`:
   ```yaml
         PRINTER_HOST: ${PRINTER_HOST:-192.168.1.100}
         PRINTER_PORT: ${PRINTER_PORT:-9100}
   ```
3. Ustaw `PRINTER_HOST` / `PRINTER_PORT` w `.env` lub `docker-compose.yml`.
4. `PRINT_ENABLED=true` — użytkownik po rejestracji dostaje auto-druk; `false` — druk tylko z panelu admina (status połączenia z drukarką jest niezależny).

### Urządzenie Kiosk (Tablet)
* **Połączenie:** Tablet kliencki musi być podłączony do tej samej sieci lokalnej (Wi-Fi) co serwer. Dostęp do aplikacji uzyskujemy wpisując w przeglądarce lokalny adres IP serwera (np. `https://192.168.1.50`).
* **Obsługa SSL (HTTPS) w sieci lokalnej:**
  Caddy domyślnie generuje wewnętrzny certyfikat SSL (`tls internal`). Przeglądarka tabletu może zgłosić błąd zabezpieczeń (Unknown CA). Aby to obejść:
  * Pobierz certyfikat główny CA z serwera Caddy (lokalizacja: wolumen `caddy_data` / `/data/caddy/pki/authorities/local/root.crt`) i zainstaluj go na tablecie w sekcji Zaufanych Głównych Urzędów Certyfikacji.
  * *Opcjonalnie (Niezalecane):* Możesz zmienić konfigurację w [Caddyfile](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/infrastructure/caddy/Caddyfile) na port `:80` bez TLS, jednak wówczas musisz ustawić `AUTH_COOKIE_SECURE=false` w `.env`.

---

## 6. Rozwój i Testowanie (Development)

Jeśli chcesz rozwijać aplikację lokalnie na maszynie deweloperskiej bez kontenerów Docker:

### Uruchomienie lokalne (backend)
1. Zainstaluj zależności Pythona za pomocą narzędzia `uv`:
   ```bash
   uv sync
   ```
2. Upewnij się, że masz lokalnie działającą bazę PostgreSQL oraz serwer Redis.
3. Wykonaj migracje bazodanowe:
   ```bash
   uv run alembic upgrade head
   ```
4. Uruchom serwer FastAPI w trybie deweloperskim:
   ```bash
   uv run uvicorn main:app --reload --port 8000
   ```

### Uruchomienie testów automatycznych
Testy pokrywają pełną walidację formularzy, logowanie, podpisy, mechanizm przydzielania numerów startowych i zadania druku.
```bash
uv run pytest
```

### Tworzenie nowych migracji bazodanowych
Gdy dokonasz zmian w modelach SQLAlchemy w katalogu [app/models/](file:///C:/Users/Paweł%20Buczek/PycharmProjects/KioskAPI/app/models):
```bash
uv run alembic revision --autogenerate -m "Opis zmian w bazie"
uv run alembic upgrade head
```

---

## 7. Zasady Bezpieczeństwa i RODO

System przetwarza dane osobowe (RODO) i działa w środowisku publicznym (samoobsługowy kiosk), dlatego wdrożono w nim restrykcyjne mechanizmy obronne:

* **Automatyczne wylogowanie (Session Idle Timeout):** Gdy użytkownik zaloguje się na swoje konto, a następnie odejdzie od tabletu bez ręcznego wylogowania, aplikacja po **30 sekundach bezczynności** (ruch myszką, dotyk ekranu) automatycznie czyści sesję, wylogowuje klienta i wraca do ekranu startowego. Wartość tę można dostosować za pomocą parametru `KIOSK_IDLE_LOGOUT_SECONDS`.
* **Izolacja Tokena Kiosku:** Aplikacja kliencka (frontend uruchomiony w przeglądarce tabletu) nie posiada w kodzie ani pamięci tokena dostępowego do API kiosku (`KIOSK_TOKEN`). Token ten jest bezpiecznie przechowywany na serwerze i automatycznie doklejany do nagłówków zapytań HTTP przez lokalny serwer Caddy Reverse Proxy.
* **Blokada konta (Lockout Policy):** Po 5 nieudanych próbach logowania, konto zostaje zablokowane na 15 minut, co uniemożliwia siłowe łamanie haseł (Brute-Force).
* **Zgody prawne (RODO):** Przepływ rejestracji wymusza zaakceptowanie klauzuli informacyjnej RODO oraz regulaminu obiektu jako warunek konieczny do przesłania formularza. Zgoda na przetwarzanie i publikację wizerunku (np. zdjęcia z jazd) jest opcjonalna.
* **Wersjonowanie oświadczeń:** Każde zgłoszenie klienta jest powiązane z konkretną, zamrożoną wersją formularza zapisaną w bazie danych. Ewentualna zmiana treści oświadczenia w przyszłości nie wpłynie na poprawność i autentyczność historycznie podpisanych PDF-ów.
