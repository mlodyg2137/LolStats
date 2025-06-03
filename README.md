**LOLStats** to prosty projekt w Django, który pozwala na przeglądanie statystyk graczy League of Legends.  
Aplikacja umożliwia:

- Wyszukanie summonera według `gameName` i `tagLine`.
- Pobranie aktualnych danych z Riot API (poziom, ikona, ranga SoloQ/FlexQ).
- Wyświetlenie statystyk za SoloQ i FlexQ (KDA, winratio, główna rola, gold/min, miniony/min, vision avg).
- Paginowaną historię meczów (z filtrowaniem po trybach kolejek).
- Możliwość „odświeżenia” historii meczów i statystyk za pomocą przycisku **Aktualizuj**.
- Informowanie użytkownika o limitach zapytań do Riot API i błędach.

---

## Spis treści

- [Wymagania](#wymagania)
- [Instalacja](#instalacja)
- [Konfiguracja](#konfiguracja)
- [Uruchomienie aplikacji](#uruchomienie-aplikacji)
- [Struktura projektu](#struktura-projektu)
- [Jak działa aplikacja](#jak-działa-aplikacja)
- [Endpointy](#endpointy)
- [Licencja](#licencja)

---

## Wymagania

- Python 3.10+
- Django 4.x
- Pakiet `requests` (wykorzystywany do komunikacji z Riot API)
- Pakiet `dotenv` (do przechowywania klucza RIOT API)

---

## Instalacja

1. **Sklonuj repozytorium**

   ```bash
   git clone https://github.com/mlodyg2137/lolstats.git
   cd lolstats
   ```

2. **Utwórz i aktywuj wirtualne środowisko**

   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate       # Windows
   ```

3. **Zainstaluj zależności**

   ```bash
   pip install -r requirements.txt
   ```

4. **Wykonaj migracje bazy danych**

   ```bash
   python manage.py migrate
   ```

5. **(Opcjonalnie) wczytaj przykładowe dane, aby już mieć w bazie graczy pare rekordów**
   ```bash
   python manage.py loaddata initial_data.json
   ```
---

## Konfiguracja

1. **Klucz Riot API**

   Aplikacja wymaga podania Twojego klucza do Riot API.  
   Utwórz plik `.env` w katalogu głównym (obok `manage.py`) i dodaj w nim:

   ```
   RIOT_API_KEY=twój_riot_api_key
   ```

   Jeżeli nie używasz `.env`, możesz też ustawić zmienną środowiskową:
   ```bash
   export RIOT_API_KEY=twój_riot_api_key     # Linux/macOS
   set RIOT_API_KEY=twój_riot_api_key        # Windows (cmd)
   ```

2. **(Opcjonalnie) Inne ustawienia**

   - W `settings.py` możesz zmienić `DEBUG`, `ALLOWED_HOSTS` czy bazę danych.
   - Domyślnie aplikacja korzysta z SQLite w pliku `db.sqlite3`.

---

## Uruchomienie aplikacji

1. **(Opcjonalnie) Zbierz pliki statyczne**

   Jeśli masz własne pliki CSS/JS czy favicony, możesz je zebrać:

   ```bash
   python manage.py collectstatic
   ```

2. **Uruchom serwer deweloperski**

   ```bash
   python manage.py runserver
   ```

3. **Dostęp do aplikacji**

   Otwórz przeglądarkę i przejdź pod adres:

   ```
   http://127.0.0.1:8000/
   ```

   Strona główna pozwala na wyszukanie summonera. Po wpisaniu `gameName`, `tagLine` i wybraniu regionu – zobaczysz profil.

---

## Struktura projektu

```
lolstats/
├── manage.py
├── README.md
├── requirements.txt
├── db.sqlite3
├── .env
└── lolstats/              # główny katalog projektu Django
    ├── settings.py
    ├── urls.py
    ├── wsgi.py
    └── asgi.py
└── stats/                  # aplikacja “stats”
    ├── migrations/
    ├── templates/
    │   └── stats/
    │       ├── base.html
    │       ├── home.html
    │       └── summoner_detail.html
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── services.py
    ├── utils.py
    ├── views.py
    ├── tests.py
    └── urls.py
```

- **`stats/models.py`** – definicje modeli: `Summoner`, `Match`, `Participant`, `Queue`, `Champion`.
- **`stats/services.py`** – logika pobierania danych z Riot API i zapisywania ich w bazie.
- **`stats/utils.py`** – funkcje pomocnicze (np. tłumaczenie regionu na serwer).
- **`stats/views.py`** – widoki: `home` (formularz do wyszukiwania) i `summoner_detail` (profil summonera).
- **`stats/templates/stats/`** – szablony HTML.
- **`stats/tests.py`** – testy jednostkowe i integracyjne.

---

## Jak działa aplikacja

1. **Strona główna (`/`)**

   - Formularz: „Nick gracza” (`gameName`), „Tag gracza” (`tagLine`), „Region”.
   - Po wciśnięciu „Szukaj” następuje przekierowanie do `/summoner/<gameName>/<tagLine>/?region=<region>`.

2. **Widok `summoner_detail`**

   - **GET**:
     - Jeśli dany **Summoner** nie istnieje w bazie, wywołujemy Riot API przez `get_summoner_by_name_and_tag`.  
       - Gdy API zwróci dane (200 OK), zapisujemy `Summoner` w bazie i pobieramy rangę oraz historię meczów.
       - Gdy API zwróci 404 → przekierowujemy na stronę główną z komunikatem „Nie ma takiego gracza…”.
       - Gdy API zwróci 429 (Rate Limit) → przekierujemy na stronę główną z komunikatem o limicie.
       - Inne błędy → przekierowujemy na home z ogólnym komunikatem o błędzie.
     - Jeśli Summoner jest w bazie, sprawdzamy, czy ma w bazie `Participant` (czyli historię).  
       - Jeśli brakuje historii (np. świeży rekord), pobieramy ją ponownie z Riot API.
     - Następnie renderujemy `summoner_detail.html` z:
       - Wyliczonymi statystykami SoloQ/FlexQ (`kda`, `winratio`, `gold/min`, `miniony/min`, `vision avg`, `main role`).
       - Panel z informacjami: `gameName`, `tagLine`, `summoner_level`, `ikona`, rangi SoloQ/FlexQ.
       - Tabelą paginowanych meczów z możliwością filtrowania po queue (tryb gry).

   - **POST** (`update=1`):
     - Usuń wszystkie powiązane z danym Summonerem rekordy `Participant` oraz `Match`.
     - Wywołaj `save_recent_matches_for_summoner(summ)` → wczytaj od nowa historię.
     - Wywołaj `recalculate_summoner_advanced_stats(summ)` → przelicz statystyki.
     - Przekieruj GET-em na ten sam widok (`?region=<region>`), aby odświeżyć tabelę i dane.

---

## Endpointy

- **`GET  /`**  
  Strona główna (formularz do wyszukiwania summonera).

- **`POST /`**  
  Obsługa formularza wyszukiwania (przekierowanie do `/summoner/...`).

- **`GET  /summoner/<gameName>/<tagLine>/?region=<region>`**  
  Profil summonera:
  - Jeśli w bazie nie ma Summonera → pobiera z Riot API → zapisuje + wczytuje historię + statystyki.
  - Jeśli jest w bazie, wyświetla zapisane dane.

- **`POST /summoner/<gameName>/<tagLine>/?region=<region>`** (z polem `update=1`)  
  - Wywoływane przez przycisk „Aktualizuj”: kasuje starą historię, pobiera ją od nowa i przelicza statystyki.

- **`GET  /summoners/`**  
  - lista wszystkich Summonerów w bazie.  

---

## Licencja

Projekt udostępniony na licencji MIT.  

---

## Kontakt

W razie pytań lub sugestii zapraszam do kontaktu:
- **E-mail:** kamilszpechcinski@gmail.com 
- **GitHub:** [github.com/mlodyg2137/lolstats](https://github.com/mlodyg2137/lolstats)

Powodzenia i miłego kodowania! 🎮✨
