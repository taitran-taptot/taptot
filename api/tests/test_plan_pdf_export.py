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
