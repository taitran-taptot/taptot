"""Export TAPTOT logo covers for Facebook and TikTok."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = (7, 11, 18, 255)  # #070B12
GREEN1 = (16, 185, 129)  # #10B981
GREEN2 = (34, 197, 94)  # #22C55E
SNOW = (255, 250, 250, 255)
WHITE = (255, 255, 255, 255)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "brand"
FONTS = Path(r"C:\Windows\Fonts")


def lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size=size)


def make_mark(size: int) -> Image.Image:
    """Exact BrandMark: white rounded square + joined TT gradient."""
    super_size = size * 4
    s = super_size / 40.0
    canvas = Image.new("RGBA", (super_size, super_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [0, 0, super_size - 1, super_size - 1],
        radius=int(10 * s),
        fill=WHITE,
    )

    mask = Image.new("L", (super_size, super_size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([6 * s, 8 * s, 34 * s, 14 * s], radius=max(1, 1.4 * s), fill=255)
    md.rounded_rectangle([10.5 * s, 12.2 * s, 15.5 * s, 32.5 * s], radius=max(1, 1.6 * s), fill=255)
    md.rounded_rectangle([24.5 * s, 12.2 * s, 29.5 * s, 32.5 * s], radius=max(1, 1.6 * s), fill=255)

    grad = Image.new("RGBA", (super_size, super_size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    x1, x2 = 6 * s, 34 * s
    for x in range(super_size):
        t = (x - x1) / (x2 - x1)
        t = min(1.0, max(0.0, t))
        if t <= 0.36:
            c = GREEN1
        elif t >= 0.64:
            c = GREEN2
        else:
            u = (t - 0.36) / 0.28
            c = tuple(lerp(GREEN1[i], GREEN2[i], u) for i in range(3))
        gd.line([(x, 0), (x, super_size)], fill=c + (255,))

    tt = Image.new("RGBA", (super_size, super_size), (0, 0, 0, 0))
    tt.paste(grad, mask=mask)
    canvas.alpha_composite(tt)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


WORDMARK = [
    ("T", GREEN1 + (255,)),
    ("AP", SNOW),
    ("T", GREEN2 + (255,)),
    ("OT", SNOW),
]
SLOGAN = "TẬP TỐT • ĂN TỐT • SỐNG TỐT"


def wordmark_width(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont) -> float:
    return sum(draw.textlength(text, font=font) for text, _ in WORDMARK)


def draw_wordmark_at(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    font: ImageFont.FreeTypeFont,
) -> None:
    for text, color in WORDMARK:
        draw.text((x, y), text, font=font, fill=color)
        x += draw.textlength(text, font=font)


def draw_wordmark(draw: ImageDraw.ImageDraw, cx: int, y: int, font: ImageFont.FreeTypeFont) -> None:
    total = wordmark_width(draw, font)
    draw_wordmark_at(draw, cx - total / 2, y, font)


def centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    cx: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - w / 2 - bbox[0], y - bbox[1]), text, font=font, fill=fill)
    return h


def save_square_logo() -> None:
    mark = make_mark(1024)
    mark.save(OUT / "taptot-logo.png", "PNG")
    transparent = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    transparent.alpha_composite(mark)
    transparent.save(OUT / "taptot-logo-vuong.png", "PNG")


def save_facebook_cover() -> None:
    w, h = 1640, 624
    img = Image.new("RGBA", (w, h), BG)
    mark = make_mark(220)
    font = load_font("seguibl.ttf", 92)
    slogan_font = load_font("seguisb.ttf", 26)
    draw = ImageDraw.Draw(img)

    word_w = wordmark_width(draw, font)
    slogan_box = draw.textbbox((0, 0), SLOGAN, font=slogan_font)
    slogan_w = slogan_box[2] - slogan_box[0]
    slogan_h = slogan_box[3] - slogan_box[1]
    text_w = max(word_w, slogan_w)
    line_gap = 14
    text_h = font.size + line_gap + slogan_h

    gap = 48
    group_w = mark.width + gap + text_w
    left = int((w - group_w) / 2)
    mark_y = int((h - mark.height) / 2)
    img.alpha_composite(mark, (left, mark_y))

    word_x = left + mark.width + gap + (text_w - word_w) / 2
    text_top = mark_y + int((mark.height - text_h) / 2)
    draw_wordmark_at(draw, word_x, text_top, font)
    centered_text(
        draw,
        SLOGAN,
        int(word_x + word_w / 2),
        text_top + font.size + line_gap,
        slogan_font,
        (255, 250, 250, 200),
    )
    img.convert("RGB").save(OUT / "taptot-bia-facebook.png", "PNG")


def save_tiktok_cover() -> None:
    w, h = 1080, 1920
    img = Image.new("RGBA", (w, h), BG)
    mark = make_mark(380)
    font = load_font("seguibl.ttf", 108)
    slogan_font = load_font("seguisb.ttf", 34)
    draw = ImageDraw.Draw(img)

    mark_x = (w - mark.width) // 2
    mark_y = 560
    img.alpha_composite(mark, (mark_x, mark_y))
    word_y = mark_y + mark.height + 56
    draw_wordmark(draw, w // 2, word_y, font)
    centered_text(
        draw,
        SLOGAN,
        w // 2,
        word_y + font.size + 16,
        slogan_font,
        (255, 250, 250, 200),
    )
    img.convert("RGB").save(OUT / "taptot-bia-tiktok.png", "PNG")


def save_square_cover() -> None:
    w = h = 1080
    img = Image.new("RGBA", (w, h), BG)
    mark = make_mark(320)
    font = load_font("seguibl.ttf", 88)
    slogan_font = load_font("seguisb.ttf", 30)
    draw = ImageDraw.Draw(img)
    mark_x = (w - mark.width) // 2
    mark_y = 230
    img.alpha_composite(mark, (mark_x, mark_y))
    word_y = mark_y + mark.height + 52
    draw_wordmark(draw, w // 2, word_y, font)
    centered_text(
        draw,
        SLOGAN,
        w // 2,
        word_y + font.size + 14,
        slogan_font,
        (255, 250, 250, 200),
    )
    img.convert("RGB").save(OUT / "taptot-bia-vuong.png", "PNG")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    save_square_logo()
    save_facebook_cover()
    save_tiktok_cover()
    save_square_cover()
    for path in sorted(OUT.glob("taptot-*.png")):
        print(path)


if __name__ == "__main__":
    main()
