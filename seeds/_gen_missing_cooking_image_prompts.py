"""Prompts for cooking-post ingredients that have no media file yet."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "seeds" / "FOODS_COOKING_IMAGE_PROMPTS_MISSING.md"

BOILER = """Create a professional realistic product photo of Vietnamese food item "{name_en}". Professional realistic food product photography for a nutrition/fitness website. Format: WebP or JPEG, 1920x1080 pixels, 16:9 aspect ratio. Pure clean solid white background, minimal studio setup. Soft even natural studio lighting, sharp focus, true-to-life colors and textures. No people, no human hands, no plates, bowls, knives, cutting boards, or props. No text, labels, logos, watermarks, or nutrition info. Single unified composition (NOT a split-panel, NOT a collage, NOT two separate frames). Show TWO states of the SAME food standing very close together side by side in one shot, almost touching, visually similar size and scale, balanced and easy to recognize. CRITICAL depth order: Part 2 (prepared/edible state) must stand in the FRONT / foreground; Part 1 (original/whole state) must stand slightly BEHIND Part 2. Subject group centered, overall food content fills about 80% of the frame. Consistent catalog style across the food dataset — prioritize realism, clarity, and recognizability over artistic effects. FRONT (Part 2 – prepared, must be in front): {front} BACK (Part 1 – original, slightly behind): {back} The two food objects must stand closely next to each other in one continuous scene, with Part 2 clearly closer to the camera than Part 1. Use the most suitable 3/4 (or best clarifying) camera angle so shape and structure are obvious. Photorealistic commercial catalog look suitable for a fitness/nutrition website food database."""

# slug, name_vi, name_en, front, back  — ordered by how often the food appears on /cach-nau
ITEMS: list[tuple[str, str, str, str, str]] = [
    (
        "bun-tuoi",
        "Bún tươi",
        "Bún tươi (fresh Vietnamese rice vermicelli — thin ROUND white noodles)",
        "a loosened nest of cooked fresh bún: many thin ROUND white rice-vermicelli strands, about 1 mm diameter, opaque white, slightly glossy, no bowl. Must be ROUND like spaghetti-thin rice noodles, NOT flat pho, NOT wider hủ tiếu, NOT yellow mì, NOT glass noodles.",
        "a compact folded bundle of whole intact fresh white bún vermicelli, uncut bundle, 3/4 angle. Do NOT generate bánh phở, hủ tiếu, udon, or bunches of round wheat noodles.",
    ),
    (
        "xa-lach",
        "Xà lách",
        "Xà lách (green leaf / butterhead lettuce used in Vietnamese bánh mì and gỏi cuốn)",
        "a few separated green lettuce leaves in front showing ruffled soft edges, pale crisp ribs, and tender leaf texture, no plate.",
        "one whole intact fresh green lettuce head, uncut, loose butterhead/leaf shape (NOT iceberg tight ball, NOT frisée, NOT purple lollo, NOT romaine romaine-only spear), 3/4 angle.",
    ),
    (
        "thit-lon-xay-song",
        "Thịt lợn xay (sống)",
        "Thịt lợn xay sống (raw ground / minced pork)",
        "a small neat mound of raw ground pork with a cut/open face so the minced pink-white fat flecks and grind texture are obvious, no bowl.",
        "a slightly larger intact heap of the same raw minced pork, unspread, 3/4 angle. Must be minced pork, NOT a whole pork cut, NOT beef mince (too red), NOT sausage links.",
    ),
    (
        "nuoc-dua-tuoi",
        "Nước dừa tươi",
        "Nước dừa tươi (fresh young coconut WATER, a clear liquid — not coconut jelly, not coconut meat)",
        "a flat glossy PUDDLE of clear slightly cloudy coconut WATER sitting directly on white — watery, liquid, refractive, NOT a solid jelly dome, NOT nata de coco, NOT coconut meat.",
        "one whole intact young green coconut, uncut, natural fruit shape, 3/4 angle.",
    ),
    (
        "suon-lon-song",
        "Sườn lợn (sống)",
        "Sườn lợn sống (raw pork spare ribs — curved rib bones with meat between)",
        "one or two raw pork spare ribs cut across to clearly show pink meat, white fat, and a curved rib bone, no plate.",
        "a short rack / few whole intact raw pork spare ribs, uncut, skinless, meat between curved bones, 3/4 angle. Must be spare ribs, NOT sườn sụn cartilage, NOT a pork chop loin, NOT beef short ribs.",
    ),
    (
        "me-chin",
        "Me chín",
        "Me chín (ripe tamarind — brown sticky pulp pods)",
        "a few pieces of ripe tamarind pulp in front showing sticky dark-brown fruit paste, fibers, and shiny seeds, no bowl.",
        "a small cluster of whole intact ripe tamarind pods, brittle light-brown shells, uncut, 3/4 angle. Must be ripe brown me, NOT green sour tamarind only, NOT tamarind candy, NOT dates.",
    ),
    (
        "banh-pho-tuoi",
        "Bánh phở tươi",
        "Bánh phở tươi (fresh pho noodles — FLAT white rice sheets, NOT bún, NOT hủ tiếu)",
        "a loosened nest of fresh pho noodles in front showing FLAT wide-ish white rice ribbons (about 3–5 mm wide), moist, opaque white, no bowl. Must be FLAT like fettuccine-thin rice noodles.",
        "a compact folded bundle of whole intact fresh bánh phở, uncut bundle, 3/4 angle. Do NOT generate round bún vermicelli, hủ tiếu, lasagna, or egg noodles.",
    ),
    (
        "dau-phu-chac",
        "Đậu phụ chắc",
        "Đậu phụ chắc (firm tofu block)",
        "thick slices or cubes of firm tofu in front showing fine white porous soy interior and clean cut faces, no plate.",
        "one whole intact rectangular firm tofu block, uncut, pale ivory, 3/4 angle. Must be firm block tofu, NOT silken custard tofu, NOT fried tofu puffs, NOT tempeh.",
    ),
    (
        "dui-ga-khong-da-song",
        "Đùi gà không da (sống)",
        "Đùi gà không da sống (raw skinless chicken thigh)",
        "a raw skinless chicken thigh cut or butterflied in front showing dark-pink thigh meat, grain, and a bone if present, no plate.",
        "one whole intact raw boneless or bone-in skinless chicken thigh, uncut, deep pink (darker than breast), 3/4 angle. NO yellow skin, NOT chicken breast, NOT a whole bird.",
    ),
    (
        "ngo-om",
        "Ngò om",
        "Ngò om (rice paddy herb, Limnophila aromatica)",
        "several rice-paddy-herb stems in front showing WHORLS of tiny sawtooth leaflets arranged in rings around a succulent square-ish green stem — this is Limnophila aromatica / rau om / ngò om, NOT thyme, NOT oregano, NOT mint.",
        "a small bunch of whole intact fresh ngò om with the same whorled leaflet pattern, uncut, 3/4 angle. Do NOT generate thyme, rosemary, or European kitchen herbs.",
    ),
    (
        "moc-nhi-ngam-nuoc",
        "Mộc nhĩ (ngâm nước)",
        "Mộc nhĩ ngâm nước (rehydrated wood-ear mushroom)",
        "a few rehydrated wood-ear pieces in front, one sliced to show thin dark-brown gelatinous flesh, ruffled ear shape, and paler underside.",
        "a compact cluster of whole intact soaked wood-ear mushrooms, glossy black-brown, uncut, 3/4 angle. Must be wood ear, NOT shiitake, NOT dried unsoaked crumbles, NOT nori.",
    ),
    (
        "soi-banh-canh",
        "Sợi bánh canh",
        "Sợi bánh canh (thick SOLID round Vietnamese tapioca-rice noodles)",
        "a few thick round bánh canh noodles, one cut to show a SOLID opaque white chewy cross-section with NO hole, NO star shape, NOT macaroni, NOT udon tubes.",
        "a compact bundle of whole intact fresh thick bánh canh strands, uncut, 3/4 angle.",
    ),
    (
        "rau-day",
        "Rau đay",
        "Rau đay (jute / Corchorus leaves for Vietnamese canh)",
        "several jute leaves in front showing small pointed oval leaves, fine teeth, and a slightly mucilaginous-looking tender green surface.",
        "a small bunch of whole intact fresh rau đay with slender stems, uncut, 3/4 angle. Do NOT generate spinach, malabar spinach (mồng tơi), or mint.",
    ),
    (
        "thit-vit-co-da",
        "Thịt vịt có da",
        "Thịt vịt có da (raw duck meat with skin)",
        "a raw duck piece cut in front showing dark-red duck meat, a layer of fat, and yellow-cream skin, no plate.",
        "one whole intact raw duck thigh or breast with skin on, uncut, 3/4 angle. Must look like duck (darker than chicken, thicker fat under skin), NOT chicken, NOT goose whole bird only.",
    ),
    (
        "cha-trung",
        "Chả trứng hấp",
        "Chả trứng hấp (Vietnamese steamed egg meatloaf for cơm tấm)",
        "a thick wedge of STEAMED (not baked, not browned crust) Vietnamese chả trứng: uniform yellow egg custard mixed throughout with minced pork, wood-ear mushroom specks, smooth moist steamed texture like a round flan-loaf.",
        "one whole intact steamed round/oval chả trứng loaf, pale golden steamed surface without oven-browned crust, uncut, 3/4 angle. Do NOT generate tamagoyaki, gyeran-mari, baked meatloaf, or a stuffed hollow center.",
    ),
    (
        "bap-ngot-luoc",
        "Bắp ngọt luộc",
        "Bắp ngọt luộc (boiled sweet corn on the cob)",
        "a boiled sweet-corn cob cut or with some kernels loosened in front showing plump yellow kernels and juicy cut face, no plate.",
        "one whole intact boiled sweet-corn cob, uncut, bright yellow kernels, 3/4 angle. Must be sweet corn, NOT baby corn, NOT popcorn kernels.",
    ),
    (
        "com-trang",
        "Cơm trắng nấu",
        "Cơm trắng nấu (cooked white rice, gạo tẻ cooked)",
        "a small loosened pile of cooked white rice in front so individual fluffy opaque grains are clearly separate, no bowl.",
        "a compact mound of the same cooked white rice, intact heap, 3/4 angle. Must be cooked steamed rice, NOT uncooked grains, NOT brown rice, NOT glutinous xôi clumps.",
    ),
    (
        "he",
        "Hẹ",
        "Hẹ (Chinese chives / garlic chives — flat leaves)",
        "a few Chinese-chive blades in front showing FLAT grass-like leaves, not hollow, bright green, cut ends visible.",
        "a small tied bunch of whole intact fresh hẹ, uncut long flat leaves, 3/4 angle. Must be flat garlic chives, NOT hollow hành lá spring-onion tubes, NOT garlic bulbs.",
    ),
    (
        "mang-tuoi",
        "Măng tươi",
        "Măng tươi (fresh bamboo shoot)",
        "sliced fresh bamboo shoot in front showing cream-white layered flesh, concentric rings, and a pale yellow edge.",
        "one whole intact fresh bamboo shoot, uncut, conical pointed shoot with brown papery sheaths, 3/4 angle. Must be bamboo shoot, NOT banana blossom, NOT corn cob.",
    ),
    (
        "thit-de-nac-song",
        "Thịt dê nạc (sống)",
        "Thịt dê nạc sống (raw lean goat meat)",
        "thick slices of raw lean goat in front showing deep red-purple grain, very little fat, slightly coarser than lamb.",
        "one whole intact raw goat meat chunk, uncut, 3/4 angle. Must look like goat (darker and leaner than pork), NOT beef steak with heavy marbling, NOT a whole goat carcass.",
    ),
]


def render_prompt(item: tuple[str, str, str, str, str]) -> str:
    _slug, _name_vi, name_en, front, back = item
    return BOILER.format(name_en=name_en, front=front, back=back)


def main() -> None:
    prompts = [render_prompt(item) for item in ITEMS]
    OUT.write_text("\n\n".join(prompts) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(ITEMS)} prompts)")
    for i, item in enumerate(ITEMS, 1):
        print(f"{i:03d} {item[0]}")


if __name__ == "__main__":
    main()
