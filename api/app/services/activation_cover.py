"""Printable TAPTOT activation covers (QR) and one order slip per shop order."""

from __future__ import annotations

import io
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps
from qrcode.constants import ERROR_CORRECT_H

from app.services.redeem_code_service import gift_landing_url

ASSETS = Path(__file__).resolve().parents[1] / "assets"
FONTS = Path(__file__).resolve().parents[1] / "data" / "fonts"
LOGO_PATH = ASSETS / "taptot-logo-vuong.png"
BG = (255, 255, 255)
GREEN_A = (16, 185, 129)
GREEN_B = (34, 197, 94)
INK = (23, 23, 23)
MUTED = (71, 85, 95)
SELLER_SITE = "taptot.vn"
SELLER_EMAIL = "tai.tran@taptot.vn"
SELLER_ZALO = "+81 70 9133 5675"
W, H = 1800, 2400

_FONT_CANDIDATES = (
    FONTS / "NotoSans-Regular.ttf",
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
)
_BOLD_CANDIDATES = (
    FONTS / "NotoSans-Bold.ttf",
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
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


def _wordmark(draw: ImageDraw.ImageDraw, y: int, size: int = 118, x: float | None = None) -> int:
    parts = [("T", GREEN_A), ("AP", INK), ("T", GREEN_B), ("OT", INK)]
    fnt = _bold(size)
    widths = [draw.textbbox((0, 0), t, font=fnt)[2] for t, _ in parts]
    total = sum(widths)
    if x is None:
        x = (W - total) / 2
    height = 0
    for (text, color), tw in zip(parts, widths):
        bbox = draw.textbbox((0, 0), text, font=fnt)
        draw.text((x, y), text, font=fnt, fill=color)
        height = max(height, bbox[3])
        x += tw
    return height


def _run(draw: ImageDraw.ImageDraw, y: int, fnt, parts: list[tuple[str, tuple[int, int, int]]]) -> int:
    widths = [draw.textlength(text, font=fnt) for text, _ in parts]
    x = (W - sum(widths)) / 2
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


def _brand_header(img: Image.Image, draw: ImageDraw.ImageDraw) -> int:
    """Logo, wordmark TAPTOT, and slogan. Returns the y just below the slogan."""
    logo_size = 320
    logo_x = (W - logo_size) // 2
    logo_y = 120
    logo = _logo().resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    img.paste(logo, (logo_x, logo_y), logo)
    plate_radius = round(logo_size * 243 / 1024)
    draw.rounded_rectangle(
        (logo_x, logo_y, logo_x + logo_size - 1, logo_y + logo_size - 1),
        radius=plate_radius,
        outline=GREEN_A,
        width=6,
    )
    y = logo_y + logo_size + 36
    y += _wordmark(draw, y) + 52
    y += _slogan(draw, y)
    return y


def _qr(url: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=2, box_size=12)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.Resampling.NEAREST)


def thanks_line(_recipient_name: str | None = None) -> str:
    return "CẢM ƠN BẠN ĐÃ TIN TƯỞNG"


def format_street(address_line: str | None) -> str:
    text = " ".join((address_line or "").split())

    def word(token: str) -> str:
        letters = [char for char in token if char.isalpha()]
        if not letters:
            return token
        if all(char.isupper() for char in letters) and any(char.isdigit() for char in token) and len(token) <= 6:
            return token
        if all(char.isupper() for char in letters):
            return token.capitalize()
        if any(char.isupper() for char in letters) and any(char.islower() for char in letters):
            return token
        chars = list(token)
        for index, char in enumerate(chars):
            if char.isalpha():
                chars[index] = char.upper()
                break
        return "".join(chars)

    return " ".join(word(token) for token in text.split())


def postal_lines(
    address_line: str | None = None,
    ward_name: str | None = None,
    province_name: str | None = None,
) -> list[str]:
    street = format_street(address_line)
    place = ", ".join(
        part
        for part in (
            " ".join((ward_name or "").split()),
            " ".join((province_name or "").split()),
        )
        if part
    )
    return [line for line in (street, place) if line][:2]


def order_address_lines(
    address_line: str | None = None,
    ward_name: str | None = None,
    district_name: str | None = None,
    province_name: str | None = None,
) -> list[str]:
    street = format_street(address_line)
    place = ", ".join(
        part
        for part in (
            " ".join((ward_name or "").split()),
            " ".join((district_name or "").split()),
            " ".join((province_name or "").split()),
        )
        if part
    )
    return [line for line in (street, place) if line]


_PAYMENT_LABELS = {
    "cod": "COD",
    "bank_transfer": "Chuyển khoản",
    "unpaid": "Chưa thanh toán",
    "awaiting_transfer": "Chờ chuyển khoản",
    "paid": "Đã thanh toán",
}


def payment_caption(method: str | None, status: str | None) -> str:
    method_label = _PAYMENT_LABELS.get(method or "", method or "")
    status_label = _PAYMENT_LABELS.get(status or "", status or "")
    parts: list[str] = []
    if method_label:
        parts.append(method_label)
    if status_label and status_label != method_label:
        parts.append(status_label)
    return " · ".join(parts)


def _fit_bold(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int = 44, minimum: int = 28):
    size = start
    font = _bold(size)
    while size > minimum and draw.textlength(text, font=font) > max_width:
        size -= 2
        font = _bold(size)
    return font


def _draw_thanks(draw: ImageDraw.ImageDraw, y: int) -> int:
    text = thanks_line()
    max_width = W - 160
    font = _fit_bold(draw, text, max_width)
    if draw.textlength(text, font=font) <= max_width:
        return _center_text(draw, text, y, font, INK)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    used = 0
    for line in lines:
        used += _center_text(draw, line, y + used, font, INK) + 8
    return used


def _ellipsize(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    trimmed = text
    while trimmed and draw.textlength(f"{trimmed}…", font=font) > max_width:
        trimmed = trimmed[:-1].rstrip()
    return f"{trimmed}…" if trimmed else text[:1]


def render_cover(code: str, qr_url: str | None = None) -> Image.Image:
    url = qr_url or gift_landing_url(code)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 10), fill=GREEN_A)
    draw.rectangle((0, H - 10, W, H), fill=GREEN_B)

    y = _brand_header(img, draw) + 78
    thanks = _bold(44)
    y += _draw_thanks(draw, y) + 16
    y += _run(
        draw,
        y,
        thanks,
        [
            ("SỬ DỤNG DỊCH VỤ CỦA ", INK),
            ("T", GREEN_A),
            ("AP", INK),
            ("T", GREEN_B),
            ("OT", INK),
        ],
    ) + 16
    y += 48
    y += _center_text(draw, "MÃ KÍCH HOẠT LỊCH TẬP CỦA BẠN", y, _bold(44), INK)
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

    label = "Mã kích hoạt thủ công: "
    label_f = _regular(36)
    code_f = _bold(46)
    gap = 14
    label_w = draw.textlength(label, font=label_f)
    code_w = draw.textlength(code, font=code_f)
    start_x = (W - (label_w + gap + code_w)) / 2
    label_box = draw.textbbox((0, 0), label, font=label_f, anchor="ls")
    code_box = draw.textbbox((0, 0), code, font=code_f, anchor="ls")
    baseline = fy + frame_h + 72 - min(label_box[1], code_box[1])
    draw.text((start_x, baseline), label, font=label_f, fill=MUTED, anchor="ls")
    draw.text((start_x + label_w + gap, baseline), code, font=code_f, fill=INK, anchor="ls")
    _center_text(draw, "taptot.vn", H - 78, _regular(26), MUTED)
    return img


def cover_png_bytes(code: str) -> bytes:
    buf = io.BytesIO()
    render_cover(code).save(buf, format="PNG", dpi=(300, 300))
    return buf.getvalue()


def images_pdf_bytes(pages: list[Image.Image]) -> bytes:
    if not pages:
        raise ValueError("no pages")
    rgb = [page.convert("RGB") for page in pages]
    buf = io.BytesIO()
    rgb[0].save(buf, format="PDF", save_all=True, append_images=rgb[1:], resolution=150)
    return buf.getvalue()


def covers_pdf_bytes(codes: list[str] | list[dict]) -> bytes:
    if not codes:
        raise ValueError("no codes")
    pages: list[Image.Image] = []
    for item in codes:
        code = item if isinstance(item, str) else str(item["code"])
        pages.append(render_cover(code))
    return images_pdf_bytes(pages)


def local_media_file(image_url: str | None, media_root: Path | None = None) -> Path | None:
    """Resolve a stored product image to a file under uploads/media. Remote URLs are skipped."""
    raw = (image_url or "").strip()
    if not raw:
        return None
    if raw.lower().startswith(("http://", "https://")):
        from urllib.parse import urlparse

        parsed = urlparse(raw)
        if not parsed.path.startswith("/media/"):
            return None
        raw = parsed.path
    path = raw.split("?", 1)[0].split("#", 1)[0].replace("\\", "/")
    if path.startswith("/media/"):
        path = path[len("/media/") :]
    path = path.lstrip("/")
    if path.startswith("media/"):
        path = path[len("media/") :]
    parts = [part for part in path.split("/") if part and part not in {".", ".."}]
    if not parts:
        return None
    if media_root is None:
        from app.core.config import get_settings

        media_root = Path(get_settings().upload_dir) / "media"
    root = media_root.resolve()
    target = root.joinpath(*parts).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return None
    return target


def _product_thumb(image_path: str | Path, size: int) -> Image.Image | None:
    try:
        with Image.open(image_path) as src:
            photo = ImageOps.exif_transpose(src).convert("RGBA")
    except (OSError, ValueError):
        return None
    photo.thumbnail((size - 8, size - 8), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    canvas.paste(photo, ((size - photo.width) // 2, (size - photo.height) // 2), photo)
    return canvas


def _vnd(amount: int | None) -> str:
    return f"{int(amount or 0):,}".replace(",", ".") + " đ"


def _time_label(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return value.strftime("%d/%m/%Y %H:%M")
    except (AttributeError, ValueError):
        return str(value)


def _right_text(draw: ImageDraw.ImageDraw, text: str, y: int, font, fill, right: int = W - 96) -> None:
    draw.text((right - draw.textlength(text, font=font), y), text, font=font, fill=fill)


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words = [part for part in text.split() if part]
    if not words:
        return []
    lines: list[str] = []
    current = ""
    index = 0
    while index < len(words) and len(lines) < max_lines:
        word = words[index]
        trial = word if not current else f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
            index += 1
            continue
        if current:
            lines.append(current)
            current = ""
            continue
        lines.append(_ellipsize(draw, word, font, max_width))
        index += 1
        current = ""
    if current and len(lines) < max_lines:
        lines.append(current)
    if index < len(words) and lines:
        lines[-1] = _ellipsize(draw, lines[-1], font, max_width)
    return lines


def _baseline(draw: ImageDraw.ImageDraw, font, top: int, height: int) -> int:
    box = draw.textbbox((0, 0), "Ag", font=font)
    return top + (height - (box[3] - box[1])) // 2 - box[1]


def _center_in(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font,
    fill,
    x0: int,
    x1: int,
) -> None:
    width = draw.textlength(text, font=font)
    draw.text((x0 + (x1 - x0 - width) / 2, y), text, font=font, fill=fill)


def _framed_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill, outline, radius: int = 22) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=3)


def render_order_sheet(sheet: dict) -> Image.Image:
    """Packing slip: seller and order boxes, recipient card, ruled product table, bold total."""
    margin = 56
    right = W - margin
    gap = 22
    line = (203, 213, 225)
    panel = (248, 250, 252)
    head_bg = (241, 245, 249)
    label_font = _bold(24)
    value_font = _bold(32)
    body = _regular(32)
    body_bold = _bold(32)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 10), fill=GREEN_A)
    draw.rectangle((0, H - 10, W, H), fill=GREEN_B)

    code = str(sheet.get("public_code") or "—")
    created = _time_label(sheet.get("created_at")) or "—"
    payment = " ".join(str(sheet.get("payment") or "—").split()) or "—"
    address = [part for part in (sheet.get("address_lines") or []) if part][:2] or ["—"]
    items = list(sheet.get("items") or [])

    top = 36
    box_h = 372
    left_w = 1048
    left_box = (margin, top, margin + left_w, top + box_h)
    right_box = (margin + left_w + gap, top, right, top + box_h)
    _framed_box(draw, left_box, BG, line)
    _framed_box(draw, right_box, panel, line)

    logo_size = 176
    logo_x = margin + 28
    logo_y = top + (box_h - logo_size) // 2
    logo = _logo().resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    img.paste(logo, (logo_x, logo_y), logo)
    plate_radius = round(logo_size * 243 / 1024)
    draw.rounded_rectangle(
        (logo_x, logo_y, logo_x + logo_size - 1, logo_y + logo_size - 1),
        radius=plate_radius,
        outline=GREEN_A,
        width=5,
    )
    text_x = logo_x + logo_size + 28
    text_right = margin + left_w - 28
    text_w = text_right - text_x
    small = _regular(28)
    ty = top + 28
    draw.text((text_x, ty), "NGƯỜI BÁN", font=label_font, fill=GREEN_A)
    ty += 34
    ty += _wordmark(draw, ty, size=64, x=text_x) + 8
    draw.text((text_x, ty), "Tập tốt \u00b7 Ăn tốt \u00b7 Sống tốt", font=_regular(28), fill=MUTED)
    ty += 36

    def contact_line(title: str, value: str, y: int) -> int:
        prefix = f"{title}: "
        prefix_w = draw.textlength(prefix, font=small)
        draw.text((text_x, y), prefix, font=small, fill=MUTED)
        draw.text(
            (text_x + prefix_w, y),
            _ellipsize(draw, value, small, text_w - prefix_w),
            font=small,
            fill=INK,
        )
        return y + 34

    ty = contact_line("Website", SELLER_SITE, ty)
    ty = contact_line("Zalo", SELLER_ZALO, ty)
    contact_line("Gmail", SELLER_EMAIL, ty)

    rx = right_box[0] + 32
    rw = right_box[2] - 32
    ry = top + 28
    draw.text((rx, ry), "PHIẾU ĐƠN HÀNG", font=label_font, fill=GREEN_A)
    ry += 40
    code_font = _fit_bold(draw, code, rw - rx, start=40, minimum=28)
    draw.text((rx, ry), code, font=code_font, fill=INK)
    ry += 58
    draw.line((rx, ry, rw, ry), fill=line, width=2)
    ry += 22

    def meta_row(label: str, value: str, y: int, lines: int = 1) -> int:
        draw.text((rx, y), label, font=label_font, fill=MUTED)
        wrapped = _wrap_lines(draw, value, value_font, rw - rx, lines) or ["—"]
        yy = y + 34
        for row in wrapped:
            draw.text((rx, yy), row, font=value_font, fill=INK)
            yy += 40
        return yy + 8

    ry = meta_row("NGÀY ĐẶT", created, ry)
    pay_font = _fit_bold(draw, payment, rw - rx, start=32, minimum=22)
    draw.text((rx, ry), "HÌNH THỨC THANH TOÁN", font=label_font, fill=MUTED)
    draw.text((rx, ry + 32), payment, font=pay_font, fill=INK)

    y = top + box_h + 22
    name = str(sheet.get("recipient_name") or "—")
    phone = str(sheet.get("phone") or "—")
    addr_font = _bold(30)
    addr_lines = []
    for part in address:
        addr_lines.extend(_wrap_lines(draw, part, addr_font, right - margin - 64, 2) or [part])
    addr_lines = addr_lines[:3] or ["—"]
    pad = 28
    rec_h = pad + 40 + 34 + 78 + 34 + 46 * len(addr_lines) + pad
    _framed_box(draw, (margin, y, right, y + rec_h), BG, line)
    inner = margin + pad
    col2 = margin + 980
    cursor = y + pad
    draw.text((inner, cursor), "NGƯỜI NHẬN", font=label_font, fill=GREEN_A)
    cursor += 40
    draw.text((inner, cursor), "TÊN", font=label_font, fill=MUTED)
    draw.text((col2, cursor), "SỐ ĐIỆN THOẠI", font=label_font, fill=MUTED)
    cursor += 34
    draw.text((inner, cursor), _ellipsize(draw, name, value_font, col2 - inner - 24), font=value_font, fill=INK)
    draw.text((col2, cursor), _ellipsize(draw, phone, value_font, right - pad - col2), font=value_font, fill=INK)
    cursor += 78
    draw.text((inner, cursor), "ĐỊA CHỈ", font=label_font, fill=MUTED)
    cursor += 34
    for line_text in addr_lines:
        draw.text((inner, cursor), line_text, font=addr_font, fill=INK)
        cursor += 46
    y += rec_h + 22

    shipping = int(sheet.get("shipping_fee_vnd") or 0)
    discount = int(sheet.get("discount_vnd") or 0)
    promo_code = " ".join(str(sheet.get("promo_code") or "").split())
    promo_discount = int(sheet.get("promo_discount_vnd") or 0)
    subtotal = sum(int(item.get("quantity") or 0) * int(item.get("unit_price_vnd") or 0) for item in items)
    money_rows = [("Tạm tính", _vnd(subtotal)), ("Phí vận chuyển", _vnd(shipping))]
    if discount:
        money_rows.append(("Giảm giá", "-" + _vnd(discount)))
    if promo_code or promo_discount:
        money_rows.append((f"Mã {promo_code}" if promo_code else "Mã CTV", "-" + _vnd(promo_discount)))
    total_text = _vnd(sheet.get("total_vnd"))
    note = " ".join(str(sheet.get("note") or "").split())
    summary_w = 820
    summary_x = right - summary_w
    note_font = _regular(32)
    note_width = summary_x - margin - 28
    note_lines = _wrap_lines(draw, note, note_font, note_width, 3) if note else []

    money_line_h = 48
    total_row_h = 72
    money_h = 16 + len(money_rows) * money_line_h + 8 + total_row_h + 8
    note_block = (36 + 40 * len(note_lines)) if note_lines else 0
    stack_h = max(note_block, money_h)
    limit_y = H - 80 - stack_h - 28

    thumb_size = 112
    has_thumbs = any(item.get("image_path") for item in items)
    row_h = 148 if has_thumbs else 92
    col_qty = 1080
    col_price = 1240
    col_total = 1500
    name_left = margin + 18 + (thumb_size + 16 if has_thumbs else 0)
    name_width = col_qty - 16 - name_left
    head = _bold(24)
    header_h = 64
    table_top = y

    shown_items: list[dict] = []
    probe = y + header_h
    for item in items:
        if probe + row_h > limit_y and shown_items:
            break
        shown_items.append(item)
        probe += row_h
    hidden = len(items) - len(shown_items)
    extra_h = row_h if hidden or not items else 0
    table_bottom = y + header_h + row_h * len(shown_items) + extra_h

    draw.rectangle((margin, table_top, right, table_top + header_h), fill=head_bg)
    head_y = _baseline(draw, head, table_top, header_h)
    draw.text((name_left if not has_thumbs else margin + 18, head_y), "MÓN", font=head, fill=MUTED)
    _center_in(draw, "SL", head_y, head, MUTED, col_qty, col_price)
    _right_text(draw, "ĐƠN GIÁ", head_y, head, MUTED, col_total - 16)
    _right_text(draw, "THÀNH TIỀN", head_y, head, MUTED, right - 16)
    y = table_top + header_h

    for index, item in enumerate(shown_items):
        if index % 2 == 1:
            draw.rectangle((margin, y, right, y + row_h), fill=panel)
        item_name = str(item.get("name") or "—")
        qty = int(item.get("quantity") or 0)
        unit = int(item.get("unit_price_vnd") or 0)
        text_y = _baseline(draw, body, y, row_h)
        if has_thumbs:
            thumb_y = y + (row_h - thumb_size) // 2
            draw.rounded_rectangle(
                (margin + 16, thumb_y, margin + 16 + thumb_size, thumb_y + thumb_size),
                radius=14,
                fill=(255, 255, 255),
                outline=line,
                width=2,
            )
            image_path = item.get("image_path")
            thumb = _product_thumb(image_path, thumb_size - 8) if image_path else None
            if thumb is not None:
                img.paste(thumb, (margin + 20, thumb_y + 4), thumb)
        draw.text((name_left, text_y), _ellipsize(draw, item_name, body, name_width), font=body, fill=INK)
        _center_in(draw, str(qty), text_y, body, INK, col_qty, col_price)
        _right_text(draw, _vnd(unit), text_y, body, INK, col_total - 16)
        _right_text(draw, _vnd(unit * qty), text_y, body_bold, INK, right - 16)
        y += row_h
    if hidden > 0:
        if len(shown_items) % 2 == 1:
            draw.rectangle((margin, y, right, y + row_h), fill=panel)
        more_y = _baseline(draw, body, y, row_h)
        draw.text((margin + 18, more_y), f"… và {hidden} món nữa", font=body, fill=MUTED)
        y += row_h
    elif not items:
        empty_y = _baseline(draw, body, y, row_h)
        draw.text((margin + 18, empty_y), "Không có sản phẩm", font=body, fill=MUTED)
        y += row_h

    for rule in (col_qty, col_price, col_total):
        draw.line((rule, table_top, rule, table_bottom), fill=line, width=2)
    row_edge = table_top + header_h
    while row_edge < table_bottom:
        draw.line((margin, row_edge, right, row_edge), fill=line, width=2)
        row_edge += row_h
    draw.rectangle((margin, table_top, right, table_bottom), outline=line, width=3)

    stack = table_bottom + 28
    if note_lines:
        note_y = stack
        draw.text((margin, note_y), "GHI CHÚ", font=label_font, fill=MUTED)
        note_y += 36
        for line_text in note_lines:
            draw.text((margin, note_y), line_text, font=note_font, fill=INK)
            note_y += 40

    _framed_box(draw, (summary_x, stack, right, stack + money_h), BG, line, radius=18)
    money_label = _regular(26)
    money_value = _bold(26)
    row_top = stack + 10
    for label, amount in money_rows:
        yy = _baseline(draw, money_label, row_top, money_line_h)
        draw.text((summary_x + 24, yy), label, font=money_label, fill=MUTED)
        _right_text(draw, amount, yy, money_value, INK, right - 24)
        row_top += money_line_h
    draw.line((summary_x + 20, row_top + 2, right - 20, row_top + 2), fill=line, width=2)
    total_top = row_top + 8
    total_label = _bold(28)
    total_value = _fit_bold(draw, total_text, summary_w - 280, start=30, minimum=24)
    total_y = _baseline(draw, total_label, total_top, total_row_h)
    draw.text((summary_x + 24, total_y), "TỔNG CỘNG", font=total_label, fill=INK)
    _right_text(draw, total_text, total_y, total_value, INK, right - 24)

    _center_text(draw, SELLER_SITE, H - 58, _regular(28), MUTED)
    return img
