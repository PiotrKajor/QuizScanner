"""Zrzuty ekranu do README (docs/zrzuty/*.png).

Uruchamia serwer w tym samym procesie bez kamery, symuluje lekcję
(przykładowa klasa, odpowiedzi wpisywane tak, jak robi to wątek kamery)
i fotografuje widoki przeglądarką Playwright (Chromium).

    python tools/screenshots.py

Wymaga: pip install playwright && python -m playwright install chromium.
Dane w data/ zostają nietknięte — migawka gry i ustawienia są przywracane.
"""

import os
import shutil
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from playwright.sync_api import sync_playwright        # noqa: E402

from quizscanner import server                         # noqa: E402
from quizscanner.paths import DATA_DIR, SESSION_JSON   # noqa: E402

PORT = 8011
BASE = f"http://127.0.0.1:{PORT}"
OUT = os.path.join(ROOT, "docs", "zrzuty")

KLASA = {
    1: "Anna Nowak", 2: "Piotr Kowalski", 3: "Maria Wiśniewska",
    4: "Jan Wójcik", 5: "Katarzyna Kamińska", 6: "Tomasz Lewandowski",
    7: "Zofia Zielińska", 8: "Michał Szymański", 9: "Julia Woźniak",
    10: "Kacper Dąbrowski", 11: "Natalia Kozłowska", 12: "Szymon Jankowski",
}
# Odpowiedzi klasy na kolejne pytania (numer karty → litera).
ODPOWIEDZI = [
    {1: "B", 2: "B", 3: "B", 4: "A", 5: "B", 6: "C", 7: "B", 8: "B",
     9: "B", 10: "D", 11: "B", 12: "B"},
    {1: "A", 2: "C", 3: "A", 4: "A", 5: "B", 6: "A", 7: "A", 8: "D",
     9: "A", 10: "A", 11: "C", 12: "A"},
]


def main():
    os.makedirs(OUT, exist_ok=True)
    kopie = {}
    for p in (SESSION_JSON, os.path.join(DATA_DIR, "settings.json")):
        kopie[p] = open(p, "rb").read() if os.path.exists(p) else None

    httpd = server.build_server(port=PORT, host="127.0.0.1", no_camera=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    s = server.session
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            desk = br.new_page(viewport={"width": 1440, "height": 900},
                               device_scale_factor=1)
            def fot(page, nazwa, czekaj=1.5):
                # Na tablicy chowamy podpowiedź o dźwiękach i pasek sterowania,
                # które w kadrze tylko zasłaniają treść.
                page.add_style_tag(content="#soundGate,#bctl{display:none!important}")
                time.sleep(czekaj)
                page.screenshot(path=os.path.join(OUT, nazwa + ".png"))

            import urllib.request, json
            def post(path, data):
                req = urllib.request.Request(BASE + path, json.dumps(data).encode(),
                                             {"Content-Type": "application/json"})
                return json.load(urllib.request.urlopen(req))

            post("/api/load", {"name": "przyklad"})
            s.set_roster({str(k): v for k, v in KLASA.items()}, "3b")

            # Pytanie 1 w trakcie: część klasy już odpowiedziała.
            post("/api/control", {"action": "start"})
            s.record_answers({k: v for k, v in ODPOWIEDZI[0].items() if k <= 8})
            desk.goto(BASE + "/board"); fot(desk, "tablica-pytanie")
            desk.goto(BASE + "/teacher"); fot(desk, "panel")

            # Wynik pytania 1.
            s.record_answers(ODPOWIEDZI[0])
            post("/api/control", {"action": "reveal"})
            desk.goto(BASE + "/board"); fot(desk, "tablica-wynik")

            post("/api/control", {"action": "next"})
            post("/api/control", {"action": "start"})
            s.record_answers(ODPOWIEDZI[1])
            post("/api/control", {"action": "reveal"})

            # Pilot w telefonie w trakcie pytania 3.
            post("/api/control", {"action": "next"})
            post("/api/control", {"action": "start"})
            s.record_answers({1: "A", 3: "B", 4: "A", 7: "C", 9: "A"})
            tel = br.new_page(viewport={"width": 390, "height": 844},
                              device_scale_factor=2, is_mobile=True, has_touch=True)
            tel.goto(BASE + "/remote"); fot(tel, "pilot")

            # Koniec gry: podium.
            for i in range(20):
                post("/api/control", {"action": "reveal"})
                post("/api/control", {"action": "next"})
                if s.state()["phase"] == "podium":
                    break
                post("/api/control", {"action": "start"})
                s.record_answers(ODPOWIEDZI[i % 2])
            desk.goto(BASE + "/board"); fot(desk, "tablica-podium", czekaj=5)

            # Edytor z przybornikiem matematycznym.
            desk.goto(BASE + "/editor?quiz=przyklad"); fot(desk, "edytor")
            br.close()
    finally:
        httpd.shutdown()
        s.stop_auto_engine()
        for p, dane in kopie.items():
            if dane is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                open(p, "wb").write(dane)
    print("Zrzuty w", OUT)


if __name__ == "__main__":
    main()
