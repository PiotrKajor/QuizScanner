"""
Szybkie sprawdzenie, czy wszystko działa — startuje serwer bez kamery
i przechodzi przez aplikację tak, jak zrobiłby to nauczyciel.

    python tools/selftest.py

Sprawdza: strony i zasoby (w tym KaTeX), API stanu, karty PDF, przebieg quizu
(start → wynik → podium), automatyczny zapis raportu, każdy format eksportu,
zamianę wzorów LaTeX na tekst oraz kompletność tłumaczeń PL/EN.
Kończy się kodem 0, gdy wszystko przeszło.
"""

import json
import os
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quizscanner import report, server                       # noqa: E402
from quizscanner.paths import REPORT_DIR                     # noqa: E402

PORT = 8099
BASE = f"http://127.0.0.1:{PORT}"


def get(path, raw=False):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        data = r.read()
    return data if raw else json.loads(data)


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


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

    # Klucze składane w locie: t("r_fmt_" + fmt), t("theme_" + name).
    used.discard("r_fmt_")
    used.discard("theme_")
    used |= {"r_fmt_" + f for f in report.FORMATS}
    used |= {"theme_" + n for n in ("dark", "light", "ocean", "forest",
                                    "sunset", "candy", "contrast")}

    for lang in ("pl", "en"):
        missing = sorted(used - keys(lang))
        assert not missing, f"brak tłumaczeń [{lang}]: {missing}"
    assert keys("pl") == keys("en"), "słowniki pl/en mają różne klucze"


def main():
    check_tex()
    check_nazwy_plikow()
    check_i18n()
    httpd = server.build_server(port=PORT, no_camera=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.6)
    try:
        # --- strony i zasoby ---
        for path in ("/teacher", "/board", "/editor"):
            assert b"QuizScanner" in get(path, raw=True), path
        for path in ("/static/themes.css", "/static/sound.js", "/static/mathbar.js",
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

        # --- przebieg quizu ---
        quizzes = get("/api/quizzes")["quizzes"]
        assert quizzes, "brak quizów startowych"
        post("/api/load", {"name": quizzes[0]})
        post("/api/roster", {"1": "Ala Testowa", "2": "Bartek Testowy"})
        total = get("/api/state")["total"]
        for i in range(total):
            post("/api/control", {"action": "start"})
            # Odpowiedzi normalnie wpisuje wątek kamery.
            server.session.record_answers({1: "A", 2: "B"})
            post("/api/control", {"action": "reveal"})
            post("/api/control", {"action": "next"})
        assert get("/api/state")["phase"] == "podium"

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


if __name__ == "__main__":
    main()
