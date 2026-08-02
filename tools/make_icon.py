"""Generator ikony programu: assets/logo.svg  ->  assets/logo.ico.

Ikoną pliku .exe zawsze jest logo QuizScannera — nigdy domyślna ikona
PyInstallera. Plik assets/logo.ico leży w repozytorium (build tylko go
używa), a to narzędzie służy do odtworzenia go po zmianie logo:

    python tools/make_icon.py

W systemie nie ma rasteryzatora SVG (cairosvg, Inkscape, ImageMagick),
a aplikacja ma działać bez dodatkowych zależności, więc rysunek powtarza
geometrię z assets/logo.svg przy użyciu Pillow. Zmieniasz logo? Popraw
oba pliki i uruchom to narzędzie ponownie.

Rysujemy w powiększeniu (antyaliasing przez pomniejszenie na końcu),
a do .ico zapisujemy komplet rozmiarów od 16 do 256 pikseli.
"""

import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG = os.path.join(ROOT, "assets", "logo.svg")
ICO = os.path.join(ROOT, "assets", "logo.ico")

K = 4                      # powiększenie rysunku (płótno 512 * K)
N = 512 * K
ROZMIARY = [(s, s) for s in (256, 128, 64, 48, 32, 16)]

KAFEL_GORA = "#232a40"     # gradient ciemnego kafla
KAFEL_DOL = "#14161f"
OBWODKA = "#333b50"
TERAKOTA = "#e2603f"       # narożniki skanera i ptaszek
KARTA_GORA = "#ffffff"     # gradient karty odpowiedzi
KARTA_DOL = "#f2efe8"
KROPKI = ("#e8a13c", "#2f9fb3", "#8a7bef", "#4faa6a")   # A / B / C / D


def s(v):
    """Współrzędna z rysunku 512 x 512 na płótno w powiększeniu."""
    return int(round(v * K))


def gradient_pionowy(gora, dol, y0, y1):
    """Pionowy gradient na całym płótnie, przechodzący między y0 a y1."""
    img = Image.new("RGB", (N, N), dol)
    rysuj = ImageDraw.Draw(img)
    g = Image.new("RGB", (1, 1), gora).getpixel((0, 0))
    d = Image.new("RGB", (1, 1), dol).getpixel((0, 0))
    wysokosc = max(1, y1 - y0)
    for y in range(N):
        t = min(1.0, max(0.0, (y - y0) / wysokosc))
        rysuj.line([(0, y), (N, y)], fill=tuple(
            round(a + (b - a) * t) for a, b in zip(g, d)))
    return img


def prostokat_zaokraglony(xy, promien):
    """Maska (tryb L) zaokrąglonego prostokąta na płótnie."""
    maska = Image.new("L", (N, N), 0)
    ImageDraw.Draw(maska).rounded_rectangle(xy, radius=promien, fill=255)
    return maska


def kreska(rysuj, punkty, grubosc, kolor):
    """Łamana z zaokrąglonymi końcami i załamaniami (odpowiednik
    stroke-linecap/linejoin="round" z SVG)."""
    rysuj.line(punkty, fill=kolor, width=grubosc)
    r = grubosc / 2
    for x, y in punkty:
        rysuj.ellipse([x - r, y - r, x + r, y + r], fill=kolor)


def karta():
    """Warstwa z kartą odpowiedzi — w SVG obrócona o 6 stopni."""
    warstwa = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    rysuj = ImageDraw.Draw(warstwa)

    # cień pod kartą (w SVG czarny z przezroczystością 0.22)
    rysuj.rounded_rectangle([s(155), s(160), s(365), s(370)],
                            radius=s(36), fill=(0, 0, 0, 56))

    # sama karta z delikatnym gradientem
    lico = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    lico.paste(gradient_pionowy(KARTA_GORA, KARTA_DOL, s(151), s(361)),
               mask=prostokat_zaokraglony([s(151), s(151), s(361), s(361)], s(36)))
    warstwa = Image.alpha_composite(warstwa, lico)
    rysuj = ImageDraw.Draw(warstwa)

    # ptaszek = poprawna odpowiedź
    kreska(rysuj, [(s(205), s(232)), (s(243), s(272)), (s(327), s(188))],
           s(29), TERAKOTA)

    # kropki A / B / C / D
    for x, kolor in zip((205, 239, 273, 307), KROPKI):
        rysuj.ellipse([s(x - 13), s(318 - 13), s(x + 13), s(318 + 13)], fill=kolor)

    return warstwa.rotate(6, resample=Image.BICUBIC, center=(s(256), s(256)))


def zbuduj():
    logo = Image.new("RGBA", (N, N), (0, 0, 0, 0))

    # ciemny kafel z obwódką
    logo.paste(gradient_pionowy(KAFEL_GORA, KAFEL_DOL, s(24), s(488)),
               mask=prostokat_zaokraglony([s(24), s(24), s(488), s(488)], s(106)))
    ImageDraw.Draw(logo).rounded_rectangle(
        [s(25), s(25), s(487), s(487)], radius=s(105), outline=OBWODKA, width=s(2))

    # narożniki „skanera" — sygnatura projektu
    rysuj = ImageDraw.Draw(logo)
    for punkty in (
        [(96, 140), (96, 96), (140, 96)],
        [(372, 96), (416, 96), (416, 140)],
        [(96, 372), (96, 416), (140, 416)],
        [(372, 416), (416, 416), (416, 372)],
    ):
        kreska(rysuj, [(s(x), s(y)) for x, y in punkty], s(16), TERAKOTA)

    logo = Image.alpha_composite(logo, karta())
    return logo.resize((256, 256), Image.LANCZOS)


def main():
    if not os.path.exists(SVG):
        print(f"Brak pliku {SVG} — ikona powstaje na wzór logo z tego pliku.")
        return 1
    zbuduj().save(ICO, format="ICO", sizes=ROZMIARY)
    kb = os.path.getsize(ICO) / 1024
    rozmiary = ", ".join(str(w) for w, _ in ROZMIARY)
    print(f"Zapisano {os.path.relpath(ICO, ROOT)} ({kb:.0f} kB, rozmiary: {rozmiary} px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
