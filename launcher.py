"""
Launcher QuizScanner (okno z przyciskami).

Uruchamia serwer aplikacji w TYM SAMYM procesie (w wątku), dzięki czemu
działa tak samo z kodu źródłowego (`python launcher.py`), jak i spakowany
w jeden plik `QuizScanner.exe` (PyInstaller). Daje przyciski do otwierania
panelu nauczyciela, tablicy i edytora w przeglądarce.
"""

import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox

from quizscanner import server as app  # build_server / stop_server / lan_ip
from quizscanner import VERSION
from quizscanner.paths import ICON_ICO


class Launcher:
    def __init__(self, root):
        self.root = root
        self.httpd = None
        self.thread = None
        root.title("QuizScanner")
        try:                                   # logo w pasku okna i na pasku zadań
            root.iconbitmap(ICON_ICO)
        except Exception:                      # brak pliku lub system bez .ico
            pass
        root.geometry("460x330")
        root.resizable(False, False)
        root.configure(bg="#14161f")

        tk.Label(root, text="QuizScanner", font=("Segoe UI", 22, "bold"),
                 fg="#e2603f", bg="#14161f").pack(pady=(18, 2))
        tk.Label(root, text=f"System quizowy z odczytem kart z kamery  ·  v{VERSION}",
                 fg="#8b91a4", bg="#14161f").pack()

        cfg = tk.Frame(root, bg="#14161f")
        cfg.pack(pady=14)
        tk.Label(cfg, text="Kamera:", fg="#eef0f6", bg="#14161f").grid(row=0, column=0, padx=6, sticky="e")
        self.cam = tk.Spinbox(cfg, from_=0, to=8, width=5)
        self.cam.grid(row=0, column=1, padx=6)
        tk.Label(cfg, text="Port:", fg="#eef0f6", bg="#14161f").grid(row=0, column=2, padx=6, sticky="e")
        self.port = tk.Entry(cfg, width=7)
        self.port.insert(0, "8000")
        self.port.grid(row=0, column=3, padx=6)

        self.startBtn = tk.Button(root, text="▶  Uruchom", bg="#4faa6a", fg="white",
                                  font=("Segoe UI", 12, "bold"), relief="flat",
                                  padx=16, pady=9, command=self.toggle, activebackground="#3f9159")
        self.startBtn.pack(pady=6)

        links = tk.Frame(root, bg="#14161f")
        links.pack(pady=8)
        self.b_teacher = self._link(links, "🎛  Panel nauczyciela", "teacher", 0)
        self.b_board = self._link(links, "📺  Tablica", "board", 1)
        self.b_editor = self._link(links, "✏️  Edytor", "editor", 2)
        self._set_links(False)

        self.status = tk.Label(root, text="Zatrzymany", fg="#8b91a4", bg="#14161f")
        self.status.pack(pady=(12, 0))

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _link(self, parent, text, path, col):
        b = tk.Button(parent, text=text, relief="flat", bg="#242938", fg="#eef0f6",
                      activebackground="#313749", activeforeground="#fff",
                      padx=10, pady=6, command=lambda: self.open(path))
        b.grid(row=0, column=col, padx=5)
        return b

    def _set_links(self, on):
        state = "normal" if on else "disabled"
        for b in (self.b_teacher, self.b_board, self.b_editor):
            b.config(state=state)

    def toggle(self):
        if self.httpd:
            self.stop()
        else:
            self.start()

    def start(self):
        port = int(self.port.get().strip() or "8000")
        cam = int(self.cam.get().strip() or "0")
        try:
            self.httpd = app.build_server(camera=cam, port=port, host="0.0.0.0")
        except OSError as e:
            messagebox.showerror("QuizScanner",
                                 f"Nie udało się uruchomić na porcie {port}.\n"
                                 f"Spróbuj innego portu.\n\n{e}")
            self.httpd = None
            return
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.startBtn.config(text="■  Zatrzymaj", bg="#d9573d", activebackground="#c44e30")
        self._set_links(True)
        ip = app.lan_ip()
        self.status.config(text=f"Działa · Tablica w sieci: http://{ip}:{port}/board", fg="#4faa6a")
        self.root.after(900, lambda: self.open("teacher"))

    def stop(self):
        if self.httpd:
            app.stop_server(self.httpd)
            self.httpd = None
        self.startBtn.config(text="▶  Uruchom", bg="#4faa6a", activebackground="#3f9159")
        self._set_links(False)
        self.status.config(text="Zatrzymany", fg="#8b91a4")

    def open(self, path):
        port = self.port.get().strip() or "8000"
        webbrowser.open(f"http://localhost:{port}/{path}")

    def on_close(self):
        self.stop()
        self.root.destroy()


def run():
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == "__main__":
    # Diagnostyka przeniesiona do tools/selftest.py (działa bez tkintera).
    # Tryb konsolowy (bez okna): QuizScanner.exe --serve [--port ... --no-camera]
    if "--serve" in sys.argv:
        sys.argv.remove("--serve")
        app.main()
    else:
        run()
