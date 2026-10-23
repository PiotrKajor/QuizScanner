# CLAUDE.md

Guidance dla Claude Code przy pracy z tym repozytorium.

QuizScanner — system quizowy dla nauczycieli: uczniowie podnoszą wydrukowane
karty z markerami ArUco, kamera odczytuje całą klasę w jednym kadrze.
Serwer HTTP stoi na czystej bibliotece standardowej Pythona (bez Flask).

## Struktura

| Ścieżka | Rola |
|---|---|
| `launcher.py` | okno startowe (tkinter) i **punkt wejścia budowanego `.exe`** |
| `quizscanner/server.py` | serwer HTTP: panel, tablica, edytor, API, strumień kamery |
| `quizscanner/session.py` | stan sesji, fazy pytania, punktacja, ranking |
| `quizscanner/camera.py`, `scanner.py`, `aruco.py` | kamera i detekcja markerów |
| `quizscanner/cards.py` | generator kart do druku (PNG/PDF) |
| `quizscanner/report.py` | raport: dane + eksport pdf/xlsx/csv/html/json/txt |
| `quizscanner/quiz_import.py` | import pytań z .docx/.txt (zipfile, bez python-docx) + szablon .docx |
| `quizscanner/roster_import.py` | import listy uczniów z CSV/XLSX, eksport CSV |
| `quizscanner/updater.py` | sprawdzanie i pobieranie nowych wydań z GitHuba |
| `quizscanner/paths.py` | ścieżki zasobów i danych (źródła vs `.exe`) |
| `quizscanner/web/` | interfejs; `vendor/katex/` to cudzy kod — nie ruszać |
| `data/` | dane użytkownika (quizy, media, klasy w `klasy/`, raporty, `sesja.json`, `pair_key.txt`) |

## Codzienna praca

```bash
python -m quizscanner --camera 0 --port 8000   # serwer
python launcher.py                             # okno startowe
python tools/selftest.py                       # szybkie sprawdzenie, czy wszystko działa
python tools/check_polish.py                   # kontrola polskich znaków
```

**Po każdej zmianie w kodzie uruchom oba narzędzia z `tools/`.** `selftest.py`
przechodzi całą aplikację (strony, API, karty PDF, przebieg quizu, wszystkie
formaty raportu, kompletność tłumaczeń PL/EN) i kończy się `SELFTEST OK`.

## Wydanie nowej wersji (tylko Windows)

`.exe` powstaje przez PyInstaller, a ten **nie robi cross-kompilacji** — plik
dla Windows da się zbudować wyłącznie na Windows. Na Linuksie/macOS ten krok
jest niewykonalny; tam kończymy na commicie i szkicu wydania.

Całość jednym poleceniem w PowerShellu (z katalogu projektu):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release.ps1
```

Skrypt po kolei: czyta numer wersji z `quizscanner/__init__.py`, sprawdza
polskie znaki i uruchamia `tools/selftest.py`, buduje
`dist\QuizScanner-v<wersja>.exe`, odpala go w trybie `--serve` i sprawdza, czy
odpowiada, wyciąga opis z `CHANGELOG.md`, wgrywa plik do wydania na GitHubie
i je publikuje.

Przełączniki: `-DryRun` (zbuduj i pokaż, nie publikuj), `-SkipTests`,
`-UpdateNotes`. Jeśli wydanie o danym tagu **już istnieje** (np. czeka szkic
z ręcznie napisanym opisem), skrypt dokłada tylko plik i publikuje — opisu nie
rusza. Nadpisanie opisu tekstem z `CHANGELOG.md`: `-UpdateNotes`.
Sam build bez publikacji: `scripts\build_exe.ps1`.

Wymagania: Python 3.10+, `pip install -r requirements.txt pyinstaller`,
`gh auth login`.

### Zanim wydasz

1. Podnieś `VERSION` w `quizscanner/__init__.py` (jedno miejsce prawdy —
   czyta je i build, i aktualizator w aplikacji).
2. Dopisz sekcję `## [wersja] — RRRR-MM-DD` na górze `CHANGELOG.md`, opisując
   **realne funkcje z punktu widzenia nauczyciela**, nie sam plik `.exe`.
3. Zaktualizuj plakietkę wersji w `README.md`.
4. Commit i push na `main`.

## Krytyczne pułapki

- **Tag wydania musi brzmieć `v<wersja>`** (np. `v3.1.0`) i zgadzać się
  z `VERSION`. Aktualizator w aplikacji porównuje właśnie tag; rozjazd oznacza,
  że użytkownicy albo nie dostaną aktualizacji, albo dostaną ją w kółko.
- **Plik `.exe` musi mieć wersję w nazwie** (`QuizScanner-v3.1.0.exe`) — pod tą
  nazwą aktualizator pobiera i podmienia plik.
- **Ikoną `.exe` zawsze jest logo programu** (`assets/logo.ico`), nigdy domyślna
  ikona PyInstallera. Po zmianie `assets/logo.svg` odtwórz ikonę:
  `python tools/make_icon.py` (rysuje logo Pillow-em, bez zewnętrznych
  narzędzi) i zacommituj `assets/logo.ico` — build i okno launchera biorą ją
  z repozytorium.
- **Zasoby w `.exe` leżą płasko**: `web` i `data` trafiają do `<_MEIPASS>\web`
  i `<_MEIPASS>\data` — dokładnie tak, jak wylicza je `quizscanner/paths.py`.
  Zmiana ścieżek w jednym miejscu wymaga zmiany w drugim.
- **Skrypty `.ps1` zapisujemy w UTF-8 z BOM.** Bez BOM Windows PowerShell 5.1
  wypisuje krzaki zamiast polskich znaków.
- **W `build_exe.ps1` znak `` ` `` musi być ostatni w linii** — komentarz po nim
  zrywa kontynuację i psuje wywołanie PyInstallera.
- **Cały tekst po polsku ma pełne znaki diakrytyczne** (komentarze, dokumentacja,
  komunikaty). Wyjątek w linii: komentarz `polish-ok`.
- **`quizscanner/web/vendor/` to cudzy kod** (KaTeX, MIT) — nie edytować i nie
  poprawiać w nim polskich znaków; narzędzia z `tools/` pomijają ten katalog.
- **Dostęp z sieci jest ograniczony** (`Handler.authorized` w `server.py`).
  Publiczne są tylko: `/board`, `/remote`, `/pair`, `/static/`, `/media/`,
  `GET /api/state` bez `full=1`, `GET /api/settings`, `/api/whoami`. Każdy nowy
  endpoint ląduje domyślnie za bramką — nie przenoś go wyżej bez powodu.
  POST musi mieć `Content-Type: application/json` (ochrona przed CSRF).
  Komputer nauczyciela (localhost i własne IP w LAN) ma pełny dostęp, inne
  urządzenia po sparowaniu kodem QR (ciasteczko `qs_key`).
- **`selftest.py` nie może ruszać danych nauczyciela** — pracuje na klasie
  `_selftest` i po sobie sprząta (klasa, `sesja.json`, ustawienia).
- **Aplikacja musi działać offline.** Żadnych CDN-ów ani zewnętrznych zasobów;
  jedyne połączenie na zewnątrz to sprawdzanie aktualizacji, które użytkownik
  może wyłączyć.
