from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

INK = "#111418"
PAPER = "#f4f1ea"
PANEL = "#fffdf8"
MUTED = "#58606b"
LINE = "#cfc7b8"
RED = "#c2412d"
GREEN = "#0b7a5b"
BLUE = "#22577a"
GOLD = "#a16207"
WHITE = "#ffffff"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def text(draw, xy, value, size, fill=INK, bold=False, anchor=None):
    draw.text(xy, value, font=font(size, bold), fill=fill, anchor=anchor)


def multiline(draw, xy, lines, size, fill=INK, bold=False, leading=1.18):
    x, y = xy
    line_height = int(size * leading)
    for line in lines:
        text(draw, (x, y), line, size, fill, bold)
        y += line_height
    return y


def border(draw):
    draw.rectangle((28, 28, 1572, 872), outline="#d7d1c7", width=2)


def save(img, name):
    path = OUT / name
    img.save(path, "PNG", optimize=True)
    print(path)


def card_overclaim():
    img = Image.new("RGB", (1600, 900), PAPER)
    draw = ImageDraw.Draw(img)
    border(draw)

    text(draw, (72, 100), "AI CITATION FAILURE MODE", 25, BLUE, True)
    multiline(
        draw,
        (72, 190),
        ["The citation", "exists.", "The claim", "still fails."],
        82,
        INK,
        True,
        1.02,
    )
    multiline(
        draw,
        (72, 570),
        [
            "Existence checks catch fake papers.",
            "Claim-support checks catch real sources",
            "used for stronger claims than they prove.",
        ],
        31,
        MUTED,
        True,
        1.35,
    )

    draw.rounded_rectangle((72, 770, 130, 828), radius=14, fill=INK)
    text(draw, (101, 808), "AJ", 25, WHITE, True, "mm")
    text(draw, (150, 803), "AI Judge / source-isolated citation audit", 28, MUTED, True)

    shadow = (860, 128, 1546, 808)
    draw.rectangle(shadow, fill="#d9d6ce")
    panel = (842, 110, 1528, 790)
    draw.rectangle(panel, fill=PANEL, outline=INK, width=3)

    text(draw, (876, 162), "GENERATED CLAIM", 20, MUTED, True)
    multiline(
        draw,
        (876, 212),
        ['"Study X proves the model causes', 'a 32% improvement."'],
        29,
        "#2c3138",
        True,
        1.28,
    )
    draw.line((876, 302, 1494, 302), fill=LINE, width=2)

    text(draw, (876, 352), "CITED SOURCE SAYS", 20, MUTED, True)
    multiline(
        draw,
        (876, 402),
        ['"We observed a correlation', 'in a limited sample."'],
        29,
        "#2c3138",
        True,
        1.28,
    )
    draw.line((876, 494, 1494, 494), fill=LINE, width=2)

    draw.rectangle((876, 552, 1168, 702), fill=WHITE, outline=LINE, width=2)
    text(draw, (902, 594), "CITATION", 20, MUTED, True)
    text(draw, (902, 650), "Real", 34, GREEN, True)

    draw.rectangle((1202, 552, 1494, 702), fill=WHITE, outline=LINE, width=2)
    text(draw, (1228, 594), "CLAIM SUPPORT", 20, MUTED, True)
    text(draw, (1228, 650), "Overclaimed", 34, RED, True)

    save(img, "x-claim-support-overclaim.png")


def card_quiet_risk():
    img = Image.new("RGB", (1600, 900), PAPER)
    draw = ImageDraw.Draw(img)
    border(draw)

    text(draw, (92, 112), "WHY THIS MATTERS NOW", 25, BLUE, True)
    multiline(
        draw,
        (92, 200),
        ["Fake citations are loud.", "Real-source overclaims are quiet."],
        82,
        INK,
        True,
        1.08,
    )

    draw.rectangle((92, 455, 740, 730), fill=PANEL, outline=INK, width=3)
    text(draw, (124, 525), "Easy to catch", 44, RED, True)
    multiline(
        draw,
        (124, 595),
        [
            "A paper, case, URL, or DOI",
            "simply does not exist.",
        ],
        31,
        MUTED,
        True,
        1.35,
    )

    draw.rectangle((860, 455, 1508, 730), fill=PANEL, outline=INK, width=3)
    text(draw, (892, 525), "Harder to catch", 44, GOLD, True)
    multiline(
        draw,
        (892, 595),
        [
            "The source is real and related,",
            "but supports a weaker claim.",
        ],
        31,
        MUTED,
        True,
        1.35,
    )

    text(draw, (92, 815), "AI Judge turns this into an auditable verdict.", 28, MUTED, True)
    text(draw, (1150, 815), "github.com/reguorier/ai-judge", 28, MUTED, True)

    save(img, "x-claim-support-quiet-risk.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    card_overclaim()
    card_quiet_risk()


if __name__ == "__main__":
    main()
