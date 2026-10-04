"""Expand homemade chả lụa / pate BOMs and fill missing cook steps."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COOKING = ROOT / "seeds" / "cooking_posts"


def add_or_bump(ings: list[dict], slug: str, grams: float, label: str, note: str | None = None) -> None:
    for item in ings:
        if item.get("food_slug") == slug:
            item["grams"] = round(float(item.get("grams") or 0) + grams, 1)
            return
    row: dict = {"food_slug": slug, "grams": grams, "amount_label": label}
    if note:
        row["note"] = note
    ings.append(row)


def drop_slug(ings: list[dict], slug: str) -> float:
    kept = []
    grams = 0.0
    for item in ings:
        if item.get("food_slug") == slug:
            grams += float(item.get("grams") or 0)
            continue
        kept.append(item)
    ings[:] = kept
    return grams


def expand_cha_lua(ings: list[dict]) -> None:
    grams = drop_slug(ings, "cha-lua")
    if grams <= 0:
        return
    starch = max(4.0, round(grams * 0.05, 1))
    mam = max(3.0, round(grams * 0.04, 1))
    add_or_bump(ings, "thit-lon-xay-song", grams, f"{grams:g}g thịt xay làm chả lụa", "quết, gói, luộc thành chả")
    add_or_bump(ings, "bot-nang", starch, f"{starch:g}g bột năng", "chả lụa")
    add_or_bump(ings, "nuoc-mam", mam, f"{mam:g}g nước mắm", "nêm chả lụa")


def expand_pate(ings: list[dict]) -> None:
    grams = drop_slug(ings, "pate-gan")
    if grams <= 0:
        return
    liver = round(grams * 0.85, 1)
    fat = round(grams - liver, 1) or 5.0
    add_or_bump(ings, "gan-heo", liver, f"{liver:g}g gan heo", "xay hấp pate")
    add_or_bump(ings, "thit-lon-ba-chi-song", fat, f"{fat:g}g ba chỉ", "mỡ xay pate")


COM_TAM_SO_CHE = (
    "1. Sườn rạch nhẹ, ướp tỏi, nước mắm, đường, tiêu 30 phút.\n"
    "2. Bì: luộc da heo 20 phút cho mềm, cạo sạch, thái sợi chỉ. "
    "Rang 1 thìa gạo (lấy từ phần nấu cơm) đến vàng, giã thính. "
    "Trộn bì với thính, tỏi băm, 1 thìa nước mắm, tiêu. Để 10 phút.\n"
    "3. Chả trứng: đánh trứng với thịt xay, 1 thìa nước mắm, tiêu, chút hành. Đổ khuôn chống dính.\n"
    "4. Pha nước mắm chua ngọt: 2 nước mắm + 1–2 đường + 2 nước + tỏi ớt (chanh/tắc).\n"
    "5. Vo gạo tấm, nấu khô hơn cơm thường một chút."
)
COM_TAM_NAU = (
    "1. Hấp chả trứng 20–25 phút đến đặc chín, để nguội, thái miếng. Khi dọn hấp lại 5 phút cho nóng.\n"
    "2. Nướng sườn than hoặc lò 200°C, 12 phút/mặt đến cạnh hơi cháy.\n"
    "3. Xới cơm tấm tơi ra đĩa.\n"
    "4. Xếp sườn, bì, chả, dưa leo.\n"
    "5. Chan nước mắm, hành mỡ nếu có."
)

CHA_SO = (
    "Chả lụa: thịt xay để lạnh, trộn bột năng, nước mắm, tiêu, 1 thìa nước đá. "
    "Quết 5–8 phút đến dai, dính tay. Gói kín túi chịu nhiệt hoặc lá chuối."
)
CHA_NAU = (
    "Chả lụa: luộc gói chả 25 phút (lô nhỏ 60–120g), ngâm nước lạnh, thái lát. "
    "Có thể rắc bột quế lên lát nếu làm chả quế."
)
PATE_SO = (
    "Pate: gan heo ngâm nước lạnh 15 phút, chần gừng 3 phút, để ráo. "
    "Phi ba chỉ lấy mỡ, xay nhuyễn gan với mỡ, nêm mắm, tiêu, hành."
)
PATE_NAU = (
    "Pate: đổ khuôn, hấp 20 phút lửa vừa, để nguội hẳn rồi phết. Nóng sẽ lỏng, khó kẹp."
)


def swap_section(md: str, heading: str, new_body: str) -> str:
    marker = f"## {heading}\n"
    start = md.find(marker)
    if start < 0:
        return md
    start_body = start + len(marker)
    nxt = md.find("\n## ", start_body)
    if nxt < 0:
        return md[:start] + marker + new_body + "\n"
    return md[:start] + marker + new_body + md[nxt:]


def insert_after_first_so_che(md: str, extra: str) -> str:
    marker = "## Sơ chế\n"
    i = md.find(marker)
    if i < 0:
        return md
    j = md.find("\n## ", i + len(marker))
    block = md[i + len(marker) : j]
    if extra[:40] in block:
        return md
    block = block.rstrip() + "\n" + extra + "\n"
    return md[: i + len(marker)] + block + md[j:]


def insert_after_first_nau(md: str, extra: str) -> str:
    marker = "## Cách nấu\n"
    i = md.find(marker)
    if i < 0:
        return md
    j = md.find("\n## ", i + len(marker))
    block = md[i + len(marker) : j]
    if extra[:40] in block:
        return md
    # prepend so homemade parts cook before plating
    block = extra + "\n" + block.lstrip()
    return md[: i + len(marker)] + block + md[j:]


UPDATES: dict[str, dict] = {
    "com-tam-suon-bi-cha-day-du": {"so_che": COM_TAM_SO_CHE, "nau": COM_TAM_NAU, "cha": False, "pate": False},
    "com-tam-sai-gon": {"so_che": COM_TAM_SO_CHE, "nau": COM_TAM_NAU, "cha": False, "pate": False},
    "bun-bo-hue-day-du": {"cha": True, "pate": False},
    "bun-dau-mam-tom": {"cha": True, "pate": False},
    "bun-thang-ha-noi": {"cha": True, "pate": False},
    "banh-mi-kep-thit-cha-pate": {"cha": True, "pate": True},
    "banh-mi-op-la-2-trung": {"cha": False, "pate": True},
    "banh-cuon-nong-kem-cha-que": {"cha": True, "pate": False},
}


def main() -> None:
    changed = 0
    for path in sorted(COOKING.glob("*.json")):
        posts = json.loads(path.read_text(encoding="utf-8"))
        dirty = False
        for post in posts:
            slug = post.get("slug")
            spec = UPDATES.get(slug)
            if not spec:
                continue
            ings = post.get("ingredients") or []
            if spec.get("cha"):
                expand_cha_lua(ings)
            if spec.get("pate"):
                expand_pate(ings)
            post["ingredients"] = ings
            md = post.get("content_md") or ""
            if spec.get("so_che"):
                md = swap_section(md, "Sơ chế", spec["so_che"])
            if spec.get("nau"):
                md = swap_section(md, "Cách nấu", spec["nau"])
            if spec.get("cha"):
                md = insert_after_first_so_che(md, CHA_SO)
                md = insert_after_first_nau(md, CHA_NAU)
            if spec.get("pate"):
                md = insert_after_first_so_che(md, PATE_SO)
                md = insert_after_first_nau(md, PATE_NAU)
            post["content_md"] = md
            dirty = True
            changed += 1
            print("updated", slug)
        if dirty:
            path.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("posts", changed)


if __name__ == "__main__":
    main()
