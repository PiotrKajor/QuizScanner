# Zmiany

Format: [wersja] — co nowego z punktu widzenia nauczyciela.

## [3.2.0] — 2026-10-24

> **Inspiracja:** to wydanie powstało dzięki forkowi
> [suoyikehahaha/QuizScanner](https://github.com/suoyikehahaha/QuizScanner)
> (chińska edycja „辨惑策” autorstwa 公众号 „蓑衣微言”). Autor dorobił tam
> m.in. natywnego pilota na Androida, klasy, import testów z Worda i losowanie
> ucznia. Najciekawsze pomysły przenieśliśmy tutaj — po swojemu: w przeglądarce
> zamiast osobnej aplikacji, bez chmury i bez wysyłania imion uczniów do
> zewnętrznych usług. Dziękujemy!

### Nowe

- **📱 Pilot w telefonie** — w panelu kliknij „Pilot w telefonie” i zeskanuj
  kod QR. Telefon staje się pilotem: duży przycisk Start → Pokaż wynik →
  Następne, czas, liczba odpowiedzi, poprawna odpowiedź tylko dla Ciebie
  i lista uczniów, którzy **jeszcze nie podnieśli karty** — chodzisz po klasie
  i wiesz, do kogo podejść. Nie trzeba niczego instalować.
- **🔒 Sterowanie tylko dla nauczyciela** — dotąd każdy w tej samej sieci Wi-Fi
  mógł przełączać pytania, a nawet podejrzeć poprawną odpowiedź pod
  `/api/state?full=1`. Teraz urządzenia w sieci widzą tylko tablicę; panel,
  edytor, raporty i obraz z kamery działają na komputerze nauczyciela i na
  urządzeniach sparowanych kodem QR. Przycisk „Odłącz wszystkie urządzenia”
  unieważnia stare parowania.
- **📺 Sterowanie z tablicy** — po poruszeniu myszą na tablicy pojawia się
  pasek: lista pytań do przeskoczenia, ◀ ▶, Start/Pokaż wynik, losowanie
  i pełny ekran (klawisz F). Na niesparowanym komputerze przy rzutniku pasek
  ma tylko powiększanie tekstu.
- **🔍 Powiększanie tekstu na tablicy** — 80–175% (przyciski A−/A+ albo
  klawisze +/−), zapamiętywane osobno na każdym komputerze. Przy dużym
  powiększeniu tablica przewija się zamiast ucinać odpowiedzi.
- **🎲 Losuj ucznia** — z panelu, pilota albo tablicy. Na tablicy krótka
  animacja przewijania imion; losowanie bez powtórzeń, dopóki nie wylosuje się
  cała klasa. Opcjonalnie tablica **czyta imię na głos** — wyłącznie głosem
  zainstalowanym w systemie, offline.
- **👥 Klasy** — osobna lista uczniów dla każdej klasy, przełącznik w panelu
  i w pilocie. Dotychczasowa lista staje się klasą „Moja klasa”. Nazwa klasy
  trafia do raportu i do nazwy pliku raportu.
- **📥 Import listy uczniów z CSV/Excela** — eksport z dziennika lub zwykły
  arkusz („Nazwisko;Imię”, „1;Anna Nowak” albo samo nazwisko w linii);
  numery kart nadają się same, gdy ich nie ma. Listę można też zapisać do CSV.
- **📄 Import pytań z Worda (.docx) i pliku tekstowego** — numerowane pytania,
  odpowiedzi A–D, poprawna przez „Odpowiedź: B”, gwiazdkę albo pogrubienie;
  działa też automatyczna numeracja Worda. W edytorze jest gotowy szablon
  .docx do pobrania. Wynik trafia do edytora do przejrzenia, z listą
  ostrzeżeń (np. „Pytanie 4: nie wskazano poprawnej odpowiedzi”).
- **💾 Wznowienie przerwanej gry** — po każdym wyniku gra zapisuje się na
  dysku. Gdy program zostanie zamknięty w trakcie lekcji (albo komputer się
  zawiesi), po ponownym uruchomieniu wracasz do tego samego pytania z tymi
  samymi punktami. Program pamięta też ostatnio wczytany quiz.

### Poprawki

- **Powrót do pytania nie dolicza punktów drugi raz.** Wcześniej „Poprzednie”
  → „Start” → „Pokaż wynik” dodawało punkty za to samo pytanie ponownie
  (raport już to pomijał, ranking na tablicy — nie). Teraz nowy wynik
  zastępuje poprzedni.
- **Raport pokazuje uczniów bez żadnej odpowiedzi** (0 pkt) — widać, kogo
  brakowało; średnie liczone są tylko z obecnych.
- Adres tablicy i kod QR działają też w szkolnej sieci bez internetu (dawniej
  panel pokazywał wtedy `127.0.0.1`); przy kilku kartach sieciowych można
  wybrać właściwą.
- Fazy pytania w panelu są opisane po polsku/angielsku zamiast `idle`/`reveal`.

### Pod spodem

- Nowe moduły `quiz_import.py` i `roster_import.py` czytają .docx/.xlsx przez
  `zipfile` z biblioteki standardowej — **żadnej nowej zależności**.
- Kod QR rysuje koder z OpenCV, który i tak jest wymagany.
- `tools/selftest.py` sprawdza dodatkowo importy, klasy, ochronę przed
  urządzeniami w sieci, parowanie, losowanie, wznowienie gry i poprawkę
  punktacji. Działa na tymczasowej klasie i nie rusza Twojej listy uczniów.

## [3.1.0] — 2026-08-02

### Nowe

- **Wzory LaTeX renderowane przez KaTeX** — wzór zamykasz w dolarach
  (`$\frac{1}{2}$`, `$\pi r^2$`, `$$\begin{cases}…\end{cases}$$`), a tablica
  i panel pokazują go złożonego jak w podręczniku. Podwójne dolary dają wzór
  wyśrodkowany w osobnej linii.
- **Sekcja LaTeX w przyborniku** — gotowe szablony: ułamek piętrowy,
  pierwiastek stopnia n, potęga i indeks, całka z granicami, suma, granica,
  symbol Newtona, kreska nad symbolem, wektor, układ równań, macierz.
  Szablony działają na zaznaczeniu.
- **Podgląd na żywo pod przybornikiem** — pokazuje edytowane właśnie pole
  dokładnie tak, jak zobaczą je uczniowie; błąd składni widać od razu.
- Przykładowy quiz ma teraz pytanie z ułamkami, żeby było co obejrzeć od razu
  po instalacji.

### Zmiany

- KaTeX leży w repozytorium (`quizscanner/web/vendor/katex`, ok. 600 kB,
  licencja MIT) i wchodzi do pliku `.exe` — **nic nie pobiera się z internetu**,
  aplikacja dalej działa w pełni offline.
- W raportach (PDF, Excel, CSV, HTML, TXT) wzory zapisywane są czytelnym
  tekstem: `$\frac{1}{2}$` → `(1)/(2)`, `$\sqrt[3]{27}$` → `³√(27)`. Pełny
  zapis LaTeX zostaje w eksporcie JSON.
- Szybkie sprawdzenie (`tools/selftest.py`) obejmuje dodatkowo zasoby KaTeX
  (razem z typem MIME czcionek) i zamianę wzorów na tekst.

## [3.0.0] — 2026-08-02

### Nowe

- **Przybornik matematyczny w edytorze** — paleta symboli w sześciu sekcjach
  (podstawowe, potęgi i ułamki, greka, zbiory i logika, geometria, analiza),
  szablony działające na zaznaczeniu (`√( )`, przedział, układ) oraz zamiana
  zaznaczonego fragmentu na indeks górny/dolny. Wzory to tekst Unicode, więc
  wyglądają tak samo w edytorze, na tablicy i w raporcie PDF.
- **Motyw ciemny jako domyślny + 6 kolejnych**: jasny, ocean, las, zachód
  słońca, cukierkowy i wysoki kontrast. Zmiana z panelu działa od razu również
  na tablicy — także gdy stoi na innym komputerze.
- **Dźwięki tablicy** — start pytania, odliczanie ostatnich pięciu sekund,
  koniec czasu, wynik i fanfara na podium. Generowane w przeglądarce (WebAudio),
  bez plików audio. Przełącznik i suwak głośności w panelu.
- **Raport po grze** — nowy przycisk **„📊 Raport"**: ranking, skuteczność
  każdego ucznia, odpowiedzi na każde pytanie, rozkład A/B/C/D i wskazanie
  najtrudniejszego pytania. Pobieranie w **PDF, Excelu (XLSX), CSV, HTML,
  JSON i TXT**.
- **Automatyczny zapis raportu** — po ostatnim pytaniu komplet HTML + CSV + JSON
  trafia sam do `data/raporty/`.
- **Automatyczna aktualizacja** — pasek z informacją o nowym wydaniu i pobranie
  jednym kliknięciem; w wersji `.exe` plik podmienia się przy zamykaniu programu.
  Sprawdzanie można wyłączyć.
- **FAQ** — [docs/FAQ.md](docs/FAQ.md) z odpowiedziami na pytania o karty,
  kamerę, wzory, raporty, prywatność i typowe kłopoty.
- **Szybkie sprawdzenie** `tools/selftest.py` — uruchamia aplikację bez kamery
  i przechodzi przez nią jak nauczyciel: strony, API, karty PDF, cały przebieg
  quizu, wszystkie formaty raportu i kompletność tłumaczeń PL/EN.

### Zmiany

- **Nowa struktura katalogów**: kod w pakiecie `quizscanner/`, dane użytkownika
  w `data/`, dokumentacja w `docs/`, skrypty w `scripts/`. Serwer uruchamia się
  teraz przez `python -m quizscanner` (dawniej `python app.py`).
- Dane nauczyciela (quizy, media, lista uczniów, raporty, ustawienia) siedzą
  w jednym folderze `data/` obok programu — łatwiej je skopiować i zarchiwizować.
- Eksport wyników przeniesiony ze skromnego `wyniki_<data>.csv` do pełnego
  raportu (stary przycisk „⬇ Eksport wyników" zastąpił „📊 Raport").
- Kontrola polskich znaków obsługuje wyjątki w linii (`polish-ok`), dzięki czemu
  nazwy funkcji trygonometrycznych nie są zgłaszane jako literówki.
- Numer wersji do budowania `.exe` czytany jest z `quizscanner/__init__.py`,
  więc nie da się wydać pliku z nieaktualnym numerem.

## [2.0.1]

- Naprawa narzędzia kontroli polskich znaków, pełne diakrytyki w repozytorium.

## [2.0.0]

- Języki PL/EN, tryb automatyczny, zdjęcia i filmy w pytaniach, telefon jako kamera.

## [1.3.0]

- Naprawa: skaner nie wykrywał większości kart (odbicie lustrzane).

## [1.2.0]

- Logo aplikacji, dopracowana strona repozytorium, numer wersji w nazwie `.exe`.

## [1.1.0]

- Pobieranie kart do druku (PDF) z poziomu aplikacji.

## [1.0.0]

- Pierwsze wydanie: system quizowy z odczytem kart ArUco z kamery,
  jednoplikowy `QuizScanner.exe`.
