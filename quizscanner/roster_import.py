"""
Import listy uczniów z pliku CSV/TXT albo arkusza Excel (.xlsx).

Akceptujemy to, co nauczyciel realnie ma pod ręką:

  - eksport z dziennika lub arkusz: „Nazwisko;Imię" albo „Imię i nazwisko",
  - listę z numerami kart: „1;Anna Nowak",
  - zwykły plik tekstowy z jednym uczniem w linii.

Gdy w pliku nie ma numerów, uczniowie dostają kolejne numery kart od 0
w kolejności z pliku. Wiersz nagłówka („id", „imię", „nazwisko"…) jest
pomijany. Wynik trafia do edytora do przejrzenia — nic nie jest zapisywane
automatycznie.

Arkusz .xlsx czytamy przez zipfile z biblioteki standardowej (bez openpyxl).
"""

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET

# Słownik markerów to DICT_4X4_250 (aruco.py) — numery kart 0..249.
MAX_ID = 249

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
HEADER_WORDS = {"id", "nr", "numer", "lp", "lp.", "imię", "imie", "nazwisko",  # polish-ok
                "imię i nazwisko", "uczeń", "uczen", "name", "student", "karta"}  # polish-ok


# --------------------------- odczyt plików ---------------------------
def _decode(blob):
    for enc in ("utf-8-sig", "cp1250"):
        try:
            return blob.decode(enc)
        except UnicodeDecodeError:
            continue
    return blob.decode("latin-1")


def csv_rows(blob):
    text = _decode(blob)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        class dialect(csv.excel):
            delimiter = ";" if ";" in sample else ("\t" if "\t" in sample else ",")
    return [row for row in csv.reader(io.StringIO(text), dialect)]


def _col_index(ref):
    """'C7' -> 2 (indeks kolumny od zera)."""
    letters = re.match(r"[A-Z]+", ref or "A").group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def xlsx_rows(blob):
    """Wiersze pierwszego arkusza jako listy tekstów."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
        # Pierwszy arkusz według workbook.xml (nie zawsze to sheet1.xml).
        sheet_path = "xl/worksheets/sheet1.xml"
        try:
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            first = next(wb.iter(NS + "sheet"))
            rid = first.get(REL_NS + "id")
            rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            for rel in rels:
                if rel.get("Id") == rid:
                    target = rel.get("Target").lstrip("/")
                    sheet_path = target if target.startswith("xl/") else "xl/" + target
        except (KeyError, StopIteration, ET.ParseError):
            pass
        root = ET.fromstring(z.read(sheet_path))

    rows = []
    for r in root.iter(NS + "row"):
        cells = {}
        for c in r.iter(NS + "c"):
            kind = c.get("t")
            if kind == "inlineStr":
                val = "".join(t.text or "" for t in c.iter(NS + "t"))
            else:
                v = c.find(NS + "v")
                val = v.text if v is not None and v.text is not None else ""
                if kind == "s" and val.isdigit():
                    val = shared[int(val)] if int(val) < len(shared) else ""
                elif re.fullmatch(r"\d+\.0+", val):
                    val = val.split(".")[0]       # Excel zapisuje 7 jako 7.0
            cells[_col_index(c.get("r"))] = val
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


# --------------------------- interpretacja ---------------------------
def _is_id(s):
    return bool(re.fullmatch(r"\d{1,3}", s.strip()))


def parse_rows(rows):
    """Zamienia wiersze na {id: imię}. Zwraca (uczniowie, ostrzeżenia)."""
    rows = [[str(c).strip() for c in row] for row in rows]
    rows = [r for r in rows if any(r)]
    warnings = []
    if rows and all(c.lower() in HEADER_WORDS or not c for c in rows[0]):
        rows = rows[1:]

    # Kolumna z numerami kart: pierwsza, w której większość wierszy to liczby
    # (liczba porządkowa „1, 2, 3…" z dziennika też się nada).
    id_col = None
    width = max((len(r) for r in rows), default=0)
    for col in range(width):
        vals = [r[col] for r in rows if col < len(r) and r[col]]
        if vals and sum(_is_id(v) for v in vals) >= 0.8 * len(rows):
            id_col = col
            break

    students = {}
    next_id = 0
    for r in rows:
        name_parts = [c for i, c in enumerate(r)
                      if i != id_col and c and not _is_id(c)]
        name = " ".join(name_parts[:2]).strip()      # „Nazwisko Imię" z dwóch kolumn
        name = re.sub(r"\s+", " ", name)
        if not name:
            continue
        if id_col is not None and id_col < len(r) and _is_id(r[id_col]):
            mid = int(r[id_col])
        else:
            while next_id in students:
                next_id += 1
            mid = next_id
        if mid > MAX_ID:
            warnings.append(f"{name}: numer karty {mid} poza zakresem 0–{MAX_ID} — pominięto.")
            continue
        if mid in students:
            warnings.append(f"Numer karty {mid} powtarza się ({students[mid]}, {name}) "
                            "— zostawiono pierwszego.")
            continue
        students[mid] = name
    if not students:
        warnings.append("Nie znaleziono uczniów w pliku.")
    return students, warnings


def import_file(name, blob):
    lower = (name or "").lower()
    if lower.endswith(".xlsx") or blob[:2] == b"PK":
        try:
            rows = xlsx_rows(blob)
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            raise ValueError("to nie jest poprawny plik .xlsx")
    elif lower.endswith(".xls"):
        raise ValueError("stary format .xls — zapisz arkusz jako .xlsx albo CSV")
    else:
        rows = csv_rows(blob)
    return parse_rows(rows)


def export_csv(roster):
    """Lista uczniów jako CSV dla Excela (średnik, UTF-8 z BOM)."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(["id", "imię i nazwisko"])
    for mid in sorted(roster):
        w.writerow([mid, roster[mid]])
    return ("﻿" + buf.getvalue()).encode("utf-8")
