// Tłumaczenia interfejsu. Domyślny język: polski.
// Użycie w HTML:  <span data-i18n="klucz"></span>  (albo data-i18n-ph dla placeholder)
// Użycie w JS:    t("klucz")  /  t("klucz", {n: 1, total: 4})

const I18N = {
  pl: {
    // --- wspólne ---
    app_name: "QuizScanner",
    lang_label: "Język",
    yes: "Tak", no: "Nie",
    save: "Zapisz", cancel: "Anuluj", delete: "Usuń", close: "Zamknij",
    theme_label: "Motyw kolorystyczny",
    theme_dark: "🌙 Ciemny", theme_light: "☀️ Jasny", theme_ocean: "🌊 Ocean",
    theme_forest: "🌲 Las", theme_sunset: "🌅 Zachód słońca",
    theme_candy: "🍬 Cukierkowy", theme_contrast: "◐ Wysoki kontrast",

    // --- panel nauczyciela ---
    t_load: "Wczytaj",
    t_editor: "✏️ Edytor",
    t_board: "📺 Tablica",
    t_no_quizzes: "— brak quizów, użyj edytora —",
    t_lan_board: "Tablica w sieci",
    t_cam_title: "Podgląd kamery (skaner)",
    t_cam_hint: "Uczniowie obracają kartę wybraną literą do góry.",
    t_cam_wait: "⏳ Kamera się uruchamia lub jest niedostępna (sprawdź źródło).",
    t_cam_source: "Źródło obrazu",
    t_cam_apply: "Przełącz",
    t_cam_source_hint: "Numer kamery (0, 1, 2…) albo adres telefonu, np. http://192.168.1.50:8080/video",
    t_phone_help: "📱 Jak podłączyć telefon?",
    t_question_of: "Pytanie {n} / {total}",
    t_start: "▶ Start pytania",
    t_reveal: "✓ Pokaż wynik",
    t_prev: "◀ Poprzednie",
    t_next: "Następne ▶",
    t_reset: "⟲ Reset punktów",
    t_stat_time: "Czas",
    t_stat_answered: "Odpowiedziało",
    t_stat_dist: "A/B/C/D",
    t_speed_label: "Punkty za szybkość",
    t_speed_sub: "Wył. = każda poprawna odpowiedź warta tyle samo. Wł. = szybciej daje więcej.",
    t_auto_label: "Tryb automatyczny",
    t_auto_sub: "Po starcie quiz sam pokazuje wyniki i przechodzi dalej — bez klikania.",
    t_auto_running: "Tryb automatyczny działa — quiz prowadzi się sam.",
    t_students_live: "Odpowiedzi uczniów na żywo",
    t_col_id: "ID", t_col_student: "Uczeń", t_col_answer: "Odpowiedź", t_col_points: "Punkty",
    t_no_answers: "Brak odpowiedzi",
    t_ranking: "Ranking",
    t_no_results: "Brak wyników",
    t_load_quiz_first: "Wczytaj quiz, aby rozpocząć.",
    t_confirm_reset: "Wyzerować punkty i zacząć od nowa?",
    t_only_known: "Tylko uczniowie z listy",
    t_only_known_sub: "Ignoruje kody spoza listy — chroni przed przypadkowymi wykryciami w tle.",
    t_sound_label: "Dźwięki tablicy",
    t_sound_sub: "Sygnały startu, odliczania, wyniku i podium na ekranie z rzutnika.",
    t_volume: "Głośność",
    t_auto_report_label: "Automatyczny raport",
    t_auto_report_sub: "Po ostatnim pytaniu raport zapisuje się sam do folderu z raportami.",

    // --- raport ---
    t_report: "📊 Raport",
    r_title: "Raport z quizu",
    r_download: "Pobierz jako",
    r_save_now: "💾 Zapisz na dysk",
    r_saved_to: "Zapisano w:",
    r_open_folder: "Folder raportów:",
    r_recent: "Ostatnio zapisane",
    r_no_recent: "Brak zapisanych raportów",
    r_empty: "Rozegraj chociaż jedno pytanie, żeby powstał raport.",
    r_stat_students: "Uczniowie",
    r_stat_questions: "Pytania",
    r_stat_avg: "Średnio poprawnych",
    r_stat_best: "Najlepszy wynik",
    r_hardest: "Najtrudniejsze pytanie",
    r_col_place: "#", r_col_student: "Uczeń", r_col_points: "Punkty",
    r_col_correct: "Poprawne", r_col_percent: "Skuteczność",
    r_fmt_pdf: "PDF", r_fmt_csv: "CSV", r_fmt_xlsx: "Excel",
    r_fmt_html: "HTML", r_fmt_json: "JSON", r_fmt_txt: "TXT",

    // --- aktualizacje ---
    u_available: "Dostępna nowa wersja {version} (masz {current}).",
    u_update_now: "⬇ Zaktualizuj teraz",
    u_open_page: "Otwórz stronę wydania",
    u_downloading: "Pobieram aktualizację…",
    u_ready: "Aktualizacja pobrana — zamknij program, żeby dokończyć wymianę.",
    u_failed: "Nie udało się pobrać aktualizacji.",
    u_source_hint: "Wersja ze źródeł — zaktualizuj poleceniem git pull.",
    u_check_label: "Sprawdzaj aktualizacje",
    u_check_sub: "Raz na uruchomienie pyta GitHuba o nowsze wydanie.",
    u_up_to_date: "Masz najnowszą wersję.",

    // --- tablica ---
    b_question_of: "Pytanie {n} z {total}",
    b_scanned: "Zeskanowano:",
    b_correct: "Poprawna:",
    b_prepare: "Przygotuj kartę — obróć wybraną literę (A/B/C/D) do góry",
    b_ready: "Gotowi do startu",
    b_load_hint: "Wczytaj quiz w panelu nauczyciela",
    b_end_kicker: "Koniec quizu",
    b_standings: "Klasyfikacja",
    b_no_results: "Brak wyników",
    b_sound_locked: "🔇 Kliknij ekran, aby włączyć dźwięki",

    // --- przybornik matematyczny ---
    mb_title: "Przybornik matematyczny",
    mb_hide: "Zwiń", mb_show: "Rozwiń",
    mb_basic: "Podstawowe", mb_powers: "Potęgi i ułamki", mb_greek: "Greka",
    mb_sets: "Zbiory i logika", mb_geo: "Geometria", mb_calc: "Analiza",
    mb_tpl_frac: "a/b", mb_tpl_sqrt: "√( )", mb_tpl_pow: "x²",
    mb_tpl_index: "x₁", mb_tpl_interval: "przedział",
    mb_to_sup: "Zaznaczone → w indeks górny",
    mb_to_sub: "Zaznaczone → w indeks dolny",
    mb_hint: "Kliknij pole pytania lub odpowiedzi, potem symbol. Zaznaczony fragment trafia w środek szablonu.",
    mb_preview: "Podgląd pola",
    mb_preview_empty: "Kliknij pole pytania lub odpowiedzi — zobaczysz tu, jak wygląda na tablicy.",

    // wzory LaTeX (KaTeX)
    mb_tex_title: "LaTeX",
    mb_tex_inline: "Wzór w linii: $ … $",
    mb_tex_frac: "Ułamek piętrowy",
    mb_tex_sqrt: "Pierwiastek kwadratowy",
    mb_tex_root: "Pierwiastek stopnia n",
    mb_tex_pow: "Potęga (dowolny wykładnik)",
    mb_tex_sub: "Indeks dolny",
    mb_tex_int: "Całka oznaczona",
    mb_tex_sum: "Suma z granicami",
    mb_tex_lim: "Granica",
    mb_tex_binom: "Symbol Newtona",
    mb_tex_bar: "Kreska nad symbolem (średnia)",
    mb_tex_vec: "Wektor",
    mb_tex_cases: "Układ równań",
    mb_tex_matrix: "Macierz",
    mb_tex_block: "Wzór wyśrodkowany: $$ … $$",

    // --- edytor ---
    e_title: "QuizScanner · Edytor",
    e_tab_quiz: "Quizy",
    e_tab_roster: "Uczniowie",
    e_tab_settings: "Ustawienia",
    e_to_teacher: "← Panel nauczyciela",
    e_quizzes: "Quizy",
    e_new_quiz: "+ Nowy quiz",
    e_no_quizzes: "Brak quizów — utwórz nowy",
    e_quiz_title: "Tytuł quizu",
    e_quiz_title_ph: "np. Powtórka z historii",
    e_save: "💾 Zapisz",
    e_duplicate: "⧉ Duplikuj",
    e_delete: "🗑 Usuń",
    e_export_file: "⬇ Zapisz do pliku",
    e_import_file: "⬆ Wczytaj z pliku",
    e_file_hint: "Plik .quiz możesz wysłać innemu nauczycielowi.",
    e_editing_file: "plik:",
    e_unsaved: "(nowy, niezapisany)",
    e_question_n: "Pytanie {n}",
    e_question_ph: "Treść pytania…",
    e_answer_ph: "Odpowiedź {letter}",
    e_correct: "poprawna",
    e_time_s: "Czas (s)",
    e_points: "Punkty (maks)",
    e_add_question: "+ Dodaj pytanie",
    e_media: "Zdjęcie / film",
    e_media_add: "🖼 Dodaj plik",
    e_media_remove: "✕ Usuń plik",
    e_media_hint: "Obraz (JPG/PNG/GIF/WEBP) lub film (MP4/WEBM) — pokaże się na tablicy przy pytaniu.",
    e_media_too_big: "Plik jest za duży (limit {mb} MB).",
    e_media_bad_type: "Nieobsługiwany typ pliku.",
    e_roster_hint: "ID = numer markera na wydrukowanej karcie.",
    e_save_roster: "💾 Zapisz listę",
    e_add_student: "+ Dodaj ucznia",
    e_cards_pdf: "📄 Pobierz karty (PDF)",
    e_cards_hint: "Karty do druku dla powyższej listy — jedna na stronę A4.",
    e_col_id: "ID", e_col_name: "Imię i nazwisko",
    e_saved: "Zapisano:",
    e_copy_made: "Utworzono kopię:",
    e_deleted: "Usunięto",
    e_roster_saved: "Zapisano listę uczniów",
    e_add_students_first: "Najpierw dodaj uczniów",
    e_generating_pdf: "Generuję PDF z kartami…",
    e_confirm_delete: "Usunąć quiz {name}?",
    e_imported: "Wczytano quiz z pliku",
    e_import_failed: "Nie udało się wczytać pliku — czy to plik quizu?",

    // ustawienia quizu
    s_quiz_settings: "Ustawienia quizu",
    s_default_time: "Domyślny czas pytania (s)",
    s_default_points: "Domyślne punkty",
    s_apply_all: "Zastosuj do wszystkich pytań",
    s_shuffle_q: "Losowa kolejność pytań",
    s_shuffle_a: "Losowa kolejność odpowiedzi",
    s_show_dist: "Pokaż rozkład odpowiedzi przy wyniku",
    s_auto_reveal_s: "Auto: ile pokazywać wynik (s)",
    s_auto_gap_s: "Auto: przerwa przed pytaniem (s)",
    s_applied: "Zastosowano do wszystkich pytań",
    s_app_settings: "Ustawienia aplikacji",

    // --- fazy pytania ---
    ph_idle: "przygotowanie", ph_question: "zbieranie", ph_reveal: "wynik", ph_podium: "koniec",

    // --- pilot w telefonie ---
    pr_button: "📱 Pilot w telefonie",
    pr_title: "Pilot w telefonie",
    pr_intro: "Zeskanuj kod aparatem telefonu podłączonego do tej samej sieci Wi-Fi. Telefon zapamięta parowanie.",
    pr_network: "Sieć",
    pr_link: "Albo otwórz ten adres w przeglądarce telefonu lub drugiego komputera:",
    pr_security: "Bez parowania inne urządzenia w sieci widzą tylko tablicę — nie przełączą pytania, nie zobaczą poprawnej odpowiedzi ani obrazu z kamery.",
    pr_reset: "Odłącz wszystkie urządzenia",
    pr_reset_confirm: "Odłączyć wszystkie sparowane urządzenia? Trzeba będzie zeskanować nowy kod.",
    rm_locked_title: "Ten telefon nie jest sparowany",
    rm_bad_key: "Ten kod jest nieaktualny — zeskanuj nowy.",
    rm_locked_1: "Na komputerze nauczyciela otwórz panel QuizScanner.",
    rm_locked_2: "Kliknij „📱 Pilot w telefonie”.",
    rm_locked_3: "Zeskanuj kod QR aparatem tego telefonu.",
    rm_open_board: "Otwórz tablicę (tylko podgląd) →",
    rm_more: "Quiz i klasa",
    rm_quiz: "Quiz",
    rm_full_panel: "Pełny panel",
    rm_restart: "⟲ Zagraj od nowa",
    rm_missing: "Bez odpowiedzi ({n})",

    // --- losowanie ucznia ---
    dr_button: "🎲 Losuj ucznia",
    dr_left: "zostało do wylosowania: {n}",
    dr_empty: "Lista uczniów tej klasy jest pusta.",
    dr_kicker: "Odpowiada",
    dr_speak_label: "Czytaj wylosowane imię",
    dr_speak_sub: "Tablica wypowiada imię głosem zainstalowanym w systemie — bez internetu.",

    // --- klasy ---
    cl_label: "Klasa",
    cl_classes: "Klasy",
    cl_new: "+ Nowa klasa",
    cl_name: "Nazwa klasy",
    cl_delete: "🗑 Usuń klasę",
    cl_active: "Klasa, z którą toczy się gra",
    cl_name_needed: "Podaj nazwę klasy.",
    cl_exists: "Klasa o tej nazwie już istnieje.",
    cl_confirm_delete: "Usunąć klasę {name}?",
    cl_confirm_switch: "Zmiana klasy zaczyna grę od nowa (punkty zostaną wyzerowane). Kontynuować?",
    cl_last: "Nie można usunąć ostatniej klasy.",
    cl_save_first: "Najpierw zapisz klasę.",

    // --- wznowienie ---
    rs_restored: "Wznowiono przerwaną grę (zapis z {time}) — punkty i pytanie są takie jak przed zamknięciem.",
    rs_new_game: "Zacznij od nowa",

    // --- tablica: pasek ---
    bc_smaller: "Mniejszy tekst (−)",
    bc_bigger: "Większy tekst (+)",
    bc_goto: "Przejdź do pytania",
    bc_fullscreen: "Pełny ekran (F)",

    // --- import ---
    wi_button: "📄 Wczytaj z Worda / tekstu",
    wi_hint: "Pytania „1.”, odpowiedzi „A.”–„D.”, poprawna: „Odpowiedź: B”.",
    wi_template: "Pobierz szablon .docx",
    wi_failed: "Nie udało się wczytać pliku:",
    wi_done: "Wczytano pytań: {n}. Sprawdź je i kliknij „Zapisz”.",
    ri_button: "📥 Wczytaj z pliku (CSV/Excel)",
    ri_hint: "Eksport z dziennika albo arkusz: imię i nazwisko w wierszu, numer karty opcjonalnie.",
    ri_export: "⬇ Zapisz listę do CSV",
    ri_failed: "Nie udało się wczytać listy:",
    ri_done: "Wczytano uczniów: {n}. Sprawdź listę i kliknij „Zapisz listę”.",
  },

  en: {
    app_name: "QuizScanner",
    lang_label: "Language",
    yes: "Yes", no: "No",
    save: "Save", cancel: "Cancel", delete: "Delete", close: "Close",
    theme_label: "Colour theme",
    theme_dark: "🌙 Dark", theme_light: "☀️ Light", theme_ocean: "🌊 Ocean",
    theme_forest: "🌲 Forest", theme_sunset: "🌅 Sunset",
    theme_candy: "🍬 Candy", theme_contrast: "◐ High contrast",

    t_load: "Load",
    t_editor: "✏️ Editor",
    t_board: "📺 Board",
    t_no_quizzes: "— no quizzes, use the editor —",
    t_lan_board: "Board on network",
    t_cam_title: "Camera preview (scanner)",
    t_cam_hint: "Students turn their chosen letter to the top.",
    t_cam_wait: "⏳ Camera is starting or unavailable (check the source).",
    t_cam_source: "Video source",
    t_cam_apply: "Switch",
    t_cam_source_hint: "Camera number (0, 1, 2…) or a phone address, e.g. http://192.168.1.50:8080/video",
    t_phone_help: "📱 How to connect a phone?",
    t_question_of: "Question {n} / {total}",
    t_start: "▶ Start question",
    t_reveal: "✓ Show result",
    t_prev: "◀ Previous",
    t_next: "Next ▶",
    t_reset: "⟲ Reset points",
    t_stat_time: "Time",
    t_stat_answered: "Answered",
    t_stat_dist: "A/B/C/D",
    t_speed_label: "Points for speed",
    t_speed_sub: "Off = every correct answer is worth the same. On = faster earns more.",
    t_auto_label: "Automatic mode",
    t_auto_sub: "After the start the quiz reveals results and advances on its own — no clicking.",
    t_auto_running: "Automatic mode is running — the quiz drives itself.",
    t_students_live: "Live student answers",
    t_col_id: "ID", t_col_student: "Student", t_col_answer: "Answer", t_col_points: "Points",
    t_no_answers: "No answers yet",
    t_ranking: "Leaderboard",
    t_no_results: "No results",
    t_load_quiz_first: "Load a quiz to begin.",
    t_confirm_reset: "Reset all points and start over?",
    t_only_known: "Only students on the list",
    t_only_known_sub: "Ignores codes outside the list — protects against accidental detections in the background.",
    t_sound_label: "Board sounds",
    t_sound_sub: "Cues for question start, countdown, reveal and podium on the projector screen.",
    t_volume: "Volume",
    t_auto_report_label: "Automatic report",
    t_auto_report_sub: "After the last question the report is saved to the reports folder on its own.",

    t_report: "📊 Report",
    r_title: "Quiz report",
    r_download: "Download as",
    r_save_now: "💾 Save to disk",
    r_saved_to: "Saved in:",
    r_open_folder: "Reports folder:",
    r_recent: "Recently saved",
    r_no_recent: "No saved reports yet",
    r_empty: "Play at least one question to get a report.",
    r_stat_students: "Students",
    r_stat_questions: "Questions",
    r_stat_avg: "Average correct",
    r_stat_best: "Top score",
    r_hardest: "Hardest question",
    r_col_place: "#", r_col_student: "Student", r_col_points: "Points",
    r_col_correct: "Correct", r_col_percent: "Accuracy",
    r_fmt_pdf: "PDF", r_fmt_csv: "CSV", r_fmt_xlsx: "Excel",
    r_fmt_html: "HTML", r_fmt_json: "JSON", r_fmt_txt: "TXT",

    u_available: "New version {version} is available (you have {current}).",
    u_update_now: "⬇ Update now",
    u_open_page: "Open release page",
    u_downloading: "Downloading update…",
    u_ready: "Update downloaded — close the app to finish the swap.",
    u_failed: "Could not download the update.",
    u_source_hint: "Running from source — update with git pull.",
    u_check_label: "Check for updates",
    u_check_sub: "Asks GitHub once per launch whether a newer release exists.",
    u_up_to_date: "You are on the latest version.",

    b_question_of: "Question {n} of {total}",
    b_scanned: "Scanned:",
    b_correct: "Correct:",
    b_prepare: "Get your card ready — turn your letter (A/B/C/D) to the top",
    b_ready: "Ready to start",
    b_load_hint: "Load a quiz in the teacher panel",
    b_end_kicker: "Quiz finished",
    b_standings: "Final standings",
    b_no_results: "No results",
    b_sound_locked: "🔇 Click the screen to enable sounds",

    mb_title: "Maths toolbox",
    mb_hide: "Collapse", mb_show: "Expand",
    mb_basic: "Basics", mb_powers: "Powers & fractions", mb_greek: "Greek",
    mb_sets: "Sets & logic", mb_geo: "Geometry", mb_calc: "Calculus",
    mb_tpl_frac: "a/b", mb_tpl_sqrt: "√( )", mb_tpl_pow: "x²",
    mb_tpl_index: "x₁", mb_tpl_interval: "interval",
    mb_to_sup: "Selection → superscript",
    mb_to_sub: "Selection → subscript",
    mb_hint: "Click a question or answer field, then a symbol. A selected fragment goes inside the template.",
    mb_preview: "Field preview",
    mb_preview_empty: "Click a question or answer field — you will see here how it looks on the board.",

    mb_tex_title: "LaTeX",
    mb_tex_inline: "Inline formula: $ … $",
    mb_tex_frac: "Stacked fraction",
    mb_tex_sqrt: "Square root",
    mb_tex_root: "n-th root",
    mb_tex_pow: "Power (any exponent)",
    mb_tex_sub: "Subscript",
    mb_tex_int: "Definite integral",
    mb_tex_sum: "Sum with limits",
    mb_tex_lim: "Limit",
    mb_tex_binom: "Binomial coefficient",
    mb_tex_bar: "Bar over a symbol (mean)",
    mb_tex_vec: "Vector",
    mb_tex_cases: "System of equations",
    mb_tex_matrix: "Matrix",
    mb_tex_block: "Centred formula: $$ … $$",

    e_title: "QuizScanner · Editor",
    e_tab_quiz: "Quizzes",
    e_tab_roster: "Students",
    e_tab_settings: "Settings",
    e_to_teacher: "← Teacher panel",
    e_quizzes: "Quizzes",
    e_new_quiz: "+ New quiz",
    e_no_quizzes: "No quizzes — create one",
    e_quiz_title: "Quiz title",
    e_quiz_title_ph: "e.g. History revision",
    e_save: "💾 Save",
    e_duplicate: "⧉ Duplicate",
    e_delete: "🗑 Delete",
    e_export_file: "⬇ Save to file",
    e_import_file: "⬆ Load from file",
    e_file_hint: "You can send a .quiz file to another teacher.",
    e_editing_file: "file:",
    e_unsaved: "(new, unsaved)",
    e_question_n: "Question {n}",
    e_question_ph: "Question text…",
    e_answer_ph: "Answer {letter}",
    e_correct: "correct",
    e_time_s: "Time (s)",
    e_points: "Points (max)",
    e_add_question: "+ Add question",
    e_media: "Image / video",
    e_media_add: "🖼 Add file",
    e_media_remove: "✕ Remove file",
    e_media_hint: "Image (JPG/PNG/GIF/WEBP) or video (MP4/WEBM) — shown on the board with the question.",
    e_media_too_big: "File is too large (limit {mb} MB).",
    e_media_bad_type: "Unsupported file type.",
    e_roster_hint: "ID = marker number on the printed card.",
    e_save_roster: "💾 Save list",
    e_add_student: "+ Add student",
    e_cards_pdf: "📄 Download cards (PDF)",
    e_cards_hint: "Printable cards for the list above — one per A4 page.",
    e_col_id: "ID", e_col_name: "Full name",
    e_saved: "Saved:",
    e_copy_made: "Copy created:",
    e_deleted: "Deleted",
    e_roster_saved: "Student list saved",
    e_add_students_first: "Add students first",
    e_generating_pdf: "Generating cards PDF…",
    e_confirm_delete: "Delete quiz {name}?",
    e_imported: "Quiz loaded from file",
    e_import_failed: "Could not read the file — is it a quiz file?",

    s_quiz_settings: "Quiz settings",
    s_default_time: "Default question time (s)",
    s_default_points: "Default points",
    s_apply_all: "Apply to all questions",
    s_shuffle_q: "Shuffle question order",
    s_shuffle_a: "Shuffle answer order",
    s_show_dist: "Show answer distribution on reveal",
    s_auto_reveal_s: "Auto: result display time (s)",
    s_auto_gap_s: "Auto: pause before next question (s)",
    s_applied: "Applied to all questions",
    s_app_settings: "Application settings",

    // --- question phases ---
    ph_idle: "getting ready", ph_question: "collecting", ph_reveal: "result", ph_podium: "finished",

    // --- phone remote ---
    pr_button: "📱 Phone remote",
    pr_title: "Phone remote",
    pr_intro: "Scan the code with the camera of a phone on the same Wi-Fi network. The phone remembers the pairing.",
    pr_network: "Network",
    pr_link: "Or open this address in the browser of a phone or another computer:",
    pr_security: "Without pairing, other devices on the network only see the board — they cannot change the question, see the correct answer or the camera image.",
    pr_reset: "Disconnect all devices",
    pr_reset_confirm: "Disconnect all paired devices? A new code will have to be scanned.",
    rm_locked_title: "This phone is not paired",
    rm_bad_key: "This code is out of date — scan a new one.",
    rm_locked_1: "Open the QuizScanner panel on the teacher's computer.",
    rm_locked_2: "Click “📱 Phone remote”.",
    rm_locked_3: "Scan the QR code with this phone's camera.",
    rm_open_board: "Open the board (view only) →",
    rm_more: "Quiz and class",
    rm_quiz: "Quiz",
    rm_full_panel: "Full panel",
    rm_restart: "⟲ Play again",
    rm_missing: "No answer yet ({n})",

    // --- student draw ---
    dr_button: "🎲 Pick a student",
    dr_left: "left to pick: {n}",
    dr_empty: "This class has no students on the list.",
    dr_kicker: "Your turn",
    dr_speak_label: "Read the picked name aloud",
    dr_speak_sub: "The board says the name with a voice installed in the system — no internet needed.",

    // --- classes ---
    cl_label: "Class",
    cl_classes: "Classes",
    cl_new: "+ New class",
    cl_name: "Class name",
    cl_delete: "🗑 Delete class",
    cl_active: "Class the game is played with",
    cl_name_needed: "Enter a class name.",
    cl_exists: "A class with this name already exists.",
    cl_confirm_delete: "Delete class {name}?",
    cl_confirm_switch: "Switching the class starts the game over (points are reset). Continue?",
    cl_last: "The last class cannot be deleted.",
    cl_save_first: "Save the class first.",

    // --- resume ---
    rs_restored: "Resumed an interrupted game (saved at {time}) — points and question are as before closing.",
    rs_new_game: "Start over",

    // --- board bar ---
    bc_smaller: "Smaller text (−)",
    bc_bigger: "Bigger text (+)",
    bc_goto: "Go to question",
    bc_fullscreen: "Full screen (F)",

    // --- import ---
    wi_button: "📄 Import from Word / text",
    wi_hint: "Questions “1.”, answers “A.”–“D.”, correct one: “Answer: B”.",
    wi_template: "Download .docx template",
    wi_failed: "Could not read the file:",
    wi_done: "Questions imported: {n}. Check them and click “Save”.",
    ri_button: "📥 Import from file (CSV/Excel)",
    ri_hint: "Gradebook export or spreadsheet: a name per row, card number optional.",
    ri_export: "⬇ Save list as CSV",
    ri_failed: "Could not read the list:",
    ri_done: "Students imported: {n}. Check the list and click “Save list”.",
  },
};

let LANG = "pl";

function t(key, vars) {
  const table = I18N[LANG] || I18N.pl;
  let s = table[key];
  if (s === undefined) s = (I18N.pl[key] !== undefined ? I18N.pl[key] : key);
  if (vars) for (const k in vars) s = s.replaceAll("{" + k + "}", vars[k]);
  return s;
}

function setLang(lang) {
  LANG = I18N[lang] ? lang : "pl";
  document.documentElement.lang = LANG;
  applyI18n();
}

// Podmienia teksty w elementach oznaczonych atrybutami data-i18n*.
function applyI18n(root) {
  (root || document).querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  (root || document).querySelectorAll("[data-i18n-ph]").forEach(el => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  (root || document).querySelectorAll("[data-i18n-title]").forEach(el => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.dispatchEvent(new CustomEvent("i18n:changed"));
}

// ---------- motyw kolorystyczny ----------
// Nazwy muszą zgadzać się z selektorami [data-theme] w themes.css.
const THEMES = ["dark", "light", "ocean", "forest", "sunset", "candy", "contrast"];

function setTheme(name) {
  const theme = THEMES.includes(name) ? name : "dark";
  if (document.documentElement.dataset.theme !== theme)
    document.documentElement.dataset.theme = theme;
}

// Wypełnia <select> listą motywów (nazwy tłumaczone jak reszta interfejsu).
function fillThemeSelect(el) {
  if (!el) return;
  const current = el.value || document.documentElement.dataset.theme || "dark";
  el.innerHTML = THEMES.map(
    name => `<option value="${name}">${t("theme_" + name)}</option>`).join("");
  el.value = current;
}

// Jedno miejsce, w którym ustawienia z serwera trafiają do interfejsu.
// Wywołują to zarówno panel i edytor (raz przy starcie), jak i tablica
// (co kilka sekund — dzięki temu zmiana motywu od razu widać na rzutniku).
let i18nApplied = false;   // pierwsze wywołanie musi podmienić teksty w HTML

function applyServerSettings(s) {
  s = s || {};
  const lang = s.lang || "pl";
  if (!i18nApplied || lang !== LANG) { setLang(lang); i18nApplied = true; }
  setTheme(s.theme);
  if (typeof Sound !== "undefined") Sound.configure(s);
  return s;
}

// Pobiera wspólne ustawienia z serwera (język, motyw, dźwięk) i stosuje je.
async function initLang() {
  try {
    return applyServerSettings(await (await fetch("/api/settings")).json());
  } catch (e) { setLang("pl"); i18nApplied = true; return {}; }
}
