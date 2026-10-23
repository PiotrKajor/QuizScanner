"""
Szybkie sprawdzenie, czy wszystko działa — startuje serwer bez kamery
i przechodzi przez aplikację tak, jak zrobiłby to nauczyciel.

    python tools/selftest.py

Sprawdza: strony i zasoby (w tym KaTeX), API stanu, karty PDF, przebieg quizu
(start → wynik → podium), automatyczny zapis raportu, każdy format eksportu,
zamianę wzorów LaTeX na tekst, kompletność tłumaczeń PL/EN, a od 3.2 także:
import pytań z Worda/tekstu, import listy uczniów (CSV/XLSX), klasy, ochronę
sterowania przed urządzeniami w sieci, parowanie kodem QR, losowanie ucznia,
wznowienie przerwanej gry i poprawkę podwójnego liczenia punktów.
Kończy się kodem 0, gdy wszystko przeszło.

Test pracuje na tymczasowej klasie „_selftest” i po sobie sprząta — lista
uczniów nauczyciela i przerwana gra zostają nietknięte.
"""

import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quizscanner import quiz_import, report, roster_import, server  # noqa: E402
from quizscanner.paths import REPORT_DIR, SESSION_JSON       # noqa: E402
from quizscanner.session import QuizSession                  # noqa: E402

PORT = 8099
BASE = f"http://127.0.0.1:{PORT}"


def get(path, raw=False):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        data = r.read()
    return data if raw else json.loads(data)


def post(path, payload, headers=None):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers=headers or {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def status(path, payload=None, headers=None):
    """Kod odpowiedzi HTTP (bez rzucania wyjątkiem przy 4xx)."""
    req = urllib.request.Request(BASE + path, headers=headers or {},
                                 data=None if payload is None else payload)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def data_url(blob):
    import base64
    return "data:application/octet-stream;base64," + base64.b64encode(blob).decode()


def check_import():
    """Import pytań z Worda i tekstu oraz listy uczniów z CSV i Excela."""
    quiz, warn = quiz_import.import_file("szablon.docx", quiz_import.template_docx())
    assert not warn, warn
    qs = quiz["questions"]
    assert [q["correct"] for q in qs] == [1, 0, 2], qs           # linia / gwiazdka / pogrubienie
    assert qs[1]["time"] == 30 and qs[2]["points"] == 500
    assert qs[0]["answers"][3] == "Poznań"

    txt = ("Kartkówka\n1) Pierwsze\nciąg dalszy\na) x\nb) y\n*c) z\n"
           "2. Drugie\nA. 1\nB. 2\n").encode("cp1250")
    quiz, warn = quiz_import.import_file("k.txt", txt)
    assert quiz["title"] == "Kartkówka"
    assert quiz["questions"][0]["text"] == "Pierwsze\nciąg dalszy"
    assert quiz["questions"][0]["correct"] == 2
    assert len(warn) == 1 and "Pytanie 2" in warn[0], warn       # brak poprawnej

    students, warn = roster_import.import_file(
        "lista.csv", "Nazwisko;Imię\nNowak;Anna\nŁuczak;Jan\n".encode("cp1250"))
    assert students == {0: "Nowak Anna", 1: "Łuczak Jan"}, students
    students, warn = roster_import.import_file("k.csv", b"5,Ala\n7,Ola\n7,Ewa\n300,Ida\n")
    assert students == {5: "Ala", 7: "Ola"} and len(warn) == 2, (students, warn)

    # Arkusz jak z Excela: tekst we wspólnej tabeli, liczba jako 3.0.
    buf = io.BytesIO()
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml",
                   f'<sst {ns}><si><t>Lp</t></si><si><t>Uczeń</t></si>'
                   f'<si><t>Zofia Ząb</t></si></sst>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet {ns}><sheetData>'
                   '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
                   '<row r="2"><c r="A2"><v>3.0</v></c><c r="B2" t="s"><v>2</v></c></row>'
                   '</sheetData></worksheet>')
    students, _ = roster_import.import_file("klasa.xlsx", buf.getvalue())
    assert students == {3: "Zofia Ząb"}, students
    assert roster_import.export_csv({1: "Żaneta"}).startswith("\ufeff".encode("utf-8"))


def check_scoring():
    """Powrót do pytania i ponowny wynik zastępuje punkty, a nie dolicza;
    raport pokazuje też uczniów bez odpowiedzi; migawka odtwarza grę."""
    s = QuizSession()
    s.set_roster({1: "Ala", 2: "Bartek", 3: "Celina"}, "Test")
    q = {"text": "?", "answers": ["a", "b", "c", "d"], "correct": 0, "time": 20, "points": 100}
    s.load_quiz({"title": "t", "questions": [q, q]})
    s.start_question(); s.record_answers({1: "A", 2: "B"}); s.reveal()
    s.prev_question()
    s.start_question(); s.record_answers({1: "A", 2: "A"}); s.reveal()
    assert s.scores == {1: 100, 2: 100}, s.scores
    data = report.build(s)
    assert data["summary"]["students"] == 2 and data["summary"]["absent"] == 1, data["summary"]
    assert data["class_name"] == "Test"

    s2 = QuizSession()
    s2.load_quiz(s.quiz)
    assert s2.restore(json.loads(json.dumps(s.snapshot())))
    assert s2.scores == s.scores and s2.index == s.index

    seen = {s.draw_student()["id"] for _ in range(3)}
    assert seen == {1, 2, 3}, seen                     # bez powtórzeń


def check_tex():
    """Wzory LaTeX muszą dać się zamienić na czytelny tekst — to one trafiają
    do raportu PDF, CSV i arkusza, gdzie nie ma czym renderować."""
    cases = {
        r"Ile wynosi $\frac{1}{2}$ ?": "Ile wynosi (1)/(2) ?",
        r"$\pi r^2$": "π r²",
        r"$\sqrt[3]{27}$": "³√(27)",
        r"$\int_0^1 x\,dx$": "∫₀¹ x dx",           # \in nie może zjeść \int
        r"$H_2O$": "H₂O",
        r"$\mathbb{R} \setminus \{0\}$": "ℝ ∖ {0}",
        r"Cena 20\$": "Cena 20$",                   # dolar bez wzoru zostaje
        "Pytanie bez matematyki": "Pytanie bez matematyki",
    }
    for src, expected in cases.items():
        got = report.tex_to_plain(src)
        assert got == expected, f"{src!r}: {got!r} != {expected!r}"


def check_nazwy_plikow():
    """Tytuły quizów piszemy po polsku, a nazwy plików muszą być ASCII —
    polskie litery transliterujemy, nie wycinamy. Nazwa raportu dodatkowo
    trafia do nagłówka Content-Disposition, który http.server koduje
    w latin-1, więc „ł" w nazwie wywracało pobieranie."""
    for tytul, oczekiwane in {
        "próba": "proba",                       # nie „prba"
        "Ułamki": "Ulamki",
        "Zażółć gęślą jaźń": "Zazolc gesla jazn",
        "../../etc/passwd": "etcpasswd",        # dalej bez wyjścia z katalogu
        "": "quiz",
    }.items():
        got = server.safe_name(tytul)
        assert got == oczekiwane, f"{tytul!r}: {got!r} != {oczekiwane!r}"

    stem = report.file_stem({"quiz_title": "Ułamki próbne"})
    assert stem.startswith("raport_Ulamki_probne_"), stem
    f'attachment; filename="{stem}.pdf"'.encode("latin-1")   # nagłówek HTTP


def check_i18n():
    """Każdy klucz użyty w HTML/JS musi istnieć w obu językach — inaczej
    w interfejsie pojawia się goła nazwa klucza zamiast napisu."""
    import glob
    import re

    web = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "quizscanner", "web")
    src = open(os.path.join(web, "i18n.js"), encoding="utf-8").read()

    def keys(lang):
        block = src.split(f"  {lang}: {{", 1)[1].split("\n  },")[0]
        return set(re.findall(r'(?:^|[{,]\s*)\s*(\w+)\s*:\s*"', block, re.M))

    used = set()
    for path in glob.glob(os.path.join(web, "*.html")):
        used |= set(re.findall(r'data-i18n(?:-ph|-title)?="([^"]+)"',
                               open(path, encoding="utf-8").read()))
    for path in glob.glob(os.path.join(web, "*.js")):
        if path.endswith("i18n.js"):
            continue
        used |= set(re.findall(r'\bt\("(\w+)"', open(path, encoding="utf-8").read()))

    # Klucze składane w locie: t("r_fmt_" + fmt), t("theme_" + name),
    # t("ph_" + faza).
    used.discard("r_fmt_")
    used.discard("theme_")
    used.discard("ph_")
    used |= {"ph_" + p for p in ("idle", "question", "reveal", "podium")}
    used |= {"r_fmt_" + f for f in report.FORMATS}
    used |= {"theme_" + n for n in ("dark", "light", "ocean", "forest",
                                    "sunset", "candy", "contrast")}

    for lang in ("pl", "en"):
        missing = sorted(used - keys(lang))
        assert not missing, f"brak tłumaczeń [{lang}]: {missing}"
    assert keys("pl") == keys("en"), "słowniki pl/en mają różne klucze"


def check_network_access():
    """Urządzenie z sieci bez parowania: tablica tak, sterowanie nie."""
    local = server.Handler.is_local
    server.Handler.is_local = lambda self: False
    try:
        assert status("/board") == 200
        assert status("/remote") == 200
        st = get("/api/state")
        assert "students" not in st
        assert status("/api/state?full=1") == 403
        assert status("/video_feed") == 403
        assert status("/api/report?format=csv") == 403
        assert status("/api/control", b'{"action":"next"}',
                      {"Content-Type": "application/json"}) == 403
        assert get("/api/whoami")["authorized"] is False
        # Zły klucz nie paruje, dobry — zapisuje ciasteczko.
        opener = urllib.request.build_opener(_NoRedirect)
        r = opener.open(BASE + "/pair?k=zly")
        assert r.headers["Location"] == "/remote?bad=1"
        r = opener.open(BASE + "/pair?k=" + server.pair_key)
        cookie = r.headers["Set-Cookie"].split(";")[0]
        assert cookie == "qs_key=" + server.pair_key and "HttpOnly" in r.headers["Set-Cookie"]
        assert status("/api/state?full=1", headers={"Cookie": cookie}) == 200
        assert post("/api/control", {"action": "dismiss_restore"},
                    {"Content-Type": "application/json", "Cookie": cookie})["ok"]
    finally:
        server.Handler.is_local = local
    # Zapis bez JSON-a (np. formularz z obcej strony) jest odrzucany.
    assert status("/api/control", b"action=next", {"Content-Type": "text/plain"}) == 415


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

    def http_error_302(self, req, fp, code, msg, headers):
        return fp


def main():
    check_tex()
    check_nazwy_plikow()
    check_i18n()
    check_import()
    check_scoring()
    try:
        with open(SESSION_JSON, encoding="utf-8") as f:
            saved_session = f.read()
    except OSError:
        saved_session = None
    httpd = server.build_server(port=PORT, no_camera=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.6)
    teacher_class = server.settings.get("class")
    teacher_last_quiz = server.settings.get("last_quiz")
    try:
        # Tymczasowa klasa: test nie nadpisuje listy uczniów nauczyciela.
        r = post("/api/class/save", {"name": "_selftest", "students": {}, "activate": True})
        assert r["ok"] and get("/api/classes")["active"] == "_selftest", r

        # --- strony i zasoby ---
        for path in ("/teacher", "/board", "/editor", "/remote"):
            assert b"QuizScanner" in get(path, raw=True), path
        for path in ("/static/themes.css", "/static/sound.js", "/static/mathbar.js",
                     "/static/remote.js", "/static/remote.css",
                     "/static/tex.js", "/static/vendor/katex/katex.min.js",
                     "/static/vendor/katex/katex.min.css"):
            assert len(get(path, raw=True)) > 100, path
        # Czcionki KaTeX muszą wyjść z właściwym typem, inaczej wzory na
        # tablicy renderują się zastępczym krojem.
        with urllib.request.urlopen(
                BASE + "/static/vendor/katex/fonts/KaTeX_Main-Regular.woff2") as r:
            assert r.headers["Content-Type"] == "font/woff2", r.headers["Content-Type"]
            assert len(r.read()) > 1000

        # --- stan i ustawienia ---
        st = get("/api/state?full=1")
        assert st["phase"] == "idle", st["phase"]
        s = get("/api/settings")
        assert s["theme"] == "dark" and s["sound"] is True, s

        # --- karty do druku ---
        pdf = get("/api/cards.pdf?count=2", raw=True)
        assert pdf[:4] == b"%PDF" and len(pdf) > 5000

        # --- parowanie, import przez HTTP ---
        assert get("/api/pair.png", raw=True)[:8] == b"\x89PNG\r\n\x1a\n"
        assert "/pair?k=" in get("/api/pair")["url"]
        r = post("/api/quiz/parse", {"name": "t.docx",
                                     "data": data_url(quiz_import.template_docx())})
        assert r["ok"] and len(r["quiz"]["questions"]) == 3, r
        assert get("/api/quiz/template.docx", raw=True)[:2] == b"PK"
        r = post("/api/roster/import", {"name": "a.csv", "data": data_url(b"Ala\nOla\n")})
        assert r["students"] == {"0": "Ala", "1": "Ola"}, r

        # --- przebieg quizu ---
        quizzes = get("/api/quizzes")["quizzes"]
        assert quizzes, "brak quizów startowych"
        post("/api/load", {"name": quizzes[0]})
        post("/api/roster", {"1": "Ala Testowa", "2": "Bartek Testowy"})
        assert get("/api/class?id=_selftest")["students"] == {
            "1": "Ala Testowa", "2": "Bartek Testowy"}
        assert get("/api/roster.csv?id=_selftest", raw=True).decode("utf-8-sig").count("\n") == 3
        assert post("/api/control", {"action": "draw"})["ok"]
        assert get("/api/state")["draw"]["name"] in ("Ala Testowa", "Bartek Testowy")
        check_network_access()
        total = get("/api/state")["total"]
        for i in range(total):
            post("/api/control", {"action": "start"})
            # Odpowiedzi normalnie wpisuje wątek kamery.
            server.session.record_answers({1: "A", 2: "B"})
            post("/api/control", {"action": "reveal"})
            if i == 0:
                # Po pierwszym wyniku jest migawka do wznowienia gry.
                snap = json.load(open(SESSION_JSON, encoding="utf-8"))
                assert len(snap["history"]) == 1 and not snap["finished"], snap
            post("/api/control", {"action": "next"})
        assert get("/api/state")["phase"] == "podium"
        assert json.load(open(SESSION_JSON, encoding="utf-8"))["finished"]
        assert not server.try_restore_session()      # skończonej gry nie wznawiamy

        # --- raport ---
        prev = report.build(server.session)
        assert prev["summary"]["questions"] == total, prev["summary"]
        assert prev["summary"]["students"] == 2
        assert len(prev["students"][0]["answers"]) == total

        for fmt in report.FORMATS:
            blob, ctype, name = report.render(prev, fmt)
            assert blob and name.endswith("." + fmt), fmt
            if fmt == "pdf":
                assert blob[:4] == b"%PDF"
            if fmt == "xlsx":
                assert blob[:2] == b"PK"
            # Polskie znaki muszą przetrwać w formatach tekstowych.
            if fmt in ("csv", "html", "json", "txt"):
                assert "ł" in blob.decode("utf-8-sig"), fmt
            # Ten sam format przez HTTP (bajt w bajt się nie porówna --
            # w raporcie siedzi znacznik czasu generowania).
            served = get(f"/api/report?format={fmt}", raw=True)
            assert abs(len(served) - len(blob)) < 2048, fmt

        # --- automatyczny zapis po podium ---
        saved = [f for f in os.listdir(REPORT_DIR)] if os.path.isdir(REPORT_DIR) else []
        assert any(f.endswith(".html") for f in saved), "brak automatycznego raportu"

        prev2 = get("/api/report/preview")
        assert prev2["summary"]["students"] == 2
        assert set(prev2["formats"]) == set(report.FORMATS)

        print("SELFTEST OK — pytania:", total, "· raporty w:", REPORT_DIR)
    finally:
        server.stop_server(httpd)
        # Sprzątanie: klasa nauczyciela wraca, tymczasowa znika.
        server.settings["class"] = teacher_class
        server.settings["last_quiz"] = teacher_last_quiz
        server.save_settings()
        try:
            os.remove(server.class_path("_selftest"))
        except OSError:
            pass
        if saved_session is None:
            try:
                os.remove(SESSION_JSON)
            except OSError:
                pass
        else:
            with open(SESSION_JSON, "w", encoding="utf-8") as f:
                f.write(saved_session)


if __name__ == "__main__":
    main()
