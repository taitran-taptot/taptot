# -*- coding: utf-8 -*-
"""Generate image prompts for each food item in the nutrition Excel database."""
import openpyxl
from pathlib import Path

ROOT = Path(r"C:\Users\Tran Tai\Projects\vietfit-db")
EXCEL = Path(
    r"c:\Users\Tran Tai\Downloads\CSDL_Dinh_Duong_Toan_Dien_Thuc_Pham_Viet_Nam (3).xlsx"
)
SHEETS = [
    "1_Rau_Cu_Qua",
    "2_Thit_GiaSuc_GiaCam_NoiTang",
    "3_Ca_ThuyHaiSan",
    "6_Trung_Sua_Whey",
    "4_Mon_An_Truyen_Thong",
    "5_An_Vat_Banh_Keo_DoUong",
]

BASE = (
    "Professional realistic food product photography for a nutrition/fitness website. "
    "Format: WebP or JPEG, 1920x1080 pixels, 16:9 aspect ratio. "
    "Pure clean solid white background, minimal studio setup. "
    "Soft even natural studio lighting, sharp focus, true-to-life colors and textures. "
    "No people, no human hands, no plates, bowls, knives, cutting boards, or props. "
    "No text, labels, logos, watermarks, or nutrition info. "
    "Single unified composition (NOT a split-panel, NOT a collage, NOT two separate frames). "
    "Show TWO states of the SAME food standing very close together side by side in one shot, "
    "almost touching, visually similar size and scale, balanced and easy to recognize. "
    "CRITICAL depth order: Part 2 (prepared/edible state) must stand in the FRONT / foreground; "
    "Part 1 (original/whole state) must stand slightly BEHIND Part 2. "
    "Subject group centered, overall food content fills about 80% of the frame. "
    "Consistent catalog style across the food dataset — prioritize realism, clarity, "
    "and recognizability over artistic effects."
)


def load_foods() -> list[dict]:
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    out: list[dict] = []
    for name in SHEETS:
        ws = wb[name]
        for row in ws.iter_rows(min_row=4, values_only=True):
            stt, group, food = row[0], row[1], row[2]
            if food and stt is not None:
                out.append(
                    {
                        "sheet": name,
                        "group": str(group) if group else "",
                        "name": str(food).strip(),
                    }
                )
    return out


def is_fruit(group: str, name: str) -> bool:
    g = group.lower()
    if "quả" in g:
        return True
    fruit_kw = [
        "xoài", "chuối", "cam", "quýt", "bưởi", "ổi", "đu đủ", "dưa", "nho", "táo",
        "lê", "đào", "vải", "nhãn", "măng cụt", "sầu riêng", "mít", "chôm chôm",
        "mận", "hồng", "kiwi", "bơ", "thanh long", "dừa", "na ", "roi", "cóc",
        "me ", "tắc", "chanh", "quất", "sung", "vú sữa", "sapoche", "hồng xiêm",
        "lựu", "dâu", "cherry", "bòn bon", "chôm", "quả",
    ]
    nl = name.lower()
    return any(k in nl for k in fruit_kw)


def is_fish(group: str, name: str) -> bool:
    g = group.lower()
    n = name.lower()
    if "ba ba" in n:
        return False
    if n.startswith("cánh"):
        return False
    if "cá" in g and "nhuyễn" not in g and "tôm" not in g and "cua" not in g and "mực" not in g:
        return True
    # Word-boundary only: "cá lóc" yes, "cánh gà" no.
    if n.startswith("cá ") or n.startswith("cá/") or n.startswith("cá-"):
        return True
    if "chạch" in n:
        return True
    return False


def is_shrimp_crab(group: str, name: str) -> bool:
    g = group.lower()
    n = name.lower()
    if "tôm" in g or "giáp xác" in g or "cua" in g or "ghẹ" in g:
        return True
    return any(k in n for k in ["tôm", "cua", "ghẹ", "tép", "bọ biển", "tôm hùm"])


def is_mollusk(group: str, name: str) -> bool:
    g = group.lower()
    n = name.lower()
    if "nhuyễn" in g or "ốc" in g or "mực" in g or "bạch tuộc" in g:
        return True
    return any(
        k in n
        for k in ["ốc", "hến", "nghêu", "sò", "trai", "mực", "bạch tuộc", "tu hài", "hàu", "vẹm"]
    )


def is_meat(group: str, name: str) -> bool:
    g = group.lower()
    return any(k in g for k in ["thịt", "nội tạng", "lợn", "heo", "bò", "bê", "gà", "vịt", "dê"])


def is_veg(group: str, name: str) -> bool:
    g = group.lower()
    return any(k in g for k in ["rau", "củ"])


def is_egg(group: str, name: str) -> bool:
    g = group.lower()
    n = name.lower()
    # "Lòng non / lòng già" are pork intestines, not eggs.
    if any(k in n for k in ["lòng non", "lòng già", "phèo", "dồi trường"]):
        return False
    return "trứng" in g or "trứng" in n or "lòng trắng" in n or "lòng đỏ" in n


def is_whey(group: str, name: str) -> bool:
    return "whey" in group.lower() or "whey" in name.lower()


def is_dish(sheet: str) -> bool:
    return sheet in ("4_Mon_An_Truyen_Thong", "5_An_Vat_Banh_Keo_DoUong")


# Meat prompts must never say "prepared/edible" — image models treat that as cooked.
BASE_MEAT = (
    "Professional realistic food product photography for a nutrition/fitness website. "
    "Format: WebP or JPEG, 1920x1080 pixels, 16:9 aspect ratio. "
    "Pure clean solid white background, minimal studio setup. "
    "Soft even natural studio lighting, sharp focus, true-to-life colors and textures. "
    "No people, no human hands, no plates, bowls, knives, cutting boards, or props. "
    "No text, labels, logos, watermarks, or nutrition info. "
    "Single unified composition (NOT a split-panel, NOT a collage, NOT two separate frames). "
    "Show TWO pieces of the SAME RAW meat standing very close together side by side in one shot, "
    "almost touching, visually similar size and scale, balanced and easy to recognize. "
    "CRITICAL: BOTH pieces are 100% RAW uncooked fresh butcher meat — never cooked, never seared, "
    "never grilled, never roasted, never smoked, no browning, no grill marks, no golden crust, "
    "no caramelization, no steam, no sauce. Fresh wet-market / butcher-counter look only. "
    "CRITICAL depth order: Part 2 (cleaned/trimmed RAW piece) must stand in the FRONT / foreground; "
    "Part 1 (whole RAW cut as sold) must stand slightly BEHIND Part 2. "
    "Subject group centered, overall food content fills about 80% of the frame. "
    "Consistent catalog style across the food dataset — prioritize realism, clarity, "
    "and recognizability over artistic effects."
)


def meat_parts(name: str) -> tuple[str, str]:
    return (
        f"FRONT (Part 2 – cleaned RAW, must be in front): the same {name} after light butcher "
        "trimming/cleaning only — still 100% RAW and uncooked. Show true raw color (pink, red, or "
        "natural raw organ/cartilage/bone color), moist raw surface, and recognizable structure "
        "(muscle grain, fat layers, or organ texture). Keep natural anatomical shape. "
        "Do NOT cook, sear, brown, glaze, or show a cooked dish.",
        f"BACK (Part 1 – whole RAW as sold, slightly behind): a whole raw {name} as typically sold "
        "at a Vietnamese wet-market butcher counter, intact anatomical shape, fresh raw moist "
        "surface, 3/4 angle. Same fully RAW uncooked state as Part 2 — both pieces look like "
        "fresh raw meat from the same counter, not cooked food.",
    )


def part_desc(food: dict) -> tuple[str, str]:
    """Return (part2_front, part1_back) — Part 2 must be described first (foreground)."""
    name = food["name"]
    group = food["group"]
    sheet = food["sheet"]
    nlow = name.lower()

    if is_egg(group, name):
        if "lòng trắng" in nlow:
            return (
                "FRONT (Part 2 – prepared, must be in front): clear raw egg white separated in its natural "
                "form, no shell, showing the translucent edible white only.",
                "BACK (Part 1 – original, slightly behind): a whole raw chicken egg in its intact shell, "
                "natural shape.",
            )
        if "lòng đỏ" in nlow:
            return (
                "FRONT (Part 2 – prepared, must be in front): a whole intact raw egg yolk, no shell, "
                "showing the golden edible yolk clearly.",
                "BACK (Part 1 – original, slightly behind): a whole raw chicken egg in its intact shell, "
                "natural shape.",
            )
        if "lộn" in nlow:
            return (
                "FRONT (Part 2 – prepared, must be in front): the same egg opened to clearly show the "
                "edible contents inside, no utensils.",
                f"BACK (Part 1 – original, slightly behind): a whole intact fertilized duck egg ({name}) "
                "in its shell, natural shape.",
            )
        if "vịt" in nlow:
            animal = "duck"
        elif "cút" in nlow:
            animal = "quail"
        else:
            animal = "chicken"
        return (
            "FRONT (Part 2 – prepared, must be in front): the same egg cracked open showing yolk and white "
            "clearly, no utensils.",
            f"BACK (Part 1 – original, slightly behind): whole intact raw {animal} egg(s) in natural shell, "
            "uncracked.",
        )

    if is_whey(group, name):
        return (
            f"FRONT (Part 2 – prepared, must be in front): a neat mound of the same {name} powder showing "
            "powder texture and color, no branding, no scoop tool if possible.",
            f"BACK (Part 1 – original, slightly behind): a sealed brand-neutral tub/container of {name} "
            "protein powder as a clean product object (no readable logo/text), natural product shape.",
        )

    if "ba ba" in nlow:
        return (
            "FRONT (Part 2 – prepared, must be in front): clean prepared edible meat of the same animal "
            "only, no head/shell/organs dominating the frame.",
            f"BACK (Part 1 – original, slightly behind): whole fresh {name} / softshell turtle as a whole "
            "natural animal form appropriate for food photography, 3/4 angle.",
        )

    if is_meat(group, name):
        return meat_parts(name)

    if is_fish(group, name):
        return (
            "FRONT (Part 2 – prepared, must be in front): the same species as clean prepared fish fillets / "
            "edible flesh only — no head, no bones, no guts, flesh structure clearly visible.",
            f"BACK (Part 1 – original, slightly behind): one whole fresh {name}, intact whole fish showing "
            "natural body shape, 3/4 angle.",
        )

    if is_shrimp_crab(group, name):
        if any(k in nlow for k in ["cua", "ghẹ"]):
            return (
                "FRONT (Part 2 – prepared, must be in front): the same species with shell opened/removed as "
                "appropriate to clearly show the edible meat inside.",
                f"BACK (Part 1 – original, slightly behind): whole fresh {name}, intact whole crab with "
                "shell, natural shape, 3/4 angle.",
            )
        return (
            "FRONT (Part 2 – prepared, must be in front): the same species peeled to show clean edible "
            "shrimp meat (shell/head removed as appropriate).",
            f"BACK (Part 1 – original, slightly behind): whole fresh {name}, intact whole shrimp/prawn "
            "with shell, natural shape, 3/4 angle.",
        )

    if is_mollusk(group, name):
        if any(k in nlow for k in ["mực", "bạch tuộc"]):
            return (
                "FRONT (Part 2 – prepared, must be in front): the same species cleaned and prepared to "
                "clearly show the edible flesh (skinned/cleaned as typical), no organs.",
                f"BACK (Part 1 – original, slightly behind): whole fresh {name}, intact natural form, "
                "3/4 angle.",
            )
        return (
            "FRONT (Part 2 – prepared, must be in front): the same species with shell opened/removed to "
            "clearly show the edible meat.",
            f"BACK (Part 1 – original, slightly behind): whole fresh {name} in natural shell, intact, "
            "3/4 angle.",
        )

    if is_fruit(group, name):
        if "cơm dừa" in nlow or nlow.startswith("cơm "):
            return (
                f"FRONT (Part 2 – prepared, must be in front): {name} clearly showing edible white coconut "
                "flesh / interior structure.",
                f"BACK (Part 1 – original, slightly behind): a whole intact mature coconut (for {name}), "
                "natural outer form.",
            )
        return (
            "FRONT (Part 2 – prepared, must be in front): the same fruit cut in half to clearly show flesh, "
            "seeds, and interior structure.",
            f"BACK (Part 1 – original, slightly behind): whole intact fresh {name}, uncut, natural fruit "
            "shape, 3/4 angle.",
        )

    if is_veg(group, name):
        rootish = any(
            k in nlow
            for k in [
                "khoai", "củ", "cà rốt", "củ cải", "su hào", "củ dền", "củ sen", "củ đậu",
                "gừng", "nghệ", "sả", "tỏi", "hành", "cà chua", "cà tím", "ớt", "bí", "bầu",
                "mướp", "dưa chuột", "dưa leo", "bắp", "ngô", "đậu bắp", "su su", "cà ",
            ]
        )
        leafy_group = any(k in group.lower() for k in ["rau mùa", "rau quanh", "rau gia vị"])
        if rootish and not leafy_group:
            return (
                f"FRONT (Part 2 – prepared, must be in front): the same {name} lightly prepared to show "
                "edible interior if meaningful (halved or cross-section only when it reveals flesh "
                "structure); otherwise keep natural whole form cleaned — do not force a meaningless cut.",
                f"BACK (Part 1 – original, slightly behind): whole intact fresh {name} in natural uncut "
                "shape, 3/4 angle best showing form.",
            )
        return (
            f"FRONT (Part 2 – prepared, must be in front): the same {name} cleaned/trimmed edible portion "
            "in natural shape — keep natural form, do NOT cut in half if cutting has no meaning for "
            "recognition.",
            f"BACK (Part 1 – original, slightly behind): fresh {name} in natural whole uncut form as "
            "typically sold (bunches/leaves/stalks kept natural), 3/4 angle.",
        )

    if is_dish(sheet):
        return (
            f"FRONT (Part 2 – prepared/detail, must be in front): the same {name} in a complementary view "
            "that reveals edible components/texture (cross-section, opened wrap, or close detail of main "
            "edible parts) — still the same food, similar visual scale, no props, no hands.",
            f"BACK (Part 1 – original presentation, slightly behind): {name} shown as a complete "
            "recognizable serving of the dish/snack itself only (no plate/bowl/utensils if possible; if "
            "containment is essential for recognition, use the most minimal neutral presentation), "
            "product-focused.",
        )

    return (
        f"FRONT (Part 2 – prepared, must be in front): the same {name} prepared appropriately to clearly "
        "show the edible part/interior, matching visual scale.",
        f"BACK (Part 1 – original, slightly behind): whole/natural form of {name}, unprocessed appearance, "
        "3/4 angle best showing shape and structure.",
    )


def main() -> None:
    foods = load_foods()
    prompts: list[str] = []
    for i, food in enumerate(foods, 1):
        name = food["name"].strip()
        group = food["group"] or "Thực phẩm"
        p2_front, p1_back = part_desc(food)
        prompt = (
            f'[{i}] {name} ({group})\n'
            f'Create a professional realistic product photo of Vietnamese food item "{name}". {BASE} '
            f"{p2_front} {p1_back} "
            "The two food objects must stand closely next to each other in one continuous scene, "
            "with Part 2 clearly closer to the camera than Part 1. "
            "Use the most suitable 3/4 (or best clarifying) camera angle so shape and structure are obvious. "
            "Photorealistic commercial catalog look suitable for a fitness/nutrition website food database."
        )
        prompts.append(prompt)

    out_path = ROOT / "prompts_thuc_pham_hinh_anh.txt"
    out_path.write_text("\n\n".join(prompts) + "\n", encoding="utf-8")
    downloads = Path(r"C:\Users\Tran Tai\Downloads\prompts_thuc_pham_hinh_anh.txt")
    downloads.write_text("\n\n".join(prompts) + "\n", encoding="utf-8")
    print(f"Wrote {len(prompts)} prompts -> {out_path}")
    print(f"Also copied -> {downloads}")
    print(f"Size: {out_path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
