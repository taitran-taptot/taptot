"""Regression: raw/fresh food catalog must pass internal nutrition audit (no FIX)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
SEEDS = ROOT / "seeds"
sys.path.insert(0, str(SCRIPTS))

from audit_raw_foods_nutrition import (  # noqa: E402
    STAPLE_AI,
    atwater,
    internal_issues,
    is_in_raw_cohort,
    load_catalog,
    run_audit,
    severity_from_internal,
)

CATALOG = SEEDS / "foods_catalog_v2.json"

# Snapshot of AI staples that live in the raw/fresh cohort (kcal/100g).
STAPLE_KCAL_100G = {
    "uc-ga-khong-da-song": 110,
    "dui-ga-khong-da-song": 121,
    "thit-lon-than-nac-song": 120,
    "thit-bo-than-song": 150,
    "ca-hoi-atlantic-song": 208,
    "ca-ro-phi-song": 96,
    "tom-the-song": 85,
    "trung-ga-ca-qua-song": 143,
    "ca-chua": 18,
    "cai-thao": 16,
    "chuoi": 89,
    "tao": 52,
    "dua-leo": 15,
}


@pytest.fixture(scope="module")
def foods() -> list[dict]:
    assert CATALOG.exists(), f"missing {CATALOG}"
    return load_catalog(CATALOG)


@pytest.fixture(scope="module")
def by_slug(foods: list[dict]) -> dict[str, dict]:
    return {f["slug"]: f for f in foods}


def test_raw_cohort_has_no_internal_fix(foods: list[dict]) -> None:
    cohort = [f for f in foods if is_in_raw_cohort(f)]
    assert len(cohort) >= 100
    fixes = []
    for f in cohort:
        issues = internal_issues(f)
        if severity_from_internal(issues) == "FIX":
            fixes.append((f["slug"], issues))
    assert fixes == [], f"internal FIX foods: {fixes[:10]}"


def test_run_audit_internal_exit_clean() -> None:
    rows = run_audit(external=False, db_path=None, catalog_path=CATALOG)
    fix = [r for r in rows if r["severity"] == "FIX"]
    assert fix == [], f"audit FIX: {[r['slug'] for r in fix]}"


def test_staple_ai_kcal_snapshot(by_slug: dict[str, dict]) -> None:
    for slug, expected in STAPLE_KCAL_100G.items():
        food = by_slug.get(slug)
        assert food is not None, f"missing staple {slug}"
        kcal = float(food.get("kcal_100g") or food.get("calories") or 0)
        assert abs(kcal - expected) <= 1.0, f"{slug}: {kcal} != {expected}"
        assert slug in STAPLE_AI


def test_serving_100g_sync_for_raw_meats(by_slug: dict[str, dict]) -> None:
    for slug in ("uc-ga-khong-da-song", "thit-lon-ba-chi-song", "thit-bo-xay-90-nac-song"):
        f = by_slug[slug]
        assert abs(float(f["serving_grams"]) - 100) < 0.51
        assert abs(float(f["calories"]) - float(f["kcal_100g"])) <= 1.0
        p, c, fat = float(f["protein_100g"]), float(f["carbs_100g"]), float(f["fat_100g"])
        expected = atwater(p, c, fat)
        assert abs(expected - float(f["kcal_100g"])) <= max(15.0, 0.12 * float(f["kcal_100g"]))


def test_pinned_usda_source_refs(by_slug: dict[str, dict]) -> None:
    assert by_slug["uc-ga-khong-da-song"]["source_ref"] == "usda:171077"
    assert by_slug["thit-lon-ba-chi-song"]["source_ref"] == "usda:167812"
    assert by_slug["thit-bo-xay-90-nac-song"]["source_ref"] == "usda:174030"
    assert by_slug["thit-lon-nac-vai-song"]["source_ref"] == "usda:168255"
