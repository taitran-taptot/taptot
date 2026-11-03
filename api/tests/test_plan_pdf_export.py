from pydantic import ValidationError
import pytest

from app.core.exceptions import BadRequestError
from app.schemas.plans import PlanExportRequest
from app.services.export_service import ExportService
from app.services.pdf_plan_export import build_plan_pdf

SAMPLE = {
    "id": 7,
    "title_vi": "Lịch tập TAPTOT thử",
    "description_vi": "3 buổi / tuần",
    "target_calories": 1800,
    "share_token": "abc",
    "days": [
        {
            "day_number": 1,
            "title_vi": "Ngày 1",
            "section_notes": {"main": "Giữ form"},
            "meal_notes": {"breakfast": "Ăn no vừa"},
            "notes_vi": "",
            "exercises": [
                {"section": "warmup", "name_vi": "Xoay khớp", "sets": 1, "reps": "30s"},
                {"section": "main", "name_vi": "Chống đẩy", "sets": 3, "reps": "8"},
            ],
            "meals": [
                {"meal_type": "breakfast", "name_vi": "Cơm gà", "servings": 1, "calories": 450},
            ],
        }
    ],
}


def test_build_plan_pdf_keeps_full_exercise_text():
    long_name = "Ngồi xổm với dây kháng lực rất dài để không bị cắt tên bài"
    full_reps = "10-12 / 10-12 / 10-12 / 8-10"
    detail = {
        **SAMPLE,
        "days": [
            {
                **SAMPLE["days"][0],
                "exercises": [
                    {
                        "section": "main",
                        "name_vi": long_name,
                        "sets": 4,
                        "reps": "8",
                        "set_prescriptions": [
                            {"reps": "10-12"},
                            {"reps": "10-12"},
                            {"reps": "10-12"},
                            {"reps": "8-10"},
                        ],
                    }
                ],
                "meals": [
                    {
                        "meal_type": "breakfast",
                        "name_vi": "Ức gà",
                        "servings": 1.5,
                        "serving_grams": 100,
                        "calories": 248,
                    }
                ],
            }
        ],
    }
    raw = build_plan_pdf(detail, encrypt=False)
    text = _pdf_text(raw)
    assert "không bị cắt tên" in text
    assert "bài" in text
    assert full_reps in text
    assert "Ức gà — 150 g — 248 kcal" in text
    assert "…" not in text


def _pdf_text(raw: bytes) -> str:
    """Decode text runs using the PDF ToUnicode maps."""
    import re
    import zlib

    streams: list[bytes] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        data = match.group(1)
        try:
            data = zlib.decompress(data)
        except zlib.error:
            pass
        streams.append(data)
    cmaps: list[dict[int, int]] = []
    for data in streams:
        if b"beginbfchar" not in data:
            continue
        cmap: dict[int, int] = {}
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", data):
            cmap[int(src, 16)] = int(dst, 16)
        cmaps.append(cmap)

    def unescape(blob: bytes) -> bytes:
        out = bytearray()
        i = 0
        simple = {
            ord("n"): 10,
            ord("r"): 13,
            ord("t"): 9,
            ord("b"): 8,
            ord("f"): 12,
            ord("("): 40,
            ord(")"): 41,
            ord("\\"): 92,
        }
        while i < len(blob):
            if blob[i] == 0x5C and i + 1 < len(blob):
                nxt = blob[i + 1]
                if nxt in simple:
                    out.append(simple[nxt])
                    i += 2
                    continue
                if 48 <= nxt <= 55:
                    octal = bytearray((nxt,))
                    i += 2
                    for _ in range(2):
                        if i < len(blob) and 48 <= blob[i] <= 55:
                            octal.append(blob[i])
                            i += 1
                        else:
                            break
                    out.append(int(octal, 8))
                    continue
                out.append(nxt)
                i += 2
                continue
            out.append(blob[i])
            i += 1
        return bytes(out)

    def decode(blob: bytes, cmap: dict[int, int]) -> str:
        if len(blob) % 2:
            return ""
        chars: list[str] = []
        for i in range(0, len(blob), 2):
            gid = (blob[i] << 8) | blob[i + 1]
            if gid not in cmap:
                return ""
            chars.append(chr(cmap[gid]))
        return "".join(chars)

    pieces: list[str] = []
    for data in streams:
        if b"Tj" not in data:
            continue
        for match in re.finditer(rb"\((?:\\.|[^\\)])*\)\s*Tj", data):
            inner = unescape(match.group(0)[1 : match.group(0).rfind(b")")])
            for cmap in cmaps:
                text = decode(inner, cmap)
                if text:
                    pieces.append(text)
    return "".join(pieces)


def test_repeat_week_collapses_and_meals_are_summarized():
    exercise = {"section": "main", "name_vi": "Chống đẩy", "sets": 3, "reps": "8"}
    meal = {
        "food_id": 9,
        "meal_type": "breakfast",
        "name_vi": "Ức gà",
        "servings": 1,
        "serving_grams": 150,
        "calories": 200,
    }
    lunch = {**meal, "meal_type": "lunch", "servings": 1, "calories": 200}
    day = {
        "day_number": 1,
        "title_vi": "Ngày 1",
        "exercises": [exercise],
        "meals": [meal, lunch],
        "meal_notes": {},
        "section_notes": {},
        "notes_vi": "",
    }
    next_day = {
        **day,
        "day_number": 2,
        "title_vi": "Ngày 2",
        "exercises": [{"section": "main", "name_vi": "Kéo xà", "sets": 3, "reps": "8"}],
        "meals": [meal],
    }
    detail = {
        **SAMPLE,
        "days": [
            day,
            next_day,
            {**day, "day_number": 8, "title_vi": "Ngày 8"},
            {**next_day, "day_number": 9, "title_vi": "Ngày 9"},
        ],
    }
    text = _pdf_text(build_plan_pdf(detail, encrypt=False))
    assert "Tập giống tuần 1 tháng 1" in text
    assert text.count("Chống đẩy") == 1
    assert text.count("Ức gà — 300 g — 400 kcal") == 1
    assert text.count("Ức gà — 150 g — 200 kcal") == 1
    assert "450" not in text
    assert "Sáng" not in text
    assert "Trưa" not in text


def test_build_plan_pdf_contains_taptot_watermark():
    raw = build_plan_pdf(SAMPLE, encrypt=False)
    assert raw.startswith(b"%PDF")
    assert b"TAPTOT" in raw


def test_build_plan_pdf_restricts_copy():
    raw = build_plan_pdf(SAMPLE, encrypt=True)
    assert raw.startswith(b"%PDF")
    assert b"/Encrypt" in raw


def test_export_service_rejects_legacy_formats():
    svc = ExportService.__new__(ExportService)
    for fmt in ("xlsx", "csv", "word", "json", "excel", "doc"):
        with pytest.raises(BadRequestError, match="pdf"):
            svc._render_detail(SAMPLE, fmt)


def test_export_service_renders_pdf():
    svc = ExportService.__new__(ExportService)
    content, ext, mime = svc._render_detail(SAMPLE, "pdf")
    assert ext == "pdf"
    assert mime == "application/pdf"
    assert content.startswith(b"%PDF")
    assert b"/Encrypt" in content


def test_plan_export_schema_only_allows_pdf():
    PlanExportRequest(format="pdf")
    with pytest.raises(ValidationError):
        PlanExportRequest(format="xlsx")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        PlanExportRequest(format="csv")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        PlanExportRequest(format="word")  # type: ignore[arg-type]
