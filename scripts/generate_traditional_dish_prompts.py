# -*- coding: utf-8 -*-
"""Prompts for 95 traditional dishes — one regional, photoreal serving each."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "seeds" / "foods_traditional_dishes.json"
OUT = Path(r"C:\Users\Tran Tai\Downloads\prompts-mon-truyen-thong.txt")

BASE = (
    "Professional photorealistic catalog photo of a REAL Vietnamese regional dish "
    "as actually served in its home place — not fusion, not a tourist mixed platter, "
    "not a collage, not a split panel. Format: JPEG, 1920x1080 pixels, 16:9. "
    "Pure solid white background, soft even studio lighting, sharp focus, true-to-life colors. "
    "Single unified composition, one serving centered, food fills about 75-80% of the frame. "
    "No people, no hands, no restaurant table clutter, no extra competing dishes, "
    "no chopsticks in frame unless they are part of the food, no text, labels, logos, watermarks. "
    "The authentic serving vessel of THIS dish is allowed. Use a plain white ceramic bowl or plate "
    "unless the vessel itself identifies the dish (tiny bánh bèo chen, banana-leaf wrap, bamboo tube). "
    "Slightly elevated 3/4 food-photography angle so toppings, broth, and texture are readable. "
    "Looks like a real local eatery portion, not a styled chef tasting plate."
)

# Visual identity: what THIS place's version looks like, and what it must not become.
LOOK = {
    "banh-beo-chen-da-nang": (
        "IDENTITY: Đà Nẵng bánh bèo — a CLUSTER of about 5 small shallow white ceramic chen, "
        "each holding a thin round steamed rice cake. Toppings: coarsely fried dried shrimp (tôm cháy) "
        "and crispy fried pork skin (da heo/tóp mỡ), scallion oil. Slightly heartier toppings than Huế. "
        "Search: 'bánh bèo chén Đà Nẵng tôm cháy da heo'. "
        "NOT Huế-style tiny sparse shrimp only, NOT bánh nậm, NOT bánh bột lọc, NOT one large pancake."
    ),
    "banh-beo-chen-hue-5-chen": (
        "IDENTITY: Huế bánh bèo — exactly 5 tiny shallow ceramic chen grouped together. "
        "Each cake is small, smooth, milky-white, very thin. Classic Huế topping: a pinch of fine "
        "orange-pink dried shrimp powder (tôm chấy), a drop of scallion oil, optional tiny crispy pork rinds, "
        "a little amber fish sauce in the chen. Delicate, court-cuisine look. "
        "Search: 'bánh bèo chén Huế 5 chén tôm chấy'. "
        "NOT Đà Nẵng heavy toppings, NOT bánh bột lọc translucent pillows, NOT bánh nậm in banana leaf."
    ),
    "banh-bot-loc-hue": (
        "IDENTITY: Huế bánh bột lọc — about 8–10 SMALL smooth translucent TAPIOCA pillows (bột năng), "
        "square or plump discs with NO ruffled wonton pleats. Each dumpling fully ENCASES a whole small "
        "pink shrimp (and a bit of minced pork) INSIDE the clear chewy skin — the shrimp silhouette shows "
        "through the tapioca, it is NOT sitting on top as a garnish. Glossy scallion oil, banana leaf. "
        "Search: 'bánh bột lọc Huế tôm bọc trong bột năng trong suốt'. "
        "NOT há cảo / har gow (pleated wheat wrappers, shrimp on top), NOT bánh nậm (flat opaque leaf cakes), "
        "NOT crystal dumplings with only chives."
    ),
    "banh-can-da-lat": (
        "IDENTITY: Đà Lạt bánh căn — a set of small round thick mini-pancakes cooked in a cast-iron "
        "mold, each with a cracked quail or chicken egg on top, golden edges, served as several pieces "
        "together. Often with a bit of ground pork or minced toppings. "
        "Search: 'bánh căn Đà Lạt trứng'. "
        "NOT bánh khọt (shrimp in the well), NOT bánh xèo, NOT Japanese takoyaki."
    ),
    "banh-canh-ca-loc": (
        "IDENTITY: Southern bánh canh cá lóc — thick round tapioca-rice noodles (udon-like, milky white) "
        "in a clear-to-slightly-cloudy fish broth in a deep bowl. Flakes of snakehead fish (cá lóc), "
        "scallion, maybe a few herbs. Noodles are THICK tubes, not phở sheets, not thin bún. "
        "Search: 'bánh canh cá lóc miền Tây'. "
        "NOT phở, NOT bún cá, NOT bánh canh cua with orange crab roe."
    ),
    "banh-canh-cua-ghe": (
        "IDENTITY: bánh canh cua/ghẹ — THICK round milky tapioca-rice noodles (bánh canh, like short udon) "
        "in a RICH orange broth colored by crab tomalley (gạch cua), shredded crab meat, optionally one "
        "crab claw. Vietnamese breakfast bowl: scallion, fried shallot, a little black pepper. "
        "Search: 'bánh canh cua gạch cua Sài Gòn'. "
        "NOT Singapore/Malay laksa (no lime wheel floating, no fishballs, no quail eggs, no coconut-laksa look), "
        "NOT bún riêu (thin vermicelli + tomato + crab-paste raft), NOT clear fish bánh canh."
    ),
    "banh-canh-trang-bang": (
        "IDENTITY: Tây Ninh Trảng Bàng bánh canh — thick translucent tapioca noodles, a large piece of "
        "pork hock/giò heo with skin, light broth, scallion. The hock is the hero. "
        "Search: 'bánh canh Trảng Bàng giò heo'. "
        "NOT bánh canh cua, NOT Japanese tonkotsu ramen, NOT phở."
    ),
    "banh-chung-luoc-truyen-thong": (
        "IDENTITY: Northern boiled bánh chưng Tết — a SQUARE glutinous-rice cake. Show TWO pieces in one shot: "
        "one still fully wrapped in dark-green banana leaf tied with string (square brick), and one unwrapped "
        "or halved to show the layered cross-section: sticky rice outside, yellow mung-bean paste, pork belly "
        "in the center. "
        "Search: 'bánh chưng luộc cắt ngang nhân thịt đỗ xanh'. "
        "NOT bánh tét (cylinder), NOT zongzi pyramid, NOT bánh chưng rán golden fried."
    ),
    "banh-chung-ran": (
        "IDENTITY: bánh chưng rán — thick SQUARE slices of leftover bánh chưng pan-fried until the rice crust "
        "is golden-brown and crispy, mung bean and pork still visible inside the cut. Greasy, toasted edges. "
        "Search: 'bánh chưng rán vàng giòn'. "
        "NOT boiled unfried bánh chưng, NOT bánh tét, NOT hash browns."
    ),
    "banh-cuon-nong-kem-cha-que": (
        "IDENTITY: Hà Nội bánh cuốn nóng on a PLATE (not a soup bowl): very thin steamed rice sheets "
        "rolled with minced pork+wood-ear, fried shallots, a light splash of nước mắm — not swimming in broth. "
        "Beside the rolls: slices of chả quế (cinnamon pork sausage) — pale pink with visible dark cinnamon "
        "specks, NOT smooth pink giò lụa. "
        "Search: 'bánh cuốn Hà Nội chả quế hành phi'. "
        "NOT giò lụa / chả lụa (plain pink sausage without cinnamon dots), NOT a wet noodle-soup bowl, "
        "NOT bánh ướt unrolled sheets, NOT gỏi cuốn."
    ),
    "banh-da-cua-hai-phong": (
        "IDENTITY: Hải Phòng bánh đa cua — DISTINCTIVE dark reddish-brown wide rice-noodle sheets (bánh đa đỏ) "
        "in a crab-tomato broth, with chả lá lốt, pig blood cake, fried tofu, morning-glory stems. "
        "The RED noodles are the tell. "
        "Search: 'bánh đa cua Hải Phòng sợi đỏ'. "
        "NOT white bún riêu, NOT phở, NOT Korean jjolmyeon."
    ),
    "banh-gai-tuyen-quang": (
        "IDENTITY: Tuyên Quang bánh gai — small dark almost-black sticky cakes from gai leaves, round or "
        "slightly flattened, one whole and one bitten/cut to show yellow mung-bean-and-coconut filling. "
        "Matte dark green-black skin, chewy. "
        "Search: 'bánh gai Tuyên Quang nhân đậu xanh'. "
        "NOT bánh chưng, NOT mooncake, NOT chocolate dessert."
    ),
    "banh-hoi-long-heo-dong-nai": (
        "IDENTITY: Đồng Nai / Biên Hòa bánh hỏi lòng heo — fine woven rice-vermicelli mats (bánh hỏi) "
        "brushed with scallion oil, next to a pile of boiled pork offal (intestine, liver, stomach) "
        "sliced, with herbs and a small dish of fish sauce. "
        "Search: 'bánh hỏi lòng heo Đồng Nai'. "
        "NOT bún thịt nướng, NOT phở, NOT pasta nests."
    ),
    "banh-khot-vung-tau": (
        "IDENTITY: Vũng Tàu bánh khọt — a tray-set of small round crispy cups, each with a WHOLE shrimp "
        "sitting in a turmeric-yellow rice-coconut batter, lacy fried edges, scallion. Several pieces "
        "clustered. "
        "Search: 'bánh khọt Vũng Tàu tôm'. "
        "NOT bánh căn (egg on top, thicker), NOT bánh xèo (large folded pancake), NOT takoyaki."
    ),
    "banh-mi-kep-thit-cha-pate": (
        "IDENTITY: Sài Gòn bánh mì thịt chả pate — a SHORT crisp Vietnamese baguette, cracked golden crust, "
        "smeared with liver pâté, filling of sliced cold cuts / roast pork and Vietnamese chả, pickled "
        "carrot-daikon, cilantro, chili. Cut or slightly open so the filling is visible. "
        "Search: 'bánh mì Sài Gòn pate chả thịt'. "
        "NOT a Western sandwich, NOT bánh mì ốp la (fried eggs), NOT a long empty baguette."
    ),
    "banh-mi-op-la-2-trung": (
        "IDENTITY: bánh mì ốp la — Vietnamese baguette with TWO sunny-side-up fried eggs, runny yolks "
        "visible, a little pâté or butter, cucumber, cilantro, chili. Breakfast look. "
        "Search: 'bánh mì ốp la 2 trứng'. "
        "NOT thịt chả bánh mì, NOT an omelette wrap, NOT English breakfast."
    ),
    "banh-mi-xiu-mai-trung-muoi": (
        "IDENTITY: bánh mì xíu mại trứng muối — baguette served with (or stuffed beside) a small bowl of "
        "pork meatballs in tomato sauce, halved salted duck-egg yolks showing bright orange-yellow. "
        "Saigon breakfast. "
        "Search: 'bánh mì xíu mại trứng muối'. "
        "NOT spaghetti meatballs, NOT bánh mì ốp la, NOT dim sum siu mai in wonton wrappers."
    ),
    "banh-nam-hue": (
        "IDENTITY: Huế bánh nậm — small flat rectangles of steamed rice paste wrapped in banana leaf, "
        "opened to show a thin pale cake topped with a line of fine minced shrimp (orange) and scallion. "
        "Show 3–4 leaf packets, some opened. "
        "Search: 'bánh nậm Huế lá chuối tôm'. "
        "NOT bánh bột lọc (translucent pillows), NOT bánh bèo in chen, NOT tamales."
    ),
    "banh-phu-the-bac-ninh": (
        "IDENTITY: Bắc Ninh bánh phu thê — a pair of small square sticky cakes wrapped in green leaves "
        "(lá giong/lá dong), pale green-white cốm-tinted glutinous rice, yellow mung filling if cut. "
        "Often presented as a matching couple of cakes. "
        "Search: 'bánh phu thê Bắc Ninh'. "
        "NOT bánh chưng (large square Tết cake with pork), NOT Japanese mochi, NOT bánh cốm Hà Nội loose."
    ),
    "banh-tai-phu-tho": (
        "IDENTITY: Phú Thọ bánh tai — small fried glutinous cakes shaped like ears/ovals, golden-brown "
        "crispy outside, one cut to show mung-bean filling. "
        "Search: 'bánh tai Phú Thọ chiên'. "
        "NOT bánh rán, NOT empanada, NOT bánh gối."
    ),
    "banh-tet-nhan-thit-dau-xanh": (
        "IDENTITY: Southern Tết bánh tét with pork and mung bean — a long CYLINDER wrapped in banana leaf. "
        "Show one whole wrapped log AND several round slices showing the spiral: sticky rice ring, yellow "
        "mung bean, pork in the center. "
        "Search: 'bánh tét nhân thịt đậu xanh cắt khoanh'. "
        "NOT square bánh chưng, NOT Swiss roll cake, NOT sushi."
    ),
    "banh-tet-vinh-long": (
        "IDENTITY: Vĩnh Long bánh tét — cylindrical banana-leaf sticky-rice log, typically banana filling "
        "(sweet, no pork) OR the Mekong Tết style. Show wrapped cylinder plus round slices with a "
        "yellow-brown ripe-banana center (not pork). "
        "Search: 'bánh tét Vĩnh Long nhân chuối'. "
        "NOT bánh tét thịt, NOT bánh chưng, NOT banana bread."
    ),
    "banh-trang-nuong-da-lat": (
        "IDENTITY: Đà Lạt bánh tráng nướng — a round thin rice paper grilled over charcoal until blistered "
        "and crispy, topped with beaten egg, scallion, dried beef floss (bò khô), crushed peanuts, chili sauce. "
        "Looks like a Vietnamese pizza on rice paper. "
        "Search: 'bánh tráng nướng Đà Lạt trứng bò khô'. "
        "NOT bánh xèo, NOT Mexican tostada, NOT bánh tráng trộn (wet mixed paper)."
    ),
    "banh-uot-long-ga-trung-non": (
        "IDENTITY: Central bánh ướt lòng gà trứng non — unfolded steamed rice sheets (not rolled bánh cuốn), "
        "topped with boiled chicken offal and immature egg yolks (trứng non — small yellow lobes), fried shallots, "
        "herbs, fish sauce. "
        "Search: 'bánh ướt lòng gà trứng non'. "
        "NOT bánh cuốn rolls, NOT phở gà, NOT gỏi."
    ),
    "banh-uot-thit-nuong-quang-tri": (
        "IDENTITY: Quảng Trị bánh ướt thịt nướng — wet unfolded rice sheets + charcoal-grilled pork slices "
        "with smoke char, herbs, crushed peanuts, fish sauce. Breakfast-stall look of Quảng Trị. "
        "Search: 'bánh ướt thịt nướng Quảng Trị'. "
        "NOT bánh cuốn Hà Nội, NOT bún thịt nướng in a bowl, NOT bánh xèo."
    ),
    "banh-xeo-mien-tay": (
        "IDENTITY: Mekong bánh xèo — ONE LARGE folded turmeric-yellow crispy crepe, 25–30 cm, lacy fried "
        "edge, stuffed with bean sprouts, shrimp and pork belly slices, coconut-milk yellow batter. "
        "Huge, rustic miền Tây size. Optional lettuce/mustard greens beside it only if small. "
        "Search: 'bánh xèo miền Tây to giòn'. "
        "NOT the small miền Trung bánh xèo (6–8 cm), NOT Korean pajeon, NOT bánh khọt cups."
    ),
    "banh-xeo-mien-trung-banh-nho": (
        "IDENTITY: Central Vietnam SMALL bánh xèo — several mini folded yellow pancakes, each about the "
        "size of a palm (much smaller than miền Tây), thinner, less filling, shrimp visible, often eaten "
        "with mustard greens and fermented fish sauce (mắm nêm) implied by the small-pancake cluster. "
        "Search: 'bánh xèo miền Trung bánh nhỏ Đà Nẵng Hội An'. "
        "NOT the giant Mekong bánh xèo, NOT bánh khọt, NOT quesadillas."
    ),
    "banh-xeo-toc-tien": (
        "IDENTITY: Bà Rịa Tóc Tiên bánh xèo — large crispy yellow crepe in the Đông Nam Bộ style, "
        "generous shrimp and pork, very crunchy edge, similar to miền Tây but associated with Tóc Tiên village. "
        "Search: 'bánh xèo Tóc Tiên'. "
        "NOT small Huế/Đà Nẵng bánh xèo, NOT bánh khọt."
    ),
    "bo-kho": (
        "IDENTITY: Vietnamese bò kho — a bowl of beef stew in an orange-red lemongrass-annatto broth, "
        "tender beef chunks, carrot, maybe potato, glossy oil on top, served as stew (optionally a piece "
        "of baguette leaning on the bowl). "
        "Search: 'bò kho cà rốt bánh mì'. "
        "NOT Hungarian goulash, NOT phở, NOT Korean galbi-jjim."
    ),
    "bo-xao-can-toi-tay": (
        "IDENTITY: Northern home stir-fry — sliced beef quickly wok-fried with celery (cần tây) and leek "
        "(tỏi tây), brown stir-fry sauce, on a white plate. Vegetable sticks still a bit crisp. "
        "Search: 'bò xào cần tây tỏi tây'. "
        "NOT bò lúc lắc, NOT phở, NOT a salad."
    ),
    "bun-bo-hue-day-du": (
        "IDENTITY: Huế bún bò 'đầy đủ' — a large bowl of THICK round rice vermicelli (not flat phở) in a "
        "RED-ORANGE lemongrass chili broth with a sheen of annatto oil. Toppings: sliced beef shank, "
        "pig knuckle, dark cubes of pig blood cake (huyết), thick slices of chả cua, scallion, cilantro, "
        "a wedge of lime. Looks spicy and oily-red. "
        "Search: 'bún bò Huế đầy đủ huyết giò'. "
        "NOT Hà Nội phở (flat noodles, clear brown broth), NOT bún riêu, NOT tom yum."
    ),
    "bun-ca-chau-doc": (
        "IDENTITY: Châu Đốc An Giang bún cá — white thin vermicelli in a fish-sauce-forward broth, "
        "snakehead fish pieces, maybe fermented fish aroma suggested by a darker amber broth than Hanoi soups, "
        "herbs, Mekong look. "
        "Search: 'bún cá Châu Đốc'. "
        "NOT bún cá Nha Trang (tomato-red, fish cakes), NOT phở, NOT bún mắm (heavy mắm, mixed seafood)."
    ),
    "bun-ca-nha-trang": (
        "IDENTITY: Nha Trang bún cá — vermicelli in a CLEAR-TO-LIGHT-TOMATO fish broth, fried golden "
        "fish cakes (chả cá) sliced, sometimes tomato wedges, pineapple, herbs. Coastal-breakfast look. "
        "Search: 'bún cá Nha Trang chả cá'. "
        "NOT bún chả cá Đà Nẵng (more tomato-red), NOT bún bò Huế, NOT Japanese udon."
    ),
    "bun-cha-ca-da-nang": (
        "IDENTITY: Đà Nẵng bún chả cá — vermicelli in a REDDISH tomato-based broth, slices of fried "
        "(and maybe steamed) fish cake, tomato, pineapple, herbs. More tomato-forward than Nha Trang. "
        "Search: 'bún chả cá Đà Nẵng cà chua'. "
        "NOT bún bò Huế, NOT bún cá Nha Trang clear broth, NOT fishball noodle Singapore style."
    ),
    "bun-cha-ha-noi": (
        "IDENTITY: Hà Nội bún chả as a SET, not one mixed soup: a bowl of warm sweet-sour fish sauce "
        "holding charcoal-grilled pork patties (chả viên) AND sliced grilled pork belly (chả miếng) "
        "with smoky char, green papaya/carrot slaw in the sauce; beside it a mound of white rice vermicelli "
        "and a pile of herbs (lettuce, perilla, mint). "
        "Search: 'bún chả Hà Nội bát nước chấm thịt nướng'. "
        "NOT bún thịt nướng miền Nam (noodles already mixed in one bowl with nước mắm poured on), "
        "NOT bún chả cá, NOT Korean BBQ."
    ),
    "bun-dau-mam-tom": (
        "IDENTITY: Hà Nội bún đậu mắm tôm — a tray/plate: squares of rice vermicelli cake (bún khô cắt), "
        "golden fried tofu, boiled pork belly slices, chả cốm or nem, herbs, and a small saucer of "
        "PURPLE-BROWN shrimp paste (mắm tôm) mixed with chili and lime. "
        "Search: 'bún đậu mắm tôm Hà Nội'. "
        "NOT bún thịt nướng, NOT Korean tofu stew, NOT a noodle soup."
    ),
    "bun-mam": (
        "IDENTITY: Mekong bún mắm — vermicelli in a cloudy, pungent BROWN fermented-fish broth, loaded "
        "with mixed Mekong protein: shrimp, squid, roast pork slices, sometimes fish, eggplant, "
        "herbs. Looks richer and darker than phở. "
        "Search: 'bún mắm miền Tây tôm mực thịt quay'. "
        "NOT bún bò Huế (red lemongrass), NOT phở, NOT bún riêu (tomato-crab red)."
    ),
    "bun-mang-vit": (
        "IDENTITY: Northern bún măng vịt — vermicelli in a light duck broth, shredded duck meat, "
        "pale bamboo-shoot slices (măng), scallion, maybe a side of ginger fish sauce implied. "
        "Clear-ish golden broth. "
        "Search: 'bún măng vịt'. "
        "NOT phở gà, NOT duck noodle Chinese style, NOT bún bò."
    ),
    "bun-nuoc-leo-can-tho": (
        "IDENTITY: Cần Thơ bún nước lèo — Mekong vermicelli in a fermented-fish (mắm) broth similar to "
        "bún mắm but the Cần Thơ/Sóc Trăng Khmer-influenced look: shrimp, roast pork, snakehead or linh, "
        "herbs, brown savory broth. "
        "Search: 'bún nước lèo Cần Thơ'. "
        "NOT clear phở, NOT Thai boat noodles only, NOT bún bò Huế."
    ),
    "bun-oc-giam-bong": (
        "IDENTITY: Hà Nội bún ốc — vermicelli in a tomato-sour broth (giấm bỗng), whole freshwater snails "
        "(ốc) in shell or picked, tomato, fried tofu, banana blossom, herbs. Red-orange sour soup. "
        "Search: 'bún ốc Hà Nội giấm bỗng'. "
        "NOT escargot in garlic butter, NOT bún riêu (crab paste rafts), NOT phở."
    ),
    "bun-rieu-cua-dong": (
        "IDENTITY: Northern bún riêu cua đồng — vermicelli in a tomato broth with a distinctive PINK-ORANGE "
        "crab-paste raft (riêu) floating on top, fried tofu puffs, pig blood cake, tomato wedges, "
        "scallion. The crab curd is the hero. "
        "Search: 'bún riêu cua đồng riêu cua đậu rán'. "
        "NOT bún ốc, NOT bánh canh cua, NOT bún bò Huế."
    ),
    "bun-thang-ha-noi": (
        "IDENTITY: Hà Nội bún thang — a refined bowl: thin vermicelli, pale clear chicken-shrimp broth, "
        "TOPPINGS LAID IN NEAT COLOR STRIPS — shredded chicken, thin egg crepe julienne (trứng), "
        "pale Vietnamese pork sausage (giò), maybe shrimp floss, a tiny drop of cà cuống essence not visible. "
        "Looks composed and light, not rustic-red. "
        "Search: 'bún thang Hà Nội thái chỉ'. "
        "NOT phở, NOT bún bò, NOT Chinese wonton soup."
    ),
    "bun-thit-nuong": (
        "IDENTITY: Southern bún thịt nướng — ONE bowl already assembled: white vermicelli topped with "
        "charcoal-grilled pork slices, pickled carrot-daikon, herbs, crushed peanuts, scallion oil, "
        "nước mắm chua ngọt. Mixed dry-style, little or no soup. "
        "Search: 'bún thịt nướng Sài Gòn đậu phộng'. "
        "NOT Hà Nội bún chả (separate dipping bowl), NOT bún bò soup, NOT Thai larb."
    ),
    "ca-basa-tra-kho-to": (
        "IDENTITY: cá basa/tra kho tộ — catfish steaks caramel-braised in a small clay pot (tộ), "
        "dark amber-brown salty-sweet sauce, visible fish steaks with white flesh, pepper, chili, "
        "green onion. Glossy sauce. "
        "Search: 'cá basa kho tộ'. "
        "NOT grilled fish, NOT cá kho lóc (snakehead whole), NOT Indian curry."
    ),
    "ca-bo-kho-quang-ngai": (
        "IDENTITY: Quảng Ngãi / Lý Sơn CÁ BÒ KHÔ — whole flattened dried TRIGGERFISH, wide diamond/oval "
        "board-like shape, golden-amber dry skin, one or two whole dried fish stacked, optionally one "
        "piece torn to show the dry fibrous interior. This is a DRIED preserved fish, still holding the "
        "flat triggerfish silhouette (broad body, small tail). "
        "Search: 'cá bò khô Lý Sơn Quảng Ngãi con dẹt'. "
        "NOT shredded grilled fresh fish strips, NOT cá lóc nướng xé, NOT squid jerky, NOT cá sặc khô, "
        "NOT a plate of white flaked cooked fish with nước chấm."
    ),
    "ca-kho-to-ca-loc-tram-den": (
        "IDENTITY: cá lóc or black carp kho tộ — a clay pot of caramelized braised snakehead or black carp, "
        "dark sticky sauce, whole steaks or a section of fish, peppercorns, chili, scallion. "
        "Search: 'cá lóc kho tộ miền Tây'. "
        "NOT cá basa (paler catfish steaks), NOT grilled fish, NOT sweet-sour fried fish."
    ),
    "ca-nuong-truong-sa": (
        "IDENTITY: Trường Sa grilled sea fish — a whole small marine fish grilled over charcoal, "
        "blistered skin, salt-chili crust, charred fins, island-fisherman look. One whole fish, "
        "not a mixed seafood platter. "
        "Search: 'cá biển nướng muối ớt'. "
        "NOT salmon fillet, NOT cá suối nướng mắc khén (stream fish, highland), NOT sushi."
    ),
    "ca-suoi-nuong-son-la": (
        "IDENTITY: Sơn La grilled stream fish — small freshwater river fish grilled, dusted with "
        "mắc khén (Sichuan-pepper-like spice, brown specks), smoky highland look, maybe beside a "
        "little xôi. Smaller and darker than sea fish. "
        "Search: 'cá suối nướng mắc khén Sơn La'. "
        "NOT sea fish, NOT cá kho tộ, NOT trout amandine."
    ),
    "canh-chua-ca-loc-nam-bo": (
        "IDENTITY: Nam Bộ canh chua cá lóc — a clear sour soup in a bowl: tamarind-sour broth, "
        "snakehead fish pieces, pineapple, tomato, bean sprouts, elephant-ear stem (bạc hà), "
        "rice paddy herb (ngò ôm), red chili. Bright, sour, many vegetables. "
        "Search: 'canh chua cá lóc miền Tây'. "
        "NOT tom yum, NOT canh chua miền Bắc sấu, NOT cá kho."
    ),
    "canh-cua-mong-toi-rau-day": (
        "IDENTITY: Northern summer soup — a light bowl of freshwater-crab broth with viscous green "
        "malabar spinach (mồng tơi) and jute (rau đay), tiny crab paste, very green and slippery-looking. "
        "Search: 'canh cua mồng tơi rau đay'. "
        "NOT bún riêu, NOT canh chua, NOT spinach cream soup."
    ),
    "canh-suon-nau-chua-sau-me": (
        "IDENTITY: Hà Nội canh sườn chua — pork-rib sour soup with sấu (Dracontomelon, small brown-green "
        "sour fruit) or tamarind, tomato, rib bones visible in a clear sour broth. Northern home soup. "
        "Search: 'canh sườn nấu sấu Hà Nội'. "
        "NOT canh chua cá miền Nam, NOT pork-bone ramen, NOT canh khổ qua."
    ),
    "cao-lau-hoi-an": (
        "IDENTITY: Hội An cao lầu — short THICK chewy TAN noodles, almost square-cut in cross-section "
        "(lye-water rice noodles, khaki-brown, NOT round Japanese udon, NOT yellow mì Quảng). "
        "VERY LITTLE dark soy-ish broth — a dry-ish bowl, noodles not swimming. Toppings: slices of "
        "xá xíu roast pork, a handful of crispy fried noodle SQUARES (croutons of the same noodle), "
        "lots of lettuce and raw herbs. Optional lime wedge. "
        "Search: 'cao lầu Hội An sợi dày xá xíu da giòn'. "
        "NOT udon, NOT ramen, NOT wonton chips, NOT peanuts, NOT mì Quảng (yellow flat noodles, shrimp, "
        "peanuts, bánh tráng mè, more broth)."
    ),
    "cha-ca-la-vong": (
        "IDENTITY: Hà Nội chả cá Lã Vọng — turmeric-yellow grilled fish chunks (cá lăng) piled with "
        "masses of fresh dill and green onion, a little oil, served with white vermicelli and roasted "
        "peanuts nearby. The dill is essential. "
        "Search: 'chả cá Lã Vọng thì là nghệ'. "
        "NOT fish and chips, NOT chả cá Nha Trang fried cakes, NOT Indian fish curry."
    ),
    "cha-la-lot-ran": (
        "IDENTITY: Northern chả lá lốt — several small cylindrical or oval pork patties each fully wrapped "
        "in a dark-green betel leaf (lá lốt), pan-fried shiny and blistered, arranged on a plate. "
        "Search: 'chả lá lốt rán'. "
        "NOT grape-leaf dolma, NOT nem nướng, NOT bánh xèo."
    ),
    "cha-muc-ha-long": (
        "IDENTITY: Hạ Long chả mực — thick fried squid patties, golden-brown crust, irregular handmade "
        "shape from pounded squid (visible white squid bits), sliced to show the dense white interior. "
        "Search: 'chả mực Hạ Long giã tay'. "
        "NOT fish cake, NOT calamari rings, NOT chả cá."
    ),
    "chao-luon-nghe-an": (
        "IDENTITY: Nghệ An cháo lươn — a bowl of thick rice porridge, topped with stir-fried eel pieces "
        "in lemongrass-galangal, fried shallots, herbs, pepper. Brownish eel on white-beige cháo. "
        "Search: 'cháo lươn Nghệ An'. "
        "NOT Chinese fish congee, NOT súp lươn (clear soup), NOT risotto."
    ),
    "com-ga-hoi-an": (
        "IDENTITY: Hội An cơm gà — a plate of TURMERIC-YELLOW chicken rice, shredded poached chicken "
        "with pale skin, pickled shredded vegetables (đồ chua), a small bowl of ginger fish sauce. "
        "Rice is yellow, not white. "
        "Search: 'cơm gà Hội An cơm vàng'. "
        "NOT Hainanese chicken rice (different garnish), NOT cơm tấm, NOT chicken biryani."
    ),
    "com-hen-hue": (
        "IDENTITY: Huế cơm hến — a plate of room-temperature broken/white rice topped with tiny baby clams "
        "(hến), crushed peanuts, crispy rice paper shards (bánh đa), pork rinds, chili, herbs, a little "
        "clam broth on the side. Mixed dry rice, not a soup. "
        "Search: 'cơm hến Huế đậu phộng bánh đa'. "
        "NOT clam chowder, NOT cơm gà, NOT cơm tấm."
    ),
    "com-lam-dak-lak": (
        "IDENTITY: Đắk Lắk cơm lam — glutinous rice cooked inside charred BAMBOO TUBES. Show 2–3 tubes, "
        "one split open to reveal the white sticky rice cylinder with the bamboo-joint imprint. "
        "Highland, smoky. "
        "Search: 'cơm lam Tây Nguyên ống tre'. "
        "NOT sushi, NOT bánh tét, NOT plain steamed rice in a bowl."
    ),
    "com-tam-sai-gon": (
        "IDENTITY: Sài Gòn cơm tấm — a plate of broken rice (small separate grains, not jasmine mounds), "
        "ONE grilled pork chop (sườn nướng) with grill marks, scallion-oil, sliced cucumber, tomato, "
        "pickled carrot-daikon, a small chả egg or not required. Street-lunch plate. "
        "Search: 'cơm tấm Sài Gòn sườn nướng'. "
        "NOT cơm tấm sườn bì chả đầy đủ (that is the next item — do NOT add bì AND chả here), "
        "NOT cơm gà Hội An yellow rice, NOT bibimbap."
    ),
    "com-tam-suon-bi-cha-day-du": (
        "IDENTITY: cơm tấm sườn bì chả đầy đủ — broken rice with ALL THREE toppings: grilled pork chop, "
        "shredded skin-and-ear pork floss (bì — pale white strands with roasted rice powder), and a "
        "slice of steamed egg meatloaf (chả trứng — yellow with specks). Cucumber, pickles, scallion oil. "
        "The fullest Sài Gòn plate. "
        "Search: 'cơm tấm sườn bì chả trứng'. "
        "NOT a plate with only the pork chop, NOT cơm gà, NOT Korean pork cutlet."
    ),
    "com-trang-gao-te": (
        "IDENTITY: a mound of COOKED Vietnamese white jasmine rice (cơm tẻ) — fluffy separate long grains, "
        "steamed, slightly glossy, sitting as a neat compact mound on white. Cooked rice only. "
        "Search: 'cơm trắng gạo tẻ'. "
        "NOT uncooked raw grains, NOT xôi sticky rice, NOT fried rice, NOT brown rice."
    ),
    "dau-phu-sot-ca-chua": (
        "IDENTITY: Northern home tofu in tomato sauce — golden-fried tofu cubes in a chunky cooked-tomato "
        "sauce, scallion, on a plate. Red sauce, white-gold tofu. "
        "Search: 'đậu phụ sốt cà chua'. "
        "NOT mapo tofu, NOT raw tofu, NOT đậu hũ nhồi thịt unless stuffing is visible — this is sauce-coated cubes."
    ),
    "dau-phu-tam-hanh-ran": (
        "IDENTITY: đậu phụ tẩm hành rán — fried tofu with a coating of chopped scallion, golden, "
        "savory oil, no tomato. "
        "Search: 'đậu phụ tẩm hành rán'. "
        "NOT đậu sốt cà, NOT agedashi tofu, NOT tofu salad."
    ),
    "de-nui-ninh-binh": (
        "IDENTITY: Ninh Bình mountain goat — a serving of goat meat, typically tái chanh (rare lime-cured "
        "thin slices, pink-brown) OR steamed with perilla, rustic, herbs, clearly GOAT (not beef), "
        "maybe a few bones. "
        "Search: 'dê núi Ninh Bình tái chanh'. "
        "NOT lamb chops Western, NOT bò lúc lắc, NOT whole roast kid."
    ),
    "ga-dong-tao-hung-yen": (
        "IDENTITY: Hưng Yên gà Đông Tảo — a WHOLE poached chicken whose legs/feet are famously HUGE, "
        "thick, scaly, oversized dragon-chicken feet. Pale yellow skin, chopped or whole so the giant "
        "feet are unmistakable. "
        "Search: 'gà Đông Tảo luộc chân to'. "
        "NOT ordinary gà ta, NOT fried chicken, NOT roast duck."
    ),
    "ga-nuong-gia-lai": (
        "IDENTITY: Gia Lai / Tây Nguyên grilled chicken — a spatchcocked or chopped gà nướng muối ớt, "
        "charred skin, highland chili-salt, often with a bamboo tube of cơm lam nearby. Smoky. "
        "Search: 'gà nướng Tây Nguyên muối ớt cơm lam'. "
        "NOT Korean fried chicken, NOT gà Đông Tảo boiled, NOT rotisserie supermarket chicken."
    ),
    "ga-rang-gung-la-chanh": (
        "IDENTITY: Northern gà rang gừng — bite-size chicken pieces wok-tossed until caramel-brown, "
        "lots of shredded ginger, kaffir lime leaves, glossy savory-sweet glaze, on a plate. "
        "Search: 'gà rang gừng lá chanh'. "
        "NOT Thai basil chicken, NOT roast whole chicken, NOT gà nướng."
    ),
    "goi-cuon-tom-thit": (
        "IDENTITY: Southern gỏi cuốn — several fresh (NOT fried) rice-paper rolls, translucent, showing "
        "whole shrimp pink against the wrapper, pork slices, vermicelli, herbs, lettuce inside. "
        "Cut one roll to show the spiral. "
        "Search: 'gỏi cuốn tôm thịt'. "
        "NOT fried chả giò/nem rán, NOT sushi, NOT summer rolls without shrimp."
    ),
    "hai-san-hoang-sa": (
        "IDENTITY: Hoàng Sa sea catch as a simple grilled/steamed seafood set — prawns, squid, and a "
        "small reef fish, charcoal-grilled or salt-steamed, island-fisherman style, clustered as one "
        "serving on white. Fresh marine, not mixed Vietnamese street food. "
        "Search: 'hải sản nướng tôm mực cá biển'. "
        "NOT sashimi platter, NOT phở, NOT lobster thermidor, NOT a huge mixed hotpot."
    ),
    "hu-tieu-my-tho": (
        "IDENTITY: Mỹ Tho hủ tiếu — a bowl of Southern rice noodles (hủ tiếu, slightly chewy, not phở) "
        "in a clear pork-bone broth, toppings of shrimp, sliced pork, liver, garlic, scallion, celery leaf. "
        "Mekong Delta breakfast. "
        "Search: 'hủ tiếu Mỹ Tho tôm thịt gan'. "
        "NOT phở Hà Nội, NOT hủ tiếu Nam Vang khô (dry), NOT wonton mee."
    ),
    "hu-tieu-nam-vang-kho": (
        "IDENTITY: hủ tiếu Nam Vang KHÔ (dry) — noodles NOT swimming in broth: chewy hủ tiếu tossed with "
        "dark soy-garlic oil, toppings of shrimp, minced pork, liver, quail egg, garlic, chili, a small "
        "separate bowl of clear broth on the side. "
        "Search: 'hủ tiếu Nam Vang khô'. "
        "NOT the soup version (nước), NOT phở, NOT pad thai."
    ),
    "hu-tieu-nam-vang-nuoc": (
        "IDENTITY: hủ tiếu Nam Vang NƯỚC — noodles IN a clear sweet pork broth, shrimp, sliced pork, "
        "liver, minced pork, garlic, celery, sometimes a split quail egg. Broth fills the bowl. "
        "Search: 'hủ tiếu Nam Vang nước'. "
        "NOT the dry khô version, NOT phở, NOT hủ tiếu Mỹ Tho only (similar but this has the Nam Vang topping mix)."
    ),
    "lau-ca-linh-dong-thap": (
        "IDENTITY: Đồng Tháp lẩu cá linh bông điên điển — a hotpot: small silver linh fish, yellow "
        "sesbania flowers (bông điên điển), herbs, a bubbling light sour-savory broth in a metal/clay pot. "
        "Flood-season Mekong look. "
        "Search: 'lẩu cá linh bông điên điển Đồng Tháp'. "
        "NOT lẩu mắm (dark fermented), NOT Chinese spicy hotpot, NOT canh chua in a small bowl only."
    ),
    "lau-mam-ca-mau": (
        "IDENTITY: Cà Mau lẩu mắm — a hotpot of VERY dark, cloudy fermented-fish broth, mixed Mekong "
        "proteins (shrimp, fish, pork), a mountain of rustic vegetables (water lily, eggplant, herbs). "
        "Darker and funkier-looking than lẩu cá linh. "
        "Search: 'lẩu mắm Cà Mau'. "
        "NOT tom yum, NOT lẩu thái, NOT clear canh chua."
    ),
    "mi-quang-tom-thit-heo-ga": (
        "IDENTITY: Quảng Nam / Đà Nẵng mì Quảng — WIDE FLAT turmeric-YELLOW rice noodles (bánh mì Quảng, "
        "like wide fettuccine of rice, NOT round wheat udon, NOT egg lo mein). Only a SHALLOW pool of "
        "reddish-yellow broth — you should see the yellow noodle sheets, not a deep soup. Toppings: "
        "shrimp AND pork (or chicken), crushed peanuts, herbs, a large toasted sesame rice cracker "
        "(bánh tráng mè) standing in the bowl. "
        "Search: 'mì Quảng tôm thịt sợi dẹt vàng bánh tráng mè'. "
        "NOT Japanese/Chinese egg noodles, NOT udon, NOT cao lầu (tan thick noodles, xá xíu, no shrimp), "
        "NOT a full deep noodle soup."
    ),
    "nem-chua-thanh-hoa": (
        "IDENTITY: Thanh Hóa nem chua — small fermented raw-pork cubes wrapped in đinh lăng leaves "
        "with a slice of garlic and chili, tied. Show a few wrapped packets and one opened pink sour "
        "pork cube. "
        "Search: 'nem chua Thanh Hóa lá đinh lăng'. "
        "NOT fried nem rán, NOT nem nướng grilled sausage, NOT salami."
    ),
    "nem-nuong-nha-trang": (
        "IDENTITY: Nha Trang nem nướng — grilled pork sausages on skewers, reddish-pink, glossy, "
        "served with bánh ướt sheets, pickles, herbs, and a distinctive sweet peanut-fish dipping sauce. "
        "Skewers are the hero. "
        "Search: 'nem nướng Nha Trang xiên'. "
        "NOT nem chua, NOT nem rán fried rolls, NOT Thai sausage, NOT bún chả patties."
    ),
    "nem-ran-cha-gio-chien": (
        "IDENTITY: Northern nem rán / southern-style chả giò — several small golden-fried spring rolls, "
        "crispy blistered rice-paper (or wheat) wrapper, one cut to show glass-noodle, pork, wood-ear filling. "
        "Search: 'nem rán Hà Nội chả giò chiên'. "
        "NOT fresh gỏi cuốn, NOT lumpia jumbo, NOT samosa."
    ),
    "pho-bo-chin-nac": (
        "IDENTITY: Hà Nội phở bò CHÍN nạc — flat bánh phở noodles, CLEAR light-brown beef broth, "
        "toppings ONLY well-done lean brisket slices (chín nạc — fully cooked, no pink, little fat), "
        "scallion, a little cilantro. Simple Hanoi bowl, no bean sprouts in the bowl. "
        "Search: 'phở bò chín nạc Hà Nội'. "
        "NOT tái (rare pink beef), NOT gầu (fatty brisket), NOT Sài Gòn phở with lots of extras, NOT ramen."
    ),
    "pho-bo-ha-noi": (
        "IDENTITY: classic Hà Nội beef phở — flat white rice noodles, crystal-clear pale brown broth, "
        "modest topping of beef, lots of sliced scallion whites, very little herb compared with the South, "
        "no bean sprouts, no hoisin in the bowl. Elegant, sparse, northern. "
        "Search: 'phở Hà Nội nước trong hành hoa'. "
        "NOT phở Sài Gòn (darker, more garnish, bean sprouts), NOT bún bò Huế thick round noodles, NOT ramen."
    ),
    "pho-bo-tai-nam-gau": (
        "IDENTITY: phở bò tái nạm gầu — same Hanoi pho bowl but toppings show THREE beef cuts: "
        "rare pink tái slices on top, well-done nạm (flank), and white-yellow fatty gầu (brisket fat) pieces. "
        "Search: 'phở tái nạm gầu'. "
        "NOT chín-only lean pho, NOT bún bò, NOT a mixed meat stew."
    ),
    "pho-chua-thai-nguyen": (
        "IDENTITY: Thái Nguyên phở CHUA — this is NOT soup pho. Dry mixed sour noodles: wide rice noodles "
        "tossed with a reddish sour-sweet sauce, grilled pork, herbs, peanuts, fried shallots. "
        "Looks like a salad-noodle, no tall broth. "
        "Search: 'phở chua Thái Nguyên'. "
        "NOT Hà Nội beef pho soup, NOT pad thai, NOT phở trộn Sài Gòn exactly — keep the Thái Nguyên sour mix look."
    ),
    "pho-ga-ta-co-da": (
        "IDENTITY: phở gà ta có da — flat noodles, LIGHTER golden chicken broth (not beef-brown), "
        "shredded free-range chicken WITH yellow skin attached, lots of scallion, maybe lime leaf. "
        "Search: 'phở gà ta có da'. "
        "NOT beef pho, NOT Hainan chicken soup, NOT khao man gai rice."
    ),
    "ram-bap-ha-tinh": (
        "IDENTITY: Hà Tĩnh ram bắp — small fried spring rolls whose filling is visibly sweetcorn kernels "
        "with minced pork, golden and crunchy, several pieces, one cut open showing yellow corn. "
        "Search: 'ram bắp Hà Tĩnh'. "
        "NOT nem rán with no corn, NOT Mexican taquito, NOT bánh rán sweet."
    ),
    "rau-muong-luoc-dam-sau-chanh": (
        "IDENTITY: Northern rau muống LUỘC — a pile of BOILED water spinach, still bright green, long "
        "hollow stems clearly visible, not oily, not wok-wilted. Served as a simple vegetable plate "
        "with a SMALL SAUCER of crushed sấu (or lime) + fish sauce + chili on the SIDE for dipping — "
        "the greens themselves are not swimming in brown stir-fry sauce. "
        "Search: 'rau muống luộc dầm sấu Hà Nội'. "
        "NOT rau muống xào tỏi (oily wilted garlic stir-fry — that is a different catalog item), "
        "NOT snails/ốc, NOT mushrooms, NOT Thai kangkung, NOT a wet mixed salad."
    ),
    "rau-muong-xao-toi": (
        "IDENTITY: rau muống xào tỏi — wok-fried water spinach, wilted dark-green leaves, garlic bits, "
        "glossy oil, on a plate. Classic Vietnamese stir-fry. "
        "Search: 'rau muống xào tỏi'. "
        "NOT the boiled dầm sấu version, NOT kangkung belacan unless garlic-only, NOT salad."
    ),
    "thang-co-lai-chau": (
        "IDENTITY: Lai Châu thắng cố — a highland hotpot/stew of mixed horse or beef offal and meat in a "
        "dark spice broth (thảo quả, cinnamon), rustic, lots of innards, served in a communal pot. "
        "Mountain-market look. "
        "Search: 'thắng cố Lai Châu'. "
        "NOT phở, NOT Korean soondae soup, NOT clear bone broth."
    ),
    "thit-ba-chi-rang-chay-canh": (
        "IDENTITY: ba chỉ rang cháy cạnh — pork belly cubes fried until the edges are dark-crisp (cháy cạnh), "
        "glazed with fish sauce, lots of green onion, caramel-brown, on a plate. "
        "Search: 'thịt ba chỉ rang cháy cạnh'. "
        "NOT thịt kho tàu (braised in coconut, whole eggs), NOT bacon, NOT lechon kawali pile only."
    ),
    "thit-chan-gio-luoc": (
        "IDENTITY: boiled pork hock — a chunk of giò heo with skin, pale gelatinous skin, pink meat, "
        "bone, sliced, served with fish sauce and maybe pickled veg. Clean boiled look, not roasted. "
        "Search: 'chân giò luộc'. "
        "NOT German pork knuckle roasted crispy, NOT bánh canh giò, NOT ham hock soup."
    ),
    "thit-chua-lao-cai": (
        "IDENTITY: Lào Cai thịt chua — fermented sour pork, pinkish, often in a banana-leaf or rustic pack, "
        "sliced to show the cured texture, highland spice (mắc khén). "
        "Search: 'thịt chua Lào Cai'. "
        "NOT nem chua Thanh Hóa (small leaf cubes), NOT salami, NOT thịt kho."
    ),
    "thit-kho-tau-nuoc-dua": (
        "IDENTITY: Southern thịt kho tàu — pork belly chunks braised in coconut water until caramel-amber, "
        "whole hard-boiled eggs stained brown in the same sauce, lots of sauce in a clay pot or bowl. "
        "Tết/family pot look. "
        "Search: 'thịt kho tàu trứng nước dừa'. "
        "NOT thịt rang cháy cạnh (dry fry, no eggs), NOT adobo (darker soy, no coconut sheen), NOT cà ri."
    ),
    "thit-trau-gac-bep-dien-bien": (
        "IDENTITY: Điện Biên thịt trâu gác bếp — dark smoked strips of buffalo hanging-dried meat, "
        "almost jerky, deep brown-red, dusty with chili and mắc khén, stacked as strips. "
        "Search: 'thịt trâu gác bếp Điện Biên'. "
        "NOT beef jerky supermarket sticks, NOT thịt chua, NOT grilled steak."
    ),
    "vit-quay-7-vi-cao-bang": (
        "IDENTITY: Cao Bằng vịt quay bảy vị — a roast duck with lacquered reddish-brown skin, chopped "
        "into pieces, aromatic herb-spice look, honey glaze sheen. "
        "Search: 'vịt quay bảy vị Cao Bằng'. "
        "NOT Peking duck pancakes, NOT vịt quay Lạng Sơn (very similar but keep Cao Bằng seven-spice glaze), "
        "NOT boiled duck."
    ),
    "vit-quay-lang-son": (
        "IDENTITY: Lạng Sơn roast duck — whole or chopped roast duck, very glossy dark-amber skin, "
        "honey-roasted, northern border style, chopped to show juicy meat. "
        "Search: 'vịt quay Lạng Sơn'. "
        "NOT Cao Bằng seven-spice specifically, NOT Peking duck with pancakes, NOT duck confit."
    ),
}

ORDER = [
    "banh-beo-chen-da-nang",
    "banh-beo-chen-hue-5-chen",
    "banh-bot-loc-hue",
    "banh-can-da-lat",
    "banh-canh-ca-loc",
    "banh-canh-cua-ghe",
    "banh-canh-trang-bang",
    "banh-chung-luoc-truyen-thong",
    "banh-chung-ran",
    "banh-cuon-nong-kem-cha-que",
    "banh-da-cua-hai-phong",
    "banh-gai-tuyen-quang",
    "banh-hoi-long-heo-dong-nai",
    "banh-khot-vung-tau",
    "banh-mi-kep-thit-cha-pate",
    "banh-mi-op-la-2-trung",
    "banh-mi-xiu-mai-trung-muoi",
    "banh-nam-hue",
    "banh-phu-the-bac-ninh",
    "banh-tai-phu-tho",
    "banh-tet-nhan-thit-dau-xanh",
    "banh-tet-vinh-long",
    "banh-trang-nuong-da-lat",
    "banh-uot-long-ga-trung-non",
    "banh-uot-thit-nuong-quang-tri",
    "banh-xeo-mien-tay",
    "banh-xeo-mien-trung-banh-nho",
    "banh-xeo-toc-tien",
    "bo-kho",
    "bo-xao-can-toi-tay",
    "bun-bo-hue-day-du",
    "bun-ca-chau-doc",
    "bun-ca-nha-trang",
    "bun-cha-ca-da-nang",
    "bun-cha-ha-noi",
    "bun-dau-mam-tom",
    "bun-mam",
    "bun-mang-vit",
    "bun-nuoc-leo-can-tho",
    "bun-oc-giam-bong",
    "bun-rieu-cua-dong",
    "bun-thang-ha-noi",
    "bun-thit-nuong",
    "ca-basa-tra-kho-to",
    "ca-bo-kho-quang-ngai",
    "ca-kho-to-ca-loc-tram-den",
    "ca-nuong-truong-sa",
    "ca-suoi-nuong-son-la",
    "canh-chua-ca-loc-nam-bo",
    "canh-cua-mong-toi-rau-day",
    "canh-suon-nau-chua-sau-me",
    "cao-lau-hoi-an",
    "cha-ca-la-vong",
    "cha-la-lot-ran",
    "cha-muc-ha-long",
    "chao-luon-nghe-an",
    "com-ga-hoi-an",
    "com-hen-hue",
    "com-lam-dak-lak",
    "com-tam-sai-gon",
    "com-tam-suon-bi-cha-day-du",
    "com-trang-gao-te",
    "dau-phu-sot-ca-chua",
    "dau-phu-tam-hanh-ran",
    "de-nui-ninh-binh",
    "ga-dong-tao-hung-yen",
    "ga-nuong-gia-lai",
    "ga-rang-gung-la-chanh",
    "goi-cuon-tom-thit",
    "hai-san-hoang-sa",
    "hu-tieu-my-tho",
    "hu-tieu-nam-vang-kho",
    "hu-tieu-nam-vang-nuoc",
    "lau-ca-linh-dong-thap",
    "lau-mam-ca-mau",
    "mi-quang-tom-thit-heo-ga",
    "nem-chua-thanh-hoa",
    "nem-nuong-nha-trang",
    "nem-ran-cha-gio-chien",
    "pho-bo-chin-nac",
    "pho-bo-ha-noi",
    "pho-bo-tai-nam-gau",
    "pho-chua-thai-nguyen",
    "pho-ga-ta-co-da",
    "ram-bap-ha-tinh",
    "rau-muong-luoc-dam-sau-chanh",
    "rau-muong-xao-toi",
    "thang-co-lai-chau",
    "thit-ba-chi-rang-chay-canh",
    "thit-chan-gio-luoc",
    "thit-chua-lao-cai",
    "thit-kho-tau-nuoc-dua",
    "thit-trau-gac-bep-dien-bien",
    "vit-quay-7-vi-cao-bang",
    "vit-quay-lang-son",
]


def main() -> None:
    by = {item["slug"]: item for item in json.loads(SEED.read_text(encoding="utf-8"))}
    missing_look = [s for s in ORDER if s not in LOOK]
    extra_look = [s for s in LOOK if s not in ORDER]
    if missing_look or extra_look:
        raise SystemExit(f"look mismatch missing={missing_look} extra={extra_look}")
    blocks = []
    for i, slug in enumerate(ORDER, 1):
        item = by[slug]
        name = item["name_vi"]
        en = (item.get("name_en") or "").strip()
        title = f"{name}" + (f" / {en}" if en else "")
        prompt = (
            f"[{i}] {title}\n"
            f'Create a professional realistic product photo of the Vietnamese dish "{name}". {BASE} '
            f"{LOOK[slug]}"
        )
        blocks.append(prompt)
    OUT.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"wrote {len(blocks)} prompts -> {OUT}")


if __name__ == "__main__":
    main()
