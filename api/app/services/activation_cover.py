"""Printable TAPTOT activation covers (QR + sticker code)."""

from __future__ import annotations

import io
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from qrcode.constants import ERROR_CORRECT_H

from app.services.redeem_code_service import gift_landing_url

ASSETS = Path(__file__).resolve().parents[1] / "assets"
LOGO_PATH = ASSETS / "taptot-logo-vuong.png"
BG = (7, 11, 18)
GREEN_A = (16, 185, 129)
GREEN_B = (34, 197, 94)
SNOW = (255, 250, 250)
MUTED = (180, 190, 196)
CREAM = (245, 240, 230)
W, H = 1800, 2400

_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
)
_BOLD_CANDIDATES = (
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
)


def _first_font(paths: tuple[Path, ...], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in paths:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _regular(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _first_font(_FONT_CANDIDATES, size)


def _bold(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _first_font(_BOLD_CANDIDATES, size)


def _logo() -> Image.Image:
    if LOGO_PATH.is_file():
        return Image.open(LOGO_PATH).convert("RGBA")
    fallback = Path(r"C:\Users\Tran Tai\Projects\vietfit-db\frontend\public\brand\taptot-logo-vuong.png")
    if fallback.is_file():
        return Image.open(fallback).convert("RGBA")
    img = Image.new("RGBA", (320, 320), (255, 255, 255, 255))
    return img


def _center_text(draw: ImageDraw.ImageDraw, text: str, y: int, fnt, fill) -> int:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, y), text, font=fnt, fill=fill)
    return bbox[3] - bbox[1]


def _wordmark(draw: ImageDraw.ImageDraw, y: int) -> int:
    parts = [("T", GREEN_A), ("AP", SNOW), ("T", GREEN_B), ("OT", SNOW)]
    fnt = _bold(118)
    widths = [draw.textbbox((0, 0), t, font=fnt)[2] for t, _ in parts]
    total = sum(widths)
    x = (W - total) / 2
    height = 0
    for (text, color), tw in zip(parts, widths):
        bbox = draw.textbbox((0, 0), text, font=fnt)
        draw.text((x, y), text, font=fnt, fill=color)
        height = max(height, bbox[3] - bbox[1])
        x += tw
    return height


def _slogan(draw: ImageDraw.ImageDraw, y: int) -> int:
    text = "Tập tốt \u00b7 Ăn tốt \u00b7 Sống tốt"
    return _center_text(draw, text, y, _regular(42), MUTED)


def _qr(url: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=2, box_size=12)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.Resampling.NEAREST)


def render_cover(code: str, qr_url: str | None = None) -> Image.Image:
    url = qr_url or gift_landing_url(code)
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((W // 2 - 420, 980, W // 2 + 420, 1820), fill=(12, 48, 38))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(90)), 0.55)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 10), fill=GREEN_A)
    draw.rectangle((0, H - 10, W, H), fill=GREEN_B)

    logo = _logo().resize((320, 320), Image.Resampling.LANCZOS)
    img.paste(logo, ((W - 320) // 2, 120), logo)

    y = 120 + 320 + 36
    y += _wordmark(draw, y) + 28
    y += _slogan(draw, y) + 78
    thanks = _bold(44)
    for line in ("CẢM ƠN BẠN ĐÃ TIN TƯỞNG", "SỬ DỤNG DỊCH VỤ CỦA TAPTOT"):
        y += _center_text(draw, line, y, thanks, CREAM) + 16
    y += 48
    y += _center_text(draw, "MÃ KÍCH HOẠT LỊCH TẬP CỦA BẠN", y, _bold(44), GREEN_A)
    y += 40

    qr_size = 780
    pad = 48
    frame_w = qr_size + pad * 2
    frame_h = qr_size + pad * 2
    fx = (W - frame_w) // 2
    fy = y
    draw.rounded_rectangle((fx - 8, fy - 8, fx + frame_w + 8, fy + frame_h + 8), radius=40, outline=GREEN_A, width=6)
    draw.rounded_rectangle((fx, fy, fx + frame_w, fy + frame_h), radius=32, fill=(255, 255, 255))
    img.paste(_qr(url, qr_size), (fx + pad, fy + pad))

    y = fy + frame_h + 48
    label = "Mã kích hoạt thủ công: "
    label_f = _regular(34)
    code_f = _bold(58)
    label_w = draw.textbbox((0, 0), label, font=label_f)[2]
    code_w = draw.textbbox((0, 0), code, font=code_f)[2]
    start_x = (W - (label_w + code_w)) / 2
    draw.text((start_x, y + 10), label, font=label_f, fill=MUTED)
    draw.text((start_x + label_w, y), code, font=code_f, fill=SNOW)
    _center_text(draw, "taptot.vn", H - 78, _regular(26), MUTED)
    return img


def cover_png_bytes(code: str) -> bytes:
    buf = io.BytesIO()
    render_cover(code).save(buf, format="PNG", dpi=(300, 300))
    return buf.getvalue()


def covers_pdf_bytes(codes: list[str]) -> bytes:
    if not codes:
        raise ValueError("no codes")
    pages = [render_cover(code).convert("RGB") for code in codes]
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:], resolution=150)
    return buf.getvalue()
