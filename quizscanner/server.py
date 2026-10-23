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
  Pilot (telefon)   : http://<IP-w-LAN>:PORT/remote  (po sparowaniu kodem QR)

Dostęp z sieci: tablica i podgląd stanu są publiczne (tylko do odczytu, bez
poprawnej odpowiedzi przed odsłonięciem). Sterowanie, edycja, raporty
i obraz z kamery działają na komputerze nauczyciela oraz na urządzeniach
sparowanych kodem QR z panelu — uczeń w tej samej sieci Wi-Fi nie przełączy
pytania ani nie podejrzy poprawnej odpowiedzi.
"""

import argparse
import json
import os
import re
import secrets
import socket
import sys
import threading
import time
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import VERSION
from . import quiz_import
from . import report as report_mod
from . import roster_import
from . import updater
from .paths import (CLASS_DIR, DATA_DIR, MEDIA_DIR, PAIR_KEY, QUIZ_DIR,
                    REPORT_DIR, ROSTER_JSON, SESSION_JSON, SETTINGS_JSON,
                    STUDENTS_CSV, WEB_DIR, ascii_pl, seed_data)
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
    "speak_draw": False,   # tablica czyta na głos wylosowane imię (głos systemu)
    "class": "",           # aktywna klasa (nazwa pliku w data/klasy)
    "last_quiz": "",       # ostatnio wczytany quiz — wraca po ponownym starcie
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


def _legacy_roster():
    """Lista sprzed wersji 3.2: roster.json, a jeśli brak -- students.csv."""
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


# --------------------------- klasy ---------------------------
# Każda klasa to osobny plik data/klasy/<id>.json: {"name": "3B", "students":
# {"0": "Anna Nowak", ...}}. Numery kart są w obrębie klasy, więc ten sam
# wydruk kart 0..29 służy każdej klasie. Aktywną klasę pamięta settings["class"].
DEFAULT_CLASS = "Moja klasa"


def class_path(cid):
    return os.path.join(CLASS_DIR, safe_name(cid) + ".json")


def read_class(cid):
    with open(class_path(cid), encoding="utf-8") as f:
        data = json.load(f)
    return {"id": safe_name(cid), "name": data.get("name") or cid,
            "students": {int(k): v for k, v in (data.get("students") or {}).items()}}


def write_class(cid, name, students):
    os.makedirs(CLASS_DIR, exist_ok=True)
    with open(class_path(cid), "w", encoding="utf-8") as f:
        json.dump({"name": name, "students": {str(k): v for k, v in sorted(students.items())}},
                  f, ensure_ascii=False, indent=2)


def list_classes():
    """Klasy posortowane po nazwie; przy pierwszym uruchomieniu wersji 3.2
    dotychczasowa lista uczniów staje się klasą „Moja klasa"."""
    os.makedirs(CLASS_DIR, exist_ok=True)
    ids = [f[:-5] for f in os.listdir(CLASS_DIR) if f.endswith(".json")]
    if not ids:
        write_class(safe_name(DEFAULT_CLASS), DEFAULT_CLASS, _legacy_roster())
        ids = [safe_name(DEFAULT_CLASS)]
    out = []
    for cid in ids:
        try:
            c = read_class(cid)
        except (OSError, ValueError):
            continue
        out.append({"id": cid, "name": c["name"], "count": len(c["students"])})
    return sorted(out, key=lambda c: c["name"].lower())


def active_class():
    classes = list_classes()
    ids = [c["id"] for c in classes]
    cid = settings.get("class") if settings.get("class") in ids else ids[0]
    return read_class(cid)


def load_roster():
    return active_class()["students"]


def save_roster(roster):
    c = active_class()
    write_class(c["id"], c["name"], roster)


def activate_class(cid):
    """Przełącza klasę: lista uczniów sesji i (gdy trzeba) nowa rozgrywka."""
    c = read_class(cid)
    settings["class"] = c["id"]
    save_settings()
    session.set_roster(c["students"], c["name"])
    return c


# --------------------------- dostęp z sieci ---------------------------
pair_key = None


def load_pair_key(regenerate=False):
    """Klucz sparowanych urządzeń. Trzymany na dysku, żeby telefon nie musiał
    parować się od nowa po każdym uruchomieniu programu."""
    global pair_key
    if not regenerate:
        try:
            with open(PAIR_KEY, encoding="utf-8") as f:
                pair_key = f.read().strip() or None
        except OSError:
            pair_key = None
    if regenerate or not pair_key:
        pair_key = secrets.token_urlsafe(24)
        try:
            with open(PAIR_KEY, "w", encoding="utf-8") as f:
                f.write(pair_key)
        except OSError:
            pass
    return pair_key


def qr_png(text, scale=8, border=4):
    """Kod QR jako PNG (koder z OpenCV — bez dodatkowej biblioteki)."""
    import cv2
    import numpy as np
    m = cv2.QRCodeEncoder.create().encode(text)
    m = np.pad(m, border, constant_values=255)
    m = cv2.resize(m, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    return cv2.imencode(".png", m)[1].tobytes()


# --------------------------- wznowienie gry ---------------------------
RESTORE_MAX_AGE = 12 * 3600


def autosave_session(_session=None):
    """Migawka gry po każdym wyniku i zmianie pytania — po zamknięciu
    programu (albo awarii) można wrócić do tego samego miejsca."""
    snap = session.snapshot()
    if not snap["history"] and not snap["index"]:
        return
    try:
        tmp = SESSION_JSON + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False)
        os.replace(tmp, SESSION_JSON)
    except OSError:
        pass


def try_restore_session():
    """Przy starcie: wczytaj przerwaną grę, jeśli jest świeża i niedokończona."""
    try:
        with open(SESSION_JSON, encoding="utf-8") as f:
            snap = json.load(f)
    except (OSError, ValueError):
        return False
    if (snap.get("finished") or not snap.get("quiz_name")
            or time.time() - float(snap.get("saved_at", 0)) > RESTORE_MAX_AGE):
        return False
    try:
        quiz = read_quiz(snap["quiz_name"])
    except (OSError, ValueError):
        return False
    for c in list_classes():
        if c["name"] == snap.get("class_name"):
            activate_class(c["id"])
    session.load_quiz(quiz, safe_name(snap["quiz_name"]))
    return session.restore(snap)


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


_ips_cache = (0.0, None)


def lan_ips():
    """Adresy IPv4 komputera w sieci lokalnej, najpewniejszy pierwszy.

    Trasa do 8.8.8.8 wskazuje kartę z dostępem do świata (nic nie jest
    wysyłane); w szkolnej sieci bez internetu jej nie ma, więc dokładamy
    adresy przypisane do nazwy komputera. Wynik trzymamy pół minuty — pytamy
    o niego przy każdym zapytaniu (sprawdzanie dostępu)."""
    global _ips_cache
    if _ips_cache[1] and time.time() - _ips_cache[0] < 30:
        return _ips_cache[1]
    found = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        found.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        found += socket.gethostbyname_ex(socket.gethostname())[2]
    except Exception:
        pass
    out = []
    for ip in found:
        if ip not in out and not ip.startswith(("127.", "169.254.")):
            out.append(ip)
    _ips_cache = (time.time(), out or ["127.0.0.1"])
    return _ips_cache[1]


def lan_ip():
    return lan_ips()[0]


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


def decode_upload(data_url):
    """Zawartość pliku przesłanego z przeglądarki jako data:URL."""
    import base64
    import binascii
    if not data_url.startswith("data:") or "," not in data_url:
        raise ValueError("brak pliku")
    try:
        return base64.b64decode(data_url.split(",", 1)[1])
    except (binascii.Error, ValueError):
        raise ValueError("uszkodzony plik")


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


def build_cards_pdf(count=None, roster=None):
    """Tworzy w pamięci PDF z kartami ArUco (jedna karta na stronę A4).
    Domyślnie karty dla aktualnej listy uczniów; jeśli lista pusta lub podano
    count -- karty o numerach 0..count-1."""
    import io
    import cv2
    from PIL import Image
    from .aruco import get_dictionary
    from .cards import make_card

    dictionary = get_dictionary()
    if roster is None:
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

    def redirect(self, location, cookie=None):
        self.send_response(302)
        self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_blob(self, body, ctype, filename=None):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # ---- dostęp ----
    def is_local(self):
        """Zapytanie z tego samego komputera (także przez jego adres w LAN)."""
        ip = self.client_address[0]
        if ip.startswith("::ffff:"):
            ip = ip[7:]
        return ip in ("127.0.0.1", "::1") or ip in lan_ips()

    def authorized(self):
        if self.is_local():
            return True
        try:
            jar = SimpleCookie(self.headers.get("Cookie", ""))
        except Exception:
            return False
        got = jar["qs_key"].value if "qs_key" in jar else ""
        return bool(pair_key and got and secrets.compare_digest(got.encode(), pair_key.encode()))

    def locked(self):
        return self.send_json({"ok": False, "error": "locked"}, code=403)

    def read_json_body(self, limit=MEDIA_MAX_MB * 1024 * 1024 * 2):
        length = int(self.headers.get("Content-Length", 0))
        if length > limit:
            return {}
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

        # --- publiczne: tablica, pilot, zasoby, stan tylko do odczytu ---
        if path == "/":
            return self.redirect("/teacher" if self.authorized() else "/board")
        if path == "/board":
            return self.send_file(os.path.join(WEB_DIR, "board.html"))
        if path == "/remote":
            return self.send_file(os.path.join(WEB_DIR, "remote.html"))
        if path == "/pair":
            # Link z kodu QR: zapisuje klucz w ciasteczku i przechodzi do pilota.
            key = query.get("k", [""])[0]
            if pair_key and secrets.compare_digest(key.encode(), pair_key.encode()):
                return self.redirect(
                    "/remote", cookie=f"qs_key={pair_key}; Max-Age=31536000; "
                                      "Path=/; HttpOnly; SameSite=Lax")
            return self.redirect("/remote?bad=1")
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            rel = os.path.normpath(rel).replace("\\", "/")
            if rel.startswith(".."):
                return self.send_error(403)
            return self.send_file(os.path.join(WEB_DIR, rel))
        if path.startswith("/media/"):
            fn = os.path.basename(path[len("/media/"):])
            return self.send_file(os.path.join(MEDIA_DIR, fn))
        if path == "/api/settings":
            return self.send_json(settings)
        if path == "/api/whoami":
            return self.send_json({"authorized": self.authorized(), "local": self.is_local()})
        if path == "/api/state" and query.get("full", ["0"])[0] != "1":
            return self.send_json(session.state(full=False))

        # --- dalej tylko komputer nauczyciela i sparowane urządzenia ---
        if not self.authorized():
            if path in ("/teacher", "/editor"):
                return self.redirect("/remote")
            return self.locked()

        if path == "/teacher":
            return self.send_file(os.path.join(WEB_DIR, "teacher.html"))
        if path == "/editor":
            return self.send_file(os.path.join(WEB_DIR, "editor.html"))
        if path == "/video_feed":
            return self.stream_mjpeg()
        if path == "/api/pair":
            port = self.server.server_address[1]
            ips = lan_ips()
            ip = query.get("ip", [ips[0]])[0]
            if ip not in ips:
                ip = ips[0]
            return self.send_json({"url": f"http://{ip}:{port}/pair?k={pair_key}",
                                   "ips": ips, "ip": ip})
        if path == "/api/pair.png":
            ips = lan_ips()
            ip = query.get("ip", [ips[0]])[0]
            if ip not in ips:
                ip = ips[0]
            url = f"http://{ip}:{self.server.server_address[1]}/pair?k={pair_key}"
            return self.send_blob(qr_png(url), "image/png")
        if path == "/api/classes":
            return self.send_json({"classes": list_classes(), "active": active_class()["id"]})
        if path == "/api/class":
            try:
                c = read_class(query.get("id", [""])[0])
            except (OSError, ValueError):
                return self.send_error(404, "Brak klasy")
            return self.send_json({"id": c["id"], "name": c["name"],
                                   "students": {str(k): v for k, v in c["students"].items()}})
        if path == "/api/roster.csv":
            try:
                c = read_class(query["id"][0]) if "id" in query else active_class()
            except (OSError, ValueError):
                return self.send_error(404, "Brak klasy")
            return self.send_blob(roster_import.export_csv(c["students"]),
                                  "text/csv; charset=utf-8",
                                  f"uczniowie_{safe_name(c['name']).replace(' ', '_')}.csv")
        if path == "/api/quiz/template.docx":
            return self.send_blob(
                quiz_import.template_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "szablon_quizu_QuizScanner.docx")

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
            cls = query.get("class", [None])[0]
            try:
                roster = read_class(cls)["students"] if cls else None
                pdf = build_cards_pdf(count=c, roster=roster)
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

        if path == "/api/state":
            st = session.state(full=True)
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
                "lan_ips": lan_ips(),
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
        if not self.authorized():
            return self.locked()
        # Tylko JSON: obca strona otwarta w przeglądarce nauczyciela nie wyśle
        # takiego zapytania bez zgody serwera (CORS), więc nie przestawi quizu.
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self.send_json({"ok": False, "error": "json"}, code=415)
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
            elif action == "draw":
                drawn = session.draw_student()
                return self.send_json({"ok": bool(drawn), "draw": drawn})
            elif action == "dismiss_restore":
                with session.lock:
                    session.restored_at = None
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
            settings["last_quiz"] = safe_name(name)
            save_settings()
            return self.send_json({"ok": True, "state": session.state(full=True)})

        if path == "/api/roster":
            roster = {int(k): v for k, v in data.items()}
            save_roster(roster)
            session.set_roster(roster)
            return self.send_json({"ok": True})

        if path == "/api/class/select":
            try:
                c = activate_class(data.get("id", ""))
            except (OSError, ValueError):
                return self.send_json({"ok": False}, code=404)
            if data.get("reset"):
                session.reset_scores()
            return self.send_json({"ok": True, "id": c["id"], "name": c["name"]})

        if path == "/api/class/save":
            # Nowa klasa albo zmiana nazwy/listy istniejącej.
            name = str(data.get("name", "")).strip()[:60]
            if not name:
                return self.send_json({"ok": False, "error": "name"}, code=400)
            old = data.get("id") or ""
            new_id = safe_name(name)
            students = data.get("students")
            if students is None:
                students = read_class(old)["students"] if old else {}
            students = {int(k): str(v) for k, v in students.items()}
            if new_id != old and os.path.exists(class_path(new_id)):
                return self.send_json({"ok": False, "error": "exists"}, code=409)
            write_class(new_id, name, students)
            if old and old != new_id and os.path.exists(class_path(old)):
                os.remove(class_path(old))
            # Zmiana aktywnej klasy od razu trafia do sesji; nowa klasa nie
            # przełącza trwającej gry, chyba że edytor wprost o to prosi.
            if (old and settings.get("class") == old) or data.get("activate"):
                activate_class(new_id)
            return self.send_json({"ok": True, "id": new_id})

        if path == "/api/class/delete":
            classes = list_classes()
            cid = safe_name(data.get("id", ""))
            if len(classes) < 2 or cid not in [c["id"] for c in classes]:
                return self.send_json({"ok": False}, code=400)
            os.remove(class_path(cid))
            if settings.get("class") == cid:
                activate_class(list_classes()[0]["id"])
            return self.send_json({"ok": True})

        if path == "/api/roster/import":
            try:
                blob = decode_upload(data.get("data", ""))
                students, warnings = roster_import.import_file(data.get("name", ""), blob)
            except ValueError as e:
                return self.send_json({"ok": False, "error": str(e)}, code=400)
            return self.send_json({"ok": True, "students": students, "warnings": warnings})

        if path == "/api/quiz/parse":
            try:
                blob = decode_upload(data.get("data", ""))
                quiz, warnings = quiz_import.import_file(data.get("name", ""), blob)
            except ValueError as e:
                return self.send_json({"ok": False, "error": str(e)}, code=400)
            return self.send_json({"ok": True, "quiz": quiz, "warnings": warnings})

        if path == "/api/pair/reset":
            load_pair_key(regenerate=True)
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
    load_pair_key()
    if camera is not None:          # jawny wybór z linii poleceń ma pierwszeństwo
        settings["camera"] = str(camera)
    c = active_class()
    session.set_roster(c["students"], c["name"])
    session.set_only_known(bool(settings.get("only_known", True)))
    session.on_podium = autosave_report
    session.on_change = autosave_session
    session.start_auto_engine()
    updater.check_async(bool(settings.get("check_updates", True)))

    if not try_restore_session():
        quizzes = list_quizzes()
        first = settings.get("last_quiz") if settings.get("last_quiz") in quizzes else None
        first = first or (quizzes[0] if quizzes else None)
        if first:
            try:
                session.load_quiz(read_quiz(first), first)
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
        print("  Pilot w telefonie : zeskanuj kod QR z panelu nauczyciela")
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
