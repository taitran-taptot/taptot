from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.migrations.common import (
    PROJECT_ROOT,
    _apply_schema_file,
    _auth_tables_exist,
    _foods_table_exists,
    _has_column,
    _seed_cooking_posts,
    _table_exists,
)

def ensure_base_schema(engine: Engine) -> None:
    """Apply 001_init + 002_extensions on an empty PostgreSQL database."""
    if engine.dialect.name == "sqlite":
        return
    schema_dir = PROJECT_ROOT / "schema" / "postgresql"
    init_file = schema_dir / "001_init.sql"
    extensions_file = schema_dir / "002_extensions.sql"
    if not init_file.is_file():
        return
    with engine.begin() as conn:
        if _table_exists(conn, "exercises", sqlite=False):
            return
        _apply_schema_file(conn, init_file)
        if extensions_file.is_file() and not _table_exists(conn, "user_daily_plans", sqlite=False):
            _apply_schema_file(conn, extensions_file)


def ensure_auth_extensions(engine: Engine) -> None:
    """Apply auth extension schema once if missing."""
    dialect = engine.dialect.name
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if dialect == "sqlite" else "postgresql")
    schema_file = schema_dir / "003_auth_extensions.sql"

    with engine.begin() as conn:
        if dialect == "sqlite":
            rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            if any(row[1] == "email_verified_at" for row in rows):
                return
            conn.execute(text("ALTER TABLE users ADD COLUMN email_verified_at TEXT"))
            for statement in schema_file.read_text(encoding="utf-8").split(";"):
                lines = [
                    line.strip()
                    for line in statement.splitlines()
                    if line.strip() and not line.strip().startswith("--")
                ]
                if not lines or lines[0].upper().startswith("ALTER TABLE"):
                    continue
                conn.execute(text("\n".join(lines)))
            return

        if _auth_tables_exist(conn):
            return
        conn.execute(text(schema_file.read_text(encoding="utf-8")))


def ensure_plan_section_column(engine: Engine) -> None:
    """Ensure user_daily_plan_exercises.section exists (warmup/main/cooldown/cardio)."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        if _has_column(conn, "user_daily_plan_exercises", "section", sqlite=is_sqlite):
            return
        if is_sqlite:
            conn.execute(
                text(
                    "ALTER TABLE user_daily_plan_exercises "
                    "ADD COLUMN section TEXT NOT NULL DEFAULT 'main'"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_user_daily_plan_exercises_section "
                    "ON user_daily_plan_exercises(plan_day_id, section, sort_order)"
                )
            )
            return
        conn.execute(
            text(
                "ALTER TABLE user_daily_plan_exercises "
                "ADD COLUMN IF NOT EXISTS section VARCHAR(20) NOT NULL DEFAULT 'main'"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_user_daily_plan_exercises_section "
                "ON user_daily_plan_exercises(plan_day_id, section, sort_order)"
            )
        )


def ensure_plan_share_token(engine: Engine) -> None:
    """Ensure user_daily_plans.share_token exists and user_id can be null (guest plans)."""
    import secrets

    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        if not _has_column(conn, "user_daily_plans", "share_token", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(text("ALTER TABLE user_daily_plans ADD COLUMN share_token TEXT"))
            else:
                conn.execute(
                    text("ALTER TABLE user_daily_plans ADD COLUMN IF NOT EXISTS share_token VARCHAR(64)")
                )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_daily_plans_share_token "
                    "ON user_daily_plans(share_token)"
                )
            )

        rows = conn.execute(
            text("SELECT id FROM user_daily_plans WHERE share_token IS NULL OR share_token = ''")
        ).fetchall()
        for (plan_id,) in rows:
            token = secrets.token_urlsafe(12)
            conn.execute(
                text("UPDATE user_daily_plans SET share_token = :t WHERE id = :id"),
                {"t": token, "id": plan_id},
            )

        if not is_sqlite:
            row = conn.execute(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'user_daily_plans' "
                    "AND column_name = 'user_id'"
                )
            ).scalar()
            if row == "NO":
                conn.execute(text("ALTER TABLE user_daily_plans ALTER COLUMN user_id DROP NOT NULL"))


def ensure_equipment_image_columns(engine: Engine) -> None:
    """Ensure equipment has image_url / image_source / image_attribution."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    cols = ("image_url", "image_source", "image_attribution")
    with engine.begin() as conn:
        for col in cols:
            if _has_column(conn, "equipment", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE equipment ADD COLUMN {col} TEXT"))
            else:
                conn.execute(text(f"ALTER TABLE equipment ADD COLUMN IF NOT EXISTS {col} TEXT"))


def ensure_exercise_content_columns(engine: Engine) -> None:
    """Ensure exercises has dedicated content fields for the detail modal."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    # (column, sqlite_type, postgres_type)
    cols = (
        ("instruction_vi", "TEXT", "TEXT"),
        ("instruction_steps_vi", "TEXT", "JSONB"),
        ("common_mistakes_vi", "TEXT", "TEXT"),
        ("tips_vi", "TEXT", "TEXT"),
        ("gif_url", "TEXT", "TEXT"),
        ("image_url", "TEXT", "TEXT"),
        ("video_url", "TEXT", "TEXT"),
    )
    with engine.begin() as conn:
        for col, sqlite_type, pg_type in cols:
            if _has_column(conn, "exercises", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE exercises ADD COLUMN {col} {sqlite_type}"))
            else:
                conn.execute(
                    text(f"ALTER TABLE exercises ADD COLUMN IF NOT EXISTS {col} {pg_type}")
                )


def ensure_feedback_contact_tables(engine: Engine) -> None:
    """Create feedback_suggestions + trainer_contact_requests if missing."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    schema_file = schema_dir / "010_feedback_contact.sql"
    with engine.begin() as conn:
        if _table_exists(conn, "feedback_suggestions", sqlite=is_sqlite) and _table_exists(
            conn, "trainer_contact_requests", sqlite=is_sqlite
        ):
            return
        sql = schema_file.read_text(encoding="utf-8")
        for statement in sql.split(";"):
            lines = [
                line.strip()
                for line in statement.splitlines()
                if line.strip() and not line.strip().startswith("--")
            ]
            if not lines:
                continue
            conn.execute(text("\n".join(lines)))


def ensure_plan_macros_and_meal_templates(engine: Engine) -> None:
    """Add plan macro targets + meal template note columns."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        plan_cols = (
            ("target_protein_g", "REAL", "REAL"),
            ("target_carbs_g", "REAL", "REAL"),
            ("target_fat_g", "REAL", "REAL"),
        )
        for col, sqlite_type, pg_type in plan_cols:
            if _has_column(conn, "user_daily_plans", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE user_daily_plans ADD COLUMN {col} {sqlite_type}"))
            else:
                conn.execute(
                    text(f"ALTER TABLE user_daily_plans ADD COLUMN IF NOT EXISTS {col} {pg_type}")
                )

        if not _has_column(conn, "meal_plans", "meal_notes_json", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(
                    text("ALTER TABLE meal_plans ADD COLUMN meal_notes_json TEXT NOT NULL DEFAULT '{}'")
                )
            else:
                conn.execute(
                    text(
                        "ALTER TABLE meal_plans "
                        "ADD COLUMN IF NOT EXISTS meal_notes_json JSONB NOT NULL DEFAULT '{}'"
                    )
                )

        if not _has_column(conn, "meal_plan_items", "notes_vi", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(text("ALTER TABLE meal_plan_items ADD COLUMN notes_vi TEXT"))
            else:
                conn.execute(
                    text("ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS notes_vi TEXT")
                )


def ensure_phase3_polish(engine: Engine) -> None:
    """Custom foods (owner_user_id)."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        if not _has_column(conn, "foods", "owner_user_id", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(text("ALTER TABLE foods ADD COLUMN owner_user_id TEXT"))
            else:
                conn.execute(
                    text(
                        "ALTER TABLE foods ADD COLUMN IF NOT EXISTS owner_user_id "
                        "UUID REFERENCES users(id) ON DELETE CASCADE"
                    )
                )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_foods_owner_user ON foods(owner_user_id)")
            )


def ensure_trainer_client_fields(engine: Engine) -> None:
    """Trainer-entered client info stored on trainer_clients."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    text_cols = ("full_name", "goal", "gender")
    with engine.begin() as conn:
        for col in text_cols:
            if _has_column(conn, "trainer_clients", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE trainer_clients ADD COLUMN {col} TEXT"))
            else:
                conn.execute(
                    text(f"ALTER TABLE trainer_clients ADD COLUMN IF NOT EXISTS {col} TEXT")
                )
        if not _has_column(conn, "trainer_clients", "age", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(text("ALTER TABLE trainer_clients ADD COLUMN age INTEGER"))
            else:
                conn.execute(
                    text("ALTER TABLE trainer_clients ADD COLUMN IF NOT EXISTS age INTEGER")
                )
        for col in ("height_cm", "weight_kg"):
            if _has_column(conn, "trainer_clients", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE trainer_clients ADD COLUMN {col} REAL"))
            else:
                conn.execute(
                    text(
                        f"ALTER TABLE trainer_clients ADD COLUMN IF NOT EXISTS {col} DECIMAL(6, 2)"
                    )
                )


def ensure_trainer_profile_fields(engine: Engine) -> None:
    """Profile fields + credentials table for trainers."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        for col, sqlite_type, pg_type in (
            ("full_name", "TEXT", "TEXT"),
            ("age", "INTEGER", "INTEGER"),
            ("years_experience", "INTEGER", "INTEGER"),
            ("share_token", "TEXT", "VARCHAR(64)"),
        ):
            if _has_column(conn, "trainer_profiles", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE trainer_profiles ADD COLUMN {col} {sqlite_type}"))
            else:
                conn.execute(
                    text(
                        f"ALTER TABLE trainer_profiles ADD COLUMN IF NOT EXISTS {col} {pg_type}"
                    )
                )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_trainer_profiles_share_token "
                "ON trainer_profiles(share_token)"
            )
        )

        if is_sqlite:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS trainer_credentials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trainer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        kind TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        image_urls TEXT NOT NULL DEFAULT '[]',
                        created_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                    """
                )
            )
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS trainer_credentials (
                        id SERIAL PRIMARY KEY,
                        trainer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        kind VARCHAR(20) NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        image_urls JSONB NOT NULL DEFAULT '[]',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_trainer_credentials_trainer "
                "ON trainer_credentials(trainer_id)"
            )
        )


def ensure_plan_ai_generation(engine: Engine) -> None:
    """Add user_daily_plans.ai_generation_id so AI plans can be restored to their original output."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if not _has_column(conn, "user_daily_plans", "ai_generation_id", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(
                    text("ALTER TABLE user_daily_plans ADD COLUMN ai_generation_id INTEGER")
                )
            else:
                conn.execute(
                    text(
                        "ALTER TABLE user_daily_plans "
                        "ADD COLUMN IF NOT EXISTS ai_generation_id INTEGER"
                    )
                )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_user_daily_plans_ai_generation "
                "ON user_daily_plans(ai_generation_id)"
            )
        )


def ensure_ai_prompt_meta(engine: Engine) -> None:
    """Add prompt_version / system_prompt_hash to ai_generations."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        for col in ("prompt_version", "system_prompt_hash"):
            if is_sqlite:
                cols = {
                    r[1]
                    for r in conn.execute(text("PRAGMA table_info(ai_generations)")).fetchall()
                }
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE ai_generations ADD COLUMN {col} TEXT"))
            else:
                conn.execute(
                    text(
                        f"ALTER TABLE ai_generations ADD COLUMN IF NOT EXISTS {col} TEXT"
                    )
                )


def ensure_food_catalog_v2(engine: Engine) -> None:
    """Food kind / per-100g columns + food_portions table."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        food_cols_sqlite = (
            ("food_kind", "TEXT NOT NULL DEFAULT 'ingredient'"),
            ("prep_state", "TEXT"),
            ("status", "TEXT NOT NULL DEFAULT 'active'"),
            ("merged_into_id", "INTEGER"),
            ("kcal_100g", "REAL"),
            ("protein_100g", "REAL"),
            ("carbs_100g", "REAL"),
            ("fat_100g", "REAL"),
            ("fiber_100g", "REAL"),
            ("sugar_100g", "REAL"),
            ("sodium_100mg", "REAL"),
            ("alcohol_100g", "REAL"),
            ("source_ref", "TEXT"),
            ("confidence", "TEXT NOT NULL DEFAULT 'estimated'"),
            ("yield_factor", "REAL"),
            ("density_g_per_ml", "REAL"),
        )
        food_cols_pg = (
            ("food_kind", "VARCHAR(20) NOT NULL DEFAULT 'ingredient'"),
            ("prep_state", "VARCHAR(10)"),
            ("status", "VARCHAR(12) NOT NULL DEFAULT 'active'"),
            ("merged_into_id", "INT"),
            ("kcal_100g", "DECIMAL(7,2)"),
            ("protein_100g", "DECIMAL(6,2)"),
            ("carbs_100g", "DECIMAL(6,2)"),
            ("fat_100g", "DECIMAL(6,2)"),
            ("fiber_100g", "DECIMAL(6,2)"),
            ("sugar_100g", "DECIMAL(6,2)"),
            ("sodium_100mg", "DECIMAL(8,2)"),
            ("alcohol_100g", "DECIMAL(5,2)"),
            ("source_ref", "VARCHAR(120)"),
            ("confidence", "VARCHAR(10) NOT NULL DEFAULT 'estimated'"),
            ("yield_factor", "DECIMAL(4,2)"),
            ("density_g_per_ml", "DECIMAL(5,3)"),
        )
        for col, typ in food_cols_sqlite if is_sqlite else food_cols_pg:
            if _has_column(conn, "foods", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE foods ADD COLUMN {col} {typ}"))
            else:
                conn.execute(text(f"ALTER TABLE foods ADD COLUMN IF NOT EXISTS {col} {typ}"))

        if is_sqlite:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS food_portions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        food_id INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
                        label_vi TEXT NOT NULL,
                        grams REAL NOT NULL,
                        is_default INTEGER NOT NULL DEFAULT 0,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        UNIQUE (food_id, label_vi)
                    )
                    """
                )
            )
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS food_portions (
                        id SERIAL PRIMARY KEY,
                        food_id INT NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
                        label_vi VARCHAR(60) NOT NULL,
                        grams DECIMAL(7,2) NOT NULL,
                        is_default BOOLEAN NOT NULL DEFAULT FALSE,
                        sort_order INT NOT NULL DEFAULT 0,
                        UNIQUE (food_id, label_vi)
                    )
                    """
                )
            )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_food_portions_food ON food_portions(food_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_foods_kind ON foods(food_kind)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_foods_status ON foods(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_foods_prep_state ON foods(prep_state)"))

        for table in ("meal_plan_items", "user_daily_plan_meals"):
            if not _has_column(conn, table, "grams", sqlite=is_sqlite):
                if is_sqlite:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN grams REAL"))
                else:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS grams DECIMAL(7,2)")
                    )
            if not _has_column(conn, table, "portion_id", sqlite=is_sqlite):
                if is_sqlite:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN portion_id INTEGER"))
                else:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS portion_id INT")
                    )


CATALOG_V2_CATEGORY_MAP = {
    "trai-cay-rau-cu": "rau-cu-qua",
    "thit-hai-san": "thit-gia-cam-noi-tang",
    "trung-sua": "trung-whey",
    "hat-dau": "ngu-coc-hat",
    "mon-phu-an-vat": "ngu-coc-hat",
}
SEAFOOD_PREFIXES = (
    "ca-",
    "tom-",
    "cua-",
    "ghe-",
    "muc-",
    "bach-",
    "so-",
    "ngao-",
    "hau",
    "oc-",
)


def _catalog_v2_category_slug(item: dict) -> str:
    raw = str(item.get("category_slug") or "")
    mapped = CATALOG_V2_CATEGORY_MAP.get(raw, raw or "rau-cu-qua")
    slug = str(item.get("slug") or "")
    if raw == "thit-hai-san" and slug.startswith(SEAFOOD_PREFIXES):
        return "ca-thuy-hai-san"
    return mapped or "rau-cu-qua"


def ensure_foods_catalog_v2_rows(engine: Engine) -> None:
    """Upsert ingredient rows from seeds/foods_catalog_v2.json so recipes can hydrate photos."""
    import json
    from datetime import UTC, datetime

    from sqlalchemy.orm import Session

    from app.models.entities import Food, FoodAlias, FoodCategory, FoodPortion

    seed_path = PROJECT_ROOT / "seeds" / "foods_catalog_v2.json"
    if not seed_path.is_file():
        return
    foods = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(foods, list) or not foods:
        return
    images_path = PROJECT_ROOT / "seeds" / "food_images.json"
    image_map = {}
    if images_path.is_file():
        raw_map = json.loads(images_path.read_text(encoding="utf-8"))
        if isinstance(raw_map, dict):
            image_map = raw_map

    media_root = PROJECT_ROOT / "uploads" / "media"
    now = datetime.now(UTC)
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as conn:
        if not _foods_table_exists(conn, sqlite=is_sqlite):
            return
        if not _table_exists(conn, "food_categories", sqlite=is_sqlite):
            return
    with Session(engine) as db:
        wanted = {
            "rau-cu-qua": ("Rau - Củ - Quả", 1),
            "thit-gia-cam-noi-tang": ("Thịt - Gia cầm - Nội tạng", 2),
            "ca-thuy-hai-san": ("Cá & Thủy hải sản", 3),
            "trung-whey": ("Trứng & Whey", 4),
            "ngu-coc-hat": ("Ngũ cốc - Hạt", 5),
        }
        cat_ids: dict[str, int] = {}
        for slug, (name, order) in wanted.items():
            cat = db.query(FoodCategory).filter(FoodCategory.slug == slug).first()
            if cat is None:
                cat = FoodCategory(slug=slug, name_vi=name, sort_order=order)
                db.add(cat)
                db.flush()
            cat_ids[slug] = cat.id

        for item in foods:
            if not isinstance(item, dict):
                continue
            if str(item.get("food_kind") or "ingredient") != "ingredient":
                continue
            slug = str(item.get("slug") or "").strip()
            if not slug:
                continue
            serving_grams = float(item.get("serving_grams") or 100)
            kcal_100 = float(item.get("kcal_100g") or 0)
            protein_100 = float(item.get("protein_100g") or 0)
            carbs_100 = float(item.get("carbs_100g") or 0)
            fat_100 = float(item.get("fat_100g") or 0)
            fiber_100 = item.get("fiber_100g")
            sodium_100 = item.get("sodium_100mg")
            scale = serving_grams / 100.0
            cover = None
            for candidate in (
                (item.get("image_url") or "").strip().replace("\\", "/").lstrip("/"),
                str(image_map.get(slug) or "").replace("\\", "/").lstrip("/"),
                f"foods/{slug}.jpg",
            ):
                if candidate and (media_root / candidate).is_file():
                    cover = candidate
                    break
            cat_slug = _catalog_v2_category_slug(item)
            fields = {
                "name_vi": str(item.get("name_vi") or slug),
                "name_en": item.get("name_en"),
                "category_id": cat_ids.get(cat_slug),
                "serving_size": str(item.get("serving_size") or "100g"),
                "serving_grams": serving_grams,
                "calories": round(kcal_100 * scale, 2),
                "protein_g": round(protein_100 * scale, 2),
                "carbs_g": round(carbs_100 * scale, 2),
                "fat_g": round(fat_100 * scale, 2),
                "fiber_g": None if fiber_100 is None else round(float(fiber_100) * scale, 2),
                "sodium_mg": None if sodium_100 is None else round(float(sodium_100) * scale, 2),
                "is_verified": bool(item.get("is_verified", True)),
                "is_common": bool(item.get("is_common", True)),
                "tags": item.get("tags") or [],
                "food_kind": "ingredient",
                "prep_state": item.get("prep_state") or "raw",
                "status": "active",
                "kcal_100g": kcal_100,
                "protein_100g": protein_100,
                "carbs_100g": carbs_100,
                "fat_100g": fat_100,
                "fiber_100g": None if fiber_100 is None else float(fiber_100),
                "sodium_100mg": None if sodium_100 is None else float(sodium_100),
                "source_ref": item.get("source_ref") or "usda-vn-table",
                "confidence": str(item.get("confidence") or "reference"),
                "macro_roles": item.get("macro_roles") or [],
                "meal_slots": item.get("meal_slots") or ["lunch", "dinner"],
                "ai_eligible": bool(item.get("ai_eligible", True)),
                "ai_priority": int(item.get("ai_priority") or 0),
                "is_complete_meal": False,
                "default_for_ai": bool(item.get("default_for_ai", False)),
            }
            if cover:
                fields["image_url"] = cover
            row = db.query(Food).filter(Food.slug == slug).first()
            if row is None:
                db.add(Food(slug=slug, created_at=now, vitamins_json={}, **fields))
                db.flush()
                row = db.query(Food).filter(Food.slug == slug).first()
            else:
                for key, value in fields.items():
                    setattr(row, key, value)
            if row is None:
                continue
            db.query(FoodPortion).filter(FoodPortion.food_id == row.id).delete()
            for i, portion in enumerate(item.get("portions") or [{"label_vi": "100g", "grams": 100, "is_default": True, "sort_order": 0}]):
                db.add(
                    FoodPortion(
                        food_id=row.id,
                        label_vi=str(portion["label_vi"]),
                        grams=float(portion["grams"]),
                        is_default=bool(portion.get("is_default")),
                        sort_order=int(portion.get("sort_order") or i),
                    )
                )
            if item.get("aliases"):
                db.query(FoodAlias).filter(FoodAlias.food_id == row.id).delete()
                for alias in item.get("aliases") or []:
                    text_alias = str(alias).strip()
                    if text_alias:
                        db.add(FoodAlias(food_id=row.id, alias=text_alias))
        db.commit()


def ensure_workout_session_plan_fks(engine: Engine) -> None:
    """Link workout_sessions to user daily plans for journal / progress tracking."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        for col in ("daily_plan_id", "daily_plan_day_id"):
            if _has_column(conn, "workout_sessions", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE workout_sessions ADD COLUMN {col} INTEGER"))
            else:
                conn.execute(
                    text(
                        f"ALTER TABLE workout_sessions ADD COLUMN IF NOT EXISTS {col} INTEGER"
                    )
                )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_workout_sessions_daily_plan "
                "ON workout_sessions(daily_plan_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_started "
                "ON workout_sessions(user_id, started_at)"
            )
        )


def ensure_plan_guest_ttl(engine: Engine) -> None:
    """Guest expiry flag: challenge_100_days on user_daily_plans."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if _has_column(conn, "user_daily_plans", "challenge_100_days", sqlite=is_sqlite):
            return
        if is_sqlite:
            conn.execute(
                text(
                    "ALTER TABLE user_daily_plans "
                    "ADD COLUMN challenge_100_days INTEGER NOT NULL DEFAULT 0"
                )
            )
        else:
            conn.execute(
                text(
                    "ALTER TABLE user_daily_plans "
                    "ADD COLUMN IF NOT EXISTS challenge_100_days BOOLEAN NOT NULL DEFAULT false"
                )
            )


def ensure_plan_insights_json(engine: Engine) -> None:
    """Add user_daily_plans.insights_json for AI plan knowledge toggle."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if _has_column(conn, "user_daily_plans", "insights_json", sqlite=is_sqlite):
            return
        if is_sqlite:
            conn.execute(text("ALTER TABLE user_daily_plans ADD COLUMN insights_json TEXT"))
        else:
            conn.execute(
                text(
                    "ALTER TABLE user_daily_plans "
                    "ADD COLUMN IF NOT EXISTS insights_json JSONB"
                )
            )


def ensure_plan_day_nutrition(engine: Engine) -> None:
    """Per-day calorie/macro targets on user_daily_plan_days."""
    is_sqlite = engine.dialect.name == "sqlite"
    cols = (
        ("target_calories", "INTEGER"),
        ("target_protein_g", "REAL"),
        ("target_carbs_g", "REAL"),
        ("target_fat_g", "REAL"),
    )
    with engine.begin() as conn:
        for col, typ in cols:
            if _has_column(conn, "user_daily_plan_days", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE user_daily_plan_days ADD COLUMN {col} {typ}"))
            else:
                pg_typ = "DOUBLE PRECISION" if typ == "REAL" else typ
                conn.execute(
                    text(
                        f"ALTER TABLE user_daily_plan_days "
                        f"ADD COLUMN IF NOT EXISTS {col} {pg_typ}"
                    )
                )


def ensure_food_ai_metadata(engine: Engine) -> None:
    """AI meal-generation metadata on foods (macro_roles, meal_slots, ai_priority)."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if is_sqlite:
            cols = (
                ("macro_roles", "TEXT NOT NULL DEFAULT '[]'"),
                ("meal_slots", "TEXT NOT NULL DEFAULT '[]'"),
                ("ai_eligible", "INTEGER NOT NULL DEFAULT 1"),
                ("ai_priority", "INTEGER NOT NULL DEFAULT 0"),
                ("is_complete_meal", "INTEGER"),
                ("default_for_ai", "INTEGER NOT NULL DEFAULT 0"),
            )
        else:
            cols = (
                ("macro_roles", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
                ("meal_slots", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
                ("ai_eligible", "BOOLEAN NOT NULL DEFAULT TRUE"),
                ("ai_priority", "SMALLINT NOT NULL DEFAULT 0"),
                ("is_complete_meal", "BOOLEAN"),
                ("default_for_ai", "BOOLEAN NOT NULL DEFAULT FALSE"),
            )
        for col, typ in cols:
            if _has_column(conn, "foods", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE foods ADD COLUMN {col} {typ}"))
            else:
                conn.execute(text(f"ALTER TABLE foods ADD COLUMN IF NOT EXISTS {col} {typ}"))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_foods_ai_eligible_priority "
                "ON foods(ai_eligible, ai_priority DESC)"
            )
        )


def ensure_drop_unused_legacy(engine: Engine) -> None:
    """Drop unused legacy tables and leftover FK columns."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    schema_file = schema_dir / "031_drop_unused_legacy.sql"
    leftover_columns = (
        ("knowledge_articles", "series_id"),
        ("workout_sessions", "program_day_id"),
        ("workout_sessions", "enrollment_id"),
        ("trainer_assigned_plans", "workout_plan_id"),
        ("trainer_assigned_plans", "program_id"),
    )
    with engine.begin() as conn:
        if schema_file.is_file():
            _apply_schema_file(conn, schema_file)
        for table, column in leftover_columns:
            if not _table_exists(conn, table, sqlite=is_sqlite):
                continue
            if not _has_column(conn, table, column, sqlite=is_sqlite):
                continue
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))


def ensure_exercise_prescription_defaults(engine: Engine) -> None:
    """Create exercise_prescription_defaults and upsert L1–L3 compound/isolation rows."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    schema_file = schema_dir / "021_exercise_prescription_defaults.sql"

    with engine.begin() as conn:
        if not _table_exists(conn, "exercise_prescription_defaults", sqlite=is_sqlite):
            sql = schema_file.read_text(encoding="utf-8")
            for statement in sql.split(";"):
                lines = [
                    line.strip()
                    for line in statement.splitlines()
                    if line.strip() and not line.strip().startswith("--")
                ]
                if not lines:
                    continue
                conn.execute(text("\n".join(lines)))

        from app.services.exercise_prescription_seed import PRESCRIPTION_SEED

        upsert = text(
            """
            INSERT INTO exercise_prescription_defaults (
                experience_level, movement_role, default_sets, default_reps
            ) VALUES (:level, :role, :sets, :reps)
            ON CONFLICT (experience_level, movement_role) DO UPDATE SET
                default_sets = excluded.default_sets,
                default_reps = excluded.default_reps
            """
        )
        for level, role, sets, reps in PRESCRIPTION_SEED:
            conn.execute(
                upsert,
                {"level": level, "role": role, "sets": sets, "reps": reps},
            )


def ensure_session_block_templates(engine: Engine) -> None:
    """Create session_block_templates and upsert L1–L3 session structure rows."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    schema_file = schema_dir / "022_session_block_templates.sql"

    with engine.begin() as conn:
        if not _table_exists(conn, "session_block_templates", sqlite=is_sqlite):
            sql = schema_file.read_text(encoding="utf-8")
            for statement in sql.split(";"):
                lines = [
                    line.strip()
                    for line in statement.splitlines()
                    if line.strip() and not line.strip().startswith("--")
                ]
                if not lines:
                    continue
                conn.execute(text("\n".join(lines)))

        from app.services.session_block_template_seed import SESSION_BLOCK_SEED

        upsert = text(
            """
            INSERT INTO session_block_templates (
                experience_level, sort_order, block_key, label_vi, plan_section,
                movement_role, count_min, count_max,
                duration_min_minutes, duration_max_minutes, is_optional
            ) VALUES (
                :level, :sort_order, :block_key, :label_vi, :plan_section,
                :movement_role, :count_min, :count_max,
                :duration_min, :duration_max, :is_optional
            )
            ON CONFLICT (experience_level, block_key) DO UPDATE SET
                sort_order = excluded.sort_order,
                label_vi = excluded.label_vi,
                plan_section = excluded.plan_section,
                movement_role = excluded.movement_role,
                count_min = excluded.count_min,
                count_max = excluded.count_max,
                duration_min_minutes = excluded.duration_min_minutes,
                duration_max_minutes = excluded.duration_max_minutes,
                is_optional = excluded.is_optional
            """
        )
        for (
            level,
            sort_order,
            block_key,
            label_vi,
            plan_section,
            movement_role,
            count_min,
            count_max,
            duration_min,
            duration_max,
            is_optional,
        ) in SESSION_BLOCK_SEED:
            optional_val = (1 if is_optional else 0) if is_sqlite else bool(is_optional)
            conn.execute(
                upsert,
                {
                    "level": level,
                    "sort_order": sort_order,
                    "block_key": block_key,
                    "label_vi": label_vi,
                    "plan_section": plan_section,
                    "movement_role": movement_role,
                    "count_min": count_min,
                    "count_max": count_max,
                    "duration_min": duration_min,
                    "duration_max": duration_max,
                    "is_optional": optional_val,
                },
            )


def ensure_exercise_movement_role(engine: Engine) -> None:
    """Add exercises.movement_role and backfill nulls via name/type heuristics."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        if not _has_column(conn, "exercises", "movement_role", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN movement_role TEXT"))
            else:
                conn.execute(
                    text(
                        "ALTER TABLE exercises "
                        "ADD COLUMN IF NOT EXISTS movement_role VARCHAR(20)"
                    )
                )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_exercises_movement_role "
                "ON exercises(movement_role)"
            )
        )

        # Only classify when we have the modern catalog columns.
        has_type = _has_column(conn, "exercises", "exercise_type", sqlite=is_sqlite)
        has_name_vi = _has_column(conn, "exercises", "name_vi", sqlite=is_sqlite)
        has_name_en = _has_column(conn, "exercises", "name_en", sqlite=is_sqlite)
        if not has_name_vi and not has_name_en:
            return

        select_cols = ["id"]
        if has_name_vi:
            select_cols.append("name_vi")
        if has_name_en:
            select_cols.append("name_en")
        if has_type:
            select_cols.append("exercise_type")

        rows = conn.execute(
            text(
                f"SELECT {', '.join(select_cols)} FROM exercises "
                "WHERE movement_role IS NULL OR TRIM(COALESCE(movement_role, '')) = ''"
            )
        ).mappings().all()
        if not rows:
            return

        from app.services.exercise_movement_role import infer_movement_role

        for row in rows:
            payload = dict(row)
            role = infer_movement_role(payload)
            conn.execute(
                text("UPDATE exercises SET movement_role = :role WHERE id = :id"),
                {"role": role, "id": row["id"]},
            )


def ensure_exercise_movement_pattern(engine: Engine) -> None:
    """Add exercises.movement_pattern and backfill nulls via name heuristics."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        if not _has_column(conn, "exercises", "movement_pattern", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN movement_pattern TEXT"))
            else:
                conn.execute(
                    text(
                        "ALTER TABLE exercises "
                        "ADD COLUMN IF NOT EXISTS movement_pattern VARCHAR(20)"
                    )
                )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_exercises_movement_pattern "
                "ON exercises(movement_pattern)"
            )
        )

        has_type = _has_column(conn, "exercises", "exercise_type", sqlite=is_sqlite)
        has_name_vi = _has_column(conn, "exercises", "name_vi", sqlite=is_sqlite)
        has_name_en = _has_column(conn, "exercises", "name_en", sqlite=is_sqlite)
        if not has_name_vi and not has_name_en:
            return

        select_cols = ["id"]
        if has_name_vi:
            select_cols.append("name_vi")
        if has_name_en:
            select_cols.append("name_en")
        if has_type:
            select_cols.append("exercise_type")

        rows = conn.execute(
            text(
                f"SELECT {', '.join(select_cols)} FROM exercises "
                "WHERE movement_pattern IS NULL OR TRIM(COALESCE(movement_pattern, '')) = ''"
            )
        ).mappings().all()
        if not rows:
            return

        from app.services.exercise_movement_pattern import infer_movement_pattern

        for row in rows:
            payload = dict(row)
            pattern = infer_movement_pattern(payload)
            conn.execute(
                text("UPDATE exercises SET movement_pattern = :pattern WHERE id = :id"),
                {"pattern": pattern, "id": row["id"]},
            )


def ensure_exercise_secondary_muscles(engine: Engine) -> None:
    """Ensure exercises.secondary_muscles JSON column exists."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        if _has_column(conn, "exercises", "secondary_muscles", sqlite=is_sqlite):
            return
        if is_sqlite:
            conn.execute(
                text(
                    "ALTER TABLE exercises "
                    "ADD COLUMN secondary_muscles TEXT NOT NULL DEFAULT '[]'"
                )
            )
        else:
            conn.execute(
                text(
                    "ALTER TABLE exercises "
                    "ADD COLUMN IF NOT EXISTS secondary_muscles "
                    "JSONB NOT NULL DEFAULT '[]'::jsonb"
                )
            )


def ensure_exercise_venue_and_difficulty_v2(engine: Engine) -> None:
    """Add exercises.venue, clamp difficulty to 1–4, default NULL venue to both."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    with engine.begin() as conn:
        if not _has_column(conn, "exercises", "venue", sqlite=is_sqlite):
            if is_sqlite:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN venue TEXT"))
            else:
                conn.execute(
                    text(
                        "ALTER TABLE exercises "
                        "ADD COLUMN IF NOT EXISTS venue VARCHAR(10)"
                    )
                )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_exercises_venue ON exercises(venue)")
        )

        if _has_column(conn, "exercises", "difficulty", sqlite=is_sqlite):
            conn.execute(text("UPDATE exercises SET difficulty = 4 WHERE difficulty > 4"))
            conn.execute(text("UPDATE exercises SET difficulty = 1 WHERE difficulty < 1"))

        conn.execute(
            text(
                "UPDATE exercises SET venue = 'both' "
                "WHERE venue IS NULL OR TRIM(COALESCE(venue, '')) = ''"
            )
        )
        if _has_column(conn, "exercises", "name_vi", sqlite=is_sqlite):
            name_en_expr = (
                "LOWER(COALESCE(name_en, ''))"
                if _has_column(conn, "exercises", "name_en", sqlite=is_sqlite)
                else "''"
            )
            conn.execute(
                text(
                    "UPDATE exercises SET venue = 'gym' "
                    f"WHERE {name_en_expr} LIKE '%sled%' "
                    "OR LOWER(COALESCE(name_vi, '')) LIKE '%xe trượt%' "
                    "OR LOWER(COALESCE(name_vi, '')) LIKE '%xe truot%'"
                )
            )
            if _has_column(conn, "exercises", "name_en", sqlite=is_sqlite):
                conn.execute(
                    text(
                        "UPDATE exercises SET name_vi = COALESCE("
                        "NULLIF(TRIM(COALESCE(name_en, '')), ''), "
                        "'Bài tập ' || CAST(id AS TEXT)"
                        ") "
                        "WHERE name_vi IS NULL OR TRIM(COALESCE(name_vi, '')) = '' "
                        "OR LOWER(TRIM(name_vi)) = 'none'"
                    )
                )
            else:
                conn.execute(
                    text(
                        "UPDATE exercises SET name_vi = 'Bài tập ' || CAST(id AS TEXT) "
                        "WHERE name_vi IS NULL OR TRIM(COALESCE(name_vi, '')) = '' "
                        "OR LOWER(TRIM(name_vi)) = 'none'"
                    )
                )


def ensure_cooking_posts(engine: Engine) -> None:
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    with engine.begin() as conn:
        if not _table_exists(conn, "cooking_posts", sqlite=is_sqlite):
            _apply_schema_file(conn, schema_dir / "025_cooking_posts.sql")
        recipe_cols = (
            (
                ("dish_slug", "TEXT"),
                ("servings", "INTEGER NOT NULL DEFAULT 1"),
                ("yield_grams", "REAL"),
                ("ingredients", "TEXT NOT NULL DEFAULT '[]'"),
            )
            if is_sqlite
            else (
                ("dish_slug", "VARCHAR(150)"),
                ("servings", "INT NOT NULL DEFAULT 1"),
                ("yield_grams", "DECIMAL(8,2)"),
                ("ingredients", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
            )
        )
        for col, typ in recipe_cols:
            if _has_column(conn, "cooking_posts", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE cooking_posts ADD COLUMN {col} {typ}"))
            else:
                conn.execute(text(f"ALTER TABLE cooking_posts ADD COLUMN IF NOT EXISTS {col} {typ}"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cooking_posts_dish_slug ON cooking_posts(dish_slug)"))
    _seed_cooking_posts(engine)


def ensure_shop_tables(engine: Engine) -> None:
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    with engine.begin() as conn:
        if _table_exists(conn, "shop_products", sqlite=is_sqlite) and _table_exists(
            conn, "shop_orders", sqlite=is_sqlite
        ):
            return
        _apply_schema_file(conn, schema_dir / "026_shop.sql")


def ensure_muscle_groups_hierarchy(engine: Engine) -> None:
    """Add parent_id/is_filter_only, seed region taxonomy, remap coarse exercises."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    schema_file = schema_dir / "028_muscle_groups_hierarchy.sql"

    with engine.begin() as conn:
        if not _table_exists(conn, "muscle_groups", sqlite=is_sqlite):
            return

        if is_sqlite:
            if not _has_column(conn, "muscle_groups", "parent_id", sqlite=True):
                conn.execute(text("ALTER TABLE muscle_groups ADD COLUMN parent_id INTEGER"))
            if not _has_column(conn, "muscle_groups", "is_filter_only", sqlite=True):
                conn.execute(
                    text(
                        "ALTER TABLE muscle_groups "
                        "ADD COLUMN is_filter_only INTEGER NOT NULL DEFAULT 0"
                    )
                )
        else:
            if schema_file.is_file():
                _apply_schema_file(conn, schema_file)
            else:
                if not _has_column(conn, "muscle_groups", "parent_id", sqlite=False):
                    conn.execute(
                        text(
                            "ALTER TABLE muscle_groups "
                            "ADD COLUMN parent_id INT REFERENCES muscle_groups(id) "
                            "ON DELETE SET NULL"
                        )
                    )
                if not _has_column(conn, "muscle_groups", "is_filter_only", sqlite=False):
                    conn.execute(
                        text(
                            "ALTER TABLE muscle_groups "
                            "ADD COLUMN IF NOT EXISTS is_filter_only "
                            "BOOLEAN NOT NULL DEFAULT FALSE"
                        )
                    )

        from app.services.muscle_group_hierarchy_seed import (
            remap_exercises_to_leaf_regions,
            seed_muscle_group_hierarchy,
        )

        seed_muscle_group_hierarchy(conn, is_sqlite=is_sqlite)
        remap_exercises_to_leaf_regions(conn, is_sqlite=is_sqlite)


def ensure_drop_meal_timing(engine: Engine) -> None:
    """Remove meal timing column — users schedule workout times outside the app."""
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    schema_file = schema_dir / "029_drop_meal_timing.sql"

    with engine.begin() as conn:
        for table in ("user_daily_plan_meals", "meal_plan_items"):
            if not _table_exists(conn, table, sqlite=is_sqlite):
                continue
            if not _has_column(conn, table, "timing", sqlite=is_sqlite):
                continue
            if schema_file.is_file():
                _apply_schema_file(conn, schema_file)
                return
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN timing"))


def ensure_deactivate_plate_equipment(engine: Engine) -> None:
    """Deactivate plate (bánh tạ) equipment and all exercises linked to it."""
    is_sqlite = engine.dialect.name == "sqlite"
    inactive = "0" if is_sqlite else "FALSE"
    with engine.begin() as conn:
        if not _table_exists(conn, "equipment", sqlite=is_sqlite):
            return
        conn.execute(text(f"UPDATE equipment SET is_active = {inactive} WHERE slug = 'plate'"))
        if not (
            _table_exists(conn, "exercise_equipment", sqlite=is_sqlite)
            and _table_exists(conn, "exercises", sqlite=is_sqlite)
        ):
            return
        conn.execute(
            text(
                f"""
                UPDATE exercises SET is_active = {inactive}
                WHERE id IN (
                  SELECT ee.exercise_id
                  FROM exercise_equipment ee
                  JOIN equipment eq ON eq.id = ee.equipment_id
                  WHERE eq.slug = 'plate'
                )
                """
            )
        )


def ensure_home_equipment_catalog_v2(engine: Engine) -> None:
    """Reactivate parallel-bars and upsert gymnastic-rings for the public home catalog."""
    is_sqlite = engine.dialect.name == "sqlite"
    active = "1" if is_sqlite else "TRUE"
    with engine.begin() as conn:
        if not _table_exists(conn, "equipment", sqlite=is_sqlite):
            return
        conn.execute(
            text(f"UPDATE equipment SET is_active = {active} WHERE slug = 'parallel-bars'")
        )
        exists = conn.execute(
            text("SELECT 1 FROM equipment WHERE slug = :slug LIMIT 1"),
            {"slug": "gymnastic-rings"},
        ).fetchone()
        if exists:
            conn.execute(
                text(
                    f"""
                    UPDATE equipment
                    SET name_vi = :name_vi,
                        name_en = :name_en,
                        category = :category,
                        is_active = {active},
                        image_url = :image_url
                    WHERE slug = :slug
                    """
                ),
                {
                    "slug": "gymnastic-rings",
                    "name_vi": "Vòng treo",
                    "name_en": "Gymnastic Rings",
                    "category": "Body Weight",
                    "image_url": "equipment/gymnastic-rings/vongtreo.jpg?v=202609121745",
                },
            )
        else:
            conn.execute(
                text(
                    f"""
                    INSERT INTO equipment
                        (slug, name_vi, name_en, category, is_active, sort_order, image_url)
                    VALUES
                        (:slug, :name_vi, :name_en, :category, {active}, :sort_order, :image_url)
                    """
                ),
                {
                    "slug": "gymnastic-rings",
                    "name_vi": "Vòng treo",
                    "name_en": "Gymnastic Rings",
                    "category": "Body Weight",
                    "sort_order": 35,
                    "image_url": "equipment/gymnastic-rings/vongtreo.jpg?v=202609121745",
                },
            )

        if _table_exists(conn, "shop_products", sqlite=is_sqlite):
            shop_exists = conn.execute(
                text("SELECT 1 FROM shop_products WHERE slug = :slug LIMIT 1"),
                {"slug": "gymnastic-rings"},
            ).fetchone()
            shop_payload = {
                "slug": "gymnastic-rings",
                "name_vi": "Vòng treo",
                "description_vi": "Gymnastic rings / vòng treo — dip, row, muscle-up tại nhà.",
                "image_url": "equipment/gymnastic-rings/vongtreo.jpg?v=202609121745",
                "price_vnd": 0,
                "stock_qty": 0,
            }
            if shop_exists:
                conn.execute(
                    text(
                        f"""
                        UPDATE shop_products
                        SET name_vi = :name_vi,
                            description_vi = :description_vi,
                            image_url = :image_url,
                            is_active = {active},
                            updated_at = CURRENT_TIMESTAMP
                        WHERE slug = :slug
                        """
                    ),
                    shop_payload,
                )
            else:
                conn.execute(
                    text(
                        f"""
                        INSERT INTO shop_products
                            (slug, name_vi, description_vi, price_vnd, stock_qty,
                             image_url, is_active, created_at, updated_at)
                        VALUES
                            (:slug, :name_vi, :description_vi, :price_vnd, :stock_qty,
                             :image_url, {active}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """
                    ),
                    shop_payload,
                )


def ensure_gymnastic_rings_exercises(engine: Engine) -> None:
    """Upsert ring exercises (no video yet) and link to gymnastic-rings equipment."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        from app.services.gymnastic_rings_exercise_seed import seed_gymnastic_rings_exercises

        seed_gymnastic_rings_exercises(conn, is_sqlite=is_sqlite)


def ensure_resistance_band_2_exercises(engine: Engine) -> None:
    """Upsert tube-band (resistance-band-2) exercises such as band front raise."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        from app.services.gymnastic_rings_exercise_seed import seed_resistance_band_2_exercises

        seed_resistance_band_2_exercises(conn, is_sqlite=is_sqlite)


def ensure_familiarization_exercises(engine: Engine) -> None:
    """Deactivate legacy seed:familiarization:* rows; gen uses the live catalog."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        from app.services.familiarization_exercise_seed import (
            deactivate_familiarization_exercises,
        )

        deactivate_familiarization_exercises(conn, is_sqlite=is_sqlite)


def ensure_exercise_copy_vi(engine: Engine) -> None:
    """Overlay beginner-friendly Vietnamese how-to copy onto catalog rows."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        from app.services.exercise_copy_seed import seed_exercise_copy

        seed_exercise_copy(conn, is_sqlite=is_sqlite)


def ensure_product_redeem_codes(engine: Engine) -> None:
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    with engine.begin() as conn:
        if not (
            _table_exists(conn, "product_redeem_codes", sqlite=is_sqlite)
            and _table_exists(conn, "product_redeem_batches", sqlite=is_sqlite)
        ):
            _apply_schema_file(conn, schema_dir / "030_product_redeem_codes.sql")

        reservation_columns = (
            ("reservation_token", "TEXT", "VARCHAR(64)"),
            ("reserved_at", "TEXT", "TIMESTAMPTZ"),
        )
        for column, sqlite_type, postgres_type in reservation_columns:
            if _has_column(conn, "product_redeem_codes", column, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(
                    text(f"ALTER TABLE product_redeem_codes ADD COLUMN {column} {sqlite_type}")
                )
            else:
                conn.execute(
                    text(
                        "ALTER TABLE product_redeem_codes "
                        f"ADD COLUMN IF NOT EXISTS {column} {postgres_type}"
                    )
                )


def ensure_food_region_metadata(engine: Engine) -> None:
    """region_slug + description_vi for traditional-dish map on /thuc-an."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        cols = (
            ("region_slug", "TEXT"),
            ("province_id", "TEXT"),
            ("description_vi", "TEXT"),
        )
        for col, typ in cols:
            if _has_column(conn, "foods", col, sqlite=is_sqlite):
                continue
            if is_sqlite:
                conn.execute(text(f"ALTER TABLE foods ADD COLUMN {col} {typ}"))
            else:
                conn.execute(text(f"ALTER TABLE foods ADD COLUMN IF NOT EXISTS {col} {typ}"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_foods_region_slug ON foods(region_slug)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_foods_province_id ON foods(province_id)"))


def ensure_traditional_dish_seeds(engine: Engine) -> None:
    """Upsert traditional dishes from seed file (optional; catalog Excel is primary).

    Empty seed is intentional after Excel catalog import — dishes live in
    foods_catalog_v2 under category mon-an-truyen-thong.
    """
    from datetime import UTC, datetime

    from sqlalchemy.orm import Session

    from app.models.entities import Food, FoodCategory

    seed_path = PROJECT_ROOT / "seeds" / "foods_traditional_dishes.json"
    if not seed_path.is_file():
        return

    import json

    dishes = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(dishes, list) or not dishes:
        # Catalog is owned by Excel import; do not recreate legacy mon-an rows.
        return

    with Session(engine) as db:
        cat = (
            db.query(FoodCategory)
            .filter(FoodCategory.slug.in_(["mon-an-truyen-thong", "mon-an"]))
            .order_by(FoodCategory.sort_order.asc())
            .first()
        )
        if not cat:
            cat = FoodCategory(
                slug="mon-an-truyen-thong",
                name_vi="Món truyền thống",
                sort_order=5,
            )
            db.add(cat)
            db.flush()

        now = datetime.now(UTC)
        for item in dishes:
            slug = str(item.get("slug") or "").strip()
            if not slug:
                continue
            row = db.query(Food).filter(Food.slug == slug).first()
            serving_grams = float(item.get("serving_grams") or 400)
            calories = float(item.get("calories") or 0)
            protein_g = float(item.get("protein_g") or 0)
            carbs_g = float(item.get("carbs_g") or 0)
            fat_g = float(item.get("fat_g") or 0)
            scale = 100.0 / serving_grams if serving_grams else 0.25
            fields = {
                "name_vi": str(item.get("name_vi") or slug),
                "name_en": item.get("name_en"),
                "category_id": cat.id,
                "serving_size": str(item.get("serving_size") or "1 phần"),
                "serving_grams": serving_grams,
                "calories": calories,
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
                "fiber_g": item.get("fiber_g"),
                "is_verified": bool(item.get("is_verified", False)),
                "is_common": bool(item.get("is_common", True)),
                "tags": item.get("tags") or ["viet-nam", "complete_meal"],
                "vitamins_json": {},
                "food_kind": "dish",
                "prep_state": None,
                "status": "active",
                "kcal_100g": round(calories * scale, 2),
                "protein_100g": round(protein_g * scale, 2),
                "carbs_100g": round(carbs_g * scale, 2),
                "fat_100g": round(fat_g * scale, 2),
                "source_ref": item.get("source_ref") or "traditional-mvp",
                "confidence": "estimated",
                "macro_roles": item.get("macro_roles") or ["carb", "protein"],
                "meal_slots": item.get("meal_slots") or ["lunch", "dinner"],
                "ai_eligible": True,
                "ai_priority": int(item.get("ai_priority") or 20),
                "is_complete_meal": True,
                "default_for_ai": False,
                "region_slug": item.get("region_slug"),
                "province_id": item.get("province_id"),
                "description_vi": item.get("description_vi"),
            }
            seed_image = item.get("image_url")
            if seed_image:
                fields["image_url"] = seed_image
            if row is None:
                db.add(Food(slug=slug, created_at=now, **fields))
            else:
                for key, value in fields.items():
                    setattr(row, key, value)
        db.commit()


def ensure_food_catalog_images(engine: Engine) -> None:
    """Set foods.image_url from seeds/food_images.json when the media file exists."""
    import json

    mapping_path = PROJECT_ROOT / "seeds" / "food_images.json"
    if not mapping_path.is_file():
        return
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict) or not mapping:
        return

    media_root = PROJECT_ROOT / "uploads" / "media"
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if not _foods_table_exists(conn, sqlite=is_sqlite):
            return
        if not _has_column(conn, "foods", "image_url", sqlite=is_sqlite):
            return
        for slug, rel in mapping.items():
            if not isinstance(slug, str) or not isinstance(rel, str):
                continue
            rel_norm = rel.replace("\\", "/").lstrip("/")
            dest = media_root / rel_norm
            if not dest.is_file():
                continue
            conn.execute(
                text("UPDATE foods SET image_url = :url WHERE slug = :slug"),
                {"url": rel_norm, "slug": slug},
            )


# Pantry slugs that duplicate live TapTot ingredients (longer catalog slugs).
DEPRECATED_FOOD_MERGES = {
    "toi": "toi-ta-toi-tia",
    "toi-tay": "toi-tay-poireau",
    "hanh-tim": "hanh-tim-kho",
    "gung": "gung-gia",
    "rieng": "cu-rieng",
    "nghe": "nghe-vang",
    "can-tay": "can-tay-da-lat",
    "hen": "hen-song-trung-truc",
    "luon": "luon-dong",
    "ca-linh": "ca-linh-mua-nuoc-noi",
    "chan-gio-heo": "bap-gio-heo-chan-gio-truoc",
    "canh-ga": "canh-ga-nguyen-chiec-canh-tien",
    "bac-ha-rau": "doc-mung-bac-ha",
    "ngo-gai": "mui-tau-ngo-gai",
    "gau-bo": "gau-gion-bo-gau-pho",
    "gio-bo": "gan-bo-gan-chu-y-gan-trong",
    "ca-chua": "ca-chua-thuong",
    "thit-lon-than-nac-song": "than-noi-heo-than-chuot",
    "thit-lon-nac-vai-song": "nac-vai-heo-nac-vai-dau-gion",
    "thit-nac-dam-heo": "nac-dam-lon-nac-dam-co",
    "gia-do": "gia-do-xanh",
    "dua-leo": "dua-chuot-ta-dua-leo",
    "ngo-ri": "rau-mui-ngo-ri",
    "dua-thom": "dua-thom-khom",
    "ca-rot-song": "ca-rot",
    "hanh-tay": "hanh-tay-trang-vang",
    "kho-qua-muop-dang": "muop-dang-kho-qua",
    "mong-toi": "rau-mong-toi",
    "dau-bap-luoc": "dau-bap",
    "tom-su-song": "tom-su-bien-nuoi",
    "tom-the-song": "tom-the-chan-trang",
    "muc-ong-song": "muc-ong",
    "cua-bien-thit": "cua-bien-ca-mau-thit",
    "ghe-thit": "ghe-xanh-phan-thiet",
    "ngao-ngheu": "ngao-trang-ngheu",
    "ca-chep-song": "ca-chep",
    "ca-dieu-hong-song": "ca-dieu-hong",
    "ca-thu-song": "ca-thu-thu-phan",
    "ca-basa-ca-tra-fillet-song": "ca-tra-basa-phi-le",
    "thit-bo-than-song": "than-noi-bo-tenderloin-than-chuot",
    "thit-bo-bap-song": "bap-bo-thong-thuong-bap-chan",
    "thit-bo-nam-song": "nam-bo-thit-ba-chi-bo",
}
DEPRECATED_FOOD_SLUGS = (
    "ca-ro-dong",
    "ca-keo",
    "ca-liet",
    "ba-chi-rut-suon-ba-roi-rut-suon",
    *DEPRECATED_FOOD_MERGES,
)
DEPRECATED_FOOD_CATEGORY_SLUGS = ("an-vat-do-uong",)


def ensure_deprecated_foods(engine: Engine) -> None:
    """Hide foods that should not appear in /thuc-an or AI meals."""
    is_sqlite = engine.dialect.name == "sqlite"
    ai_off = "0" if is_sqlite else "FALSE"
    with engine.begin() as conn:
        if not _foods_table_exists(conn, sqlite=is_sqlite):
            return
        if not _has_column(conn, "foods", "status", sqlite=is_sqlite):
            return
        ai_sql = ""
        if _has_column(conn, "foods", "ai_eligible", sqlite=is_sqlite):
            ai_sql = f", ai_eligible = {ai_off}"
        for slug in DEPRECATED_FOOD_SLUGS:
            conn.execute(
                text(f"UPDATE foods SET status = 'deprecated'{ai_sql} WHERE slug = :slug"),
                {"slug": slug},
            )
        if _has_column(conn, "foods", "merged_into_id", sqlite=is_sqlite):
            for src, dest in DEPRECATED_FOOD_MERGES.items():
                dest_id = conn.execute(
                    text("SELECT id FROM foods WHERE slug = :slug"),
                    {"slug": dest},
                ).scalar()
                if dest_id is None:
                    continue
                conn.execute(
                    text(
                        f"UPDATE foods SET status = 'deprecated'{ai_sql}, merged_into_id = :dest_id "
                        "WHERE slug = :src"
                    ),
                    {"dest_id": dest_id, "src": src},
                )
        if not _table_exists(conn, "food_categories", sqlite=is_sqlite):
            return
        for cat_slug in DEPRECATED_FOOD_CATEGORY_SLUGS:
            conn.execute(
                text(
                    f"""
                    UPDATE foods SET status = 'deprecated'{ai_sql}
                    WHERE category_id IN (
                      SELECT id FROM food_categories WHERE slug = :slug
                    )
                    """
                ),
                {"slug": cat_slug},
            )


def ensure_grain_nut_foods(engine: Engine) -> None:
    """Upsert ngũ cốc / hạt staples and their catalog photos."""
    import json
    from datetime import UTC, datetime

    from sqlalchemy.orm import Session

    from app.models.entities import Food, FoodAlias, FoodCategory, FoodPortion

    seed_path = PROJECT_ROOT / "seeds" / "grain_nut_foods.json"
    if not seed_path.is_file():
        return
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    cat_meta = payload.get("category") or {}
    foods = payload.get("foods") or []
    if not cat_meta.get("slug") or not isinstance(foods, list):
        return

    media_root = PROJECT_ROOT / "uploads" / "media"
    now = datetime.now(UTC)
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as conn:
        if not _foods_table_exists(conn, sqlite=is_sqlite):
            return
        if not _table_exists(conn, "food_categories", sqlite=is_sqlite):
            return
    with Session(engine) as db:
        for slug, order in (("mon-an-truyen-thong", 6), ("an-vat-do-uong", 7)):
            row = db.query(FoodCategory).filter(FoodCategory.slug == slug).first()
            if row:
                row.sort_order = order
        cat_slug = str(cat_meta["slug"])
        cat = db.query(FoodCategory).filter(FoodCategory.slug == cat_slug).first()
        if cat is None:
            cat = FoodCategory(
                slug=cat_slug,
                name_vi=str(cat_meta.get("name_vi") or "Ngũ cốc - Hạt"),
                sort_order=int(cat_meta.get("sort_order") or 5),
            )
            db.add(cat)
            db.flush()
        else:
            cat.name_vi = str(cat_meta.get("name_vi") or cat.name_vi)
            cat.sort_order = int(cat_meta.get("sort_order") or cat.sort_order)

        for item in foods:
            slug = str(item.get("slug") or "").strip()
            if not slug:
                continue
            serving_grams = float(item.get("serving_grams") or 100)
            kcal_100 = float(item["kcal_100g"])
            protein_100 = float(item["protein_100g"])
            carbs_100 = float(item["carbs_100g"])
            fat_100 = float(item["fat_100g"])
            fiber_100 = item.get("fiber_100g")
            sodium_100 = item.get("sodium_100mg")
            scale = serving_grams / 100.0
            cover = f"foods/{slug}.jpg"
            if not (media_root / cover).is_file():
                cover = None
            fields = {
                "name_vi": str(item["name_vi"]),
                "name_en": item.get("name_en"),
                "category_id": cat.id,
                "serving_size": str(item.get("serving_size") or "100g"),
                "serving_grams": serving_grams,
                "calories": round(kcal_100 * scale, 2),
                "protein_g": round(protein_100 * scale, 2),
                "carbs_g": round(carbs_100 * scale, 2),
                "fat_g": round(fat_100 * scale, 2),
                "fiber_g": None if fiber_100 is None else round(float(fiber_100) * scale, 2),
                "sodium_mg": None if sodium_100 is None else round(float(sodium_100) * scale, 2),
                "is_verified": True,
                "is_common": True,
                "tags": item.get("tags") or [],
                "food_kind": "ingredient",
                "prep_state": item.get("prep_state") or "raw",
                "status": "active",
                "kcal_100g": kcal_100,
                "protein_100g": protein_100,
                "carbs_100g": carbs_100,
                "fat_100g": fat_100,
                "fiber_100g": None if fiber_100 is None else float(fiber_100),
                "sodium_100mg": None if sodium_100 is None else float(sodium_100),
                "source_ref": item.get("source_ref") or "usda",
                "confidence": "reference",
                "macro_roles": item.get("macro_roles") or ["carb"],
                "meal_slots": item.get("meal_slots") or ["breakfast", "lunch", "dinner"],
                "ai_eligible": True,
                "ai_priority": int(item.get("ai_priority") or 0),
                "is_complete_meal": False,
                "default_for_ai": bool(item.get("default_for_ai", False)),
            }
            if cover:
                fields["image_url"] = cover
            row = db.query(Food).filter(Food.slug == slug).first()
            if row is None:
                db.add(Food(slug=slug, created_at=now, vitamins_json={}, **fields))
                db.flush()
                row = db.query(Food).filter(Food.slug == slug).first()
            else:
                for key, value in fields.items():
                    setattr(row, key, value)
            if row is None:
                continue
            db.query(FoodPortion).filter(FoodPortion.food_id == row.id).delete()
            for i, portion in enumerate(item.get("portions") or []):
                db.add(
                    FoodPortion(
                        food_id=row.id,
                        label_vi=str(portion["label_vi"]),
                        grams=float(portion["grams"]),
                        is_default=bool(portion.get("is_default")),
                        sort_order=int(portion.get("sort_order") or i),
                    )
                )
            db.query(FoodAlias).filter(FoodAlias.food_id == row.id).delete()
            for alias in item.get("aliases") or []:
                text_alias = str(alias).strip()
                if text_alias:
                    db.add(FoodAlias(food_id=row.id, alias=text_alias))
        db.commit()


def ensure_cooking_pantry_foods(engine: Engine) -> None:
    """Upsert Vietnamese cooking pantry ingredients used by recipe posts."""
    import json
    from datetime import UTC, datetime

    from sqlalchemy.orm import Session

    from app.models.entities import Food, FoodAlias, FoodCategory, FoodPortion

    seed_path = PROJECT_ROOT / "seeds" / "foods_cooking_pantry.json"
    if not seed_path.is_file():
        return
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    foods = payload.get("foods") or []
    categories_meta = payload.get("categories") or []
    if not isinstance(foods, list) or not foods:
        return

    media_root = PROJECT_ROOT / "uploads" / "media"
    now = datetime.now(UTC)
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as conn:
        if not _foods_table_exists(conn, sqlite=is_sqlite):
            return
        if not _table_exists(conn, "food_categories", sqlite=is_sqlite):
            return
    with Session(engine) as db:
        cat_ids: dict[str, int] = {}
        for meta in categories_meta:
            slug = str((meta or {}).get("slug") or "").strip()
            if not slug:
                continue
            cat = db.query(FoodCategory).filter(FoodCategory.slug == slug).first()
            if cat is None:
                cat = FoodCategory(
                    slug=slug,
                    name_vi=str(meta.get("name_vi") or slug),
                    sort_order=int(meta.get("sort_order") or 20),
                )
                db.add(cat)
                db.flush()
            else:
                if meta.get("name_vi"):
                    cat.name_vi = str(meta["name_vi"])
                if meta.get("sort_order") is not None:
                    cat.sort_order = int(meta["sort_order"])
            cat_ids[slug] = cat.id
        for slug in (
            "rau-cu-qua",
            "thit-gia-cam-noi-tang",
            "ca-thuy-hai-san",
            "ngu-coc-hat",
            "gia-vi-mam-dau",
        ):
            if slug in cat_ids:
                continue
            row = db.query(FoodCategory).filter(FoodCategory.slug == slug).first()
            if row:
                cat_ids[slug] = row.id

        for item in foods:
            slug = str(item.get("slug") or "").strip()
            if not slug:
                continue
            serving_grams = float(item.get("serving_grams") or 100)
            kcal_100 = float(item["kcal_100g"])
            protein_100 = float(item["protein_100g"])
            carbs_100 = float(item["carbs_100g"])
            fat_100 = float(item["fat_100g"])
            fiber_100 = item.get("fiber_100g")
            sodium_100 = item.get("sodium_100mg")
            scale = serving_grams / 100.0
            cover = (item.get("image_url") or "").strip().replace("\\", "/").lstrip("/") or f"foods/{slug}.jpg"
            if not (media_root / cover).is_file():
                cover = None
            cat_slug = str(item.get("category_slug") or "gia-vi-mam-dau")
            fields = {
                "name_vi": str(item["name_vi"]),
                "name_en": item.get("name_en"),
                "category_id": cat_ids.get(cat_slug),
                "serving_size": str(item.get("serving_size") or "100g"),
                "serving_grams": serving_grams,
                "calories": round(kcal_100 * scale, 2),
                "protein_g": round(protein_100 * scale, 2),
                "carbs_g": round(carbs_100 * scale, 2),
                "fat_g": round(fat_100 * scale, 2),
                "fiber_g": None if fiber_100 is None else round(float(fiber_100) * scale, 2),
                "sodium_mg": None if sodium_100 is None else round(float(sodium_100) * scale, 2),
                "is_verified": True,
                "is_common": True,
                "tags": item.get("tags") or ["gia-vi"],
                "food_kind": "ingredient",
                "prep_state": item.get("prep_state") or "raw",
                "status": "active",
                "kcal_100g": kcal_100,
                "protein_100g": protein_100,
                "carbs_100g": carbs_100,
                "fat_100g": fat_100,
                "fiber_100g": None if fiber_100 is None else float(fiber_100),
                "sodium_100mg": None if sodium_100 is None else float(sodium_100),
                "source_ref": item.get("source_ref") or "usda-vn-table",
                "confidence": str(item.get("confidence") or "estimated"),
                "macro_roles": item.get("macro_roles") or ["produce"],
                "meal_slots": item.get("meal_slots") or ["lunch", "dinner"],
                "ai_eligible": bool(item.get("ai_eligible", True)),
                "ai_priority": int(item.get("ai_priority") or 0),
                "is_complete_meal": False,
                "default_for_ai": bool(item.get("default_for_ai", False)),
            }
            if cover:
                fields["image_url"] = cover
            row = db.query(Food).filter(Food.slug == slug).first()
            if row is None:
                db.add(Food(slug=slug, created_at=now, vitamins_json={}, **fields))
                db.flush()
                row = db.query(Food).filter(Food.slug == slug).first()
            else:
                for key, value in fields.items():
                    setattr(row, key, value)
            if row is None:
                continue
            db.query(FoodPortion).filter(FoodPortion.food_id == row.id).delete()
            portions = item.get("portions") or [
                {"label_vi": "100g", "grams": 100, "is_default": True, "sort_order": 0}
            ]
            for i, portion in enumerate(portions):
                db.add(
                    FoodPortion(
                        food_id=row.id,
                        label_vi=str(portion["label_vi"]),
                        grams=float(portion["grams"]),
                        is_default=bool(portion.get("is_default")),
                        sort_order=int(portion.get("sort_order") or i),
                    )
                )
            db.query(FoodAlias).filter(FoodAlias.food_id == row.id).delete()
            for alias in item.get("aliases") or []:
                text_alias = str(alias).strip()
                if text_alias:
                    db.add(FoodAlias(food_id=row.id, alias=text_alias))
        db.commit()


def ensure_pushup_challenge_entries(engine: Engine) -> None:
    """Ranking table retired; drop leftover rows if the table still exists."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as conn:
        if not _table_exists(conn, "pushup_challenge_entries", sqlite=is_sqlite):
            return
        conn.execute(text("DROP TABLE IF EXISTS pushup_challenge_entries"))


def ensure_pushup_challenge_sessions(engine: Engine) -> None:
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    schema_dir = PROJECT_ROOT / "schema" / ("sqlite" if is_sqlite else "postgresql")
    with engine.begin() as conn:
        if _table_exists(conn, "pushup_challenge_sessions", sqlite=is_sqlite):
            return
        _apply_schema_file(conn, schema_dir / "033_pushup_challenge_sessions.sql")


def ensure_user_roles_normalized(engine: Engine) -> None:
    """Account roles are only user|admin. Former trainer accounts become users."""
    with engine.begin() as conn:
        if not _table_exists(conn, "users", sqlite=engine.dialect.name == "sqlite"):
            return
        conn.execute(text("UPDATE users SET role = 'user' WHERE role = 'trainer'"))

