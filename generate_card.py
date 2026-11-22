#!/usr/bin/env python3
import argparse
import io
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is missing. Install it with:  pip install pillow")

BASE = Path(__file__).resolve().parent

# 1. DETAILS
TITLE = "yaswanthkorukonda"
IMAGE_SOURCE = "assets/profile.png"

# Art width in characters. More columns = more detail, but the art is always scaled to the same box, so each character just gets smaller.
# Good range: 80 to 120.
ART_COLS = 500
ART_INVERT = False
# YYYYMMDD
BIRTH_DATE = date(2001, 10, 20)

# Each section is (name, rows). The first section's name is replaced by TITLE.
# A row is (key parts, value). Use None for an empty dotted line.
# A key with two parts, like ("Languages", "Programming"), shows as Languages.Programming
# The value "{age}" is replaced by the calculated uptime.
SECTIONS = [
    ("Main", [
        (("OS",), "Windows, Android"),
        (("Uptime",), "{age}"),
        (("Host",), "LTM"),
        (("Kernel",), "Sitecore Developer"),
        (("IDE",), "VS Code, Visual Studio"),
        None,
        (("Languages", "Programming"), "C#, Python, Java, JavaScript"),
        (("Languages", "Computer"), "HTML, CSS"),
        (("Languages", "Real"), "Telugu, English"),
        None,
        (("Hobbies", "Creative"), "Photography, Photoshop"),
        (("Hobbies", "Leisure"), "Cinema, Video Games"),
    ]),
    ("Contact", [
        (("Email", "Personal"), "yaswanthkorukonda2001@gmail.com"),
        (("LinkedIn",), "yaswanthkorukonda"),
        (("GitHub",), "yaswanthkorukonda"),
        (("Instagram",), "yaswanthkorukonda"),
        (("Telegram",), "yaswanthkorukonda"),
    ]),
    ("Certifications", [
        (("Sitecore",), "10 .NET, XM Cloud, Content Hub"),
        (("Microsoft",), "Azure AZ-204, Azure AZ-900"),
    ]),
]

# 2. LAYOUT
WIDTH = 985
LEFT_X = 15          # left edge of the art box
RIGHT_X = 390        # x position of the text column
TOP_Y = 30
LINE_HEIGHT = 20     # pixels between text rows
LINE_WIDTH = 58      # characters per line in the text column (safe on mobile)
EM = "—"

# Monospace fonts are about 0.6 em wide. The card's font setting makes Consolas match that.
CHAR_W = 0.6         # character width, in em
LINE_H = 1.25        # art line step, in em
CELL_ASPECT = CHAR_W / LINE_H   # width / height of one character cell
RAMP = " .:-=+*#%@"  # light to dense. Bright pixels become dense characters.

HEAD = """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="{width}px" height="{height}px" font-size="16px">
<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: #ffa657;}}
.value {{fill: #a5d6ff;}}
.cc {{fill: #616e7f;}}
text, tspan {{white-space: pre;}}
</style>
<rect width="{width}px" height="{height}px" fill="#161b22" rx="15"/>
"""


# ---------------------------------------------------------------- text column
def uptime(born, today):
    """Age as 'X years, Y months, Z days'."""
    years = today.year - born.year
    months = today.month - born.month
    days = today.day - born.day
    if days < 0:
        months -= 1
        days += (today.replace(day=1) - timedelta(days=1)).day
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months, {days} days"


def header_line(text):
    """Heading such as: yaswanthkorukonda -————————-—-"""
    fill = LINE_WIDTH - len(text) - 5
    return ("", escape(text), " -" + EM * fill + "-" + EM + "-")


def blank_line():
    return (' class="cc"', ". ", "")


def data_line(key_parts, value, age):
    value = value.replace("{age}", age)
    key = ".".join(key_parts)
    dots = LINE_WIDTH - 5 - len(key) - len(value)
    if dots < 3:
        raise SystemExit(
            f"Line too long: {key}: {value}\n"
            f"Shorten the value or raise LINE_WIDTH (now {LINE_WIDTH})."
        )
    key_xml = ".".join(f'<tspan class="key">{escape(p)}</tspan>' for p in key_parts)
    rest = (
        f'{key_xml}:<tspan class="cc"> {"." * dots} </tspan>'
        f'<tspan class="value">{escape(value)}</tspan>'
    )
    return (' class="cc"', ". ", rest)


def build_text_lines(age):
    lines = []
    for i, (name, rows) in enumerate(SECTIONS):
        if i:
            lines.append(None)  # empty row between sections
        lines.append(header_line(TITLE if i == 0 else "- " + name))
        for row in rows:
            lines.append(blank_line() if row is None else data_line(row[0], row[1], age))
    return lines


# ------------------------------------------------------------------ ASCII art
def load_image(source):
    """Open a photo from a path or URL. Transparent areas become black (blank art)."""
    if source.startswith(("http://", "https://", "file://")):
        request = urllib.request.Request(source, headers={"User-Agent": "profile-card"})
        with urllib.request.urlopen(request, timeout=30) as response:
            img = Image.open(io.BytesIO(response.read()))
    else:
        path = Path(source)
        if not path.is_absolute():
            path = BASE / path
        if not path.exists():
            raise SystemExit(f"Photo not found: {path}\nCheck IMAGE_SOURCE in generate_card.py.")
        img = Image.open(path)
    img = img.convert("RGBA")
    canvas = Image.new("RGBA", img.size, (0, 0, 0, 255))
    canvas.alpha_composite(img)
    return canvas.convert("L")


def make_art(gray, cols, invert):
    """Return the art as a list of text lines, plus its size in characters."""
    gray = ImageOps.autocontrast(gray, cutoff=2)
    width, height = gray.size
    rows = max(1, round(cols * height / width * CELL_ASPECT))
    small = gray.resize((cols, rows), Image.LANCZOS)
    ramp = RAMP[::-1] if invert else RAMP
    last = len(ramp) - 1
    pixels = small.load()
    art = []
    for y in range(rows):
        art.append("".join(ramp[pixels[x, y] * last // 255] for x in range(cols)).rstrip())
    return art, cols, rows


# ----------------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description="Build the profile card (dark_mode.svg)")
    parser.add_argument("--image", default=IMAGE_SOURCE, help="photo path or URL")
    parser.add_argument("--cols", type=int, default=ART_COLS, help="art width in characters")
    parser.add_argument("--invert", action="store_true", help="swap light and dark in the art")
    parser.add_argument("--out", default=str(BASE / "dark_mode.svg"), help="output file")
    args = parser.parse_args()

    if args.cols > 160:
        print(f"Note: {args.cols} columns is more than the card can show. 80 to 120 is enough.")

    age = uptime(BIRTH_DATE, date.today())
    text_lines = build_text_lines(age)
    height = TOP_Y + LINE_HEIGHT * len(text_lines)

    art, cols, rows = make_art(load_image(args.image), args.cols, args.invert or ART_INVERT)

    # The art always fills the same box, whatever the number of characters.
    box_x, box_y = LEFT_X, 15
    box_w, box_h = RIGHT_X - 15 - LEFT_X, height - 30
    font = min(box_w / (CHAR_W * cols), box_h / (LINE_H * rows), 24)
    step = LINE_H * font
    art_x = box_x + (box_w - CHAR_W * font * cols) / 2
    art_top = box_y + (box_h - step * rows) / 2

    out = [HEAD.format(width=WIDTH, height=height)]

    out.append(f'<text x="{art_x:.1f}" y="{art_top + font:.1f}" fill="#c9d1d9" '
               f'class="ascii" font-size="{font:.2f}px">')
    for i, line in enumerate(art):
        y = art_top + step * i + font
        out.append(f'<tspan x="{art_x:.1f}" y="{y:.1f}">{escape(line)}</tspan>')
    out.append("</text>")

    out.append(f'<text x="{RIGHT_X}" y="{TOP_Y}" fill="#c9d1d9">')
    for i, line in enumerate(text_lines):
        if line is None:
            continue
        cls, first, rest = line
        y = TOP_Y + LINE_HEIGHT * i
        out.append(f'<tspan x="{RIGHT_X}" y="{y}"{cls}>{first}</tspan>{rest}')
    out.append("</text>")
    out.append("</svg>")

    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}: {WIDTH}x{height}px card, art {cols}x{rows} characters "
          f"at {font:.1f}px font, uptime {age}")


if __name__ == "__main__":
    main()
