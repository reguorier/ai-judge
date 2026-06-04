#!/usr/bin/env python3
"""
Generate Marvis-like 2.5D robot avatars for AI Judge.

The UI renders these at 32-56px, so the composition deliberately favors:
- a large white robot head
- a wide black face screen
- simple eyes/mouth readable at small sizes
- a colored scarf/badge as the model identity cue
- a distinct Grand Judge robe and gavel medallion
"""
from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256
SCALE = 3
CANVAS = SIZE * SCALE
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "product" / "avatars"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    "gpt4o": (16, 163, 127),
    "claude": (204, 120, 92),
    "gemini": (66, 133, 244),
    "deepseek": (77, 107, 254),
    "qwen": (112, 91, 214),
    "kimi": (255, 92, 113),
    "grok": (17, 24, 39),
    "yuanbao": (20, 184, 166),
    "doubao": (249, 115, 22),
    "minimax": (139, 92, 246),
    "zhipu": (14, 165, 233),
    "mimo": (168, 85, 247),
    "wenxin": (34, 197, 94),
}

ACCESSORIES = {
    "gpt4o": "antenna",
    "claude": "side-dot",
    "gemini": "star",
    "deepseek": "visor",
    "qwen": "diamond",
    "kimi": "sprout",
    "grok": "bolt",
    "yuanbao": "coin",
    "doubao": "flame",
    "minimax": "hex",
    "zhipu": "ring",
    "mimo": "moon",
    "wenxin": "leaf",
}


def s(v: float) -> int:
    return int(round(v * SCALE))


def rgba(color: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return (*color, alpha)


def lighten(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in color)


def darken(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(max(0, c - amount) for c in color)


def rounded(draw: ImageDraw.ImageDraw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(tuple(map(s, xy)), radius=s(radius), fill=fill, outline=outline, width=s(width))


def ellipse(draw: ImageDraw.ImageDraw, xy, fill, outline=None, width=1):
    draw.ellipse(tuple(map(s, xy)), fill=fill, outline=outline, width=s(width))


def polygon(draw: ImageDraw.ImageDraw, pts, fill, outline=None):
    draw.polygon([(s(x), s(y)) for x, y in pts], fill=fill, outline=outline)


def line(draw: ImageDraw.ImageDraw, pts, fill, width=1):
    draw.line([(s(x), s(y)) for x, y in pts], fill=fill, width=s(width), joint="curve")


def shadow_layer(base: Image.Image, xy, radius: float, blur: float, alpha: int):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse(tuple(map(s, xy)), fill=(15, 23, 42, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(s(blur)))
    base.alpha_composite(layer)


def gradient_round_rect(size, radius, top, bottom):
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    pix = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            a = mask.getpixel((x, y))
            if a:
                pix[x, y] = (*color, a)
    return img


def draw_badge(draw: ImageDraw.ImageDraw, cx: float, cy: float, color, kind: str):
    if kind == "diamond":
        polygon(draw, [(cx, cy - 13), (cx + 13, cy), (cx, cy + 13), (cx - 13, cy)], fill=rgba(color))
    elif kind == "hex":
        pts = []
        for i in range(6):
            a = math.pi / 6 + i * math.pi / 3
            pts.append((cx + math.cos(a) * 14, cy + math.sin(a) * 14))
        polygon(draw, pts, fill=rgba(color))
    elif kind == "star":
        pts = []
        for i in range(10):
            r = 15 if i % 2 == 0 else 7
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        polygon(draw, pts, fill=rgba(color))
    elif kind == "coin":
        ellipse(draw, (cx - 13, cy - 13, cx + 13, cy + 13), fill=rgba(color), outline=rgba(lighten(color, 50)), width=3)
    elif kind == "flame":
        ellipse(draw, (cx - 10, cy - 7, cx + 10, cy + 15), fill=rgba(color))
        polygon(draw, [(cx - 8, cy - 3), (cx + 8, cy - 3), (cx, cy - 18)], fill=rgba((255, 198, 82)))
    elif kind == "leaf":
        ellipse(draw, (cx - 10, cy - 16, cx + 13, cy + 9), fill=rgba(color))
        line(draw, [(cx - 3, cy - 10), (cx + 8, cy + 10)], fill=rgba(darken(color, 70)), width=2)
    elif kind == "moon":
        ellipse(draw, (cx - 13, cy - 13, cx + 13, cy + 13), fill=rgba(color))
        ellipse(draw, (cx - 5, cy - 15, cx + 17, cy + 9), fill=(255, 255, 255, 255))
    elif kind == "bolt":
        polygon(draw, [(cx + 2, cy - 16), (cx - 9, cy + 1), (cx, cy + 1), (cx - 5, cy + 17), (cx + 11, cy - 4), (cx + 1, cy - 4)], fill=rgba((255, 202, 62)))
    elif kind == "ring":
        ellipse(draw, (cx - 13, cy - 13, cx + 13, cy + 13), fill=(0, 0, 0, 0), outline=rgba(color), width=4)
        line(draw, [(cx - 13, cy), (cx + 13, cy)], fill=rgba(color), width=3)
        line(draw, [(cx, cy - 13), (cx, cy + 13)], fill=rgba(color), width=3)
    else:
        ellipse(draw, (cx - 12, cy - 12, cx + 12, cy + 12), fill=rgba(color))


def draw_top_accessory(draw: ImageDraw.ImageDraw, model_id: str, color):
    kind = ACCESSORIES.get(model_id, "")
    if kind == "antenna":
        line(draw, [(128, 33), (128, 18)], fill=rgba((37, 44, 55)), width=4)
        ellipse(draw, (118, 7, 138, 27), fill=rgba(color), outline=rgba(lighten(color, 44)), width=2)
    elif kind == "sprout":
        line(draw, [(128, 36), (128, 21)], fill=rgba((42, 94, 56)), width=4)
        ellipse(draw, (111, 10, 132, 30), fill=rgba((69, 178, 96)))
        ellipse(draw, (126, 8, 149, 29), fill=rgba((84, 194, 109)))
    elif kind == "visor":
        rounded(draw, (92, 31, 164, 47), 8, fill=rgba((28, 34, 48)), outline=rgba(color), width=2)
    elif kind == "side-dot":
        ellipse(draw, (166, 55, 184, 73), fill=rgba(color), outline=rgba(lighten(color, 40)), width=2)
    elif kind == "star":
        draw_badge(draw, 174, 57, color, "star")
    elif kind == "bolt":
        draw_badge(draw, 176, 61, color, "bolt")


def create_avatar(model_id: str, color: tuple[int, int, int], *, judge: bool = False) -> Image.Image:
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Soft circular badge, like a real app icon rather than a bare glyph.
    shadow_layer(img, (34, 24, 222, 224), 94, 14, 34)
    ellipse(d, (28, 20, 228, 220), fill=(255, 255, 255, 255), outline=(235, 238, 243, 255), width=2)
    ellipse(d, (46, 34, 210, 196), fill=(250, 251, 253, 255))

    if judge:
        color = (214, 160, 39)
        draw_top_accessory(d, "antenna", color)
    else:
        draw_top_accessory(d, model_id, color)

    # Ear pods behind the head.
    ellipse(d, (39, 87, 77, 143), fill=(215, 221, 230, 255), outline=(155, 164, 177, 255), width=3)
    ellipse(d, (179, 87, 217, 143), fill=(215, 221, 230, 255), outline=(155, 164, 177, 255), width=3)
    ellipse(d, (49, 98, 68, 132), fill=rgba(color), outline=rgba(lighten(color, 45)), width=2)
    ellipse(d, (188, 98, 207, 132), fill=rgba(color), outline=rgba(lighten(color, 45)), width=2)

    # Big rounded robot head.
    head = gradient_round_rect((s(142), s(116)), s(32), (255, 255, 255), (232, 236, 244))
    img.alpha_composite(head, (s(57), s(48)))
    rounded(d, (57, 48, 199, 164), 32, fill=None, outline=(199, 207, 220, 255), width=3)

    # Dark face screen.
    rounded(d, (77, 77, 179, 136), 22, fill=(24, 28, 36, 255), outline=(55, 62, 75, 255), width=2)
    rounded(d, (83, 82, 173, 98), 12, fill=(38, 44, 56, 150))

    # Eyes and smile.
    for ex in (107, 149):
        ellipse(d, (ex - 9, 92, ex + 9, 118), fill=(246, 250, 255, 255))
        ellipse(d, (ex - 3, 95, ex + 3, 103), fill=(255, 255, 255, 210))
    d.arc(tuple(map(s, (112, 111, 144, 132))), start=18, end=162, fill=(202, 210, 224, 255), width=s(3))

    # Scarf / robe: low on the icon so the head remains dominant.
    if judge:
        rounded(d, (68, 151, 188, 204), 18, fill=(25, 28, 40, 255), outline=(18, 20, 29, 255), width=2)
        polygon(d, [(101, 154), (128, 181), (155, 154), (154, 173), (128, 195), (102, 173)], fill=(246, 236, 210, 255))
        ellipse(d, (110, 166, 146, 202), fill=(229, 178, 56, 255), outline=(154, 108, 25, 255), width=3)
        line(d, [(119, 183), (137, 183)], fill=(78, 44, 13, 255), width=4)
        line(d, [(127, 174), (127, 191)], fill=(78, 44, 13, 255), width=4)
    else:
        polygon(d, [(63, 153), (193, 153), (174, 204), (82, 204)], fill=rgba(darken(color, 10)))
        polygon(d, [(75, 157), (128, 186), (181, 157), (169, 177), (128, 202), (87, 177)], fill=rgba(color))
        line(d, [(88, 164), (168, 164)], fill=rgba(lighten(color, 42), 190), width=4)
        draw_badge(d, 154, 184, lighten(color, 8), ACCESSORIES.get(model_id, "dot"))

    # A tiny base shadow inside the badge.
    shadow_layer(img, (70, 198, 186, 216), 40, 5, 22)

    return img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


MODELS = [
    ("gpt4o", False),
    ("claude", False),
    ("gemini", False),
    ("deepseek", False),
    ("qwen", False),
    ("kimi", False),
    ("grok", False),
    ("yuanbao", False),
    ("doubao", False),
    ("minimax", False),
    ("zhipu", False),
    ("mimo", False),
    ("wenxin", False),
    ("grandjudge", True),
]


def main() -> None:
    for model_id, judge in MODELS:
        color = (214, 160, 39) if judge else COLORS[model_id]
        img = create_avatar(model_id, color, judge=judge)
        path = OUT / f"avatar_{model_id}.png"
        img.save(path, "PNG")
        print(f"OK {model_id:12s} {path.stat().st_size:6d} bytes")
    print(f"\nDone. {len(MODELS)} avatars in {OUT}")


if __name__ == "__main__":
    main()
