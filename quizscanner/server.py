"""
Serwer aplikacji QuizScanner (biblioteka standardowa Pythona, bez Flask).

Uruchamia:
  - wątek kamery (skaner ArUco),
  - serwer HTTP z panelem nauczyciela, tablica i edytorem.

Użycie:
  python -m quizscanner                 # kamera 0, port 8000, otwiera przeglądarkę
  python -m quizscanner --camera 1 --port 8000 --no-browser

Adresy:
  Panel nauczyciela : http://localhost:PORT/teacher
  Tablica (rzutnik) : http://localhost:PORT/board
  Edytor pytań      : http://localhost:PORT/editor
  Tablica w sieci   : http://<IP-w-LAN>:PORT/board
"""

import argparse
import json
import os
import re
import socket
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import VERSION
from . import report as report_mod
from . import updater
from .paths import (DATA_DIR, MEDIA_DIR, QUIZ_DIR, REPORT_DIR, ROSTER_JSON,
                    SETTINGS_JSON, STUDENTS_CSV, WEB_DIR, ascii_pl, seed_data)
from .session import QuizSession, PHASE_IDLE
from .camera import CameraScanner

# Ustawienia aplikacji (zapisywane w folderze danych).
DEFAULT_SETTINGS = {
    "lang": "pl",          # język interfejsu: pl / en
    "camera": "0",         # numer kamery albo adres strumienia (telefon)
    "mirror": True,        # lustro w podglądzie (nie wpływa na rozpoznawanie)
    "only_known": True,    # akceptuj tylko ID z listy uczniów
    "theme": "dark",       # motyw kolorystyczny interfejsu i tablicy
    "sound": True,         # dźwięki tablicy
    "volume": 0.6,         # głośność dźwięków (0..1)
    "auto_report": True,   # zapisuj raport automatycznie po zakończeniu quizu
    "check_updates": True,  # sprawdzaj nowe wydania na GitHubie
}
settings = dict(DEFAULT_SETTINGS)


def load_settings():
    global settings
    data = dict(DEFAULT_SETTINGS)
    try:
        if os.path.exists(SETTINGS_JSON):
            with open(SETTINGS_JSON, encoding="utf-8") as f:
                data.update(json.load(f))
    except Exception:
        pass
    settings = data
    return settings


def save_settings():
    try:
        with open(SETTINGS_JSON, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


session = QuizSession()
scanner = None       # ustawiany przy starcie serwera
pending_swap = None  # skrypt podmiany pliku po pobraniu aktualizacji

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp",
    ".mp4": "video/mp4", ".webm": "video/webm", ".ogg": "video/ogg",
    # Czcionki KaTeX (web/vendor/katex/fonts).
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf",
}

# Dozwolone typy plików dodawanych do pytań.
MEDIA_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp",
    "video/mp4": ".mp4", "video/webm": ".webm",
}
MEDIA_MAX_MB = 40


# --------------------------- pomocnicze ---------------------------
def safe_name(name):
    """Sanityzuje nazwę pliku quizu (bez ścieżek).

    Polskie znaki najpierw transliterujemy, więc „próba" daje plik „proba",
    a nie okaleczone „prba".
    """
    return re.sub(r"[^A-Za-z0-9_\- ]", "", ascii_pl(name)).strip() or "quiz"


def list_quizzes():
    if not os.path.isdir(QUIZ_DIR):
        return []
    out = []
    for f in sorted(os.listdir(QUIZ_DIR)):
        if f.endswith(".json"):
            out.append(f[:-5])
    return out


def read_quiz(name):
    path = os.path.join(QUIZ_DIR, safe_name(name) + ".json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_quiz(name, quiz):
    os.makedirs(QUIZ_DIR, exist_ok=True)
    path = os.path.join(QUIZ_DIR, safe_name(name) + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(quiz, f, ensure_ascii=False, indent=2)


def delete_quiz(name):
    path = os.path.join(QUIZ_DIR, safe_name(name) + ".json")
    if os.path.exists(path):
        os.remove(path)


def load_roster():
    """Roster z roster.json, a jeśli brak -- ze students.csv."""
    if os.path.exists(ROSTER_JSON):
        with open(ROSTER_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}
    roster = {}
    if os.path.exists(STUDENTS_CSV):
        import csv
        with open(STUDENTS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].strip().isdigit():
                    roster[int(row[0])] = row[1].strip()
    return roster


def save_roster(roster):
    with open(ROSTER_JSON, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in roster.items()}, f, ensure_ascii=False, indent=2)


def placeholder_jpeg(text):
    """Statyczny kadr JPEG (gdy nie ma kamery)."""
    import io
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (640, 360), (34, 34, 40))
    d = ImageDraw.Draw(img)
    d.text((210, 168), text, fill=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def export_quiz_bundle(quiz):
    """Buduje samodzielny plik .quiz -- z osadzonymi mediami (base64),
    żeby dało się go wysłać innemu nauczycielowi jako jeden plik."""
    import base64
    bundle = json.loads(json.dumps(quiz))  # kopia
    bundle["format"] = "quizscanner/1"
    media = {}
    for q in bundle.get("questions", []):
        m = q.get("media")
        if not m or not m.get("file"):
            continue
        p = os.path.join(MEDIA_DIR, os.path.basename(m["file"]))
        if os.path.exists(p) and os.path.getsize(p) <= MEDIA_MAX_MB * 1024 * 1024:
            with open(p, "rb") as f:
                media[m["file"]] = base64.b64encode(f.read()).decode("ascii")
    if media:
        bundle["media_data"] = media
    return json.dumps(bundle, ensure_ascii=False, indent=2)


def import_quiz_bundle(bundle):
    """Odwrotność export_quiz_bundle: zapisuje media na dysk i zwraca quiz."""
    import base64
    quiz = json.loads(json.dumps(bundle))
    blobs = quiz.pop("media_data", None) or {}
    quiz.pop("format", None)
    if blobs:
        os.makedirs(MEDIA_DIR, exist_ok=True)
        for fname, b64 in blobs.items():
            safe = os.path.basename(str(fname))
            ext = os.path.splitext(safe)[1].lower()
            if ext not in set(MEDIA_EXT.values()):
                continue
            try:
                data = base64.b64decode(b64)
            except Exception:
                continue
            if len(data) > MEDIA_MAX_MB * 1024 * 1024:
                continue
            with open(os.path.join(MEDIA_DIR, safe), "wb") as f:
                f.write(data)
    return quiz


def save_media(data_url, orig_name=""):
    """Zapisuje plik przesłany jako data:URL. Zwraca (nazwa, typ) albo błąd."""
    import base64
    import hashlib
    if not data_url.startswith("data:"):
        raise ValueError("bad payload")
    head, _, b64 = data_url.partition(",")
    mime = head[5:].split(";")[0].strip().lower()
    ext = MEDIA_EXT.get(mime)
    if not ext:
        raise ValueError("unsupported type")
    raw = base64.b64decode(b64)
    if len(raw) > MEDIA_MAX_MB * 1024 * 1024:
        raise ValueError("too large")
    os.makedirs(MEDIA_DIR, exist_ok=True)
    digest = hashlib.sha1(raw).hexdigest()[:16]
    fname = digest + ext
    with open(os.path.join(MEDIA_DIR, fname), "wb") as f:
        f.write(raw)
    kind = "video" if mime.startswith("video/") else "image"
    return fname, kind


def build_cards_pdf(count=None):
    """Tworzy w pamięci PDF z kartami ArUco (jedna karta na stronę A4).
    Domyślnie karty dla aktualnej listy uczniów; jeśli lista pusta lub podano
    count -- karty o numerach 0..count-1."""
    import io
    import cv2
    from PIL import Image
    from .aruco import get_dictionary
    from .cards import make_card

    dictionary = get_dictionary()
    with session.lock:
        roster = dict(session.roster)

    if roster and not count:
        ids = sorted(roster)
    else:
        ids = list(range(count or 30))

    W, H = 1165, 1653              # ~A5 przy 200 DPI
    marker_px = int(min(W, H) * 0.55)
    pages = []
    for mid in ids:
        card = make_card(mid, roster.get(mid, ""), dictionary, (W, H), marker_px)
        pages.append(Image.fromarray(cv2.cvtColor(card, cv2.COLOR_BGR2RGB)))

    buf = io.BytesIO()
    if pages:
        pages[0].save(buf, format="PDF", save_all=True,
                      append_images=pages[1:], resolution=200.0)
    return buf.getvalue()


AUTOSAVE_FORMATS = ("html", "csv", "json")


def save_report(formats=AUTOSAVE_FORMATS):
    """Zapisuje raport z bieżącej rozgrywki do folderu raportów."""
    return report_mod.save(report_mod.build(session), REPORT_DIR, formats)


def autosave_report(_session=None):
    """Wywoływane automatycznie, gdy quiz dobiegnie końca (podium)."""
    if not settings.get("auto_report", True):
        return []
    with session.lock:
        if not session.history:
            return []          # nic nie rozegrano -- nie ma czego zapisywać
    return save_report()


# --------------------------- handler ---------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "QuizScanner"
    # HTTP/1.1 = trwałe połączenia. Bez tego każde zapytanie zrywa połączenie,
    # co bardzo spowalnia odpytywanie stanu przez panel i tablice.
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass  # cisza w konsoli

    # ---- odpowiedzi ----
    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        if not os.path.isfile(path):
            self.send_error(404, "Nie znaleziono")
            return
        ext = os.path.splitext(path)[1].lower()
        ctype = CONTENT_TYPES.get(ext, "application/octet-stream")
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ---- MJPEG ----
    def stream_mjpeg(self):
        if scanner is None:
            # Tryb bez kamery -- pojedynczy statyczny kadr zastępczy.
            jpg = placeholder_jpeg("Tryb bez kamery")
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpg)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(jpg)
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        # Strumień nie ma Content-Length -- musi zamykać połączenie na koniec.
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()
        try:
            while True:
                jpg = scanner.get_jpeg() if scanner else None
                if jpg:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(("Content-Length: %d\r\n\r\n" % len(jpg)).encode())
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
                time.sleep(0.04)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    # ---- GET ----
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            return self.redirect("/teacher")
        if path == "/teacher":
            return self.send_file(os.path.join(WEB_DIR, "teacher.html"))
        if path == "/board":
            return self.send_file(os.path.join(WEB_DIR, "board.html"))
        if path == "/editor":
            return self.send_file(os.path.join(WEB_DIR, "editor.html"))
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            rel = os.path.normpath(rel).replace("\\", "/")
            if rel.startswith(".."):
                return self.send_error(403)
            return self.send_file(os.path.join(WEB_DIR, rel))
        if path == "/video_feed":
            return self.stream_mjpeg()

        if path == "/api/report":
            fmt = (query.get("format", ["pdf"])[0] or "pdf").lower()
            try:
                blob, ctype, fname = report_mod.render(report_mod.build(session), fmt)
            except ValueError:
                return self.send_error(400, "Nieznany format raportu")
            except Exception as e:
                return self.send_error(500, f"Błąd raportu: {e}")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Disposition",
                             f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(blob)
            return
        if path == "/api/report/preview":
            data = report_mod.build(session)
            return self.send_json({
                "summary": data["summary"], "questions": data["questions"],
                "students": data["students"], "quiz_title": data["quiz_title"],
                "formats": report_mod.FORMATS,
                "dir": REPORT_DIR,
                "saved": report_mod.list_saved(REPORT_DIR),
            })
        if path == "/api/update":
            force = query.get("force", ["0"])[0] == "1"
            if not settings.get("check_updates", True) and not force:
                return self.send_json({"current": VERSION, "update": False,
                                       "disabled": True})
            return self.send_json(updater.check(force=force))

        if path == "/api/cards.pdf":
            c = query.get("count", [None])[0]
            c = int(c) if (c and c.isdigit()) else None
            try:
                pdf = build_cards_pdf(count=c)
            except Exception as e:
                return self.send_error(500, f"Błąd generowania kart: {e}")
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition",
                             'attachment; filename="karty_QuizScanner.pdf"')
            self.send_header("Content-Length", str(len(pdf)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(pdf)
            return

        # API
        if path == "/api/state":
            full = query.get("full", ["0"])[0] == "1"
            st = session.state(full=full)
            if full:
                st["camera_ok"] = bool(scanner and scanner.camera_ok)
            return self.send_json(st)
        if path == "/api/quizzes":
            active = session.quiz_name
            return self.send_json({"quizzes": list_quizzes(), "active": active})
        if path == "/api/quiz":
            name = query.get("name", [""])[0]
            try:
                return self.send_json(read_quiz(name))
            except FileNotFoundError:
                return self.send_error(404, "Brak quizu")
        if path == "/api/roster":
            return self.send_json(load_roster())
        if path == "/api/settings":
            return self.send_json(settings)
        if path.startswith("/media/"):
            fn = os.path.basename(path[len("/media/"):])
            return self.send_file(os.path.join(MEDIA_DIR, fn))
        if path == "/api/quiz/export":
            name = query.get("name", [""])[0]
            try:
                quiz = read_quiz(name)
            except FileNotFoundError:
                return self.send_error(404, "Brak quizu")
            body = export_quiz_bundle(quiz).encode("utf-8")
            fname = safe_name(name) + ".quiz"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/meta":
            return self.send_json({
                "lan_ip": lan_ip(),
                "port": self.server.server_address[1],
                "camera_ok": bool(scanner and scanner.camera_ok),
                "version": VERSION,
                "report_dir": REPORT_DIR,
                "data_dir": DATA_DIR,
            })

        return self.send_error(404, "Nie znaleziono")

    # ---- POST ----
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self.read_json_body()

        if path == "/api/control":
            action = data.get("action")
            if action == "start":
                session.start_question()
            elif action == "reveal":
                session.reveal()
            elif action == "next":
                session.next_question()
            elif action == "prev":
                session.prev_question()
            elif action == "goto":
                session.goto(int(data.get("index", 0)))
            elif action == "reset":
                session.reset_scores()
            elif action == "speed_bonus":
                session.set_speed_bonus(data.get("value", False))
            elif action == "auto_mode":
                session.set_auto_mode(data.get("value", False))
                if data.get("value") and session.phase == PHASE_IDLE:
                    session.start_question()   # tryb auto rusza od razu
            return self.send_json({"ok": True, "state": session.state(full=True)})

        if path == "/api/quiz":
            name = safe_name(data.get("name", ""))
            quiz = data.get("quiz", {})
            write_quiz(name, quiz)
            return self.send_json({"ok": True, "name": name})

        if path == "/api/quiz/delete":
            delete_quiz(data.get("name", ""))
            return self.send_json({"ok": True})

        if path == "/api/load":
            name = data.get("name", "")
            try:
                quiz = read_quiz(name)
            except FileNotFoundError:
                return self.send_error(404, "Brak quizu")
            session.load_quiz(quiz, safe_name(name))
            return self.send_json({"ok": True, "state": session.state(full=True)})

        if path == "/api/roster":
            roster = {int(k): v for k, v in data.items()}
            save_roster(roster)
            session.set_roster(roster)
            return self.send_json({"ok": True})

        if path == "/api/export":
            fmts = data.get("formats") or list(AUTOSAVE_FORMATS)
            fmts = [f for f in fmts if f in report_mod.RENDERERS]
            paths = save_report(fmts or AUTOSAVE_FORMATS)
            return self.send_json({"ok": bool(paths), "paths": paths,
                                   "dir": REPORT_DIR})

        if path == "/api/update/apply":
            res = updater.apply()
            if res.get("script"):
                global pending_swap
                pending_swap = res["script"]
            return self.send_json(res)

        if path == "/api/settings":
            changed_cam = ("camera" in data and
                           str(data["camera"]) != str(settings.get("camera")))
            for k in DEFAULT_SETTINGS:
                if k in data:
                    settings[k] = data[k]
            save_settings()
            apply_settings()
            if changed_cam:
                restart_camera()
            return self.send_json({"ok": True, "settings": settings})

        if path == "/api/media":
            try:
                fname, kind = save_media(data.get("data", ""), data.get("name", ""))
            except ValueError as e:
                return self.send_json({"ok": False, "error": str(e)}, code=400)
            return self.send_json({"ok": True, "file": fname, "type": kind})

        if path == "/api/quiz/import":
            bundle = data.get("quiz")
            name = safe_name(data.get("name", "") or (bundle or {}).get("title", ""))
            if not isinstance(bundle, dict) or "questions" not in bundle:
                return self.send_json({"ok": False}, code=400)
            quiz = import_quiz_bundle(bundle)
            write_quiz(name, quiz)
            return self.send_json({"ok": True, "name": name})

        return self.send_error(404, "Nie znaleziono")


def apply_settings():
    """Przenosi ustawienia do działających obiektów (sesja, skaner)."""
    session.set_only_known(bool(settings.get("only_known", True)))
    if scanner:
        scanner.mirror = bool(settings.get("mirror", True))
        scanner.only_known = bool(settings.get("only_known", True))


def restart_camera():
    """Zatrzymuje obecny wątek kamery i uruchamia nowy z aktualnym źródłem."""
    global scanner
    if scanner:
        scanner.stop()
        scanner = None
    scanner = CameraScanner(session, camera=settings.get("camera", "0"),
                            mirror=bool(settings.get("mirror", True)),
                            only_known=bool(settings.get("only_known", True)))
    scanner.start()


def build_server(camera=None, port=8000, host="0.0.0.0", no_camera=False):
    """Przygotowuje sesje, wątek kamery i serwer HTTP. Zwraca obiekt httpd
    (jeszcze nie wystartowany). Używane zarówno przez CLI (main), jak i przez
    launcher uruchamiający serwer w tym samym procesie (działa w .exe)."""
    global scanner

    seed_data()
    load_settings()
    if camera is not None:          # jawny wybór z linii poleceń ma pierwszeństwo
        settings["camera"] = str(camera)
    session.set_roster(load_roster())
    session.set_only_known(bool(settings.get("only_known", True)))
    session.on_podium = autosave_report
    session.start_auto_engine()
    updater.check_async(bool(settings.get("check_updates", True)))

    quizzes = list_quizzes()
    if quizzes:
        try:
            session.load_quiz(read_quiz(quizzes[0]), quizzes[0])
        except Exception:
            pass

    if not no_camera:
        scanner = CameraScanner(session, camera=settings.get("camera", "0"),
                                mirror=bool(settings.get("mirror", True)),
                                only_known=bool(settings.get("only_known", True)))
        scanner.start()

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd


def stop_server(httpd):
    """Zatrzymuje serwer, wątek kamery i silnik trybu automatycznego."""
    global scanner
    if scanner:
        scanner.stop()
        scanner = None
    session.stop_auto_engine()
    if httpd:
        httpd.shutdown()
    # Pobrana aktualizacja czeka na wymianę pliku -- teraz program już nie działa.
    if pending_swap:
        updater.run_swap_script(pending_swap)


def _utf8_console():
    """Konsola Windows bywa ustawiona na stronę kodową bez polskich znaków.
    Przełączamy strumienie na UTF-8, żeby komunikaty nie wywracały programu."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    _utf8_console()
    ap = argparse.ArgumentParser(description="Serwer QuizScanner")
    ap.add_argument("--camera", default=None,
                    help="Numer kamery (0, 1, ...) albo adres strumienia "
                         "z telefonu, np. http://192.168.1.50:8080/video")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-camera", action="store_true",
                    help="Uruchom bez kamery (np. do edycji quizów).")
    args = ap.parse_args()

    httpd = build_server(camera=args.camera, port=args.port,
                         host=args.host, no_camera=args.no_camera)

    ip = lan_ip()
    if sys.stdout:  # w trybie bezokienkowym (.exe) stdout może być None
        print("=" * 58)
        print(f"  QuizScanner {VERSION} uruchomiony")
        print(f"  Panel nauczyciela : http://localhost:{args.port}/teacher")
        print(f"  Tablica (rzutnik) : http://localhost:{args.port}/board")
        print(f"  Edytor pytań      : http://localhost:{args.port}/editor")
        print(f"  Tablica w sieci   : http://{ip}:{args.port}/board")
        print("=" * 58)
        print("  Zatrzymanie: Ctrl+C")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(
            f"http://localhost:{args.port}/teacher")).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nZatrzymywanie...")
    finally:
        stop_server(httpd)


if __name__ == "__main__":
    main()
