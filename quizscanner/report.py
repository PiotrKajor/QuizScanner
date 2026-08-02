"""
Raport z rozegranego quizu: zbieranie danych i eksport do plików.

Jedno źródło danych (`build`) i kilka formatów wyjściowych:

    dane = build(session)
    blob, ctype, nazwa = render(dane, "pdf")

Obsługiwane formaty: pdf, xlsx, csv, html, json, txt.
PDF powstaje przez Pillow (biblioteka i tak jest wymagana przez generator
kart), a XLSX przez zipfile z biblioteki standardowej — raport nie dokłada
żadnej nowej zależności. Wzory LaTeX z pytań zamienia na tekst tex_to_plain().
"""

import csv
import datetime as dt
import io
import json
import os
import re

from . import VERSION
from .paths import ascii_pl

LETTERS = ["A", "B", "C", "D"]
FORMATS = ["pdf", "csv", "xlsx", "html", "json", "txt"]

# --------------------------- LaTeX -> tekst ---------------------------
# Wzory w pytaniach zapisujemy jako LaTeX w dolarach ($\frac{1}{2}$) i na
# tablicy renderuje je KaTeX. Raport to plik do wydruku albo arkusza, więc
# zamieniamy zapis na czytelny tekst z symbolami Unicode.
#
# ponytail: to konwerter przybliżony, nie parser LaTeX-a. Radzi sobie z tym,
# co realnie pojawia się w szkolnym pytaniu; przy egzotycznej składni zostawia
# nazwę polecenia. Gdyby raporty miały kiedyś odwzorować wzór wiernie, trzeba
# renderować je jako obrazki — nie rozbudowywać tego o kolejne wyjątki.
TEX_SYMBOLS = {
    r"\cdot": "·", r"\times": "×", r"\div": "÷", r"\pm": "±", r"\mp": "∓",
    r"\leq": "≤", r"\le": "≤", r"\geq": "≥", r"\ge": "≥", r"\neq": "≠",
    r"\ne": "≠", r"\approx": "≈", r"\equiv": "≡", r"\propto": "∝",
    r"\infty": "∞", r"\to": "→", r"\rightarrow": "→", r"\Rightarrow": "⇒",
    r"\Leftrightarrow": "⇔", r"\in": "∈", r"\notin": "∉", r"\subset": "⊂",
    r"\subseteq": "⊆", r"\cup": "∪", r"\cap": "∩", r"\emptyset": "∅",
    r"\forall": "∀", r"\exists": "∃", r"\land": "∧", r"\lor": "∨",
    r"\neg": "¬", r"\sum": "∑", r"\prod": "∏", r"\int": "∫", r"\oint": "∮",
    r"\partial": "∂", r"\nabla": "∇", r"\angle": "∠", r"\perp": "⊥",
    r"\parallel": "∥", r"\triangle": "△", r"\cong": "≅", r"\sim": "∼",
    r"\degree": "°", r"\circ": "°", r"\ldots": "…", r"\dots": "…",
    r"\setminus": "∖", r"\cdots": "⋯", r"\ast": "∗",
    r"\mathbb{N}": "ℕ", r"\mathbb{Z}": "ℤ", r"\mathbb{Q}": "ℚ",
    r"\mathbb{R}": "ℝ", r"\mathbb{C}": "ℂ",
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ε", r"\varepsilon": "ε", r"\theta": "θ", r"\lambda": "λ",
    r"\mu": "μ", r"\pi": "π", r"\rho": "ρ", r"\sigma": "σ", r"\tau": "τ",
    r"\phi": "φ", r"\varphi": "φ", r"\omega": "ω", r"\Delta": "Δ",
    r"\Sigma": "Σ", r"\Pi": "Π", r"\Omega": "Ω", r"\Theta": "Θ",
    r"\Lambda": "Λ",
}
SUP = str.maketrans("0123456789+-n()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ⁽⁾")
SUB = str.maketrans("0123456789+-n()", "₀₁₂₃₄₅₆₇₈₉₊₋ₙ₍₎")

_BRACED = r"\{([^{}]*)\}"


def _script(body, table, marker):
    """Indeks górny/dolny: cyfry idą na Unicode, reszta zostaje z ^ lub _."""
    if body and all(c in "0123456789+-n()" for c in body):
        return body.translate(table)
    return marker + body


def tex_to_plain(text):
    """Zamienia zapis $LaTeX$ na czytelny tekst (do raportów i wydruków)."""
    text = str(text or "")
    if "$" not in text:
        return text

    def convert(code):
        # Nawiasy klamrowe pisane wprost (\{ \}) chowamy, żeby nie zniknęły
        # razem z klamrami składniowymi na końcu konwersji.
        s = code.replace(r"\{", "\u0001").replace(r"\}", "\u0002")
        s = re.sub(r"\\begin\{[a-z]+\*?\}|\\end\{[a-z]+\*?\}", " ", s)
        s = s.replace(r"\\", "; ").replace(r"\left", "").replace(r"\right", "")
        s = re.sub(r"\\[,;:!\s]", " ", s)
        s = re.sub(r"\\sqrt\[([^\]]*)\]" + _BRACED,
                   lambda m: f"{_script(m.group(1), SUP, '')}√({m.group(2)})", s)
        s = re.sub(r"\\sqrt" + _BRACED, lambda m: f"√({m.group(1)})", s)
        s = re.sub(r"\\d?frac" + _BRACED + _BRACED,
                   lambda m: f"({m.group(1)})/({m.group(2)})", s)
        s = re.sub(r"\\binom" + _BRACED + _BRACED,
                   lambda m: f"C({m.group(1)}, {m.group(2)})", s)
        s = re.sub(r"\\(?:overline|bar)" + _BRACED, lambda m: m.group(1) + "\u0304", s)
        s = re.sub(r"\\vec" + _BRACED, lambda m: m.group(1) + "\u20d7", s)
        s = re.sub(r"\\text(?:bf|it|rm)?" + _BRACED, lambda m: m.group(1), s)
        # Od najdłuższego polecenia: inaczej \in zjadłoby początek \int.
        for tex in sorted(TEX_SYMBOLS, key=len, reverse=True):
            s = s.replace(tex, TEX_SYMBOLS[tex])
        s = re.sub(r"\^" + _BRACED, lambda m: _script(m.group(1), SUP, "^"), s)
        s = re.sub(r"_" + _BRACED, lambda m: _script(m.group(1), SUB, "_"), s)
        s = re.sub(r"\^(\w)", lambda m: _script(m.group(1), SUP, "^"), s)
        s = re.sub(r"_(\w)", lambda m: _script(m.group(1), SUB, "_"), s)
        s = re.sub(r"\\([a-zA-Z]+)", r"\1", s)      # reszta poleceń: sama nazwa
        s = s.replace("{", "").replace("}", "")
        s = s.replace("\u0001", "{").replace("\u0002", "}")
        return re.sub(r"\s{2,}", " ", s).strip()

    out = re.sub(r"\$\$([\s\S]+?)\$\$|(?<!\\)\$([^$\n]+?)(?<!\\)\$",
                 lambda m: convert(m.group(1) if m.group(1) is not None else m.group(2)),
                 text)
    return out.replace(r"\$", "$")


CONTENT_TYPES = {
    "json": "application/json; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "html": "text/html; charset=utf-8",
    "txt": "text/plain; charset=utf-8",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


# --------------------------- dane ---------------------------
def build(session):
    """Buduje pełny raport (słownik) z bieżącego stanu sesji."""
    with session.lock:
        roster = dict(session.roster)
        scores = dict(session.scores)
        title = session.quiz.get("title", "")
        quiz_name = session.quiz_name
        # Powrót do pytania i ponowne "Pokaż wynik" dokłada drugi wpis dla tego
        # samego pytania -- liczy się ostatni.
        by_index = {}
        for i, h in enumerate(session.history):
            by_index[h.get("index", i)] = h
        history = [by_index[k] for k in sorted(by_index)]

    questions = []
    for n, h in enumerate(history, 1):
        answers = h.get("answers", {})
        dist = {L: 0 for L in LETTERS}
        for a in answers.values():
            if a.get("answer") in dist:
                dist[a["answer"]] += 1
        ok = sum(1 for a in answers.values() if a.get("correct"))
        # text/correct_text zostają w oryginale (z LaTeX-em) — to źródło prawdy
        # w eksporcie JSON; *_plain trafia tam, gdzie nie ma czym renderować.
        questions.append({
            "n": n,
            "text": h.get("question", ""),
            "text_plain": tex_to_plain(h.get("question", "")),
            "options": h.get("options", []),
            "correct": h.get("correct"),
            "correct_text": h.get("correct_text", ""),
            "correct_text_plain": tex_to_plain(h.get("correct_text", "")),
            "answered": len(answers),
            "correct_count": ok,
            "percent": round(100.0 * ok / len(answers), 1) if answers else 0.0,
            "distribution": dist,
        })

    ids = sorted(set(list(scores) + [i for h in history for i in h.get("answers", {})]))
    students = []
    for mid in ids:
        per_q, ok, answered = [], 0, 0
        for h in history:
            a = h.get("answers", {}).get(mid)
            if not a:
                per_q.append("")
                continue
            answered += 1
            ok += 1 if a.get("correct") else 0
            per_q.append(a.get("answer", ""))
        students.append({
            "id": mid,
            "name": roster.get(mid, f"#{mid}"),
            "score": scores.get(mid, 0),
            "answered": answered,
            "correct": ok,
            "percent": round(100.0 * ok / len(history), 1) if history else 0.0,
            "answers": per_q,
        })
    students.sort(key=lambda s: (-s["score"], s["name"].lower()))
    for place, s in enumerate(students, 1):
        s["place"] = place

    hardest = min(questions, key=lambda q: q["percent"]) if questions else None
    return {
        "app": "QuizScanner",
        "version": VERSION,
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "quiz_title": title,
        "quiz_file": quiz_name,
        "questions": questions,
        "students": students,
        "summary": {
            "students": len(students),
            "questions": len(questions),
            "avg_score": round(sum(s["score"] for s in students) / len(students), 1)
                         if students else 0,
            "avg_percent": round(sum(s["percent"] for s in students) / len(students), 1)
                           if students else 0.0,
            "best": students[0]["name"] if students else "",
            "hardest_n": hardest["n"] if hardest else None,
            "hardest_text": hardest["text"] if hardest else "",
            "hardest_text_plain": hardest["text_plain"] if hardest else "",
            "hardest_percent": hardest["percent"] if hardest else None,
        },
    }


def file_stem(data):
    """Bezpieczna nazwa pliku raportu: raport_<quiz>_<data>.

    Czysto ASCII: nazwa trafia do nagłówka Content-Disposition, a ten
    http.server koduje w latin-1 — polska litera wywracała tam pobieranie.
    """
    base = data.get("quiz_file") or data.get("quiz_title") or "quiz"
    base = re.sub(r"[^A-Za-z0-9_\- ]", "", ascii_pl(base)).strip().replace(" ", "_")
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    return f"raport_{base or 'quiz'}_{stamp}"


# --------------------------- formaty ---------------------------
def _rows(data):
    """Wspólna tabela wynikowa (nagłówek + wiersze) dla CSV i XLSX."""
    head = ["miejsce", "id", "uczeń", "punkty", "poprawne", "odpowiedzi", "%"]
    head += [f"P{q['n']}" for q in data["questions"]]
    rows = [[s["place"], s["id"], s["name"], s["score"], s["correct"],
             s["answered"], s["percent"]] + s["answers"] for s in data["students"]]
    return head, rows


def to_csv(data):
    # Średnik + BOM: Excel z polskimi ustawieniami otwiera taki plik od razu
    # w kolumnach, bez kreatora importu.
    buf = io.StringIO()
    wr = csv.writer(buf, delimiter=";")
    head, rows = _rows(data)
    wr.writerow(head)
    wr.writerows(rows)
    wr.writerow([])
    wr.writerow(["pytanie", "treść", "poprawna", "odpowiedziało", "poprawnie", "%"])
    for q in data["questions"]:
        wr.writerow([q["n"], q["text_plain"], q["correct"] or "",
                     q["answered"], q["correct_count"], q["percent"]])
    return buf.getvalue().encode("utf-8-sig")


def to_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def to_txt(data):
    s = data["summary"]
    out = [f"{data['app']} {data['version']} — raport",
           f"Quiz: {data['quiz_title']}",
           f"Data: {data['generated']}",
           f"Uczniowie: {s['students']}   Pytania: {s['questions']}   "
           f"Średnio poprawnych: {s['avg_percent']}%", "",
           "RANKING", "-" * 52]
    for st in data["students"]:
        out.append(f"{st['place']:>3}. {st['name']:<28} {st['score']:>6} pkt   "
                   f"{st['correct']}/{s['questions']} ({st['percent']}%)")
    out += ["", "PYTANIA", "-" * 52]
    for q in data["questions"]:
        out.append(f"{q['n']:>3}. [{q['correct'] or '-'}] {q['text_plain']}")
        out.append(f"     poprawnie {q['correct_count']}/{q['answered']} ({q['percent']}%)"
                   f"   A/B/C/D: " + "/".join(str(q["distribution"][L]) for L in LETTERS))
    return "\n".join(out).encode("utf-8")


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def to_html(data):
    s = data["summary"]
    rank = "".join(
        f"<tr><td class=p>{st['place']}</td><td>{_esc(st['name'])}</td>"
        f"<td class=n>#{st['id']}</td><td class=n>{st['score']}</td>"
        f"<td class=n>{st['correct']}/{s['questions']}</td>"
        f"<td class=n>{st['percent']}%</td></tr>" for st in data["students"])
    qs = "".join(
        f"<tr><td class=p>{q['n']}</td><td>{_esc(q['text_plain'])}"
        f"<div class=sub>{_esc(q['correct_text_plain'])}</div></td>"
        f"<td class=n><b>{q['correct'] or '—'}</b></td>"
        f"<td class=n>{q['correct_count']}/{q['answered']}</td>"
        f"<td class=bar><i style='width:{q['percent']}%'></i><span>{q['percent']}%</span></td>"
        f"<td class=n>" + "/".join(str(q["distribution"][L]) for L in LETTERS) + "</td></tr>"
        for q in data["questions"])
    return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<title>Raport — {_esc(data['quiz_title'])}</title><style>
:root{{--ac:#e2603f;--ink:#14161f;--line:#e6e2d8;--muted:#868b99}}
*{{box-sizing:border-box}}
body{{font:15px/1.5 "Segoe UI",system-ui,Arial,sans-serif;color:#232733;
  background:#f4f2ec;margin:0;padding:32px}}
.wrap{{max-width:980px;margin:0 auto;background:#fff;border:1px solid var(--line);
  border-radius:16px;padding:32px}}
h1{{margin:0 0 4px;font-size:26px}} h2{{font-size:13px;text-transform:uppercase;
  letter-spacing:.1em;color:var(--muted);margin:32px 0 10px}}
.head{{border-bottom:3px solid var(--ac);padding-bottom:16px}}
.meta{{color:var(--muted);font-size:13px}}
.cards{{display:flex;flex-wrap:wrap;gap:12px;margin-top:18px}}
.card{{flex:1 1 140px;border:1px solid var(--line);border-radius:12px;padding:12px 16px}}
.card b{{display:block;font-size:24px}} .card span{{font-size:11px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);padding:8px;border-bottom:2px solid var(--line)}}
td{{padding:8px;border-bottom:1px solid var(--line);vertical-align:top}}
td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.p{{font-weight:800;color:var(--ac);width:44px}}
tr:nth-child(-n+3) td.p{{font-size:16px}}
.sub{{color:var(--muted);font-size:12px}}
td.bar{{position:relative;min-width:120px}}
td.bar i{{display:block;height:8px;border-radius:5px;background:var(--ac);opacity:.75}}
td.bar span{{font-size:12px;color:var(--muted)}}
footer{{margin-top:28px;color:var(--muted);font-size:12px;text-align:center}}
@media print{{body{{background:#fff;padding:0}}.wrap{{border:0;padding:0}}}}
</style></head><body><div class="wrap">
<div class="head"><h1>{_esc(data['quiz_title'] or 'Quiz')}</h1>
<div class="meta">Raport QuizScanner {data['version']} · {_esc(data['generated'].replace('T', ' '))}</div></div>
<div class="cards">
  <div class="card"><span>Uczniowie</span><b>{s['students']}</b></div>
  <div class="card"><span>Pytania</span><b>{s['questions']}</b></div>
  <div class="card"><span>Średnio poprawnych</span><b>{s['avg_percent']}%</b></div>
  <div class="card"><span>Średnio punktów</span><b>{s['avg_score']}</b></div>
  <div class="card"><span>Najlepszy wynik</span><b style="font-size:17px">{_esc(s['best'] or '—')}</b></div>
</div>
<h2>Ranking</h2>
<table><thead><tr><th>#</th><th>Uczeń</th><th class=n>ID</th><th class=n>Punkty</th>
<th class=n>Poprawne</th><th class=n>Skuteczność</th></tr></thead><tbody>{rank}</tbody></table>
<h2>Pytania</h2>
<table><thead><tr><th>#</th><th>Treść</th><th class=n>Popr.</th><th class=n>Trafień</th>
<th>Skuteczność</th><th class=n>A/B/C/D</th></tr></thead><tbody>{qs}</tbody></table>
<footer>Wygenerowano przez QuizScanner — github.com/PiotrKajor/QuizScanner</footer>
</div></body></html>""".encode("utf-8")


def to_xlsx(data):
    """Arkusz Excela bez dodatkowych bibliotek: XLSX to ZIP z plikami XML."""
    import zipfile

    head, rows = _rows(data)
    sheet = [head] + rows

    def cell(ref, val):
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return f'<c r="{ref}"><v>{val}</v></c>'
        return (f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                f'{_esc(val)}</t></is></c>')

    def col(i):
        name = ""
        while True:
            name = chr(ord("A") + i % 26) + name
            i = i // 26 - 1
            if i < 0:
                return name

    body = ""
    for r, row in enumerate(sheet, 1):
        cells = "".join(cell(f"{col(c)}{r}", v) for c, v in enumerate(row))
        body += f'<row r="{r}">{cells}</row>'

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="Wyniki" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                   '</Relationships>')
        z.writestr("xl/worksheets/sheet1.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   f'<sheetData>{body}</sheetData></worksheet>')
    return buf.getvalue()


# --------------------------- PDF ---------------------------
# Kartki A4 rysowane przez Pillow (jak karty do druku). Dzięki temu polskie
# znaki wychodzą poprawnie i nie potrzeba reportlab/fpdf.
A4 = (1240, 1754)          # A4 przy 150 DPI
MARGIN = 90


def to_pdf(data):
    from PIL import Image, ImageDraw
    from .cards import get_font

    ink, muted, accent, line = (35, 39, 51), (134, 139, 153), (226, 96, 63), (225, 221, 211)
    pages, page, draw, y = [], None, None, 0

    def new_page():
        nonlocal page, draw, y
        page = Image.new("RGB", A4, "white")
        draw = ImageDraw.Draw(page)
        pages.append(page)
        y = MARGIN

    def space(need):
        if y + need > A4[1] - MARGIN:
            new_page()

    def text(s, x, size=22, bold=False, color=ink):
        draw.text((x, y), str(s), font=get_font(size, bold), fill=color)

    def clip(s, size, width, bold=False):
        """Skraca napis tak, by zmieścił się w zadanej szerokości."""
        font = get_font(size, bold)
        s = str(s)
        if draw.textlength(s, font=font) <= width:
            return s
        while s and draw.textlength(s + "…", font=font) > width:
            s = s[:-1]
        return s + "…"

    new_page()
    s = data["summary"]
    text(data["quiz_title"] or "Quiz", MARGIN, 40, True)
    y += 54
    text(f"Raport QuizScanner {data['version']} · {data['generated'].replace('T', ' ')}",
         MARGIN, 20, False, muted)
    y += 32
    draw.rectangle([MARGIN, y, A4[0] - MARGIN, y + 4], fill=accent)
    y += 34

    stats = [("Uczniowie", s["students"]), ("Pytania", s["questions"]),
             ("Śr. poprawnych", f"{s['avg_percent']}%"), ("Śr. punktów", s["avg_score"])]
    colw = (A4[0] - 2 * MARGIN) // len(stats)
    for i, (k, v) in enumerate(stats):
        x = MARGIN + i * colw
        draw.text((x, y), k.upper(), font=get_font(16, True), fill=muted)
        draw.text((x, y + 24), str(v), font=get_font(34, True), fill=ink)
    y += 90

    def header(title, cols):
        nonlocal y
        space(120)
        text(title.upper(), MARGIN, 18, True, accent)
        y += 30
        for label, x, align_right in cols:
            w = draw.textlength(label, font=get_font(16, True))
            draw.text((x - w if align_right else x, y), label,
                      font=get_font(16, True), fill=muted)
        y += 24
        draw.line([MARGIN, y, A4[0] - MARGIN, y], fill=line, width=2)
        y += 12

    right = A4[0] - MARGIN
    rank_cols = [("#", MARGIN, False), ("UCZEŃ", MARGIN + 60, False),
                 ("PUNKTY", right - 220, True), ("POPRAWNE", right - 90, True),
                 ("%", right, True)]
    header("Ranking", rank_cols)
    for st in data["students"]:
        space(46)
        if y == MARGIN:
            header("Ranking (c.d.)", rank_cols)
        text(st["place"], MARGIN, 22, True, accent)
        text(clip(st["name"], 22, right - 320 - MARGIN), MARGIN + 60, 22)
        for val, x in ((st["score"], right - 220),
                       (f"{st['correct']}/{s['questions']}", right - 90),
                       (f"{st['percent']}%", right)):
            w = draw.textlength(str(val), font=get_font(22))
            draw.text((x - w, y), str(val), font=get_font(22), fill=ink)
        y += 30
        draw.line([MARGIN, y, right, y], fill=line)
        y += 8

    y += 30
    q_cols = [("#", MARGIN, False), ("PYTANIE", MARGIN + 60, False),
              ("POPR.", right - 200, True), ("TRAFIEŃ", right - 90, True),
              ("%", right, True)]
    header("Pytania", q_cols)
    for q in data["questions"]:
        space(56)
        if y == MARGIN:
            header("Pytania (c.d.)", q_cols)
        text(q["n"], MARGIN, 22, True, accent)
        text(clip(q["text_plain"], 22, right - 300 - MARGIN), MARGIN + 60, 22)
        for val, x in ((q["correct"] or "—", right - 200),
                       (f"{q['correct_count']}/{q['answered']}", right - 90),
                       (f"{q['percent']}%", right)):
            w = draw.textlength(str(val), font=get_font(22, True))
            draw.text((x - w, y), str(val), font=get_font(22, True), fill=ink)
        y += 26
        dist = "  ".join(f"{L}: {q['distribution'][L]}" for L in LETTERS)
        text(dist, MARGIN + 60, 17, False, muted)
        y += 26
        draw.line([MARGIN, y, right, y], fill=line)
        y += 8

    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:],
                  resolution=150.0)
    return buf.getvalue()


RENDERERS = {"json": to_json, "csv": to_csv, "html": to_html,
             "txt": to_txt, "pdf": to_pdf, "xlsx": to_xlsx}


def render(data, fmt):
    """Zwraca (bajty, content-type, nazwa pliku) dla wybranego formatu."""
    fmt = (fmt or "pdf").lower()
    if fmt not in RENDERERS:
        raise ValueError(f"nieznany format: {fmt}")
    return RENDERERS[fmt](data), CONTENT_TYPES[fmt], f"{file_stem(data)}.{fmt}"


def save(data, out_dir, formats=("json", "csv", "html")):
    """Zapisuje raport na dysk. Zwraca listę utworzonych plików."""
    os.makedirs(out_dir, exist_ok=True)
    stem = file_stem(data)
    paths = []
    for fmt in formats:
        try:
            blob = RENDERERS[fmt](data)
        except Exception:
            continue          # jeden zepsuty format nie może zabrać reszty
        path = os.path.join(out_dir, f"{stem}.{fmt}")
        with open(path, "wb") as f:
            f.write(blob)
        paths.append(path)
    return paths


def list_saved(out_dir, limit=25):
    """Ostatnio zapisane raporty (najnowsze pierwsze)."""
    if not os.path.isdir(out_dir):
        return []
    items = []
    for name in os.listdir(out_dir):
        path = os.path.join(out_dir, name)
        if os.path.isfile(path):
            items.append({"file": name, "size": os.path.getsize(path),
                          "mtime": os.path.getmtime(path)})
    items.sort(key=lambda i: i["mtime"], reverse=True)
    return items[:limit]
