"""
Import pytań z dokumentu Word (.docx) albo zwykłego pliku tekstowego.

Nauczyciel pisze test tak, jak pisze go na kartkówkę:

    Tytuł: Powtórka z ułamków

    1. Ile to jest $\\frac{1}{2} + \\frac{1}{4}$?
    A. $\\frac{3}{4}$
    B. $\\frac{2}{6}$
    C. 1
    D. $\\frac{1}{8}$
    Odpowiedź: A
    Czas: 30

Poprawną odpowiedź wskazuje linia „Odpowiedź: X", gwiazdka przed literą
(„*A. …") albo pogrubienie całej odpowiedzi w Wordzie. Linie „Czas:"
i „Punkty:" są opcjonalne. Automatyczna numeracja Worda też działa:
akapit listy pierwszego poziomu to pytanie, drugiego — kolejna odpowiedź.

Czytamy .docx przez zipfile z biblioteki standardowej (bez python-docx),
tak samo jak report.py pisze .xlsx — import nie dokłada zależności.
Wynik (quiz + lista ostrzeżeń) trafia do edytora do przejrzenia; nic nie
jest zapisywane automatycznie.
"""

import io
import re
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LETTERS = "ABCD"

RE_TITLE = re.compile(r"^\s*(?:tytuł|tytul|title)\s*:\s*(.+)$", re.I)
RE_QUESTION = re.compile(r"^\s*(?:pytanie\s*)?(\d{1,3})\s*[.)]\s*(.*)$", re.I)
RE_ANSWER = re.compile(r"^\s*(\*?)\s*([A-Da-d])\s*[.)]\s*(.*?)\s*(\*?)\s*$")
RE_KEY = re.compile(r"^\s*(?:odpowiedź|odpowiedz|poprawna|answer|correct)\s*:\s*([A-Da-d])\b",  # polish-ok
                    re.I)
RE_TIME = re.compile(r"^\s*(?:czas|time)\s*:\s*(\d+)", re.I)
RE_POINTS = re.compile(r"^\s*(?:punkty|points)\s*:\s*(\d+)", re.I)


# --------------------------- odczyt plików ---------------------------
def _is_bold(run):
    """Czy fragment tekstu (w:r) jest pogrubiony."""
    rpr = run.find(W + "rPr")
    b = rpr.find(W + "b") if rpr is not None else None
    if b is None:
        return False
    return b.get(W + "val", "true").lower() not in ("0", "false", "off")


def docx_paragraphs(blob):
    """Akapity dokumentu Word jako lista (tekst, pogrubiony, poziom_listy).

    poziom_listy to None dla zwykłego akapitu, 0, 1, … dla automatycznej
    numeracji Worda (numer nie jest wtedy częścią tekstu)."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    out = []
    for p in root.iter(W + "p"):
        parts, bold_chars, all_chars = [], 0, 0
        for r in p.iter(W + "r"):
            chunk = []
            for el in r:
                if el.tag == W + "t":
                    chunk.append(el.text or "")
                elif el.tag == W + "tab":
                    chunk.append(" ")
                elif el.tag in (W + "br", W + "cr"):
                    chunk.append("\n")
            text = "".join(chunk)
            parts.append(text)
            n = len(text.strip())
            all_chars += n
            if _is_bold(r):
                bold_chars += n
        level = None
        ppr = p.find(W + "pPr")
        num = ppr.find(W + "numPr") if ppr is not None else None
        if num is not None:
            ilvl = num.find(W + "ilvl")
            level = int(ilvl.get(W + "val", "0")) if ilvl is not None else 0
        text = "".join(parts)
        bold = all_chars > 0 and bold_chars == all_chars
        for i, line in enumerate(text.split("\n")):
            # Miękki enter (Shift+Enter) dzieli akapit na linie; numeracja
            # listy dotyczy tylko pierwszej z nich.
            out.append((line, bold, level if i == 0 else None))
    return out


def text_paragraphs(blob):
    """Plik tekstowy: UTF-8 (z BOM lub bez), awaryjnie Windows-1250."""
    for enc in ("utf-8-sig", "cp1250"):
        try:
            text = blob.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return [(line, False, None) for line in text.splitlines()]


# --------------------------- parser ---------------------------
def parse(paragraphs, default_time=20, default_points=1000):
    """Zamienia akapity na quiz. Zwraca (quiz, ostrzeżenia)."""
    title = ""
    questions = []
    warnings = []
    cur = None

    def finish():
        if cur is None:
            return
        n = len(questions) + 1
        answers = [a for a in cur["answers"]]
        if not cur["text"].strip():
            warnings.append(f"Pytanie {n}: brak treści.")
        if len(answers) < 2:
            warnings.append(f"Pytanie {n}: mniej niż dwie odpowiedzi.")
        correct = cur["key"]
        if correct is None and len(cur["bold"]) == 1:
            correct = cur["bold"][0]
        if correct is None or correct >= len(answers):
            warnings.append(f"Pytanie {n}: nie wskazano poprawnej odpowiedzi — ustawiono A.")
            correct = 0
        questions.append({
            "text": cur["text"].strip(),
            "answers": (answers + ["", "", "", ""])[:4],
            "correct": correct,
            "time": cur["time"],
            "points": cur["points"],
            "media": None,
        })

    def new_question(text):
        return {"text": text, "answers": [], "key": None, "bold": [],
                "time": default_time, "points": default_points}

    for line, bold, level in paragraphs:
        s = line.strip()
        if not s:
            continue
        m = RE_TITLE.match(s)
        if m and not questions and cur is None:
            title = m.group(1).strip()
            continue
        m = RE_KEY.match(s)
        if m and cur is not None:
            cur["key"] = LETTERS.index(m.group(1).upper())
            continue
        m = RE_TIME.match(s)
        if m and cur is not None:
            cur["time"] = int(m.group(1))
            continue
        m = RE_POINTS.match(s)
        if m and cur is not None:
            cur["points"] = int(m.group(1))
            continue

        m = RE_ANSWER.match(s)
        if m and cur is not None:
            star = bool(m.group(1) or m.group(4))
            idx = LETTERS.index(m.group(2).upper())
            if idx != len(cur["answers"]):
                # Litera nie po kolei (np. drugie „A.") — to raczej treść.
                m = None
            else:
                cur["answers"].append(m.group(3))
                if star:
                    cur["key"] = idx
                if bold:
                    cur["bold"].append(idx)
                continue

        m = RE_QUESTION.match(s)
        if m:
            finish()
            cur = new_question(m.group(2))
            continue

        # Automatyczna numeracja Worda: poziom 0 = pytanie, głębiej = odpowiedź.
        if level is not None:
            if level == 0 and (cur is None or cur["answers"] or cur["text"]):
                finish()
                cur = new_question(s)
                continue
            if level > 0 and cur is not None and len(cur["answers"]) < 4:
                star = s.startswith("*")
                if star:
                    s = s[1:].strip()
                if bold:
                    cur["bold"].append(len(cur["answers"]))
                if star:
                    cur["key"] = len(cur["answers"])
                cur["answers"].append(s)
                continue

        if cur is None:
            # Tekst przed pierwszym pytaniem: pierwszy akapit traktujemy jak tytuł.
            if not title:
                title = s
            continue
        # Kontynuacja: dopisz do ostatniej odpowiedzi albo do treści pytania.
        if cur["answers"]:
            cur["answers"][-1] += " " + s
        else:
            cur["text"] += ("\n" if cur["text"] else "") + s
    finish()

    for q in questions:
        if len([a for a in q["answers"] if a.strip()]) > 4:
            warnings.append("Pytanie ma więcej niż 4 odpowiedzi — zostawiono A–D.")
    if not questions:
        warnings.append("Nie znaleziono pytań. Numeruj je „1.”, „2.”, a odpowiedzi „A.”, „B.”.")
    quiz = {"title": title, "questions": questions}
    return quiz, warnings


def import_file(name, blob):
    """Główne wejście: nazwa pliku (do rozpoznania typu) + zawartość."""
    lower = (name or "").lower()
    if lower.endswith(".docx") or blob[:2] == b"PK":
        try:
            paras = docx_paragraphs(blob)
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            raise ValueError("to nie jest poprawny plik .docx")
    elif lower.endswith(".doc"):
        raise ValueError("stary format .doc — zapisz plik w Wordzie jako .docx")
    else:
        paras = text_paragraphs(blob)
    quiz, warnings = parse(paras)
    if not quiz["title"]:
        base = re.sub(r"\.(docx|txt)$", "", name or "", flags=re.I).strip()
        quiz["title"] = base or "Zaimportowany quiz"
    return quiz, warnings


# --------------------------- szablon .docx ---------------------------
TEMPLATE_LINES = [
    ("Tytuł: Przykładowy test z Worda", True),
    ("", False),
    ("Zasady: pytanie zaczyna się numerem („1.”), odpowiedzi literami A–D. "
     "Poprawną wskaż linią „Odpowiedź: X”, gwiazdką przed literą albo "
     "pogrubieniem odpowiedzi. „Czas:” i „Punkty:” są opcjonalne. "
     "Wzory piszesz w dolarach, np. $\\frac{1}{2}$. Ten akapit możesz usunąć.", False),
    ("", False),
    ("1. Stolica Polski to:", False),
    ("A. Kraków", False),
    ("B. Warszawa", False),
    ("C. Gniezno", False),
    ("D. Poznań", False),
    ("Odpowiedź: B", False),
    ("", False),
    ("2. Ile to jest $\\frac{1}{2} + \\frac{1}{4}$?", False),
    ("*A. $\\frac{3}{4}$", False),
    ("B. $\\frac{2}{6}$", False),
    ("C. 1", False),
    ("D. $\\frac{1}{8}$", False),
    ("Czas: 30", False),
    ("", False),
    ("3. Który pierwiastek ma symbol O?", False),
    ("A. złoto", False),
    ("B. ołów", False),
    ("C. tlen", True),
    ("D. osm", False),
    ("Punkty: 500", False),
]


def _xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def template_docx():
    """Minimalny dokument Word z przykładowymi pytaniami (do pobrania)."""
    paras = []
    for text, bold in TEMPLATE_LINES:
        rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
        paras.append(f'<w:p><w:r>{rpr}<w:t xml:space="preserve">{_xml_escape(text)}'
                     f"</w:t></w:r></w:p>")
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(paras) + "</w:body></w:document>")
    files = {
        "[Content_Types].xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        "_rels/.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>",
        "word/document.xml": document,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()
