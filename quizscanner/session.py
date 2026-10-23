"""
Stan sesji quizu i logika punktacji (niezależne od interfejsu i kamery).

QuizSession trzyma aktualny quiz, fazy pytania, odpowiedzi uczniów
(dostarczane przez skaner kamery) i wyniki. Jest bezpieczny wątkowo,
bo aktualizuje go wątek kamery, a odczytuje serwer HTTP.

Fazy:
  idle     -- pytanie pokazane, jeszcze nie zbieramy odpowiedzi
  question -- zbieramy odpowiedzi z kamery (timer leci)
  reveal   -- pokazana poprawna odpowiedź + rozkład, punkty naliczone
  podium   -- ranking końcowy
"""

import random
import threading
import time

DEFAULT_QUIZ_SETTINGS = {
    "default_time": 20,        # domyślny czas nowego pytania (s)
    "default_points": 1000,    # domyślne punkty nowego pytania
    "shuffle_questions": False,
    "shuffle_answers": False,
    "show_distribution": True,  # słupki rozkładu odpowiedzi przy wyniku
    "auto_reveal_s": 6,        # tryb auto: jak długo pokazywać wynik
    "auto_gap_s": 3,           # tryb auto: przerwa przed kolejnym pytaniem
}

PHASE_IDLE = "idle"
PHASE_QUESTION = "question"
PHASE_REVEAL = "reveal"
PHASE_PODIUM = "podium"

LETTERS = ["A", "B", "C", "D"]


class QuizSession:
    def __init__(self):
        self.lock = threading.RLock()
        self.quiz = {"title": "Brak wczytanego quizu", "questions": []}
        self.quiz_name = None
        self.roster = {}          # id(int) -> imię
        self.index = 0
        self.phase = PHASE_IDLE
        self.q_start = None
        self.q_end = None
        self.answers = {}         # id -> "A".."D"
        self.answer_time = {}     # id -> czas ostatniej zmiany odpowiedzi
        self.scores = {}          # id -> suma punktów
        self.awarded = False      # zabezpieczenie przed podwójnym liczeniem
        self.history = []         # wyniki per pytanie (do eksportu)
        self.speed_bonus = False  # False = punkty stałe; True = szybciej więcej
        self.only_known = True    # ignoruj ID spoza listy uczniów
        self.order = []           # kolejność pytań (może być losowa)
        self.perm = [0, 1, 2, 3]  # kolejność odpowiedzi w bieżącym pytaniu
        self.on_podium = None     # wywoływane raz, gdy quiz dobiegnie końca
        self.on_change = None     # wywoływane po każdym naliczeniu punktów (autozapis)
        self.class_name = ""      # nazwa aktywnej klasy (do raportu)
        self.restored_at = None   # czas migawki, z której wznowiono grę

        # Losowanie ucznia: kto już był wylosowany (bez powtórzeń do wyczerpania
        # listy) i ostatni wynik, który tablica pokazuje przez chwilę.
        self.drawn = set()
        self.draw = None

        # Tryb automatyczny: quiz sam odsłania wynik i przechodzi dalej.
        self.auto_mode = False
        self._auto_thread = None
        self._auto_stop = threading.Event()
        self._auto_at = None      # znacznik czasu następnego przejścia

    # ---------- konfiguracja ----------
    def settings(self):
        """Ustawienia quizu z bezpiecznymi wartościami domyślnymi."""
        s = dict(DEFAULT_QUIZ_SETTINGS)
        s.update(self.quiz.get("settings") or {})
        return s

    def load_quiz(self, quiz, name=None):
        with self.lock:
            self.quiz = quiz
            self.quiz_name = name
            self.index = 0
            self.phase = PHASE_IDLE
            self.scores = {}
            self.history = []
            self.restored_at = None
            self._build_order()
            self._reset_question_state()

    def _build_order(self):
        """Ustala kolejność pytań (opcjonalnie losowa)."""
        n = len(self.quiz.get("questions", []))
        self.order = list(range(n))
        if self.settings().get("shuffle_questions"):
            random.shuffle(self.order)

    def set_roster(self, roster, class_name=None):
        with self.lock:
            self.roster = {int(k): v for k, v in roster.items()}
            self.drawn &= set(self.roster)
            if class_name is not None:
                self.class_name = class_name

    def set_speed_bonus(self, value):
        with self.lock:
            self.speed_bonus = bool(value)

    def set_only_known(self, value):
        with self.lock:
            self.only_known = bool(value)

    def set_auto_mode(self, value):
        with self.lock:
            self.auto_mode = bool(value)
            self._auto_at = None

    # ---------- przepływ pytania ----------
    def _reset_question_state(self):
        self.answers = {}
        self.answer_time = {}
        self.q_start = None
        self.q_end = None
        self.awarded = False
        self._set_answer_perm()

    def _set_answer_perm(self):
        """Ustala kolejność wyświetlania odpowiedzi (opcjonalnie losowa).

        perm[i] = która oryginalna odpowiedź pokazujemy na pozycji i.
        Losowanie jest ustalane raz na pytanie, żeby tablica nie migotała.
        """
        self.perm = [0, 1, 2, 3]
        if self.settings().get("shuffle_answers"):
            random.shuffle(self.perm)

    def displayed_answers(self, q):
        """Odpowiedzi w kolejności pokazywanej uczniom."""
        src = list(q.get("answers", ["", "", "", ""]))
        src += [""] * (4 - len(src))
        return [src[i] for i in self.perm]

    def displayed_correct(self, q):
        """Indeks poprawnej odpowiedzi PO ewentualnym przetasowaniu."""
        c = q.get("correct", None)
        if not isinstance(c, int) or not (0 <= c < 4):
            return None
        try:
            return self.perm.index(c)
        except ValueError:
            return c

    def current_question(self):
        qs = self.quiz.get("questions", [])
        if not self.order or len(self.order) != len(qs):
            self._build_order()
        if 0 <= self.index < len(self.order):
            real = self.order[self.index]
            if 0 <= real < len(qs):
                return qs[real]
        return None

    def start_question(self):
        with self.lock:
            q = self.current_question()
            if not q:
                return
            self._reset_question_state()
            self.q_start = time.time()
            t = q.get("time", 20)
            self.q_end = self.q_start + t if t else None
            self.phase = PHASE_QUESTION

    def record_answers(self, confirmed):
        """confirmed: dict {id: 'A'/'B'/'C'/'D'} z potwierdzonymi odczytami.
        Wywoływane przez wątek kamery. Zapisuje odpowiedzi i czas zmiany."""
        with self.lock:
            if self.phase != PHASE_QUESTION:
                return
            if self.q_end and time.time() > self.q_end:
                return  # czas minął -> zamrażamy odpowiedzi
            now = time.time()
            for mid, ans in confirmed.items():
                # Ochrona przed przypadkowymi wykryciami: przyjmuj tylko ID,
                # które faktycznie są na liście uczniów.
                if self.only_known and self.roster and mid not in self.roster:
                    continue
                if self.answers.get(mid) != ans:
                    self.answers[mid] = ans
                    self.answer_time[mid] = now

    def time_left(self):
        if self.phase == PHASE_QUESTION and self.q_end:
            return max(0.0, self.q_end - time.time())
        return None

    def reveal(self):
        with self.lock:
            q = self.current_question()
            if not q:
                return
            if not self.awarded:
                self._award(q)
                self.awarded = True
            self.phase = PHASE_REVEAL
        self._changed()

    def _changed(self):
        if self.on_change:
            try:
                self.on_change(self)
            except Exception:
                pass

    def _award(self, q):
        # Uczniowie odpowiadają litera z TABLICY, więc liczy się pozycja
        # po ewentualnym przetasowaniu odpowiedzi.
        correct = self.displayed_correct(q)
        base = int(q.get("points", 1000) or 0)
        t = float(q.get("time", 20) or 20)
        letter = LETTERS[correct] if isinstance(correct, int) and 0 <= correct < 4 else None
        shown = self.displayed_answers(q)
        result = {
            "index": self.index,
            "question": q.get("text", ""),
            "options": shown,
            "correct": letter,
            "correct_text": shown[correct] if letter else "",
            "points_max": base,
            "answers": {},
        }
        for mid, ans in self.answers.items():
            is_correct = letter is not None and ans == letter
            pts = 0
            if is_correct and base > 0:
                if self.speed_bonus:
                    # Styl Kahoot: kto szybciej ustalił odpowiedź, dostaje więcej.
                    elapsed = self.answer_time.get(mid, self.q_start) - self.q_start
                    frac = 1.0 - min(max(elapsed / t, 0.0), 1.0)
                    pts = int(round(base * (0.5 + 0.5 * frac)))
                else:
                    # Punkty stałe: każda poprawna odpowiedź warta tyle samo.
                    pts = base
            result["answers"][mid] = {"answer": ans, "correct": is_correct, "points": pts}
        # Powrót do pytania i ponowne „Pokaż wynik" zastępuje poprzedni wynik
        # tego pytania, zamiast doliczać punkty drugi raz.
        self.history = [h for h in self.history if h.get("index") != self.index]
        self.history.append(result)
        self._recount_scores()

    def _recount_scores(self):
        """Suma punktów liczona od nowa z historii (po jednym wpisie na pytanie)."""
        scores = {}
        for h in self.history:
            for mid, a in h.get("answers", {}).items():
                scores[mid] = scores.get(mid, 0) + int(a.get("points", 0))
        self.scores = scores

    def next_question(self):
        with self.lock:
            if self.index < len(self.quiz["questions"]) - 1:
                self.index += 1
                self.phase = PHASE_IDLE
                self._reset_question_state()
                finished = None
            else:
                finished = self.phase != PHASE_PODIUM
                self.phase = PHASE_PODIUM
        self._changed()
        if finished is None:
            return
        # ponytail: raport zapisujemy tu, w wątku wywołującym -- to ułamek
        # sekundy; osobny wątek dopiero gdyby doszły ciężkie formaty.
        if finished and self.on_podium:
            try:
                self.on_podium(self)
            except Exception:
                pass

    def prev_question(self):
        with self.lock:
            if self.index > 0:
                self.index -= 1
                self.phase = PHASE_IDLE
                self._reset_question_state()
        self._changed()

    def goto(self, idx):
        with self.lock:
            if 0 <= idx < len(self.quiz["questions"]):
                self.index = idx
                self.phase = PHASE_IDLE
                self._reset_question_state()
        self._changed()

    def reset_scores(self):
        with self.lock:
            self.scores = {}
            self.history = []
            self.index = 0
            self.phase = PHASE_IDLE
            self.restored_at = None
            self._reset_question_state()
        self._changed()

    # ---------- losowanie ucznia ----------
    def draw_student(self):
        """Losuje ucznia z listy klasy, bez powtórzeń aż do wyczerpania listy.
        Zwraca {"id", "name"} albo None, gdy lista jest pusta."""
        with self.lock:
            if not self.roster:
                return None
            pool = [mid for mid in self.roster if mid not in self.drawn]
            if not pool:
                self.drawn = set()
                pool = list(self.roster)
            mid = random.choice(pool)
            self.drawn.add(mid)
            seq = (self.draw or {}).get("seq", 0) + 1
            self.draw = {"seq": seq, "id": mid, "name": self.roster[mid],
                         "at": time.time(), "left": len(pool) - 1}
            return dict(self.draw)

    # ---------- migawka (wznowienie po awarii) ----------
    def snapshot(self):
        """Stan gry do zapisania na dysk — tyle, ile trzeba, żeby po
        zamknięciu programu wrócić do tego samego pytania z tymi samymi punktami."""
        with self.lock:
            return {
                "quiz_name": self.quiz_name,
                "class_name": self.class_name,
                "index": self.index,
                "order": list(self.order),
                "finished": self.phase == PHASE_PODIUM,
                "history": [dict(h, answers={str(k): v for k, v in h["answers"].items()})
                            for h in self.history],
                "saved_at": time.time(),
            }

    def restore(self, snap):
        """Odtwarza grę z migawki (quiz musi być już wczytany)."""
        with self.lock:
            n = len(self.quiz.get("questions", []))
            order = [int(i) for i in snap.get("order", [])]
            if sorted(order) != list(range(n)):
                return False                 # quiz zmienił się od migawki
            self.order = order
            self.history = [dict(h, answers={int(k): v for k, v in h["answers"].items()})
                            for h in snap.get("history", [])]
            self._recount_scores()
            self.index = min(int(snap.get("index", 0)), max(n - 1, 0))
            self.phase = PHASE_IDLE
            self._reset_question_state()
            self.restored_at = snap.get("saved_at")
            return True

    # Skróty używane przez pętlę automatyczna (lock jest reentrantny).
    def _do_reveal(self):
        self.reveal()

    def _do_next(self):
        self.next_question()

    def _do_start(self):
        self.start_question()

    # ---------- tryb automatyczny ----------
    def start_auto_engine(self):
        """Uruchamia wątek prowadzący quiz samodzielnie (gdy auto_mode=True)."""
        if self._auto_thread and self._auto_thread.is_alive():
            return
        self._auto_stop.clear()
        self._auto_thread = threading.Thread(target=self._auto_loop, daemon=True)
        self._auto_thread.start()

    def stop_auto_engine(self):
        self._auto_stop.set()

    def _auto_loop(self):
        while not self._auto_stop.wait(0.2):
            try:
                self._auto_tick()
            except Exception:
                pass  # tryb auto nigdy nie może wywrócić aplikacji

    def _auto_tick(self):
        with self.lock:
            if not self.auto_mode or self.phase == PHASE_PODIUM:
                self._auto_at = None
                return
            st = self.settings()
            now = time.time()

            if self.phase == PHASE_QUESTION:
                # Czas pytania minął -> pokaż wynik.
                if self.q_end and now >= self.q_end:
                    self._do_reveal()
                    self._auto_at = now + float(st.get("auto_reveal_s", 6) or 0)
                return

            if self.phase == PHASE_REVEAL:
                # Po pokazaniu wyniku -> następne pytanie (lub podium).
                if self._auto_at and now >= self._auto_at:
                    self._do_next()
                    self._auto_at = (now + float(st.get("auto_gap_s", 3) or 0)
                                     if self.phase != PHASE_PODIUM else None)
                return

            if self.phase == PHASE_IDLE:
                # Krótka przerwa między pytaniami, potem start kolejnego.
                if self._auto_at is None:
                    self._auto_at = now + float(st.get("auto_gap_s", 3) or 0)
                elif now >= self._auto_at:
                    self._do_start()
                    self._auto_at = None

    def auto_next_in(self):
        """Ile sekund do automatycznego przejścia (None, gdy nie dotyczy)."""
        if self.auto_mode and self._auto_at:
            return max(0.0, self._auto_at - time.time())
        return None

    def leaderboard(self, top=None):
        items = sorted(self.scores.items(), key=lambda kv: kv[1], reverse=True)
        board = [{"id": mid, "name": self.roster.get(mid, f"#{mid}"), "score": sc}
                 for mid, sc in items]
        return board[:top] if top else board

    # ---------- widok stanu ----------
    def state(self, full=False):
        """Słownik stanu do JSON. full=True (nauczyciel) dołącza poprawna
        odpowiedź zawsze; dla tablicy tylko w fazie reveal."""
        with self.lock:
            q = self.current_question()
            tl = self.time_left()
            dist = {"A": 0, "B": 0, "C": 0, "D": 0}
            per_student = {}
            for mid, a in self.answers.items():
                if a in dist:
                    dist[a] += 1
                per_student[mid] = a
            st = {
                "quiz_title": self.quiz.get("title", ""),
                "quiz_name": self.quiz_name,
                "index": self.index,
                "total": len(self.quiz["questions"]),
                "phase": self.phase,
                "time_left": round(tl, 1) if tl is not None else None,
                "answered": len(self.answers),
                "distribution": dist,
                "question": None,
                "leaderboard": self.leaderboard(top=10),
                "auto_mode": self.auto_mode,
                "auto_next_in": (round(self.auto_next_in(), 1)
                                 if self.auto_next_in() is not None else None),
                "show_distribution": bool(self.settings().get("show_distribution", True)),
                "class_name": self.class_name,
                "class_size": len(self.roster),
                "draw": None,
            }
            # Wylosowany uczeń widnieje na tablicy przez kilka sekund.
            if self.draw and time.time() - self.draw["at"] < 12:
                st["draw"] = {"seq": self.draw["seq"], "name": self.draw["name"],
                              "pool": [self.roster[m] for m in sorted(self.roster)][:60]}
            if q:
                qd = {
                    "text": q.get("text", ""),
                    "answers": self.displayed_answers(q),
                    "time": q.get("time", 20),
                    "points": q.get("points", 1000),
                    "media": q.get("media") or None,
                }
                if full or self.phase == PHASE_REVEAL:
                    qd["correct"] = self.displayed_correct(q)
                st["question"] = qd
            if full:
                st["students"] = {
                    str(mid): {"name": self.roster.get(mid, f"#{mid}"), "answer": a}
                    for mid, a in per_student.items()
                }
                st["scores"] = {str(k): v for k, v in self.scores.items()}
                st["speed_bonus"] = self.speed_bonus
                st["only_known"] = self.only_known
                # Kto jeszcze nie odpowiedział — nauczyciel widzi to w pilocie.
                st["missing"] = ([{"id": m, "name": self.roster[m]} for m in sorted(self.roster)
                                  if m not in self.answers]
                                 if self.phase == PHASE_QUESTION else [])
                st["restored_at"] = self.restored_at
                # Spis pytań w kolejności gry (lista wyboru na tablicy i w pilocie).
                qs = self.quiz.get("questions", [])
                st["outline"] = [str(qs[i].get("text", ""))[:90] for i in self.order
                                 if 0 <= i < len(qs)]
                if self.draw:
                    st["last_draw"] = {"name": self.draw["name"], "left": self.draw["left"]}
            return st
