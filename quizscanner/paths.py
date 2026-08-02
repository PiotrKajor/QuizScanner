"""Ścieżki do zasobów i danych — jedno miejsce dla całej aplikacji.

Działa tak samo z kodu źródłowego, jak i w spakowanym .exe (PyInstaller):

  RES_DIR   zasoby tylko-do-odczytu (web/, dane startowe)
  DATA_DIR  folder zapisywalny (quizy, media, lista uczniów, raporty)

Ze źródeł DATA_DIR = <repo>/data, w .exe = <folder z exe>/data — dzięki temu
wszystko, co tworzy nauczyciel, leży w jednym katalogu obok programu.
"""

import os
import shutil
import sys

if getattr(sys, "frozen", False):
    RES_DIR = sys._MEIPASS                                        # zasoby exe
    DATA_DIR = os.path.join(os.path.dirname(sys.executable), "data")
else:
    RES_DIR = os.path.dirname(os.path.abspath(__file__))          # pakiet
    DATA_DIR = os.path.join(os.path.dirname(RES_DIR), "data")     # <repo>/data

WEB_DIR = os.path.join(RES_DIR, "web")
# Ikona programu (logo) — ta sama, którą dostaje .exe i okno launchera.
# Ze źródeł leży w <repo>/assets, w .exe w <_MEIPASS>\assets.
_ASSET_ROOT = RES_DIR if getattr(sys, "frozen", False) else os.path.dirname(RES_DIR)
ICON_ICO = os.path.join(_ASSET_ROOT, "assets", "logo.ico")
QUIZ_DIR = os.path.join(DATA_DIR, "quizzes")
MEDIA_DIR = os.path.join(DATA_DIR, "media")
REPORT_DIR = os.path.join(DATA_DIR, "raporty")
ROSTER_JSON = os.path.join(DATA_DIR, "roster.json")
STUDENTS_CSV = os.path.join(DATA_DIR, "students.csv")
SETTINGS_JSON = os.path.join(DATA_DIR, "settings.json")


def seed_data():
    """Tworzy folder danych i przy pierwszym uruchomieniu kopiuje tam dane
    startowe (przykładowy quiz, lista uczniów) dołączone do programu."""
    os.makedirs(DATA_DIR, exist_ok=True)
    src_root = os.path.join(RES_DIR, "data") if getattr(sys, "frozen", False) else DATA_DIR
    try:
        if not os.path.isdir(QUIZ_DIR):
            src = os.path.join(src_root, "quizzes")
            if os.path.isdir(src):
                shutil.copytree(src, QUIZ_DIR)
            else:
                os.makedirs(QUIZ_DIR, exist_ok=True)
        if not os.path.exists(STUDENTS_CSV):
            src = os.path.join(src_root, "students.csv")
            if os.path.exists(src):
                shutil.copy(src, STUDENTS_CSV)
    except OSError:
        pass
