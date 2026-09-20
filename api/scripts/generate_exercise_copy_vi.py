"""Author beginner-friendly Vietnamese how-to copy for the active catalog."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
META_PATH = ROOT / "api" / "exports" / "_active_exercises_meta.json"
SEED_PATH = ROOT / "seeds" / "exercise_copy_vi.json"
RINGS_PATH = ROOT / "seeds" / "gymnastic_rings_exercises.json"
BAND_PATH = ROOT / "seeds" / "resistance_band_2_exercises.json"

BRACE = "Siết bụng (bụng cứng như sắp bị đấm), vai kéo nhẹ xuống xa tai."
FOOT = "Giữ cả bàn chân trên sàn, hơi nhấn giữa bàn chân và gót — không nhón mũi."


@dataclass
class Copy:
    steps: list[str]
    mistakes: list[str]
    tips: str
    instruction_vi: str


def _n(name: str) -> str:
    return name.lower()


def kind(name: str, equipment: str = "") -> str:
    n = _n(name)
    e = equipment or ""
    if "ring" in n or "gymnastic-rings" in e:
        return "rings"
    if n.startswith("band ") or "resistance-band" in e:
        return "band"
    if "smith" in n:
        return "smith"
    if "cable" in n or "functional-trainer" in e or "lat-pulldown" in e or "seated-row" in e:
        return "cable"
    if "machine" in n:
        return "machine"
    if "kettlebell" in n:
        return "kb"
    if "dumbbell" in n:
        return "db"
    if "ez bar" in n:
        return "ez"
    if "barbell" in n or "trap bar" in n:
        return "bb"
    if "backpack" in n or "ba lô" in n:
        return "pack"
    if "bodyweight" in n or equipment == "":
        return "bw"
    return "other"


def load_word(k: str) -> str:
    return {
        "bb": "thanh tạ",
        "ez": "thanh cong",
        "db": "tạ đơn",
        "kb": "tạ ấm",
        "cable": "tay cầm cáp",
        "smith": "thanh máy trượt",
        "machine": "tay cầm máy",
        "band": "dây kháng lực",
        "rings": "vòng treo",
        "pack": "balo",
        "bw": "thân người",
        "other": "dụng cụ",
    }.get(k, "dụng cụ")


def flags(name: str) -> dict[str, bool]:
    n = _n(name)
    return {
        "incline": "incline" in n or "dốc lên" in n or "dốc cao" in n,
        "decline": "decline" in n,
        "seated": "seated" in n or "ngồi" in n,
        "standing": "standing" in n,
        "single": any(x in n for x in ("single", "one-arm", "unilateral", "một tay", "một chân", "một bên")),
        "close": "close" in n or "narrow" in n or "hẹp" in n,
        "wide": "wide" in n or "rộng" in n,
        "neutral": "neutral" in n or "hammer" in n or "nắm dọc" in n,
        "tempo": "tempo" in n or "chậm" in n or "pause" in n,
        "reverse": "reverse" in n and "lunge" not in n,
        "kneeling": "kneel" in n or "knee" in n and "raise" not in n,
    }


def copy_of(steps: list[str], mistakes: list[str], tips: str, instruction_vi: str) -> Copy:
    steps = [s.strip() for s in steps if s.strip()][:6]
    mistakes = [m.strip() for m in mistakes if m.strip()][:4]
    if len(steps) < 4:
        raise ValueError(f"need 4+ steps, got {len(steps)}: {steps}")
    if len(mistakes) < 2:
        raise ValueError(f"need 2+ mistakes, got {mistakes}")
    return Copy(steps=steps, mistakes=mistakes, tips=tips.strip(), instruction_vi=instruction_vi.strip())


# ---------------------------------------------------------------------------
# Hand-written copy for unusual, high-skill, or easy-to-misunderstand moves
# ---------------------------------------------------------------------------

OVERRIDES: dict[str, Copy] = {}


def _put(name: str, steps: list[str], mistakes: list[str], tips: str, instruction_vi: str) -> None:
    OVERRIDES[name] = copy_of(steps, mistakes, tips, instruction_vi)


def _init_overrides() -> None:
    _put(
        "Wall Sit",
        [
            "Tựa lưng phẳng vào tường, chân bước ra trước, rộng bằng vai.",
            "Trượt lưng xuống đến khi đùi gần song song sàn, gối khoảng 90 độ. Gót dính sàn.",
            BRACE + " Gối đi cùng hướng mũi chân, không sụp vào trong.",
            "Giữ hết thời gian, thở đều. Đứng lên bằng cách trượt lưng lên tường — không thả sập.",
        ],
        [
            "Gối sụp vào trong.",
            "Lưng rời tường, mông tụt.",
            "Gót nhấc, dồn mũi chân.",
        ],
        "Giữ sạch ngắn hơn giữ xấu dài. Gối đau thì đứng cao hơn (góc gối lớn hơn 90 độ).",
        "Ngồi tựa tường: lưng dán tường, đùi gần song song, giữ yên. Đây là bài giữ, không phải ngồi xổm lên xuống.",
    )
    _put(
        "Split Squat Isometric Hold",
        [
            "Bước chân trước–sau, khoảng cách vừa để hạ được gối sau gần sàn.",
            "Hạ xuống tư thế chùng chân và giữ yên. Thân hơi thẳng. " + BRACE,
            "Gối trước theo mũi chân, không sụp. Gót trước dính sàn.",
            "Thở đều đến hết thời gian. Đứng lên, đổi bên. Không đứng–ngồi liên tục.",
        ],
        [
            "Gối trước sụp vào trong.",
            "Cúi gù lưng.",
            "Đứng lên giữa chừng làm mất bài giữ.",
        ],
        "Thu ngắn bước nếu gối đau. Giữ sạch quan trọng hơn hạ thật sâu.",
        "Giữ tư thế chùng chân trước–sau, không lên xuống. Tập sức bền chân và ổn định gối.",
    )
    _put(
        "Wall Push-up",
        [
            "Đứng cách tường khoảng nửa bước, hai bàn tay đặt trên tường ngang ngực, rộng bằng vai.",
            "Chân đứng vững, thân từ tai đến mắt cá thành một đường thẳng. " + BRACE,
            "Gập khuỷu, hạ ngực về tường chậm; khuỷu chếch ra khoảng 45 độ, không xòe ngang vai.",
            "Khi ngực gần tường, đẩy tường ra để duỗi tay. Không nhún vai lên tai.",
            "Thở ra khi đẩy. Lặp lại, giữ hông không gãy gập.",
        ],
        [
            "Nhún vai lên tai khi mệt, làm vai làm việc thay ngực.",
            "Gãy hông (mông thụt hoặc ưỡn) thay vì thân thẳng.",
            "Đứng quá gần tường nên gần như không hạ được người.",
        ],
        "Càng lùi chân ra sau bài càng nặng. Còn dễ thì chuyển sang chống đẩy tay trên ghế hoặc bàn.",
        "Chống đẩy trên tường để học thân thẳng và hạ ngực có kiểm soát. Đây là bước đầu trước khi chống đẩy dưới sàn.",
    )
    _put(
        "Pull-up Bar Inverted Row",
        [
            "Nắm xà thấp (hoặc vòng/xà ngang tầm ngực), nằm ngửa bên dưới, thân thẳng, gót chống sàn.",
            BRACE + " Kéo bả vai xuống xa tai trước khi gập khuỷu.",
            "Kéo ngực về phía xà, siết lưng giữa. Khuỷu đi sát sườn.",
            "Dừng ngắn khi ngực gần xà, rồi hạ chậm đến tay gần thẳng — không thả võng.",
            "Giữ hông thẳng với vai; không để mông sệ xuống sàn.",
        ],
        [
            "Kéo bằng cằm và cổ thay vì kéo ngực về xà.",
            "Hông sệ, biến bài thành nằm võng.",
            "Rụt vai lên tai, mất chỗ cho cơ lưng.",
        ],
        "Muốn dễ hơn: đứng cao hơn (thân gần đứng). Muốn khó hơn: hạ xà hoặc đưa chân ra xa.",
        "Nằm kéo ngực về xà thấp. Bài này dạy kéo lưng trước khi bạn làm được kéo xà.",
    )
    _put(
        "Hollow Body Hold",
        [
            "Nằm ngửa, ép thắt lưng sát sàn (không còn khe hở).",
            "Tay với ra sau đầu, chân duỗi thấp. Nhấc vai và chân khỏi sàn một chút.",
            "Giữ hình thuyền: xương sườn hạ, bụng siết, thở đều bằng mũi.",
            "Nếu thắt lưng bật khỏi sàn, nâng chân cao hơn hoặc gập gối.",
            "Giữ đến hết thời gian; hạ xuống khi không còn ép được lưng sát sàn.",
        ],
        [
            "Thắt lưng võng khỏi sàn — lúc đó bụng không còn làm việc đúng.",
            "Nín thở đến đỏ mặt.",
            "Nhấc chân quá thấp khi chưa giữ được lưng.",
        ],
        "Ưu tiên lưng dán sàn hơn chân thấp. Người mới có thể gập gối 90 độ.",
        "Nằm giữ thân hình thuyền, thắt lưng luôn sát sàn. Đây là nền tảng siết bụng cho chống đẩy và kéo xà.",
    )
    _put(
        "Backpack Good Morning",
        [
            "Ôm balo trước ngực (an toàn hơn để sau gáy). Chân rộng bằng vai, gối hơi mềm.",
            BRACE + " Lưng thẳng như một tấm ván.",
            "Đẩy hông ra sau, thân cúi về trước đến khi cảm giác căng sau đùi.",
            "Không để lưng tròn. Dừng trước khi mất thẳng lưng.",
            "Đẩy hông ra trước để đứng lên, siết mông ở đỉnh.",
        ],
        [
            "Cong lưng khi cúi — đây là lỗi dễ đau thắt lưng nhất.",
            "Gập gối quá sâu biến bài thành ngồi xổm.",
            "Cúi quá thấp khi sau đùi chưa đủ dài.",
        ],
        "Chỉ cúi đến mức lưng còn thẳng. Balo nhẹ trước; tăng dần khi động tác đã sạch.",
        "Cúi người bằng hông, lưng thẳng, để tập mặt sau đùi và mông với balo.",
    )
    _put(
        "Backpack Single-leg Romanian Deadlift",
        [
            "Đứng một chân trụ, gối trụ hơi mềm. Ôm balo trước ngực.",
            "Đẩy hông ra sau, thân cúi, chân sau duỗi ra sau như kim đồng hồ.",
            "Lưng thẳng, hông vuông với sàn — không xoay mông ra ngoài.",
            "Hạ đến khi thân gần song song hoặc đến lúc mất thăng bằng có kiểm soát.",
            "Đẩy gót trụ xuống sàn để đứng lên, siết mông chân trụ.",
        ],
        [
            "Xoay hông mở ra ngoài, làm lệch lưng.",
            "Cong lưng để với balo xuống thấp hơn.",
            "Khóa cứng gối trụ.",
        ],
        "Giữ nhẹ ngón chân sau trên sàn (kiểu chân trụ) nếu chưa giữ được thăng bằng một chân.",
        "Gập hông một chân với balo để tập thăng bằng, mông và mặt sau đùi.",
    )
    _put(
        "1/3 Pull-up",
        [
            "Nắm xà, treo người, tay gần thẳng, vai kéo xuống xa tai (treo chủ động).",
            "Kéo người lên chỉ khoảng 1/3 quãng đường — khuỷu hơi gập, ngực hướng xà.",
            "Dừng 1 giây ở đỉnh đoạn ngắn này, siết lưng.",
            "Hạ chậm về tay gần thẳng, vẫn giữ vai không nhún lên tai.",
            "Xuống đất ngay nếu vai hoặc khuỷu đau nhói.",
        ],
        [
            "Nhún vai lên tai rồi giật người.",
            "Kéo cằm bằng cổ thay vì kéo lưng.",
            "Đá chân lấy đà khi chưa kiểm soát được thân.",
        ],
        "Nếu chưa kéo được: dùng ghế bật nhẹ lên rồi hạ chậm, hoặc làm kéo người nằm trước.",
        "Kéo xà một đoạn ngắn từ tư thế treo chủ động. Mục tiêu là học siết lưng, không phải hoàn thành một cái kéo xà đầy đủ.",
    )
    _put(
        "Bodyweight Squat",
        [
            "Đứng chân rộng bằng vai, mũi chân hơi xoay ra. Tay đưa ra trước để thăng bằng.",
            BRACE + " " + FOOT,
            "Đẩy hông ra sau rồi ngồi xuống như ngồi vào ghế thấp.",
            "Hạ đến đùi gần song song sàn (hoặc sâu hơn nếu gót không nhấc và lưng không tròn). Gối đi cùng hướng mũi chân.",
            "Đẩy sàn để đứng lên, siết mông ở đỉnh. Không khóa gối giật.",
        ],
        [
            "Gối sụp vào trong.",
            "Gót nhấc khỏi sàn.",
            "Cong lưng hoặc cúi ngực sấp khi xuống sâu.",
        ],
        "Nếu gót nhấc: mở mũi chân ra một chút hoặc ngồi lên hộp/ghế phía sau. Không dồn hết lực lên mũi chân.",
        "Ngồi xổm không tạ: hông ra sau, gối theo mũi chân, cả bàn chân trên sàn. Đây là nền cho mọi biến thể ngồi xổm có tạ.",
    )
    _put(
        "Barbell Squat",
        [
            "Đặt thanh trên cơ xô trên (không để lên cổ). Tay nắm thanh vừa tầm, bả vai siết lại.",
            "Bước ra, chân rộng bằng vai, mũi hơi xoay ra. " + BRACE,
            "Hít, siết bụng, đẩy hông ra sau và ngồi xuống. " + FOOT,
            "Hạ đến đùi gần song song hoặc sâu hơn nếu lưng còn thẳng và gối ổn.",
            "Đẩy sàn đứng lên, hông và gối duỗi cùng lúc. Thở ra gần đỉnh.",
        ],
        [
            "Thanh trượt lên cổ, gây đau đốt sống cổ.",
            "Gối sụp vào trong khi đứng lên.",
            "Cong thắt lưng ở đáy.",
        ],
        "Học ngồi xổm không tạ và ôm tạ trước ngực trước khi chất tạ nặng. Nếu gót nhấc, giảm độ sâu.",
        "Ngồi xổm tạ đòn sau vai. Giữ lưng thẳng, gối theo mũi chân, đứng lên bằng cả bàn chân.",
    )
    _put(
        "Barbell Deadlift",
        [
            "Đứng chân rộng bằng hông, thanh tạ nằm trên giữa bàn chân, ống chân sát thanh.",
            "Hông đẩy ra sau, nắm thanh ngoài gối, lưng thẳng, ngực ưỡn nhẹ, nách siết.",
            "Kéo căng tay (kéo hết độ chùng của thanh) rồi hít, siết bụng.",
            "Đẩy sàn bằng chân, thanh luôn sát ống chân. Vai và hông lên cùng nhịp.",
            "Đứng thẳng, siết mông — không ưỡn thắt lưng ra sau. Hạ: hông ra sau trước, gối gập sau.",
        ],
        [
            "Cong lưng khi nhấc — dừng set, giảm tạ.",
            "Thanh tạ trôi xa ống chân.",
            "Giật thanh trước khi kéo hết độ chùng.",
        ],
        "Tạ phải cho phép lưng thẳng mọi rep. Ống chân sát thanh suốt đường đi.",
        "Nhấc tạ đòn từ đất bằng chân và hông, lưng thẳng, thanh sát người. Không dùng lưng cong để 'vớt' tạ.",
    )
    _put(
        "Barbell Bench Press",
        [
            "Nằm trên ghế, mắt dưới thanh tạ. Chân đặt chắc trên sàn. Kéo bả vai xuống và lại gần nhau.",
            "Nắm thanh rộng hơn vai một chút, cổ tay thẳng trên khuỷu. Nhấc thanh khỏi giá, giữ trên ngực.",
            BRACE + " Hạ thanh chậm về vùng ngực giữa–dưới.",
            "Khuỷu không xòe 90 độ; để khoảng 45–75 độ so với thân. Thanh chạm ngực nhẹ, không nảy.",
            "Đẩy thanh lên trên (hơi về phía giá), thở ra. Không đập khuỷu khóa cứng.",
        ],
        [
            "Khuỷu xòe ngang vai, dễ đau khớp vai.",
            "Nảy thanh trên ngực.",
            "Trượt mông khỏi ghế hoặc ưỡn cổ quá mức.",
        ],
        "Cần người đứng hỗ trợ khi tạ nặng. Nếu vai khó chịu, thu hẹp tay nắm một chút.",
        "Nằm đẩy tạ đòn: bả vai ổn định, hạ có kiểm soát về ngực, đẩy lên không nảy tạ.",
    )
    _put(
        "Pull Ups",
        [
            "Nắm xà sấp tay (lòng bàn tay ra trước), rộng hơn vai một chút. Treo chủ động: vai kéo xuống xa tai.",
            "Siết bụng, chân duỗi hoặc hơi gập, không đung đưa.",
            "Kéo khuỷu xuống dưới, ngực hướng lên xà, đến khi cằm qua xà.",
            "Hạ chậm đến tay gần thẳng, vẫn giữ vai không thả võng.",
            "Dừng nếu đau nhói vai. Không giật cổ để cằm qua xà.",
        ],
        [
            "Nhún vai rồi đá chân lấy đà.",
            "Kéo cằm bằng cổ.",
            "Thả người rơi tự do khi hạ.",
        ],
        "Chưa làm được rep đầy đủ: dùng dây trợ lực, kéo người nằm, hoặc hạ chậm từ trên xuống.",
        "Kéo xà sấp tay từ treo chủ động đến cằm qua xà, hạ chậm. Ưu tiên thân ổn định hơn số cái.",
    )
    _put(
        "Push Up",
        [
            "Plank cao: tay dưới vai, thân thẳng từ đầu đến gót. " + BRACE,
            "Hạ ngực xuống giữa hai tay, khuỷu chếch 30–45 độ, không xòe ngang.",
            "Hạ đến ngực gần sàn (hoặc đến tầm kiểm soát). Không để hông sệ hay mông chổng.",
            "Đẩy sàn để duỗi tay, vai không nhô lên tai.",
            "Thở ra khi đẩy. Nếu chưa làm được: chống gối hoặc tay trên ghế.",
        ],
        [
            "Hông sệ, ưỡn thắt lưng.",
            "Khuỷu xòe 90 độ, vai chịu lực xấu.",
            "Chỉ gập cổ xuống sàn thay vì hạ cả thân.",
        ],
        "Giữ thân như tấm ván. Tay trên ghế dễ hơn; chân trên ghế khó hơn.",
        "Chống đẩy sàn: thân thẳng, hạ ngực giữa hai tay, đẩy lên. Đây là bài đẩy ngang cơ bản không tạ.",
    )
    _put(
        "Jumping Jack",
        [
            "Đứng thẳng, chân gần nhau, tay thả dọc người. Gối luôn hơi mềm, không khóa cứng.",
            "Nhảy nhẹ, dang chân rộng hơn hông đồng thời vung tay lên trên đầu.",
            "Tiếp đất cả bàn chân, gối hấp thụ — không tiếp đất gối thẳng.",
            "Nhảy thu chân vào, hạ tay về dọc người.",
            "Giữ nhịp đều. Giảm biên độ nếu hụt hơi hoặc đau gối.",
        ],
        [
            "Tiếp đất gối thẳng.",
            "Tập trên nền trơn hoặc quá cứng khi khớp gối đang đau.",
            "Nín thở khi tăng tốc.",
        ],
        "Làm chậm, không cần nhảy cao. Có thể bước dang chân thay vì nhảy nếu khớp gối khó chịu.",
        "Nhảy dang chân và vung tay lên đầu theo nhịp. Dùng để khởi động hoặc tăng nhịp tim, tiếp đất mềm.",
    )
    _put(
        "Mountain Climber",
        [
            "Vào plank cao, tay dưới vai, thân thẳng. " + BRACE,
            "Đưa một gối về phía ngực, mũi chân chạm nhẹ hoặc lướt sát sàn — hông không nhảy lên.",
            "Đổi chân nhanh nhưng kiểm soát, như đang chạy tại chỗ ở tư thế plank.",
            "Giữ vai ổn định trên cổ tay. Không để mông chổng cao.",
            "Thở đều. Giảm tốc nếu mất tư thế plank.",
        ],
        [
            "Hông nhảy lên xuống, mất plank.",
            "Vai trôi về trước quá cổ tay.",
            "Chỉ đung đưa chân cho có nhịp, bụng không siết.",
        ],
        "Làm chậm và sạch trước khi làm nhanh. Có thể chống tay trên ghế cho dễ.",
        "Plank cao xen kẽ kéo gối về ngực. Mục tiêu là bụng và vai ổn định, không phải giật càng nhanh càng tốt.",
    )
    _put(
        "Front Plank on Elbows",
        [
            "Chống cẳng tay và mũi chân. Khuỷu dưới vai, cẳng tay song song hoặc tay đan.",
            BRACE + " Siết mông nhẹ để hông không sệ.",
            "Thân thẳng từ đầu đến gót. Nhìn xuống sàn, cổ trung lập.",
            "Thở chậm. Nếu hông sệ hoặc mông chổng, dừng set.",
            "Giữ hết thời gian rồi hạ gối xuống, không thả sập.",
        ],
        [
            "Hông sệ, ưỡn thắt lưng.",
            "Mông chổng cao, bụng nghỉ.",
            "Nhún vai lên tai.",
        ],
        "Người mới chống gối. Chất lượng tư thế quan trọng hơn giữ lâu.",
        "Chống khuỷu giữ thân thẳng. Dừng khi không còn giữ được hông ngang.",
    )
    _put(
        "Hand Plank",
        [
            "Chống thẳng tay, cổ tay dưới vai, thân thẳng như chống đẩy ở đỉnh.",
            BRACE + " Siết mông nhẹ.",
            "Không khóa khuỷu giật; giữ khuỷu mềm. Nhìn xuống sàn.",
            "Thở đều. Dừng nếu cổ tay đau — chuyển sang chống khuỷu.",
            "Hạ gối khi mất thẳng thân.",
        ],
        [
            "Hông sệ hoặc mông chổng.",
            "Khóa khuỷu cứng, đẩy lực vào khớp.",
            "Đầu ngẩng lên làm căng cổ.",
        ],
        "Nếu cổ tay khó chịu, chống nắm đấm hoặc chuyển plank khuỷu.",
        "Plank chống thẳng tay. Giữ thân ván, vai trên cổ tay.",
    )
    _put(
        "Elbow Side Plank",
        [
            "Nằm nghiêng, chống khuỷu dưới vai, cẳng tay vuông góc thân. Chân chồng hoặc chân trên đặt trước.",
            "Nâng hông khỏi sàn, thân thành đường thẳng. Vai không nhún lên tai.",
            "Siết mông và cạnh sườn. Thở đều.",
            "Giữ. Hạ hông có kiểm soát khi hết thời gian, rồi đổi bên.",
        ],
        [
            "Hông xoay úp xuống sàn.",
            "Khuỷu trượt ra trước vai.",
            "Đầu thõng làm căng cổ.",
        ],
        "Chống gối nếu chưa nâng được hông thẳng. Làm đều hai bên.",
        "Chống khuỷu nghiêng, nâng hông, giữ thân thẳng để tập cạnh sườn.",
    )
    _put(
        "Lat Pulldown",
        [
            "Ngồi máy kéo xô, kẹp đùi dưới đệm. Nắm thanh rộng, lòng bàn tay ra trước.",
            "Ngồi thẳng, hơi ngả sau rất nhẹ. Tay duỗi, vai kéo xuống xa tai trước khi gập khuỷu.",
            "Kéo thanh về xương đòn / ngực trên. Khuỷu đi xuống dưới, không ra sau đầu.",
            "Siết xô (cảm giác hai bên sườn sau). Không kéo thanh ra sau gáy.",
            "Để thanh lên chậm đến tay gần thẳng, vẫn giữ vai không thả võng.",
        ],
        [
            "Kéo thanh ra sau gáy.",
            "Ngả người quá nhiều biến thành chèo ngang.",
            "Giật người lấy đà.",
        ],
        "Kéo về ngực, không về gáy. Nếu vai khó chịu, nắm hẹp hơn hoặc nắm dọc.",
        "Ngồi kéo thanh cáp cao về ngực trên. Học kéo xô trước khi làm kéo xà.",
    )
    _put(
        "Behind-the-Neck Press",
        [
            "Ngồi hoặc đứng, thanh sau đầu ở độ cao tai, nắm rộng hơn vai.",
            "Chỉ làm bài này nếu vai và ngực đã mềm, không đau. " + BRACE,
            "Đẩy thanh lên trên đầu đến tay gần thẳng, không ưỡn thắt lưng.",
            "Hạ thanh về sau đầu chỉ đến ngang tai — không ép xuống thấp hơn khi vai căng.",
            "Dừng ngay nếu đau nhói phía trước vai. Người mới nên chọn đẩy vai trước mặt.",
        ],
        [
            "Hạ quá thấp sau gáy khi vai chưa đủ mềm.",
            "Ưỡn thắt lưng để đẩy tạ lên.",
            "Làm khi đang đau vai.",
        ],
        "Phần lớn người mới nên đẩy vai trước mặt thay bài này. Nếu vẫn làm: tạ nhẹ, biên độ ngắn.",
        "Đẩy tạ từ sau gáy lên trên đầu. Khớp vai phải đủ mềm; nếu đau thì đổi sang đẩy trước mặt.",
    )
    _put(
        "Barbell Upright Row",
        [
            "Đứng, nắm thanh trước đùi, tay hẹp hơn vai. " + BRACE,
            "Kéo thanh dọc thân lên, khuỷu dẫn, đến khoảng ngang ngực giữa.",
            "Không kéo cao hơn vai nếu vai bị cấn. Cổ tay không gãy gập.",
            "Hạ chậm về đùi. Không đung đưa thân.",
        ],
        [
            "Kéo thanh lên tận cằm khi vai bị cấn.",
            "Dùng đà lắc người.",
            "Cổ tay gãy, khuỷu thấp hơn thanh.",
        ],
        "Dừng khi khuỷu ngang vai. Vai khó chịu thì đổi sang dang tay hoặc kéo dây về mặt.",
        "Kéo tạ đòn dọc thân lên, khuỷu dẫn, dừng khoảng ngang vai. Không ép biên độ cao nếu khớp vai kêu.",
    )
    _put(
        "Nordic Hamstring Curl",
        [
            "Quỳ, cố định gót (đệm, ghế nặng, hoặc người giữ). Thân thẳng từ gối đến vai.",
            BRACE + " Tay sẵn sàng chống sàn phía trước.",
            "Từ từ đổ người về trước bằng cách duỗi gối, sau đùi hãm.",
            "Khi không giữ được, chống tay xuống rồi đẩy nhẹ về tư thế quỳ.",
            "Không gãy hông; tưởng như tấm ván đổ về trước.",
        ],
        [
            "Gãy hông ngồi ra sau, sau đùi nghỉ.",
            "Buông rơi người thay vì hãm.",
            "Gối đau vì không đệm.",
        ],
        "Người mới chỉ hạ 1/3–1/2 quãng rồi chống tay. Đệm gối luôn.",
        "Quỳ, cố định gót, đổ người về trước có kiểm soát để tập mặt sau đùi. Bài nặng; làm biên độ ngắn trước.",
    )
    _put(
        "Kettlebell Swing",
        [
            "Đứng chân rộng hơn hông, tạ ấm trước. Nắm quai bằng hai tay.",
            "Đẩy hông ra sau, tạ đung giữa hai chân. Lưng thẳng, gối mềm — không ngồi xổm.",
            "Bật hông ra trước mạnh, siết mông, tạ bay lên khoảng ngang ngực.",
            "Tay chỉ dẫn tạ, không lấy vai để 'nhấc' tạ lên đầu.",
            "Để tạ rơi, hông ra sau đón. Thở ra khi bật hông.",
        ],
        [
            "Ngồi xổm rồi nhấc tạ bằng tay.",
            "Ưỡn thắt lưng ở đỉnh.",
            "Tạ đi quá cao khi chưa kiểm soát hông.",
        ],
        "Tạ phải đi nhờ bật hông, không nhờ tay. Học gập hông lưng thẳng trước khi đánh tạ ấm nặng.",
        "Đánh tạ ấm bằng bật hông. Tạ lên ngang ngực, lưng thẳng, sau đùi và mông làm việc.",
    )
    _put(
        "Kettlebell Turkish Get-Up",
        [
            "Nằm ngửa, tạ ấm trên một tay thẳng. Cùng bên: gối gập, chân đặt sàn. Tay kia và chân kia duỗi.",
            "Mắt nhìn tạ. Lăn sang khuỷu tay kia, rồi lên bàn tay, hông nâng.",
            "Rút chân duỗi ra sau thành quỳ, rồi đứng lên. Tay tạ luôn thẳng trên vai.",
            "Đảo ngược từng bước để nằm xuống. Đổi bên.",
            "Tạ rất nhẹ khi học. Dừng nếu mất kiểm soát tạ trên đầu.",
        ],
        [
            "Gập khuỷu tay đang giữ tạ.",
            "Nhìn chỗ khác, mất phương hướng tạ.",
            "Vội đứng khi chưa khóa vị trí trung gian.",
        ],
        "Học không tạ, rồi chai nước, rồi tạ ấm nhẹ. Mỗi bước dừng 1 giây.",
        "Từ nằm đến đứng với tạ ấm một tay thẳng trên đầu. Bài kỹ thuật; làm chậm từng chặng.",
    )
    _put(
        "Kettlebell Windmill",
        [
            "Đứng rộng, đẩy tạ ấm một tay lên thẳng trên đầu. Mắt nhìn tạ.",
            "Chân cùng bên tạ hơi xoay ra. " + BRACE,
            "Đẩy hông về phía tay tạ, thân gập sang bên, tay kia trượt xuống trong chân trước.",
            "Tạ luôn thẳng trên vai. Hạ chỉ đến mức sau đùi và hông cho phép.",
            "Đẩy hông trở lại để đứng. Đổi bên.",
        ],
        [
            "Tạ nghiêng ra trước hoặc sau vai.",
            "Cong lưng thay vì gập hông sang bên.",
            "Tạ quá nặng khi chưa mềm khớp.",
        ],
        "Học không tạ trước. Biên độ nhỏ vẫn tính là đúng nếu tạ thẳng trên vai.",
        "Gập hông sang bên với tạ ấm trên đầu. Tập vai, mông và sự ổn định thân; không phải bài gập bụng thông thường.",
    )
    _put(
        "Sissy Squat",
        [
            "Đứng thẳng, nắm điểm tựa nhẹ. Gót có thể hơi nhấc. Đùi và thân nghiêng ra sau một khối.",
            "Gập gối, hạ người ra sau, gối đi ra trước. Giữ thân và đùi thẳng hàng.",
            "Hạ đến mức đùi trước căng nhưng gối không đau nhói.",
            "Đẩy sàn để duỗi gối đứng lên. Không gãy hông ngồi xuống.",
        ],
        [
            "Gãy hông thành ngồi xổm thường.",
            "Ép sâu khi gối đau.",
            "Buông điểm tựa khi chưa kiểm soát.",
        ],
        "Bài này tải gối nhiều. Người mới làm biên độ ngắn, hoặc chọn ngồi xổm/ôm tạ trước ngực thay thế.",
        "Ngồi xổm kiểu sissy: thân và đùi nghiêng ra sau, gối đi ra trước. Chỉ làm nếu gối khỏe, biên độ kiểm soát.",
    )
    _put(
        "JM Press",
        [
            "Nằm ghế, nắm thanh hẹp hơn bench thông thường. Thanh trên ngực trên.",
            "Hạ thanh về phía cổ/xương đòn, khuỷu đi về trước, cẳng tay gần thẳng đứng.",
            "Khi thanh gần mặt trên ngực, đẩy lên bằng tay sau. Không nảy thanh trên cổ.",
            "Tạ nhẹ hơn bench. Cổ tay thẳng.",
        ],
        [
            "Hạ thanh vào cổ.",
            "Tạ quá nặng, mất kiểm soát gần mặt.",
            "Khuỷu xòe mất đường đi tay sau.",
        ],
        "Bài lai giữa đẩy ngực tay hẹp và duỗi tay sau nằm. Người mới nên duỗi tay sau nằm hoặc đẩy cáp xuống trước.",
        "Nằm đẩy tạ đòn tay hẹp, hạ thanh về ngực trên với khuỷu đưa về trước. Tập tay sau; tạ phải nhẹ và kiểm soát.",
    )
    _put(
        "Tate Press",
        [
            "Nằm ghế, hai tạ đơn trên ngực, lòng bàn tay hướng về nhau, tạ gần chạm nhau.",
            "Gập khuỷu, hạ tạ ra hai bên ngực, khuỷu chỉ ra ngoài.",
            "Duỗi khuỷu đẩy tạ lên trên, tạ chạm nhau nhẹ ở đỉnh.",
            "Chuyển động nhỏ, có kiểm soát. Không đập tạ vào nhau.",
        ],
        [
            "Tạ quá nặng, khuỷu mất đường.",
            "Đập hai tạ vào nhau.",
            "Vai nhô, mất ổn định.",
        ],
        "Tạ nhẹ. Nếu khó hình dung, làm duỗi tay sau nằm tạ đơn thông thường.",
        "Nằm, hạ tạ đơn ra hai bên ngực rồi duỗi khuỷu lên. Bài cô lập tay sau, biên độ ngắn.",
    )
    _put(
        "Pallof Press",
        [
            "Gắn tay cầm ngang ngực. Đứng nghiêng so với máy/dây, hai tay nắm trước ngực.",
            BRACE + " Bước ra đến khi dây muốn xoay bạn.",
            "Đẩy hai tay ra thẳng trước ngực, giữ thân không xoay theo dây.",
            "Giữ 1–2 giây, kéo tay về ngực. Lặp lại, rồi đổi bên.",
        ],
        [
            "Xoay hông và vai theo dây.",
            "Đứng quá gần nên dây không có lực.",
            "Ưỡn thắt lưng khi đẩy tay ra.",
        ],
        "Chọn lực vừa phải: thân run nhẹ nhưng không bị kéo xoay. Đây là bài chống xoay, không phải đẩy ngực.",
        "Đứng nghiêng, đẩy tay cầm ra trước và chống lại lực muốn xoay thân. Tập bụng giữ thẳng người.",
    )
    _put(
        "Dead Hang",
        [
            "Nắm xà, treo thả lỏng có kiểm soát: vai không nhún mạnh, nhưng cũng không gồng cứng hết cỡ.",
            "Chân duỗi hoặc hơi gập. Thở đều. Cổ trung lập.",
            "Giữ hết thời gian. Xuống đất có kiểm soát, không thả rơi.",
            "Đau nhói vai hoặc bàn tay tê: xuống ngay.",
        ],
        [
            "Đung đưa mạnh.",
            "Treo đến khi mất cảm giác tay.",
            "Nhảy xuống từ trên cao khi mệt.",
        ],
        "Bắt đầu 10–20 giây. Có thể để chân chạm ghế giảm tải.",
        "Treo xà thả lỏng có kiểm soát để làm quen khớp vai và nắm. Không phải bài kéo.",
    )
    _put(
        "Box Jump",
        [
            "Đứng trước hộp chắc, thấp hơn khả năng tối đa. Chân rộng hông, tay đung.",
            "Ngồi xổm nông, đánh tay, nhảy hai chân lên hộp. Tiếp đất cả bàn chân, gối mềm.",
            "Đứng thẳng trên hộp. Bước xuống từng chân — không nhảy xuống khi mới học.",
            "Hộp trơn hoặc quá cao: chọn thấp hơn.",
        ],
        [
            "Nhảy xuống từ hộp cao, gối chịu sốc.",
            "Hộp quá cao, cằm hoặc ống chân va cạnh.",
            "Tiếp đất gối sụp vào trong.",
        ],
        "Chọn hộp thấp làm đẹp tiếp đất. Bước xuống luôn an toàn hơn nhảy xuống.",
        "Nhảy hai chân lên hộp chắc, tiếp đất mềm, bước xuống. Ưu tiên hộp thấp và sạch hơn hộp cao.",
    )
    _put(
        "Burpee",
        [
            "Từ đứng, ngồi xổm, hai tay đặt sàn.",
            "Bước hoặc nhảy chân ra plank, thân thẳng. Có thể làm một chống đẩy nếu lịch yêu cầu.",
            "Bước hoặc nhảy chân về tay, đứng lên, nhảy nhẹ vỗ tay nếu còn sức.",
            "Giữ bụng siết khi ở plank. Giảm nhảy nếu gối hoặc cổ tay đau.",
        ],
        [
            "Hông sệ khi plank.",
            "Đập gối xuống sàn khi mệt.",
            "Nhảy hết sức mỗi cái khi chưa có nhịp thở.",
        ],
        "Bước chân thay vì nhảy để dễ hơn. Chống đẩy có thể bỏ khi mới học.",
        "Ngồi xuống, plank, trở lại đứng. Bài điều hòa; làm sạch tư thế quan trọng hơn tốc độ.",
    )
    _put(
        "Man Maker",
        [
            "Hai tạ đơn dưới tay. Burpee: tay nắm tạ, chân ra plank.",
            "Chèo một tay, rồi tay kia, thân không xoay mạnh.",
            "Bước chân về, đứng lên, đẩy hai tạ lên trên đầu.",
            "Tạ phải nhẹ. Nghỉ giữa rep nếu mất thăng bằng.",
        ],
        [
            "Tạ quá nặng, lưng xoay khi chèo.",
            "Hông sệ ở plank.",
            "Đẩy tạ lên khi lưng còn cong.",
        ],
        "Tách thành chống đẩy + chèo + đẩy vai nếu chưa ghép được một mạch.",
        "Ghép plank, chèo tạ đơn và đẩy vai. Bài phức hợp; dùng tạ nhẹ.",
    )
    _put(
        "Battle Ropes",
        [
            "Đứng chân trước sau hoặc rộng hông, gối mềm, nắm hai đầu dây.",
            BRACE + " Tạo sóng bằng vai và tay, hông ổn định.",
            "Giữ sóng đều đến hết thời gian. Không khóa gối.",
            "Khi mệt, giảm biên độ chứ đừng gù lưng.",
        ],
        [
            "Khóa gối, chỉ lấy tay.",
            "Gù lưng khi mệt.",
            "Nắm quá chặt đến chuột rút cẳng tay ngay từ đầu.",
        ],
        "Sóng nhỏ đều tốt hơn sóng to rồi chết sớm. Gối luôn mềm.",
        "Đập dây tạo sóng, gối mềm, thân ổn định. Dùng để tăng nhịp tim, không phải bài tay thuần.",
    )
    _put(
        "Kettlebell Farmers Carry",
        [
            "Nhấc hai tạ ấm/tạ đơn dọc người, đứng thẳng, vai kéo xuống.",
            "Đi bước ngắn chắc, mắt nhìn trước. " + BRACE,
            "Không để tạ kéo vai lệch một bên. Tay thẳng, không nhún.",
            "Đặt tạ xuống có kiểm soát khi hết cự ly.",
        ],
        [
            "Gù lưng, tạ kéo người về trước.",
            "Bước lê, mất thăng bằng.",
            "Nhún vai lên tai.",
        ],
        "Tạ vừa để đi thẳng người. Vai lệch thì giảm tạ.",
        "Đi bộ cầm tạ nặng hai bên, thân thẳng. Tập nắm, vai và sự ổn định.",
    )
    _put(
        "Cossack Squat",
        [
            "Đứng chân rất rộng, mũi chân hơi xoay ra.",
            "Dồn người sang một bên, ngồi xổm chân đó, chân kia duỗi.",
            "Gót chân ngồi giữ trên sàn nếu được. Thân ưỡn nhẹ, không gù.",
            "Đẩy về giữa rồi sang bên kia. Biên độ nhỏ khi mới học.",
        ],
        [
            "Gót chân ngồi nhấc và gối sụp.",
            "Cong lưng nặng để xuống sâu.",
            "Ép sâu khi háng hoặc gối đau.",
        ],
        "Giữ tay trước để thăng bằng. Đây là bài mềm dẻo kiêm sức; đừng so độ sâu với người khác.",
        "Ngồi xổm sang một bên, chân kia duỗi. Tập háng và chân; chỉ xuống sâu khi khớp cho phép.",
    )
    _put(
        "Toes-to-Bar",
        [
            "Treo xà chủ động, vai kéo xuống. Siết bụng.",
            "Đưa chân lên, chạm mu hoặc mũi chân vào xà trước mặt.",
            "Hạ chân có kiểm soát, không đung đưa mất kiểm soát.",
            "Chưa chạm xà được: nâng gối vào ngực trước.",
        ],
        [
            "Đung đưa lấy đà rồi ném thắt lưng.",
            "Nhún vai thả võng.",
            "Buông xà khi chân đang trên cao.",
        ],
        "Học nâng gối treo trước. Chạm xà không bắt buộc nếu lưng đang võng.",
        "Treo xà, đưa chân chạm xà. Bài bụng nâng cao; người mới làm nâng gối treo.",
    )
    _put(
        "Hanging Knee Raises",
        [
            "Treo xà chủ động, thân yên.",
            "Kéo gối lên về phía ngực, siết bụng dưới.",
            "Hạ chân chậm, không đung đưa.",
            "Vai luôn kéo xuống xa tai.",
        ],
        [
            "Đung đưa lấy đà.",
            "Nhún vai.",
            "Ném thắt lưng ra sau.",
        ],
        "Siết bụng để gối lên, không đá chân. Nghỉ khi thân bắt đầu đu.",
        "Treo xà, nâng gối về ngực, hạ chậm. Nền tảng cho các bài bụng treo.",
    )
    _put(
        "Captain's Chair Knee Raise",
        [
            "Tựa lưng vào ghế treo, tay nắm, khuỷu trên đệm. Lưng dán tựa.",
            "Nâng gối về ngực, siết bụng.",
            "Hạ chân chậm, không đung.",
            "Không lấy đà bằng thân rời khỏi tựa.",
        ],
        [
            "Lưng rời đệm, lấy đà.",
            "Đá chân thay vì nâng gối.",
            "Nín thở.",
        ],
        "Lưng dán đệm suốt. Chậm và siết bụng hơn là đá mạnh.",
        "Trên ghế treo, nâng gối về ngực. Lưng tựa đệm để bụng làm việc.",
    )
    _put(
        "False Grip Ring Hang",
        [
            "Chỉnh vòng ngang đầu. Cổ tay gác lên vòng (nắm cổ tay chồng lên vòng), nắm chắc.",
            "Treo, vai kéo xuống. Cẳng tay thẳng hàng với vòng nếu được.",
            "Giữ thời gian ngắn. Đau cổ tay sắc: xuống ngay, bỏ kiểu nắm này.",
            "Đây là kỹ năng vòng, không phải bài mới bắt buộc.",
        ],
        [
            "Cổ tay gãy đau rồi vẫn giữ.",
            "Vòng xoay mạnh làm mất nắm.",
            "Treo quá lâu lần đầu.",
        ],
        "Bọc vòng, làm 5–10 giây. Người mới treo thường (dead hang) trước.",
        "Treo vòng với cổ tay gác lên vòng. Kỹ năng nâng cao cho dip/kéo vòng; không bắt người mới phải làm.",
    )
    _put(
        "Ring Support Hold",
        [
            "Chỉnh vòng ngang hông. Nhảy lên vị trí chống thẳng tay trên vòng (như đỉnh dip).",
            "Khuỷu gần khóa nhưng không giật. Vai kéo xuống xa tai. Vòng sát thân.",
            "Siết bụng, chân duỗi. Giữ vòng ít xoay.",
            "Hạ xuống có kiểm soát khi hết thời gian.",
        ],
        [
            "Vai nhún lên tai, khớp không ổn định.",
            "Vòng xoay mạnh ra xa thân.",
            "Khóa khuỷu giật.",
        ],
        "Học chống đẩy vòng và dip có trợ trước. Giữ ngắn, sạch.",
        "Chống thẳng tay trên vòng treo, vai hạ, vòng sát thân. Nền tảng cho dip vòng.",
    )
    _put(
        "Ring Hold",
        [
            "Nắm hai vòng, đứng hoặc quỳ tùy chiều cao vòng.",
            "Giữ cánh tay ổn định, vai kéo xuống, bụng siết.",
            "Vòng không xoay mạnh. Thở đều.",
            "Đây là giữ ổn định, không phải kéo hay đẩy.",
        ],
        [
            "Vai nhún, vòng xoay.",
            "Khóa khớp giật.",
            "Nín thở.",
        ],
        "Hạ vòng hoặc quỳ để dễ hơn. Tập làm quen vòng trước khi chống đẩy vòng.",
        "Giữ vòng treo ổn định, vai hạ. Bài làm quen với vòng động.",
    )
    _put(
        "Ring Dead Hang",
        [
            "Nắm vòng, treo người. Vai không thả sập đột ngột.",
            "Thân yên, thở đều. Vòng có thể hơi động — chống lại bằng siết nhẹ.",
            "Giữ hết thời gian ngắn. Đau nhói vai hoặc tê tay: xuống ngay.",
            "Xuống đất có kiểm soát, không nhảy thả rơi.",
        ],
        [
            "Đung đưa mất kiểm soát.",
            "Treo đến tê tay.",
            "Nhảy xuống khi mệt.",
        ],
        "Thời gian ngắn hơn xà cố định vì vòng khó giữ hơn.",
        "Treo thả lỏng trên vòng. Khó hơn xà vì vòng động.",
    )
    _put(
        "Ring Push-Up",
        [
            "Chỉnh vòng thấp, khoảng ngang ngực khi quỳ. Nắm vòng, chân ra sau vào plank.",
            "Thân thẳng đầu đến gót. " + BRACE,
            "Hạ ngực xuống giữa hai vòng, khuỷu gần thân, vòng ít xoay.",
            "Đẩy lên đến tay gần thẳng. Không để hông sệ.",
            "Người mới: chống gối hoặc kéo vòng cao hơn (thân dốc).",
        ],
        [
            "Vòng xoay mạnh, vai mất ổn định.",
            "Hông sệ hoặc ưỡn thắt lưng.",
            "Khuỷu xòe rộng.",
        ],
        "Vòng càng thấp bài càng nặng. Quỳ hoặc dốc người là cách giảm tải đúng.",
        "Chống đẩy trên vòng treo. Giữ thân thẳng, vòng ổn định; dễ hơn bằng cách nâng vòng hoặc chống gối.",
    )
    _put(
        "Ring Dip",
        [
            "Vòng ngang hông. Nhảy lên chống thẳng tay, vai kéo xuống, vòng sát thân.",
            "Hạ người, gập khuỷu, thân hơi nghiêng trước nếu muốn nhấn ngực.",
            "Hạ đến vai ngang khuỷu — không sâu hơn nếu vai căng.",
            "Đẩy lên chống thẳng tay có kiểm soát. Không dùng đà nhảy.",
        ],
        [
            "Buông vai lên tai.",
            "Hạ quá sâu khi vai chưa sẵn.",
            "Vòng xoay ra xa, mất đường đẩy.",
        ],
        "Làm chống đẩy vòng và giữ chống thẳng tay trước. Trợ bằng chân trên sàn nếu cần.",
        "Hạ người rồi đẩy lên trên vòng treo. Vai phải ổn định; đừng hạ sâu hơn tầm kiểm soát.",
    )
    _put(
        "Ring Chest Fly",
        [
            "Vòng ngang ngực. Đứng chân trước sau, nắm vòng, khuỷu hơi cong và giữ nguyên góc.",
            "Mở tay sang hai bên theo hình cung, cảm giác căng ngực. Không mở quá rộng.",
            "Ép vòng về trước ngực bằng lực ngực, không gập khuỷu thêm.",
            "Thân vững, không để vòng kéo bạn ngã trước.",
        ],
        [
            "Gập khuỷu biến thành chống đẩy.",
            "Mở quá rộng, căng vai trước.",
            "Đứng quá xa, mất thăng bằng.",
        ],
        "Giữ góc khuỷu cố định khoảng 10–20°. Đứng càng thẳng (gần đứng) càng dễ.",
        "Ép ngực trên vòng: mở tay rồi khép lại, khuỷu gần như không đổi góc.",
    )
    _put(
        "Ring Row",
        [
            "Vòng ngang ngực–hông. Nằm ngửa, nắm vòng, thân thẳng, gót trên sàn.",
            "Kéo ngực về vòng, siết lưng giữa, khuỷu sát sườn.",
            "Hạ chậm đến tay gần thẳng. Hông không sệ.",
            "Càng nằm ngang càng nặng.",
        ],
        [
            "Hông sệ.",
            "Kéo cằm thay vì ngực.",
            "Vòng xoay, vai nhún.",
        ],
        "Đứng hơn = dễ. Nằm hơn = khó. Chân trên ghế là mức nặng.",
        "Nằm kéo ngực về vòng treo. Điều chỉnh độ dốc để còn làm được từng rep sạch.",
    )
    _put(
        "Archer Ring Row",
        [
            "Bắt đầu như chèo vòng hai tay, thân thẳng, gót trên sàn.",
            "Một tay kéo ngực về vòng, tay kia duỗi sang bên như cung.",
            "Ngực hướng về vòng tay kéo. Hạ chậm, rồi đổi bên.",
            "Chỉ làm khi chèo vòng thường đã chắc. Giảm độ dốc nếu lệch người.",
        ],
        [
            "Xoay hông bù cho tay yếu.",
            "Tay duỗi mất kiểm soát, vòng kéo mạnh.",
            "Làm khi chưa vững chèo hai tay.",
        ],
        "Giảm độ dốc khi mới chuyển sang archer. Đổi bên đều.",
        "Chèo vòng lệch một tay, tay kia duỗi. Bài nâng cao sau khi chèo vòng đều hai tay.",
    )
    _put(
        "Ring Pull-Up",
        [
            "Nắm vòng, treo chủ động, lòng bàn tay đối diện hoặc hơi sấp.",
            "Kéo ngực lên, vòng về phía ngực, cằm trên tay nắm.",
            "Hạ chậm. Vòng có thể xoay nhẹ — siết để ổn định.",
            "Chưa được: chèo vòng hoặc kéo xà trợ lực.",
        ],
        [
            "Giật đà mạnh.",
            "Vai thả võng khi hạ.",
            "Kéo lệch một vòng.",
        ],
        "Khó hơn xà cố định. Làm chèo vòng và treo chủ động trước.",
        "Kéo người trên vòng treo đến cằm qua tay nắm. Ổn định vòng quan trọng hơn số cái.",
    )
    _put(
        "Ring Chin-Up",
        [
            "Nắm vòng lòng bàn tay hướng vào bạn. Treo chủ động, vai kéo xuống xa tai.",
            "Kéo người lên, khuỷu sát sườn, cằm trên tay nắm.",
            "Siết bụng, không đung đưa.",
            "Hạ chậm đến tay gần thẳng, vai không thả võng.",
        ],
        [
            "Đung đưa.",
            "Nhún vai.",
            "Hạ rơi tự do.",
        ],
        "Thường dễ hơn kéo xà sấp một chút vì bắp tay hỗ trợ. Vẫn giữ vai hạ.",
        "Kéo vòng lòng bàn tay hướng vào. Vai hạ, hạ người chậm.",
    )
    _put(
        "Ring Biceps Curl",
        [
            "Vòng ngang ngực. Đứng hoặc nằm dốc, nắm vòng lòng bàn tay lên.",
            "Khuỷu cố định gần sườn, gập tay kéo vai về vòng.",
            "Duỗi tay chậm. Không lấy lưng giật.",
            "Điều chỉnh độ dốc để còn 8–12 cái sạch.",
        ],
        [
            "Khuỷu chạy tới trước.",
            "Giật hông.",
            "Duỗi tay thả rơi.",
        ],
        "Càng đứng thẳng càng dễ. Giữ khuỷu im.",
        "Gập tay trên vòng treo. Khuỷu im, người không lấy đà.",
    )
    _put(
        "Ring Triceps Extension",
        [
            "Vòng ngang ngực–đầu. Đứng dốc, nắm vòng, tay đưa ra trước.",
            "Gập khuỷu, hạ đầu/thân về giữa vòng, khuỷu chỉ về trước.",
            "Duỗi khuỷu đẩy về. Thân không gãy hông.",
            "Biên độ ngắn nếu khuỷu khó chịu.",
        ],
        [
            "Khuỷu xòe ra ngoài.",
            "Hông gãy, lưng ưỡn.",
            "Vòng xoay mất đường.",
        ],
        "Đứng gần thẳng cho dễ. Đẩy cáp xuống hoặc chống đẩy hẹp dễ học hơn nếu vòng quá khó.",
        "Đứng dốc, gập rồi duỗi khuỷu trên vòng để tập tay sau. Giữ thân thẳng.",
    )
    _put(
        "Ring Face Pull",
        [
            "Vòng ngang mặt. Nắm vòng, bước ra sau đến khi dây/vòng căng, tay duỗi.",
            "Kéo vòng về thái dương, khuỷu cao ngang vai, xoay tay ra ngoài nhẹ.",
            "Siết vai sau và giữa lưng. Đưa vòng ra chậm.",
            "Không lấy thắt lưng giật.",
        ],
        [
            "Kéo xuống ngực biến thành chèo.",
            "Nhún vai lên tai.",
            "Tạ/dốc quá nặng, phải giật.",
        ],
        "Lực nhẹ, siết vai sau. Đây là bài vai sau và tư thế, không phải bài kéo nặng.",
        "Kéo vòng về gần mặt, khuỷu ngang vai, siết vai sau.",
    )
    _put(
        "Ring Rear Delt Fly",
        [
            "Nắm vòng, thân dốc, tay gần thẳng, khuỷu mềm.",
            "Mở hai vòng sang hai bên, siết vai sau. Không gập khuỷu thành chèo.",
            "Khép vòng chậm về trước. Thân thẳng, không xoay hông lấy đà.",
            "Lực nhẹ. Cảm giác sau vai, không phải lưng xô.",
        ],
        [
            "Gập khuỷu quá nhiều.",
            "Nhún cầu vai.",
            "Xoay hông lấy đà.",
        ],
        "Biên độ vừa, lực nhẹ. Cảm giác sau vai, không phải lưng xô.",
        "Mở vòng sang hai bên với tay gần thẳng để tập vai sau.",
    )
    _put(
        "Ring Pec Stretch",
        [
            "Nắm một vòng ngang ngực, xoay người ngược chiều tay đến khi ngực căng nhẹ.",
            "Giữ 20–30 giây, thở chậm. Không nảy.",
            "Căng tức, không đau nhói vai. Giảm xoay nếu tê tay.",
            "Đổi bên. Vòng phải cố định, không để bị kéo ngã.",
        ],
        [
            "Xoay quá mạnh, đau phía trước vai.",
            "Nảy giãn.",
            "Vòng không cố định, bị kéo ngã.",
        ],
        "Căng vừa phải. Giảm xoay nếu tê tay.",
        "Giãn ngực với một vòng treo. Xoay người đến căng nhẹ, giữ thở, không nảy.",
    )
    _put(
        "Ring Lat Stretch",
        [
            "Nắm vòng, lùi hông ra sau, tay duỗi, ngực hạ, cảm giác căng xô.",
            "Giữ 20–30 giây, thở. Không ưỡn thắt lưng quá mức.",
            "Hông ra sau, tay dài, bụng siết nhẹ. Không nảy.",
            "Đổi bên nếu làm một tay.",
        ],
        [
            "Ưỡn thắt lưng để giả độ sâu.",
            "Nhún vai lên tai.",
            "Nảy.",
        ],
        "Hông ra sau, tay dài, bụng vẫn siết nhẹ.",
        "Giãn xô trên vòng: hông lùi, tay duỗi, căng nhẹ dọc sườn sau.",
    )
    _put(
        "Band Front Raise",
        [
            "Đứng lên giữa dây ống có tay cầm, chân rộng hông.",
            "Cầm hai đầu dây, lòng bàn tay xuống hoặc vào nhau, tay trước đùi.",
            BRACE + " Nâng hai tay ra trước đến ngang vai, khuỷu mềm.",
            "Hạ chậm 2–3 giây về đùi. Không lắc người.",
        ],
        [
            "Lắc thân lấy đà.",
            "Nâng quá cao lên trên đầu.",
            "Gập khuỷu quá nhiều.",
        ],
        "Đứng rộng trên dây thì nặng hơn. Dừng ngang vai.",
        "Đứng lên dây, nâng tay ra trước đến ngang vai. Tập vai trước; không lấy đà lưng.",
    )


_init_overrides()


def _stretch(setup: str, action: str, extra: str, mistakes: list[str], tips: str, summary: str) -> Copy:
    return copy_of(
        [
            setup,
            action,
            extra,
            "Giữ 20–30 giây, thở chậm. Không nảy. Đổi bên nếu là một bên.",
        ],
        mistakes,
        tips,
        summary,
    )


def stretch_copy(name: str) -> Copy | None:
    table = {
        "Abdominals Stretch Variation One": _stretch(
            "Nằm sấp, cẳng tay trên sàn, khuỷu dưới vai.",
            "Đẩy nhẹ qua tay, nâng ngực như rắn, hông vẫn gần sàn.",
            "Vai kéo xuống xa tai. Chỉ ngửa trong tầm dễ chịu.",
            ["Ép lưng dưới quá mạnh.", "Nhún vai lên tai.", "Nín thở."],
            "Giãn bụng/mặt trước, không phải bài 'cong càng nhiều càng tốt'.",
            "Nằm sấp, nâng ngực nhẹ để mở bụng. Hông gần sàn, thở chậm.",
        ),
        "Abdominals Stretch Variation Two": _stretch(
            "Đứng chân rộng hông, tay thả dọc người.",
            "Đưa hai tay lên cao, nâng ngực, ngửa nhẹ nếu dễ chịu.",
            "Không đẩy hông ra trước quá mức.",
            ["Ưỡn thắt lưng mạnh.", "Khóa gối cứng.", "Ngửa cổ quá xa."],
            "Biên độ nhỏ vẫn được. Đau thắt lưng thì chỉ đưa tay lên, không ngửa.",
            "Đứng, tay lên cao, mở mặt trước người trong tầm thoải mái.",
        ),
        "Abdominals Stretch Variation Three": _stretch(
            "Đứng, một tay đưa lên cao.",
            "Nghiêng người sang bên đối diện, hông giữ giữa.",
            "Không xoay ngực ra trước hay ra sau.",
            ["Hông lắc sang bên, mất giãn sườn.", "Xoay thân.", "Ép sâu ngay từ giây đầu."],
            "Giãn cạnh sườn. Hông đứng yên, chỉ nghiêng thân.",
            "Đứng, tay lên cao, nghiêng sang bên để giãn cơ liên sườn.",
        ),
        "Cat-Cow Stretch": copy_of(
            [
                "Quỳ bốn điểm: tay dưới vai, gối dưới hông.",
                "Thở ra, vòng lưng lên trời (mèo), cằm gần ngực.",
                "Hít vào, hạ bụng, nhìn nhẹ ra trước (bò), không ưỡn cổ quá.",
                "Chuyển chậm 6–10 lần. Đau thì giảm biên độ.",
            ],
            ["Nảy nhanh.", "Treo đầu quá sâu.", "Khóa khuỷu cứng."],
            "Làm chậm theo hơi thở. Đây là khởi động cột sống, không phải bài sức mạnh.",
            "Quỳ bốn điểm, luân phiên vòng lưng và võng lưng nhẹ theo hơi thở.",
        ),
        "Child's Pose": copy_of(
            [
                "Quỳ, mông về gót, tay với ra trước trên sàn.",
                "Trán đặt sàn nếu được. Thở vào lưng.",
                "Giữ 20–40 giây. Gối đau thì chêm chăn giữa mông và gót.",
                "Không ép mông nếu háng căng.",
            ],
            ["Ép ngực xuống khi gối đau.", "Nín thở.", "Bật người dậy đột ngột."],
            "Mở gối rộng nếu bụng chạm đùi khó chịu. Nghỉ thở, không tranh độ sâu.",
            "Quỳ, mông về gót, tay với ra trước. Tư thế nghỉ giãn lưng.",
        ),
        "Cross-Body Shoulder Stretch": _stretch(
            "Đứng hoặc ngồi thẳng.",
            "Đưa một tay ngang ngực, tay kia kéo nhẹ cánh tay vào người.",
            "Vai kéo xuống, không nhún.",
            ["Kéo quá mạnh, đau phía trước vai.", "Nhún vai.", "Xoay thân bù."],
            "Căng nhẹ sau vai. Tê tay thì giảm lực kéo.",
            "Kéo một tay ngang ngực để giãn vai. Nhẹ, không nảy.",
        ),
        "Doorway Chest Stretch": _stretch(
            "Đứng trong khung cửa, cẳng tay hoặc bàn tay tì lên khung ngang ngực.",
            "Bước chân trước, xoay ngực ra khỏi tay đến khi ngực căng nhẹ.",
            "Giữ, thở. Đổi bên.",
            ["Xoay quá mạnh.", "Ưỡn thắt lưng.", "Khuỷu quá cao gây cấn vai."],
            "Tay ngang vai hoặc hơi thấp hơn. Căng ngực, không đau khớp vai.",
            "Giãn ngực tại khung cửa. Bước chân và xoay nhẹ đến căng, giữ thở.",
        ),
        "Floor Chest Stretch": _stretch(
            "Nằm sấp, một tay dang ngang vai.",
            "Xoay người ngược chiều tay, chân cùng bên mở, đến khi ngực căng.",
            "Giữ. Đổi bên.",
            ["Xoay quá mạnh.", "Nảy.", "Kê cổ khó."],
            "Biên độ nhỏ. Dùng gối hoặc chăn dưới ngực nếu khó chịu.",
            "Nằm sấp, một tay dang, xoay người để giãn ngực.",
        ),
        "Overhead Shoulder/Triceps Stretch": _stretch(
            "Đưa một tay lên, gập khuỷu, bàn tay giữa hai bả vai nếu được.",
            "Tay kia cầm khuỷu, kéo nhẹ ra sau.",
            "Thân thẳng, không ưỡn lưng.",
            ["Ép khuỷu khi đau.", "Ưỡn thắt lưng.", "Nín thở."],
            "Căng tay sau và vai. Giảm kéo nếu tê tay.",
            "Gập một tay sau đầu, tay kia kéo nhẹ khuỷu để giãn tay sau.",
        ),
        "Seated Spinal Twist": _stretch(
            "Ngồi thẳng, chân duỗi hoặc một chân gập.",
            "Xoay thân về một bên, tay chống sau để dài lưng.",
            "Xoay từ ngực, không giật cổ.",
            ["Giật xoay.", "Gù lưng.", "Nín thở."],
            "Xoay vừa, thở. Đau chèn đĩa thì bỏ bài, chọn cat-cow nhẹ.",
            "Ngồi xoay cột sống nhẹ. Lưng dài, không giật.",
        ),
        "Standing Calf Stretch": _stretch(
            "Đứng trước tường, một chân sau duỗi, gót sau dán sàn.",
            "Chân trước chùng, thân hơi đổ vào tường.",
            "Cảm giác căng bắp chân sau. Đổi chân.",
            ["Gót sau nhấc.", "Khóa gối sau quá cứng đau.", "Nảy."],
            "Gót phải dính sàn. Hơi gập gối sau nếu muốn nhấn thấp bắp chân.",
            "Chân sau duỗi, gót dán sàn, đổ người để giãn bắp chân.",
        ),
        "Standing Chest Opener": _stretch(
            "Đứng, đan tay sau lưng, kéo vai ra sau, ngực mở.",
            "Không ưỡn thắt lưng bù. Cằm hơi thu.",
            "Giữ 20–30 giây.",
            ["Ưỡn lưng dưới.", "Nhún vai.", "Kéo tay đến đau cổ tay."],
            "Mở ngực nhẹ. Có thể nắm khăn sau lưng nếu tay chưa gặp nhau.",
            "Đan tay sau lưng, mở ngực, vai ra sau. Không bù bằng ưỡn thắt lưng.",
        ),
        "Standing Quad Stretch": _stretch(
            "Đứng, nắm một mắt cá, kéo gót về mông.",
            "Hai gối gần nhau, siết mông nhẹ, không ưỡn lưng.",
            "Giữ tường nếu mất thăng bằng. Đổi chân.",
            ["Gối mở sang ngang.", "Ưỡn thắt lưng.", "Kéo quá mạnh khi gối đau."],
            "Gối sát nhau. Đau gối thì giảm độ gập.",
            "Đứng, kéo gót về mông để giãn đùi trước. Gối thẳng hàng, không ưỡn lưng.",
        ),
        "Standing/Seated Hamstring Stretch": _stretch(
            "Đứng một chân trên bục thấp hoặc ngồi duỗi chân.",
            "Cúi từ hông, lưng dài, đến khi sau đùi căng.",
            "Không gù lưng để tay chạm mũi chân.",
            ["Cong lưng nặng.", "Khóa gối đau.", "Nảy."],
            "Lưng thẳng quan trọng hơn tay chạm chân. Gối hơi mềm.",
            "Cúi từ hông để giãn sau đùi. Lưng dài, không gù để với tay.",
        ),
        "Wrist Flexor/Extensor Stretch": copy_of(
            [
                "Đưa một tay ra trước, lòng bàn tay lên, tay kia kéo nhẹ các ngón xuống.",
                "Giữ 15–20 giây. Lật lòng bàn tay xuống, kéo nhẹ mu tay.",
                "Khuỷu thẳng nhưng không khóa giật. Đổi tay.",
                "Đau nhói cổ tay: giảm lực, chỉ giữ tư thế không kéo.",
            ],
            ["Kéo mạnh khi cổ tay đang đau.", "Khóa khuỷu giật.", "Nảy cổ tay."],
            "Làm nhẹ sau khi đẩy hoặc chống đẩy. Không ép nếu đang viêm cổ tay.",
            "Giãn cổ tay hai chiều: lòng bàn tay lên rồi xuống, kéo nhẹ, giữ thở.",
        ),
        "Cycling Warmup": copy_of(
            [
                "Ngồi xe, chỉnh yên cao gần duỗi gối khi đạp dưới.",
                "Đạp nhẹ 5–8 phút, sức cản thấp, thở dễ nói chuyện.",
                "Giữ thân ổn định, không lấy tay chống hết lực.",
                "Tăng nhẹ sức cản ở phút cuối nếu khớp đã ấm.",
            ],
            ["Sức cản quá nặng lúc lạnh.", "Yên quá thấp, gối đau.", "Gù lưng, nhún vai."],
            "Đây là khởi động, không phải buổi đạp kiệt sức.",
            "Đạp xe nhẹ để ấm khớp và tăng nhịp tim trước buổi tập.",
        ),
        "Cycling Cooldown": copy_of(
            [
                "Giảm sức cản, đạp chậm 5 phút.",
                "Thở chậm, vai thả. Không dừng đột ngột sau hiệp nặng.",
                "Xuống xe khi nhịp thở đã dễ.",
                "Uống nước, đi bộ vài vòng nếu còn choáng.",
            ],
            ["Dừng xe gấp sau hiệp nặng.", "Sức cản vẫn cao.", "Gù người hoàn toàn lên ghi đông."],
            "Mục tiêu hạ nhịp tim dần, không phải đạp thêm thành tích.",
            "Đạp chậm, sức cản thấp để hạ nóng sau buổi tập.",
        ),
        "Romanian Deadlift Hamstring Sweeps": copy_of(
            [
                "Đứng một chân trụ, gối mềm. Tay với về trước hoặc nhẹ nhàng quét dọc chân trụ.",
                "Đẩy hông ra sau, chân sau duỗi, lưng thẳng.",
                "Quét tay dọc ống chân trong tầm kiểm soát, không gù lưng.",
                "Đứng lên siết mông. Đổi chân.",
            ],
            ["Cong lưng để tay chạm thấp.", "Khóa gối trụ.", "Xoay hông."],
            "Đây là giãn kiêm học gập hông. Biên độ nhỏ vẫn đúng.",
            "Gập hông một chân, tay quét nhẹ dọc chân trụ để mở sau đùi.",
        ),
    }
    return table.get(name)


def cardio_copy(name: str) -> Copy | None:
    table = {
        "Elliptical": copy_of(
            [
                "Bước lên bàn đạp, tay nắm tay cầm di chuyển. Đứng thẳng, bụng siết nhẹ.",
                "Chọn độ dốc và sức cản vừa nói chuyện được.",
                "Đạp hết vòng, cả bàn chân dính bàn đạp. Tay đẩy–kéo theo nhịp chân.",
                "Không chống hết thân lên tay cầm. Giảm sức cản rồi bước xuống khi bàn đạp chậm.",
            ],
            ["Treo người trên tay cầm, chân gần như nghỉ.", "Gót nhấc khỏi bàn đạp.", "Bước xuống khi máy còn quay nhanh."],
            "Tư thế đứng, bước dài vừa. Điều chỉnh dốc để đổi chỗ mỏi (đùi trước hoặc mông).",
            "Máy elip: đạp vòng không tác động mạnh khớp. Đứng thẳng, đừng treo người lên tay cầm.",
        ),
        "Incline Treadmill Walk": copy_of(
            [
                "Bám tay vịn lúc lên máy. Chọn dốc 5–12% tùy sức, tốc độ đi bộ nhanh.",
                "Tay có thể buông nhẹ khi đã vững. Bước ngắn, thân hơi thẳng.",
                "Không cầm tay vịn rồi ngả sau. Giảm dốc trước khi dừng.",
                "Xuống máy khi băng đã chậm.",
            ],
            ["Cầm tay vịn ngả người, giảm tải chân.", "Dốc quá cao, bước lê.", "Nhảy khỏi máy khi băng còn chạy."],
            "Đi bộ dốc tốt cho nhịp tim và mông/đùi sau, ít sốc hơn chạy. Nói được câu ngắn là ổn.",
            "Đi bộ dốc trên máy chạy. Giữ thân thẳng, giảm dốc trước khi xuống máy.",
        ),
        "Indoor Cycling (Spin Bike)": copy_of(
            [
                "Chỉnh yên khoảng cao háng, ghi đông vừa tầm. Đạp với sức cản luôn có (không quay trớn).",
                "Lưng dài, vai thả. Tăng sức cản khi đứng đạp.",
                "Giữ nhịp đều theo lịch. Không khóa gối.",
                "Giảm cản, đạp chậm trước khi xuống.",
            ],
            ["Sức cản bằng không, gối bị quán tính.", "Yên quá thấp.", "Gù lưng, nhún vai."],
            "Luôn có sức cản nhẹ. Đứng đạp chỉ khi đã ngồi chắc.",
            "Đạp xe trong nhà với sức cản. Yên đúng cao, gối không khóa.",
        ),
        "Jump Rope": copy_of(
            [
                "Cầm dây, khuỷu sát sườn. Nhảy thấp, tiếp đất mũi–giữa bàn chân, gối mềm.",
                "Quay dây bằng cổ tay, không bằng cả vai.",
                "Nhịp đều. Vướng dây thì dừng, không giật chân.",
                "Nền không trơn. Giày đế mỏng vừa phải.",
            ],
            ["Nhảy quá cao.", "Khóa gối.", "Quay dây bằng vai, khuỷu xòe."],
            "Nhảy thấp, ít va. Nghỉ nếu bắp chân chuột rút.",
            "Nhảy dây thấp, quay bằng cổ tay, tiếp đất mềm.",
        ),
        "Long Run": copy_of(
            [
                "Khởi động đi bộ 5 phút. Chạy tốc độ nói được câu ngắn.",
                "Vai và tay thả, bước thoải, không gót đập mạnh.",
                "Uống nước theo lịch. Giảm về đi bộ khi mất hơi chứ đừng gắng sụp.",
                "Kết thúc đi bộ chậm 5 phút.",
            ],
            ["Xuất phát quá nhanh.", "Sải quá dài, gót phanh.", "Không uống nước buổi dài."],
            "Chạy bền: đều và dễ thở hơn là nhanh. Đi bộ xen kẽ vẫn tính.",
            "Chạy dài tốc độ nói chuyện được. Ưu tiên đều và hạ từng bước, không xuất phát như chạy nước rút.",
        ),
        "Rowing Intervals": copy_of(
            [
                "Ngồi máy chèo, chân trên bàn đạp, nắm tay cầm. Thứ tự: chân đẩy, thân ngả sau nhẹ, tay kéo.",
                "Về: tay duỗi, thân, rồi gối gập. Chọn sức cản vừa.",
                "Hiệp nhanh theo lịch, hiệp nghỉ đạp nhẹ. Lưng không gù.",
                "Dừng êm, không buông tay cầm bật.",
            ],
            ["Gù lưng khi kéo.", "Gập gối trước khi tay duỗi lúc về.", "Kéo chỉ bằng tay."],
            "Chân làm phần lớn việc. Học nhịp chậm sạch trước khi làm hiệp nhanh.",
            "Chèo máy theo hiệp nhanh–chậm. Thứ tự: chân, thân, tay; về ngược lại.",
        ),
        "Running Intervals": copy_of(
            [
                "Khởi động đi bộ/chạy chậm. Chạy nhanh theo thời gian lịch, không phải nước rút hết sức nếu chưa quen.",
                "Hiệp nghỉ đi bộ hoặc chạy rất chậm đến khi thở dễ hơn.",
                "Giữ vai thả. Giảm tốc nếu đau nhói.",
                "Hạ nóng đi bộ 5 phút.",
            ],
            ["Hiệp đầu quá nhanh, các hiệp sau chết.", "Cắt ngắn nghỉ.", "Khóa gối, sải dài phanh gót."],
            "Hiệp nhanh = 'hơi khó nói chuyện', không phải nôn. Nghỉ đủ mới chất lượng.",
            "Xen kẽ chạy nhanh và đi bộ/chạy chậm. Xuất phát vừa, nghỉ đủ.",
        ),
        "Shadow Boxing": copy_of(
            [
                "Đứng chân trước sau, gối mềm, tay gác má.",
                "Đấm thẳng, móc, hook nhẹ, xoay hông, không khóa khuỷu.",
                "Di chuyển bước nhỏ. Thở theo đòn.",
                "Không đấm hết lực vào không khí nếu vai chưa ấm.",
            ],
            ["Khóa khuỷu khi đấm thẳng.", "Đứng cứng chân.", "Nín thở."],
            "Xoay hông, vai thả. Đây là cardio, không phải đấm bao nặng.",
            "Đấm tưởng tượng, xoay hông, chân luôn mềm. Giữ nhịp thở.",
        ),
        "Steady-State Rowing Machine": copy_of(
            [
                "Cùng kỹ thuật chèo: chân–thân–tay. Chọn nhịp đều 20–24 lần/phút nếu mới.",
                "Lưng thẳng, vai thả. Sức cản vừa nói được câu.",
                "Giữ đều đến hết thời gian. Không tăng đột ngột rồi chết.",
                "Kết thúc 1–2 phút rất nhẹ rồi rời máy.",
            ],
            ["Gù lưng.", "Chỉ kéo tay.", "Nhịp quá cao, biên độ ngắn."],
            "Đều và sạch. Tay là khâu cuối, chân là khâu chính.",
            "Chèo máy nhịp đều. Chân đẩy trước, tay kéo sau, lưng thẳng.",
        ),
        "Trail Run": copy_of(
            [
                "Chọn đường quen, giày bám. Khởi động đi bộ.",
                "Chạy/đi nhanh theo địa hình; xuống dốc ngắn bước, không thả trôi.",
                "Nhìn 2–3 mét phía trước. Giảm tốc trên đất trơn.",
                "Mang nước nếu buổi dài.",
            ],
            ["Chạy xuống dốc mất kiểm soát.", "Tai nghe quá to, không nghe xe/chó.", "Giày trơn."],
            "An toàn địa hình trên tốc độ. Đi bộ đoạn khó vẫn là buổi tốt.",
            "Chạy hoặc đi nhanh ngoài đường mòn. Bước ngắn khi xuống dốc, ưu tiên bám đường.",
        ),
        "Treadmill Run": copy_of(
            [
                "Bám tay vịn khi lên. Bắt đầu đi bộ, rồi chạy tốc độ nói được câu ngắn.",
                "Tay buông khi vững, nhìn trước, không nhìn xuống băng.",
                "Không cầm tay vịn lúc chạy (làm méo bước). Giảm tốc, đi bộ, rồi dừng.",
                "Xuống khi băng đã chậm.",
            ],
            ["Cầm tay vịn khi chạy.", "Nhìn xuống băng.", "Nhảy khỏi máy còn chạy."],
            "Tốc độ vừa. Luôn giảm tốc trước khi xuống.",
            "Chạy máy chạy bộ: bắt đầu chậm, không bám tay vịn khi chạy, giảm tốc trước khi xuống.",
        ),
    }
    return table.get(name)


def family(name: str, pattern: str, role: str) -> str:
    n = _n(name)
    if name in OVERRIDES:
        return "override"
    if role == "mobility" or "stretch" in n:
        return "stretch"
    if role == "cardio" or n in {
        "jumping jack",
        "jump rope",
        "burpee",
        "man maker",
        "battle ropes",
        "shadow boxing",
    }:
        return "cardio"
    if "wood chop" in n or "woodchop" in n:
        return "chop"
    if "pallof" in n:
        return "pallof"
    if "dead bug" in n:
        return "dead_bug"
    if "bird dog" in n:
        return "bird_dog"
    if "plank" in n:
        return "plank"
    if "crunch" in n or "sit-up" in n or "situp" in n or n.endswith("v-up"):
        return "crunch"
    if "russian twist" in n:
        return "twist"
    if "side bend" in n:
        return "side_bend"
    if "mountain climber" in n:
        return "climber"
    if "hollow" in n:
        return "hollow"
    if "farmers carry" in n or "farmer" in n:
        return "carry"
    if "shrug" in n:
        return "shrug"
    if "upright row" in n:
        return "upright"
    if "face pull" in n:
        return "face_pull"
    if "pullover" in n:
        return "pullover"
    if "fly" in n or "pec" in n and "reverse" in n:
        return "fly"
    if "lateral raise" in n or "front raise" in n:
        return "raise"
    if "rear delt" in n:
        return "rear_fly"
    if "curl" in n and "leg" not in n and "hamstring" not in n:
        return "curl"
    if "pushdown" in n or "push down" in n or "tricep" in n or "skull" in n or "overhead" in n and "extension" in n:
        return "tricep"
    if "extension" in n and ("leg" in n or "quad" in n):
        return "leg_ext"
    if "leg curl" in n or "hamstring curl" in n:
        return "leg_curl"
    if "calf" in n or "tibialis" in n:
        return "calf"
    if "abduction" in n or "adduction" in n or "kickback" in n:
        return "glute_iso"
    if "wrist" in n:
        return "wrist"
    if "hip thrust" in n or "glute bridge" in n or "frog pump" in n:
        return "bridge"
    if "good morning" in n:
        return "gm"
    if "back extension" in n:
        return "back_ext"
    if "swing" in n:
        return "swing"
    if "pull through" in n:
        return "pull_through"
    if "romanian" in n or "rdl" in n:
        return "rdl"
    if "deadlift" in n or "rack pull" in n:
        return "deadlift"
    if "lunge" in n or "split squat" in n or "bulgarian" in n or "step" in n and "up" in n:
        return "lunge"
    if "leg press" in n or "hack squat" in n or "belt squat" in n:
        return "leg_press"
    if "squat" in n or "wall sit" in n:
        return "squat"
    if "dip" in n:
        return "dip"
    if "push-up" in n or "push up" in n:
        return "pushup"
    if "bench" in n or "chest press" in n or "floor press" in n:
        return "bench"
    if "overhead press" in n or "military" in n or "arnold" in n or "push press" in n or "push jerk" in n or "landmine press" in n or "thruster" in n:
        return "ohp"
    if "pull-up" in n or "pull up" in n or "chin" in n:
        return "pullup"
    if "pulldown" in n or "lat " in n:
        return "pulldown"
    if "inverted" in n or "table" in n and "row" in n:
        return "inv_row"
    if "row" in n:
        return "row"
    if "superman" in n:
        return "superman"
    if pattern == "core":
        return "core_generic"
    if pattern == "hinge":
        return "rdl"
    if pattern == "squat":
        return "squat"
    if pattern == "h_push":
        return "bench"
    if pattern == "v_push":
        return "ohp"
    if pattern in {"h_pull"}:
        return "row"
    if pattern in {"v_pull", "vertical_pull"}:
        return "pulldown"
    return "generic"


def author(row: dict[str, Any]) -> Copy:
    name = row["name_en"]
    if name in OVERRIDES:
        return OVERRIDES[name]
    sc = stretch_copy(name)
    if sc:
        return sc
    cc = cardio_copy(name)
    if cc:
        return cc
    n = _n(name)
    k = kind(name, row.get("equipment") or "")
    f = flags(name)
    w = load_word(k)
    fam = family(name, row.get("movement_pattern") or "", row.get("movement_role") or "")
    builders = {
        "squat": _build_squat,
        "lunge": _build_lunge,
        "leg_press": _build_leg_press,
        "deadlift": _build_deadlift,
        "rdl": _build_rdl,
        "gm": _build_gm,
        "bridge": _build_bridge,
        "back_ext": _build_back_ext,
        "pull_through": _build_pull_through,
        "bench": _build_bench,
        "pushup": _build_pushup,
        "dip": _build_dip,
        "ohp": _build_ohp,
        "row": _build_row,
        "inv_row": _build_inv_row,
        "pullup": _build_pullup,
        "pulldown": _build_pulldown,
        "shrug": _build_shrug,
        "face_pull": _build_face_pull,
        "pullover": _build_pullover,
        "fly": _build_fly,
        "raise": _build_raise,
        "rear_fly": _build_rear_fly,
        "curl": _build_curl,
        "tricep": _build_tricep,
        "leg_ext": _build_leg_ext,
        "leg_curl": _build_leg_curl,
        "calf": _build_calf,
        "glute_iso": _build_glute_iso,
        "wrist": _build_wrist,
        "crunch": _build_crunch,
        "twist": _build_twist,
        "chop": _build_chop,
        "side_bend": _build_side_bend,
        "dead_bug": _build_dead_bug,
        "bird_dog": _build_bird_dog,
        "plank": _build_plank,
        "superman": _build_superman,
        "core_generic": _build_core_generic,
        "upright": _build_upright,
        "generic": _build_generic,
    }
    fn = builders.get(fam, _build_generic)
    return fn(name, n, k, w, f, row)


def _setup_load(k: str, w: str, seated: bool, extra: str = "") -> str:
    if k == "cable":
        base = f"Chọn mức tạ vừa trên máy cáp, nắm {w} chắc."
    elif k == "band":
        base = "Cố định dây kháng lực chắc, đứng vào vị trí đến khi dây căng nhẹ lúc bắt đầu."
    elif k == "machine":
        base = "Chỉnh ghế/đệm vừa tầm, chọn mức tạ, nắm tay cầm."
    elif k == "smith":
        base = "Đứng vào máy trượt tạ, xoay thanh mở khóa khi đã sẵn sàng."
    elif k == "bb":
        base = "Đặt thanh tạ chắc, nắm vừa tay, tháo khỏi giá có kiểm soát."
    elif k == "db":
        base = "Nhấc tạ đơn chắc, cổ tay thẳng, không để tạ đu đưa."
    elif k == "kb":
        base = "Nắm quai tạ ấm chắc, vai kéo xuống."
    elif k == "pack":
        base = "Đeo hoặc ôm balo chắc, tạ trong balo không xô lệch."
    else:
        base = "Vào tư thế, thân ổn định."
    if seated:
        base = "Ngồi tựa lưng nếu có đệm. " + base
    return (base + " " + extra).strip()


def _build_squat(name, n, k, w, f, row) -> Copy:
    goblet = "goblet" in n
    front = "front" in n and "split" not in n
    overhead = "overhead squat" in n
    pause = "pause" in n
    jump = "jump" in n
    box = "box" in n
    belt = "belt" in n
    if goblet:
        setup = f"Ôm {w} sát ngực, khuỷu xuống. Chân rộng vai, mũi hơi xoay ra."
    elif front:
        setup = f"Đặt {w} trước vai (khuỷu cao) hoặc ôm tạ trước ngực. Chân rộng vai."
    elif overhead:
        setup = f"Đưa {w} lên thẳng trên đầu, tay khóa, vai chủ động. Chân rộng vai."
    elif belt:
        setup = "Cài đai hông vào máy, chọn tạ, đứng chân rộng vai."
    elif k == "band":
        setup = "Đứng lên dây, kéo dây lên vai hoặc cầm trước ngực. Chân rộng vai."
    elif k in {"bw", "other"}:
        setup = "Đứng chân rộng vai, mũi hơi xoay ra. Tay đưa ra trước để thăng bằng."
    elif k == "db":
        setup = _setup_load(k, w, False) + " Tạ đơn hai bên vai hoặc trước ngực. Chân rộng vai, mũi hơi xoay ra."
    elif k == "kb":
        setup = _setup_load(k, w, False) + " Tạ ấm trước ngực hoặc hai bên. Chân rộng vai, mũi hơi xoay ra."
    else:
        setup = _setup_load(k, w, False) + " Đặt tạ sau vai hoặc trước ngực tùy bài. Chân rộng vai, mũi hơi xoay ra."
    steps = [
        setup,
        BRACE + " " + FOOT,
        "Đẩy hông ra sau rồi ngồi xuống, gối theo mũi chân.",
        "Hạ đến đùi gần song song (hoặc chạm hộp nếu ngồi xuống hộp). Lưng không tròn.",
        "Đẩy sàn đứng lên, siết mông. Không khóa gối giật.",
    ]
    if pause:
        steps[3] = "Hạ xuống và dừng 1–2 giây ở đáy, rồi mới đứng."
    if jump:
        steps[4] = "Đẩy sàn bật lên, tiếp đất gối mềm, rồi lập tức vào tư thế ngồi xổm tiếp."
        steps.append("Chọn biên độ thấp nếu gối khó chịu.")
    return copy_of(
        steps[:6],
        ["Gối sụp vào trong.", "Gót nhấc.", "Cong lưng ở đáy."],
        "Nếu gót nhấc: mở mũi chân hoặc giảm độ sâu. Học không tạ sạch trước khi thêm tạ.",
        f"{row['name_vi']}: ngồi xổm, hông ra sau, gối theo mũi chân, cả bàn chân trên sàn.",
    )


def _build_lunge(name, n, k, w, f, row) -> Copy:
    reverse = "reverse" in n
    bg = "bulgarian" in n or "rear" in n and "elevat" in n or "chân sau kê" in (row.get("name_vi") or "")
    walking = "walk" in n
    step = "step" in n
    if bg:
        setup = "Đặt mu chân sau trên ghế thấp. Chân trước đủ xa để gối trước không vượt quá mũi quá mức khó chịu."
        action = "Hạ gối sau xuống gần sàn, thân hơi thẳng. Đẩy gót trước đứng lên."
    elif reverse:
        setup = _setup_load(k, w, False) + " Đứng thẳng, chân rộng hông."
        action = "Bước chân ra sau, hạ gối sau gần sàn. Đẩy gót trước để về đứng."
    elif walking:
        setup = _setup_load(k, w, False) + " Đứng thẳng."
        action = "Bước dài về trước, hạ gối sau gần sàn, rồi bước chân sau vượt lên cái tiếp."
    elif step:
        setup = _setup_load(k, w, False) + " Đứng trước bục chắc, thấp vừa."
        action = "Bước một chân lên bục, đẩy gót trên bục để đứng thẳng, rồi bước xuống có kiểm soát."
    else:
        setup = _setup_load(k, w, False) + " Đứng thẳng."
        action = "Bước chân trước, hạ gối sau gần sàn. Đẩy gót trước về đứng."
    return copy_of(
        [
            setup,
            BRACE,
            action,
            "Gối trước đi cùng hướng mũi chân, không sụp vào trong.",
            "Làm xong một bên đủ số cái rồi đổi, hoặc luân phiên nếu đang bước tới.",
        ],
        ["Gối trước sụp vào trong.", "Bước quá ngắn, gối bị đẩy quá mũi không kiểm soát.", "Cúi gù lưng."],
        "Thu ngắn bước nếu gối đau. Ghế càng cao với chân sau kê ghế càng khó — bắt đầu ghế thấp.",
        f"{row['name_vi']}: một chân chịu lực, hạ gối sau gần sàn, thân ổn định.",
    )


def _build_leg_press(name, n, k, w, f, row) -> Copy:
    hack = "hack" in n
    setup = "Ngồi máy, lưng/hông dán đệm, chân trên bàn đạp rộng vai, mũi hơi xoay ra."
    if hack:
        setup = "Vào máy đẩy chéo, vai dưới đệm, chân trên bàn đạp rộng vai."
    return copy_of(
        [
            setup,
            "Mở khóa máy. Hạ tạ bằng cách gập gối, hông không nhấc khỏi đệm.",
            "Hạ đến đùi gần ngực hoặc đến tầm lưng còn dán đệm.",
            "Đẩy bàn đạp, không khóa gối giật. Thở ra khi đẩy.",
        ],
        ["Hông nhấc, lưng tròn.", "Khóa gối bật.", "Hạ quá sâu đến mất tiếp xúc đệm."],
        "Chân cao trên bàn đạp nhấn mông/sau đùi hơn; chân thấp nhấn đùi trước hơn. Vẫn giữ lưng dán.",
        f"{row['name_vi']}: đẩy bằng chân trên máy, lưng dán đệm, không khóa gối giật.",
    )


def _build_deadlift(name, n, k, w, f, row) -> Copy:
    sumo = "sumo" in n
    trap = "trap" in n
    rack = "rack" in n
    if sumo:
        stance = "Chân rất rộng, mũi xoay ra, tay nắm trong hai chân. Ống chân sát tạ."
    elif trap:
        stance = "Đứng trong thanh lục giác, chân rộng hông, nắm tay cầm hai bên."
    elif rack:
        stance = "Thanh đặt trên giá khoảng dưới gối. Ống chân sát thanh, nắm ngoài gối."
    else:
        stance = "Chân rộng hông, thanh trên giữa bàn chân, ống chân sát thanh, nắm ngoài gối."
    return copy_of(
        [
            stance,
            "Hông ra sau, lưng thẳng, ngực ưỡn nhẹ, kéo hết độ chùng của tạ. " + BRACE,
            "Đẩy sàn, tạ sát chân. Vai và hông lên cùng nhịp.",
            "Đứng thẳng, siết mông, không ưỡn thắt lưng. Hạ hông ra sau trước.",
        ],
        ["Cong lưng.", "Tạ trôi xa ống chân.", "Giật tạ trước khi kéo căng tay."],
        "Tạ chỉ nặng đến mức lưng thẳng mọi cái. Sumo thì gối theo mũi chân xoay ra.",
        f"{row['name_vi']}: nhấc tạ từ thấp bằng chân và hông, lưng thẳng, tạ sát người.",
    )


def _build_rdl(name, n, k, w, f, row) -> Copy:
    single = f["single"] or "kickstand" in n or "b-stance" in n or "single-leg" in n
    deficit = "deficit" in n
    setup = _setup_load(k, w, False) + " Chân rộng hông, gối mềm, tạ trước đùi."
    if single:
        setup = _setup_load(k, w, False) + " Đứng một chân trụ (hoặc gót sau chỉ chạm nhẹ). Gối trụ mềm."
    if deficit:
        setup += " Đứng trên bục thấp chắc."
    action = "Đẩy hông ra sau, tạ trượt sát chân, lưng thẳng, đến khi sau đùi căng."
    if single:
        action = "Đẩy hông ra sau, chân sau duỗi, lưng thẳng, hông vuông."
    return copy_of(
        [
            setup,
            BRACE,
            action,
            "Không cong lưng. Dừng trước khi mất thẳng lưng.",
            "Đẩy hông ra trước đứng lên, siết mông.",
        ],
        ["Cong lưng.", "Gập gối quá sâu thành ngồi xổm.", "Tạ rời xa chân."],
        "Gối giữ độ mềm suốt. Cảm giác sau đùi và mông, không phải 'cúi chạm đất'.",
        f"{row['name_vi']}: gập hông, lưng thẳng, tạ sát người, đứng lên bằng mông và sau đùi.",
    )


def _build_gm(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            _setup_load(k, w, False) + " Tạ sau vai hoặc ôm trước ngực. Chân rộng vai, gối mềm.",
            BRACE + " Lưng thẳng như tấm ván.",
            "Đẩy hông ra sau, thân cúi đến căng sau đùi.",
            "Đẩy hông đứng lên, siết mông. Không cong lưng.",
        ],
        ["Cong lưng.", "Gập gối quá nhiều.", "Cúi quá sâu mất thẳng lưng."],
        "Tạ nhẹ hơn squat. Chỉ cúi đến mức lưng còn thẳng.",
        f"{row['name_vi']}: cúi từ hông, lưng thẳng, tập sau đùi.",
    )


def _build_bridge(name, n, k, w, f, row) -> Copy:
    thrust = "thrust" in n
    single = f["single"] or "b-stance" in n or "single" in n
    frog = "frog" in n
    if thrust:
        setup = "Lưng trên tựa ghế, chân trên sàn. Tạ đặt trên hông (có đệm). Cằm thu."
    else:
        setup = "Nằm ngửa, gối gập, chân trên sàn. Tay thả hoặc giữ tạ trên hông."
    if frog:
        setup = "Nằm ngửa, lòng bàn chân chạm nhau, gối mở. Tay thả."
    if single:
        setup += " Một chân nâng hoặc gót sau chỉ chạm nhẹ."
    return copy_of(
        [
            setup,
            "Siết bụng. Đẩy hông lên bằng gót, siết mông ở đỉnh. Không ưỡn thắt lưng.",
            "Vai–hông–gối gần thẳng hàng ở đỉnh.",
            "Hạ hông chậm, không thả sập.",
        ],
        ["Ưỡn thắt lưng thay vì siết mông.", "Đẩy bằng mũi chân, gót nhấc.", "Cằm ngẩng, cổ căng."],
        "Cằm thu, sườn hạ. Nếu chuột rút sau đùi: chân đặt gần mông hơn một chút.",
        f"{row['name_vi']}: đẩy hông lên, siết mông, không bù bằng ưỡn thắt lưng.",
    )


def _build_back_ext(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Kê chân máy/ghế 45°, đệm ngang hông dưới. Tay trước ngực hoặc sau đầu nhẹ.",
            "Cúi từ hông, lưng thẳng, đến căng sau đùi/lưng dưới.",
            "Duỗi hông lên đến thân thẳng — không ưỡn quá mức.",
            "Hạ chậm. Tạ đơn ôm ngực chỉ khi đã chắc.",
        ],
        ["Ưỡn thắt lưng ở đỉnh.", "Cong lưng khi hạ.", "Dùng giật."],
        "Dừng khi thân thẳng hàng với chân. Ưỡn quá dễ đau lưng.",
        f"{row['name_vi']}: cúi và duỗi hông trên ghế 45°, lưng thẳng, không ưỡn quá.",
    )


def _build_pull_through(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Gắn dây giữa hai chân từ máy cáp thấp. Đứng quay lưng máy, bước ra, dây căng, nắm giữa hai chân.",
            BRACE + " Gối mềm.",
            "Đẩy hông ra sau, để dây kéo tay về sau. Lưng thẳng.",
            "Bật hông ra trước, siết mông. Tay chỉ giữ dây, không kéo bằng tay.",
        ],
        ["Kéo bằng tay.", "Cong lưng.", "Ngồi xổm thay vì gập hông."],
        "Nghĩ 'đẩy hông' chứ không 'kéo dây'. Tạ vừa.",
        f"{row['name_vi']}: dây đi giữa hai chân, gập hông rồi bật mông. Tay chỉ giữ, không kéo.",
    )


def _build_bench(name, n, k, w, f, row) -> Copy:
    incline = f["incline"]
    decline = f["decline"]
    close = f["close"]
    floor = "floor" in n
    machine = k in {"machine", "cable", "smith"}
    if floor:
        setup = "Nằm sàn, gối gập. Nhấc tạ đơn lên, bả vai xuống sàn."
        depth = "Hạ đến khuỷu chạm sàn nhẹ, dừng, rồi đẩy."
    elif decline:
        setup = "Kẹp chân đệm ghế dốc xuống. Nằm, mắt dưới thanh/tạ. Bả vai kéo lại."
        depth = "Hạ về ngực dưới. Không nảy tạ."
    elif incline:
        setup = "Ghế dốc khoảng 15–45°. Nằm, bả vai kéo xuống đệm. Nắm " + w + "."
        depth = "Hạ về ngực trên. Khuỷu không xòe 90°."
    else:
        setup = ("Ngồi/nằm máy, nắm tay cầm ngang ngực. " if machine else "Nằm ghế phẳng, mắt dưới tạ, chân chắc sàn. Bả vai kéo xuống. Nắm ") + w + "."
        depth = "Hạ về ngực giữa–dưới, khuỷu 45–75° so với thân."
    if close:
        depth = "Nắm hẹp hơn vai, khuỷu sát sườn hơn. Hạ về ngực dưới."
    return copy_of(
        [
            setup,
            BRACE,
            depth,
            "Đẩy lên đến tay gần thẳng, không đập khóa khuỷu. Thở ra khi đẩy.",
        ],
        ["Khuỷu xòe 90°.", "Nảy tạ trên ngực.", "Mông trượt, ưỡn cổ."],
        "Ghế dốc cao quá 45° dễ thành đẩy vai. Cần người hỗ trợ khi tạ đòn nặng.",
        f"{row['name_vi']}: đẩy tạ từ ngực lên, bả vai ổn định, không nảy tạ.",
    )


def _build_pushup(name, n, k, w, f, row) -> Copy:
    knee = "knee" in n
    incline = "incline" in n or "tay trên" in (row.get("name_vi") or "")
    decline = "decline" in n or "chân trên" in (row.get("name_vi") or "")
    diamond = "diamond" in n
    setup = "Plank cao, tay dưới vai, thân thẳng."
    if knee:
        setup = "Chống tay và gối, thân thẳng từ đầu đến gối."
    if incline:
        setup = "Tay trên ghế/bàn chắc, chân lùi, thân thẳng."
    if decline:
        setup = "Chân trên ghế, tay trên sàn, thân thẳng — bài nặng hơn."
    if diamond:
        setup += " Hai tay gần nhau tạo hình kim cương dưới ngực."
    return copy_of(
        [
            setup,
            BRACE,
            "Hạ ngực giữa hai tay, khuỷu 30–45°. Không xòe ngang vai.",
            "Đẩy lên, hông không sệ. Thở ra khi đẩy.",
        ],
        ["Hông sệ.", "Khuỷu xòe 90°.", "Chỉ gập cổ xuống sàn."],
        "Tay càng cao càng dễ. Kim cương nhấn tay sau hơn.",
        f"{row['name_vi']}: thân thẳng, hạ ngực, đẩy lên. Điều chỉnh độ dốc cho vừa sức.",
    )


def _build_dip(name, n, k, w, f, row) -> Copy:
    machine = k == "machine" or "machine" in n
    setup = "Nắm song song, nhảy lên chống thẳng tay, vai kéo xuống, thân hơi nghiêng trước."
    if machine:
        setup = "Ngồi/kẹp máy dip, chọn trợ lực hoặc tạ, nắm tay cầm, vai hạ."
    return copy_of(
        [
            setup,
            "Hạ người, gập khuỷu, đến vai ngang khuỷu nếu khớp cho phép.",
            "Không buông vai lên tai. Đẩy lên chống thẳng tay có kiểm soát.",
            "Dừng nếu đau phía trước vai.",
        ],
        ["Buông vai.", "Hạ quá sâu.", "Đung đưa lấy đà."],
        "Nghiêng trước nhấn ngực; thân thẳng nhấn tay sau. Người mới dùng máy trợ hoặc chống đẩy hẹp.",
        f"{row['name_vi']}: hạ người giữa hai tay chống, rồi đẩy lên. Vai phải hạ và ổn định.",
    )


def _build_ohp(name, n, k, w, f, row) -> Copy:
    arnold = "arnold" in n
    push = "push press" in n or "jerk" in n
    landmine = "landmine" in n
    thruster = "thruster" in n
    seated = f["seated"]
    setup = _setup_load(k, w, seated) + " Tạ ngang vai, khuỷu hơi trước thân, cổ tay thẳng."
    if landmine:
        setup = "Một đầu thanh cắm đất/góc tường. Nắm đầu kia ngang vai, chân rộng."
    if arnold:
        setup = "Ngồi, tạ đơn ngang vai, lòng bàn tay hướng vào mặt, khuỷu trước thân."
    press = "Đẩy tạ lên trên đầu, đầu hơi thụt qua, không ưỡn thắt lưng. Khóa nhẹ ở đỉnh rồi hạ về vai."
    if arnold:
        press = "Đẩy lên đồng thời xoay lòng bàn tay ra trước. Hạ về, xoay lòng bàn tay vào mặt."
    if landmine:
        press = "Đẩy thanh lên đường chéo trước–trên. Hạ về vai. Thân không xoay mất kiểm soát."
    if push:
        press = "Chùng gối nhẹ rồi bật chân hỗ trợ đẩy tạ lên. Hạ về vai có kiểm soát."
    if thruster:
        setup = _setup_load(k, w, False) + " Tạ ngang vai."
        press = "Ngồi xổm, rồi đứng lên kéo theo đẩy tạ lên đầu một mạch. Hạ tạ về vai trước cái sau."
    return copy_of(
        [
            setup,
            BRACE,
            press,
            "Hạ chậm. Đau vai nhói thì giảm tạ hoặc đổi bài đẩy trước mặt.",
        ],
        ["Ưỡn thắt lưng bù.", "Đẩy ra trước quá nhiều mất thăng bằng.", "Khóa khuỷu giật."],
        "Siết bụng như sắp bị đấm để khỏi ưỡn lưng. Ngồi thì dễ giữ lưng hơn đứng.",
        f"{row['name_vi']}: đẩy tạ lên trên đầu, bụng siết, không lấy thắt lưng bù.",
    )


def _build_row(name, n, k, w, f, row) -> Copy:
    pendlay = "pendlay" in n
    meadows = "meadows" in n
    seated = "seated" in n or k == "machine" and "row" in n
    chest = "chest-supported" in n or "chest supported" in n or "chống ngực" in (row.get("name_vi") or "")
    gorilla = "gorilla" in n
    if pendlay:
        setup = "Thanh trên sàn, cúi lưng thẳng song song sàn, nắm sấp."
        pull = "Kéo thanh lên bụng dưới, thân im. Hạ chạm sàn mỗi cái, không nảy."
    elif meadows:
        setup = "Một đầu thanh cắm đất. Cúi, nắm một tay đầu thanh, chân vững."
        pull = "Kéo thanh về hông, khuỷu sát. Hạ chậm. Đổi bên."
    elif chest:
        setup = "Nằm sấp trên ghế dốc, ngực tựa đệm, tạ treo thẳng."
        pull = "Kéo tạ về hông/thấp ngực, siết lưng. Hạ hết căng."
    elif seated:
        setup = _setup_load(k, w, True) + " Chân trên bàn đạp, lưng thẳng, tay duỗi."
        pull = "Kéo tay cầm về bụng, ngực ưỡn, siết lưng giữa. Duỗi tay chậm, không gù."
    elif gorilla:
        setup = "Hai tạ ấm giữa hai chân, đứng rộng, cúi hông, lưng thẳng, nắm hai quai."
        pull = "Kéo một tạ về hông, tạ kia giữ sàn. Luân phiên, thân không xoay mạnh."
    else:
        setup = _setup_load(k, w, False) + " Cúi hông, lưng thẳng, tạ treo."
        pull = "Kéo tạ về hông, khuỷu sát sườn. Hạ chậm đến tay gần thẳng."
    if f["single"]:
        pull += " Làm xong một bên rồi đổi."
    return copy_of(
        [
            setup,
            BRACE,
            pull,
            "Không giật bằng thắt lưng. Vai kéo xuống xa tai.",
        ],
        ["Cong lưng.", "Giật đà thân.", "Nhún vai, kéo bằng cổ."],
        "Nghĩ kéo khuỷu về túi quần sau. Chống ngực thì lưng dễ thẳng hơn cúi người.",
        f"{row['name_vi']}: kéo tạ về thân, lưng thẳng, siết giữa lưng.",
    )


def _build_inv_row(name, n, k, w, f, row) -> Copy:
    elev = "elevated" in n or "chân trên" in (row.get("name_vi") or "")
    setup = "Nằm dưới bàn chắc hoặc xà thấp, nắm cạnh bàn, thân thẳng, gót sàn."
    if elev:
        setup = "Gót kê ghế, nắm cạnh bàn, thân thẳng gần nằm ngang — nặng hơn."
    return copy_of(
        [
            setup,
            BRACE + " Kéo bả vai xuống trước khi gập khuỷu.",
            "Kéo ngực về cạnh bàn/xà, siết lưng.",
            "Hạ chậm, hông không sệ.",
        ],
        ["Hông sệ.", "Kéo cằm.", "Vai nhún."],
        "Bàn phải chắc, không lật. Chân càng cao càng khó.",
        f"{row['name_vi']}: nằm kéo ngực về cạnh bàn/xà, thân thẳng.",
    )


def _build_pullup(name, n, k, w, f, row) -> Copy:
    chin = "chin" in n
    assist = "assist" in n or "band assisted" in n
    wide = f["wide"]
    neu = f["neutral"]
    weighted = "weighted" in n
    grip = "Nắm sấp, rộng hơn vai."
    if chin:
        grip = "Nắm ngửa (lòng bàn tay về bạn), hẹp hơn vai một chút."
    if neu:
        grip = "Nắm tay cầm dọc, lòng bàn tay đối diện."
    if wide:
        grip = "Nắm sấp rộng hơn vai — đừng quá rộng đến vai cấn."
    if assist:
        grip += " Đặt gối/bàn chân vào bệ trợ hoặc vòng dây."
    if weighted:
        grip += " Đai tạ hoặc tạ kẹp chân chỉ khi pull-up thường đã chắc."
    return copy_of(
        [
            grip + " Treo chủ động, vai kéo xuống xa tai.",
            BRACE,
            "Kéo khuỷu xuống, ngực lên, cằm qua xà.",
            "Hạ chậm đến tay gần thẳng, không thả võng vai.",
        ],
        ["Đá chân lấy đà.", "Kéo cằm bằng cổ.", "Nhún vai rồi giật."],
        "Chưa được rep đầy đủ: dây trợ, máy trợ, hoặc kéo người nằm.",
        f"{row['name_vi']}: treo chủ động, kéo cằm qua xà, hạ chậm.",
    )


def _build_pulldown(name, n, k, w, f, row) -> Copy:
    straight = "straight-arm" in n or "straight arm" in n or "pullover" in n and "machine" in n
    single = f["single"]
    kneeling = "kneel" in n
    if straight:
        return copy_of(
            [
                "Gắn thanh hoặc dây cao. Đứng hơi cúi hông, tay gần thẳng, nắm cao.",
                BRACE + " Vai kéo xuống.",
                "Kéo tay cầm hình cung về phía đùi, siết xô. Khuỷu chỉ hơi mềm.",
                "Đưa tay lên chậm đến căng xô, không ưỡn thắt lưng.",
            ],
            ["Gập khuỷu thành đẩy tay sau.", "Ưỡn thắt lưng.", "Đứng quá gần, mất quãng trên đầu."],
            "Giữ tay gần thẳng. Cảm giác sườn sau, không phải tay sau.",
            f"{row['name_vi']}: kéo cáp từ trên xuống với tay gần thẳng để tập xô.",
        )
    setup = "Ngồi, kẹp đùi, nắm thanh. Lòng bàn tay ra trước trừ khi bài nắm dọc/ngửa."
    if kneeling:
        setup = "Quỳ, dây cố định trên cao, nắm hai đầu dây, thân thẳng."
    if single:
        setup = "Ngồi hoặc quỳ, nắm một bên, thân ổn định."
    return copy_of(
        [
            setup,
            "Tay duỗi, vai kéo xuống trước khi gập khuỷu. " + BRACE,
            "Kéo về ngực trên, không ra sau gáy. Siết xô.",
            "Để tạ lên chậm, tay gần thẳng.",
        ],
        ["Kéo sau gáy.", "Ngả quá nhiều.", "Giật đà."],
        "Kéo về xương đòn. Nắm dọc thường dễ chịu vai hơn nắm rộng.",
        f"{row['name_vi']}: kéo từ trên về ngực, vai hạ, không kéo ra gáy.",
    )


def _build_shrug(name, n, k, w, f, row) -> Copy:
    behind = "behind" in n
    setup = _setup_load(k, w, False) + " Tạ dọc người, tay thẳng, vai thả."
    if behind:
        setup = "Thanh sau người, tay thẳng. Chỉ nhún nếu vai dễ chịu."
    return copy_of(
        [
            setup,
            BRACE,
            "Nhún vai lên về tai, siết cầu vai 1 giây. Không xoay vai vòng tròn.",
            "Hạ chậm hết căng. Cổ trung lập.",
        ],
        ["Xoay vai vòng, dễ cấn.", "Lắc người lấy đà.", "Đầu thè về trước."],
        "Nhún thẳng lên–xuống. Tạ vừa để còn hạ hết vai.",
        f"{row['name_vi']}: nhún vai lên rồi hạ chậm. Không xoay vòng khớp vai.",
    )


def _build_face_pull(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Gắn dây ngang mặt hoặc hơi cao. Nắm hai đầu, bước ra, tay duỗi.",
            BRACE,
            "Kéo về thái dương, khuỷu cao ngang vai, tách dây, siết vai sau.",
            "Đưa ra chậm. Không giật thắt lưng.",
        ],
        ["Kéo xuống ngực thành chèo.", "Nhún vai.", "Tạ nặng phải giật."],
        "Tạ nhẹ, siết đã. Bài vai sau và tư thế đầu–vai.",
        f"{row['name_vi']}: kéo dây về gần mặt, khuỷu ngang vai, siết sau vai.",
    )


def _build_pullover(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            _setup_load(k, w, False) + " Nằm ghế hoặc đứng cúi nhẹ với cáp cao, tay gần thẳng.",
            BRACE + " Sườn hạ.",
            "Đưa tạ/cáp hình cung từ trên đầu về phía hông/ngực, siết xô.",
            "Trả về căng xô, không ưỡn thắt lưng.",
        ],
        ["Ưỡn thắt lưng.", "Gập khuỷu thành tay sau.", "Tạ quá nặng, mất cung."],
        "Khuỷu mềm cố định. Cảm giác xô và ngực trên tùy góc, không phải cổ.",
        f"{row['name_vi']}: tay gần thẳng, kéo hình cung để căng rồi siết xô.",
    )


def _build_fly(name, n, k, w, f, row) -> Copy:
    reverse = "reverse" in n
    if reverse:
        return _build_rear_fly(name, n, k, w, f, row)
    setup = _setup_load(k, w, f["seated"])
    if k == "db":
        setup = "Nằm ghế, tạ đơn trên ngực, khuỷu hơi cong và giữ nguyên góc."
    if k == "cable":
        setup = "Đứng giữa hai cột cáp hoặc nằm ghế giữa hai cáp, nắm tay cầm, khuỷu mềm cố định."
    if k == "machine":
        setup = "Ngồi máy mở ngực, khuỷu trên đệm hoặc nắm tay cầm, lưng dán."
    high = "high-to-low" in n
    low = "low-to-high" in n
    path = "Mở tay sang hai bên đến căng ngực, rồi khép về giữa."
    if high:
        path = "Kéo từ cao xuống thấp vào trước bụng dưới, siết ngực dưới."
    if low:
        path = "Kéo từ thấp lên cao vào trước ngực trên."
    return copy_of(
        [
            setup,
            BRACE,
            path + " Không gập khuỷu thành chống đẩy.",
            "Không mở quá rộng đến đau vai trước. Khép có kiểm soát.",
        ],
        ["Gập khuỷu quá nhiều.", "Mở quá rộng.", "Nhún vai, ưỡn lưng."],
        "Khuỷu giữ một góc suốt. Tạ nhẹ hơn bench.",
        f"{row['name_vi']}: mở rồi khép tay theo hình cung, khuỷu gần như không đổi góc, tập ngực.",
    )


def _build_raise(name, n, k, w, f, row) -> Copy:
    front = "front" in n
    lean = "lean" in n
    setup = _setup_load(k, w, f["seated"]) + " Tạ dọc người hoặc trước đùi."
    if lean:
        setup = "Nắm khung máy, nghiêng người ra xa, tay cầm cáp thấp hoặc tạ, tay thả."
    move = "Nâng tay ra trước đến ngang vai, lòng bàn tay xuống." if front else "Nâng tay sang ngang đến ngang vai, úp nhẹ, khuỷu mềm."
    return copy_of(
        [
            setup,
            BRACE,
            move,
            "Hạ chậm 2–3 giây. Không lắc người. Không nâng cao quá đầu.",
        ],
        ["Lắc thân lấy đà.", "Nâng quá cao.", "Nhún cầu vai."],
        "Tạ nhẹ, siết giữa quãng. Dừng ngang vai.",
        f"{row['name_vi']}: nâng tay đến ngang vai, không lấy đà lưng.",
    )


def _build_rear_fly(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            _setup_load(k, w, f["seated"]) + " Cúi hông hoặc nằm sấp ghế, tay treo, khuỷu mềm.",
            BRACE,
            "Mở tay sang hai bên, siết vai sau. Không nhún cầu vai.",
            "Hạ chậm. Không biến thành chèo bằng cách gập khuỷu nhiều.",
        ],
        ["Gập khuỷu quá nhiều.", "Nhún vai.", "Giật đà thân."],
        "Tạ nhẹ. Cảm giác sau vai, như muốn bẻ hai tạ ra ngoài.",
        f"{row['name_vi']}: mở tay, siết vai sau, thân ổn định.",
    )


def _build_curl(name, n, k, w, f, row) -> Copy:
    preacher = "preacher" in n
    hammer = "hammer" in n or "búa" in n
    conc = "concentration" in n
    spider = "spider" in n
    zott = "zottman" in n
    reverse = f["reverse"] or "reverse grip" in n
    setup = _setup_load(k, w, f["seated"]) + " Tay dọc người, khuỷu sát sườn."
    if preacher:
        setup = "Nách trên mép đệm, mặt sau cánh tay dán đệm, nắm tạ lòng bàn tay lên."
    if conc:
        setup = "Ngồi, khuỷu chân trong đùi, tạ đơn buông thẳng, lòng bàn tay lên."
    if spider:
        setup = "Nằm sấp ghế dốc, ngực tựa, tay treo vuông góc sàn."
    path = "Gập khuỷu, nâng tạ, siết bắp tay, hạ chậm gần duỗi — không khóa giật."
    if hammer:
        path = "Lòng bàn tay đối diện (nắm dọc). Gập khuỷu, hạ chậm."
    if reverse:
        path = "Lòng bàn tay úp. Gập khuỷu, cẳng tay làm nhiều hơn. Tạ nhẹ."
    if zott:
        path = "Gập lòng bàn tay lên; ở đỉnh xoay úp rồi hạ. Tạ nhẹ."
    return copy_of(
        [
            setup,
            BRACE,
            path,
            "Khuỷu không chạy tới trước. Không lắc người.",
        ],
        ["Lắc thân.", "Khuỷu rời đệm tựa.", "Hạ rơi tạ."],
        "Hạ chậm quan trọng hơn kéo mạnh. Tạ vừa để khuỷu im.",
        f"{row['name_vi']}: gập khuỷu, khuỷu im, hạ chậm. Tập mặt trước cánh tay.",
    )


def _build_tricep(name, n, k, w, f, row) -> Copy:
    pushdown = "pushdown" in n or "push down" in n
    overhead = "overhead" in n
    kick = "kickback" in n
    setup = _setup_load(k, w, f["seated"])
    if pushdown:
        setup = "Gắn dây hoặc thanh cao. Khuỷu sát sườn, nắm, cẳng tay song song sàn."
        path = "Duỗi khuỷu đẩy xuống, siết tay sau, về chậm. Khuỷu không mở ra."
    elif overhead:
        setup = setup + " Đưa tạ lên trên đầu, khuỷu chỉ lên trời, sát tai."
        path = "Hạ tạ sau đầu bằng cách gập khuỷu, rồi duỗi lên. Không xòe khuỷu."
    elif kick:
        setup = "Cúi, khuỷu ghim sát sườn, cẳng tay vuông góc."
        path = "Duỗi tay ra sau, siết, rồi gập về. Thân im."
    else:
        path = "Chỉ gập–duỗi khuỷu, thân im, siết tay sau ở đỉnh, hạ chậm."
    return copy_of(
        [
            setup,
            BRACE,
            path,
            "Giảm tạ nếu phải giật vai hoặc hông.",
        ],
        ["Khuỷu xòe / chạy.", "Giật đà.", "Khóa khuỷu bật đau."],
        "Khuỷu như đóng đinh. Cảm giác sau cánh tay, không phải vai.",
        f"{row['name_vi']}: duỗi khuỷu có kiểm soát để tập tay sau. Khuỷu giữ im.",
    )


def _build_leg_ext(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Ngồi máy, trục khớp khớp với gối, đệm trước mắt cá. Lưng tựa.",
            "Duỗi gối nâng đệm, siết đùi trước 1 giây. Không bật.",
            "Hạ chậm, không thả rơi. Chân không khóa gối giật.",
            "Giảm tạ nếu phải nhấc mông.",
        ],
        ["Nhấc mông.", "Bật đà.", "Khóa gối mạnh."],
        "Tạ vừa, siết đỉnh. Đau gối: giảm biên độ, hỏi chuyên gia nếu đau kéo dài.",
        f"{row['name_vi']}: ngồi đá đùi trước, lưng tựa, hạ chậm.",
    )


def _build_leg_curl(name, n, k, w, f, row) -> Copy:
    lying = "lying" in n or "nằm" in n
    seated = "seated" in n or "ngồi" in n
    ball = "ball" in n or "towel" in n
    if ball:
        setup = "Nằm ngửa, gót trên bóng hoặc khăn trượt. Hông nâng nhẹ."
        path = "Kéo gót về mông, bóng/khăn trượt lại. Duỗi chân chậm, hông không sệ."
    elif lying:
        setup = "Nằm sấp máy, đệm sau gót, khớp gối khớp trục."
        path = "Cuốn gót về mông, siết sau đùi, hạ chậm."
    elif seated:
        setup = "Ngồi máy, đệm dưới bắp chân, đùi kẹp."
        path = "Cuốn gót xuống dưới ghế, siết, về chậm."
    else:
        setup = _setup_load(k, w, False)
        path = "Gập gối, gót về mông, hạ chậm."
    return copy_of(
        [
            setup,
            BRACE,
            path,
            "Không lấy thắt lưng giật. Đau gối: giảm tạ.",
        ],
        ["Giật hông.", "Thả rơi tạ.", "Trục máy lệch gối."],
        "Siết sau đùi ở đỉnh. Ưu tiên chậm hơn nặng.",
        f"{row['name_vi']}: gập gối để tập mặt sau đùi, hạ chậm.",
    )


def _build_calf(name, n, k, w, f, row) -> Copy:
    seated = f["seated"] or "seated" in n
    tib = "tibialis" in n
    if tib:
        return copy_of(
            [
                "Đứng tựa tường hoặc ngồi, gót dính, mu chân kéo lên về ống chân.",
                "Siết trước ống chân 1 giây, hạ chậm.",
                "Biên độ nhỏ, đều hai chân.",
                "Không nảy. Đau shin: giảm số cái.",
            ],
            ["Nảy.", "Lấy đà thân.", "Biên độ quá mạnh khi chưa quen."],
            "Bài cân bằng với nhón bắp chân. Làm nhẹ sau chạy.",
            f"{row['name_vi']}: kéo mu chân về ống chân để tập mặt trước cẳng chân.",
        )
    setup = "Đặt phần trước bàn chân trên bục, gót treo. Tạ trên đùi (ngồi) hoặc đứng thẳng."
    if seated:
        setup = "Ngồi, tạ trên đùi gần gối, phần trước bàn chân trên bục nếu có, gót treo."
    return copy_of(
        [
            setup,
            "Hạ gót hết căng bắp chân.",
            "Nhón lên cao, siết 1 giây, hạ chậm. Gối giữ nguyên (cong nếu ngồi, gần thẳng nếu đứng).",
            "Không nảy. Giữ thăng bằng, bám nhẹ nếu cần.",
        ],
        ["Cắt ngắn đáy.", "Nảy.", "Đặt tạ lên khớp gối."],
        "Hạ hết mới nhón. Ngồi (gối cong) nhấn bắp chân sâu hơn; đứng nhấn cả bụng chân.",
        f"{row['name_vi']}: hạ gót hết căng rồi nhón lên, chậm, không nảy.",
    )


def _build_glute_iso(name, n, k, w, f, row) -> Copy:
    add = "adduction" in n or "khép" in n
    kick = "kickback" in n
    if kick:
        path = "Đá chân ra sau, siết mông, không ưỡn lưng. Về chậm."
        setup = "Cố định dây/máy ở cổ chân, đứng vững tay bám, thân hơi cúi."
    elif add:
        path = "Khép gối/chân vào giữa, siết, về chậm."
        setup = "Ngồi máy khép đùi hoặc đứng với dây phía ngoài chân."
    else:
        path = "Dạng chân ra ngoài, siết mông cạnh, về chậm."
        setup = "Ngồi máy dạng đùi, hoặc dây ở cổ chân, đứng, dạng chân ra."
    return copy_of(
        [
            setup,
            BRACE,
            path,
            "Không lấy đà thân. Làm đều hai bên nếu một chân.",
        ],
        ["Ưỡn thắt lưng.", "Giật đà.", "Biên độ quá rộng đau háng."],
        "Tạ vừa, siết mông. Dạng/khép không thay thế squat hay hinge.",
        f"{row['name_vi']}: dạng hoặc khép hông có kiểm soát, thân ổn định.",
    )


def _build_wrist(name, n, k, w, f, row) -> Copy:
    ext = "extension" in n or "duỗi" in n
    setup = "Cẳng tay tựa đùi hoặc ghế, cổ tay nhô mép, nắm tạ nhẹ."
    path = "Duỗi cổ tay (mu tay lên) chậm." if ext else "Gập cổ tay (lòng tay lên) chậm."
    return copy_of(
        [
            setup,
            path,
            "Hạ hết căng, không nảy. Tạ rất nhẹ.",
            "Đau nhói: dừng, chỉ giãn nhẹ.",
        ],
        ["Tạ nặng phải lấy khuỷu giật.", "Nảy.", "Khuỷu rời điểm tựa."],
        "Bài nhỏ, tạ nhỏ. 10–15 cái chậm là đủ.",
        f"{row['name_vi']}: chỉ cử động cổ tay, cẳng tay tựa, tạ nhẹ.",
    )


def _build_crunch(name, n, k, w, f, row) -> Copy:
    sit = "sit" in n
    decline = "decline" in n
    cable = k == "cable" or "cable" in n
    machine = k == "machine"
    vup = "v-up" in n
    if vup:
        return copy_of(
            [
                "Nằm ngửa, tay sau đầu hoặc đưa lên, chân duỗi.",
                "Đồng thời gập nâng vai và chân, tay với về chân, thành chữ V.",
                "Hạ chậm, thắt lưng không đập sàn.",
                "Khó thì nâng gối thay chân duỗi.",
            ],
            ["Giật cổ.", "Ném thắt lưng.", "Nín thở."],
            "Chậm và siết bụng. Gập gối nếu lưng khó chịu.",
            f"{row['name_vi']}: gập hai đầu người vào nhau. Bài khó; giảm biên độ khi mới.",
        )
    setup = "Nằm ngửa, gối gập, tay sau đầu lỏng (đỡ, không kéo cổ)."
    if decline:
        setup = "Kẹp chân ghế dốc, tay trước ngực hoặc sau đầu lỏng."
    if sit:
        path = "Gập thân ngồi lên, rồi hạ chậm từng đốt lưng."
    else:
        path = "Cuốn xương sườn về chậu, vai nhấc, thắt lưng vẫn gần sàn, rồi hạ."
    if cable:
        setup = "Quỳ, dây cao sau đầu, nắm hai bên đầu."
        path = "Cuốn thân xuống, siết bụng, về chậm. Hông im."
    if machine:
        setup = "Ngồi máy gập bụng, đệm trên ngực, chọn tạ."
        path = "Cuốn thân, siết, về chậm. Không giật."
    return copy_of(
        [
            setup,
            BRACE,
            path,
            "Thở ra khi gập. Không kéo cổ.",
        ],
        ["Kéo cổ bằng tay.", "Giật đà.", "Ưỡn thắt lưng."],
        "Biên độ ngắn sạch hơn ngồi dậy hết nếu lưng khó. Tay trước ngực dễ hơn sau đầu.",
        f"{row['name_vi']}: cuốn thân bằng bụng, không kéo cổ, hạ chậm.",
    )


def _build_twist(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Ngồi, hơi ngả sau, ngực ưỡn, bàn chân chạm sàn hoặc nhấc nhẹ nếu chắc.",
            BRACE + " Cầm tạ/đĩa trước ngực nếu có.",
            "Xoay vai sang một bên, hông tương đối im, rồi xoay bên kia.",
            "Không lấy đà ném tạ. Thở đều.",
        ],
        ["Xoay bằng thắt lưng giật.", "Gù lưng.", "Tạ quá nặng."],
        "Xoay ngực, không phải ném tay. Gót chạm sàn nếu mất thăng bằng.",
        f"{row['name_vi']}: ngồi ngả, xoay thân có kiểm soát. Hông ổn định.",
    )


def _build_chop(name, n, k, w, f, row) -> Copy:
    low = "low to high" in n or "thấp lên cao" in n
    path = "Kéo từ cao xuống thấp chéo qua thân, hông xoay có kiểm soát, tay gần thẳng."
    if low:
        path = "Kéo từ thấp lên cao chéo qua thân, hông xoay, kết thúc tay cao phía đối diện."
    return copy_of(
        [
            _setup_load(k, w, False) + " Đứng nghiêng so với máy/dây, chân vững.",
            BRACE,
            path,
            "Về chậm. Đổi bên. Không khóa gối.",
        ],
        ["Chỉ lấy tay, hông chết.", "Giật thắt lưng.", "Khóa gối."],
        "Xoay từ hông và thân. Tạ vừa để còn kiểm soát quãng về.",
        f"{row['name_vi']}: kéo chéo qua thân, hông xoay có kiểm soát.",
    )


def _build_side_bend(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Đứng, tạ một tay dọc người, tay kia chống hông hoặc đặt đầu.",
            BRACE + " Hông không lắc.",
            "Nghiêng sang bên tạ, căng cạnh sườn đối diện, rồi kéo người lên bằng sườn.",
            "Không cúi ra trước. Đổi bên.",
        ],
        ["Hông lắc.", "Cúi trước.", "Tạ quá nặng, trượt sang squat."],
        "Biên độ vừa. Bài cạnh sườn; tạ nhẹ–vừa.",
        f"{row['name_vi']}: nghiêng người sang bên với tạ, hông im, không cúi trước.",
    )


def _build_dead_bug(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Nằm ngửa, tay thẳng lên, gối 90° trên hông. Ép thắt lưng sát sàn.",
            "Duỗi chậm một chân và tay đối diện sát sàn, lưng vẫn dán.",
            "Thu về, đổi bên. Thở đều.",
            "Nếu lưng võng: giảm biên độ, gót không chạm sàn.",
        ],
        ["Thắt lưng võng.", "Nín thở.", "Duỗi quá nhanh."],
        "Lưng dán sàn là thành công, không phải chân càng thấp càng tốt.",
        f"{row['name_vi']}: nằm, duỗi tay chân đối diện, thắt lưng luôn sát sàn.",
    )


def _build_bird_dog(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Quỳ bốn điểm, tay dưới vai, gối dưới hông. Lưng phẳng.",
            "Duỗi tay và chân đối diện song song sàn, hông không xoay.",
            "Giữ 1 giây, về, đổi bên. " + BRACE,
            "Nếu rung mất thăng bằng: chỉ duỗi chân hoặc chỉ duỗi tay.",
        ],
        ["Hông xoay, lưng võng.", "Nhấc chân quá cao.", "Nín thở."],
        "Tưởng một ly nước trên lưng không đổ. Chậm hơn nhanh.",
        f"{row['name_vi']}: quỳ, giơ tay chân đối diện, hông im, lưng phẳng.",
    )


def _build_plank(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Vào plank (khuỷu hoặc tay thẳng tùy bài), thân từ đầu đến gót thẳng.",
            BRACE + " Siết mông nhẹ.",
            "Thở đều. Dừng khi hông sệ hoặc mông chổng.",
            "Hạ gối, không thả sập.",
        ],
        ["Hông sệ.", "Mông chổng.", "Nhún vai, ngẩng cổ."],
        "Giữ sạch ngắn hơn giữ xấu dài. Chống gối nếu cần.",
        f"{row['name_vi']}: giữ thân ván, bụng siết, dừng khi mất thẳng.",
    )


def _build_superman(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Nằm sấp, tay đưa trước, trán gần sàn.",
            "Nhấc ngực, tay và chân thấp khỏi sàn, siết lưng giữa và mông. Nhìn sàn.",
            "Giữ 1–2 giây, hạ chậm. Không ưỡn cổ.",
            "Đau thắt lưng: chỉ nhấc tay hoặc chỉ nhấc ngực rất thấp.",
        ],
        ["Ngẩng cổ quá.", "Ưỡn thắt lưng mạnh.", "Nín thở."],
        "Biên độ nhỏ. Đây là siết lưng sau, không phải ưỡn hết cỡ.",
        f"{row['name_vi']}: nằm sấp, nhấc tay chân nhẹ, siết lưng sau, cổ trung lập.",
    )


def _build_core_generic(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            "Vào tư thế bài " + row["name_vi"] + ", lưng trung lập. " + BRACE,
            "Thực hiện động tác chậm, bụng luôn siết.",
            "Thở đều, không nín đến đỏ mặt.",
            "Dừng khi mất thẳng lưng hoặc đau nhói.",
        ],
        ["Cong hoặc ưỡn thắt lưng mất kiểm soát.", "Lấy đà.", "Nín thở."],
        "Ưu tiên siết bụng và thở. Giảm biên độ nếu lưng khó chịu.",
        f"{row['name_vi']}: giữ bụng siết, động tác chậm, lưng ổn định.",
    )


def _build_upright(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            _setup_load(k, w, False) + " Tạ trước đùi, nắm hẹp hơn vai.",
            BRACE,
            "Kéo tạ dọc thân, khuỷu dẫn, đến khoảng ngang ngực giữa — không cao hơn vai nếu bị cấn.",
            "Hạ chậm. Không lắc người.",
        ],
        ["Kéo quá cao, vai cấn.", "Lắc đà.", "Cổ tay gãy."],
        "Dừng khi khuỷu ngang vai. Khó chịu thì đổi dang tay hoặc kéo dây về mặt.",
        f"{row['name_vi']}: kéo tạ dọc thân, khuỷu dẫn, dừng khoảng ngang vai.",
    )


def _build_generic(name, n, k, w, f, row) -> Copy:
    return copy_of(
        [
            _setup_load(k, w, f["seated"]) + f" Vào tư thế ổn định cho bài {row['name_vi']}.",
            BRACE,
            "Làm động tác hết tầm kiểm soát, chậm hơn là giật.",
            "Về vị trí đầu có kiểm soát. Dừng nếu đau nhói khớp.",
            "Giữ nhịp thở: thở ra lúc gắng sức.",
        ],
        ["Lấy đà thân khi tạ quá nặng.", "Cong hoặc ưỡn lưng mất kiểm soát.", "Khóa khớp giật."],
        "Giảm tạ đến khi làm được từng cái sạch. Đau bất thường thì dừng, đừng cố.",
        f"{row['name_vi']}: giữ thân ổn định, làm chậm, dừng khi đau nhói.",
    )


def to_json_item(row: dict[str, Any], copy: Copy) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name_en": row["name_en"],
        "name_vi": row["name_vi"],
        "instruction_vi": copy.instruction_vi,
        "instruction_steps_vi": copy.steps,
        "common_mistakes_vi": copy.mistakes,
        "tips_vi": copy.tips,
    }


def load_meta() -> list[dict[str, Any]]:
    if META_PATH.is_file():
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    import os
    import psycopg

    url = os.environ.get("DATABASE_URL", "")
    url = url.replace("postgresql+psycopg://", "postgresql://")
    if not url:
        raise SystemExit("Missing meta JSON and DATABASE_URL")
    conn = psycopg.connect(url)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.id, e.name_en, e.name_vi, e.movement_pattern, e.movement_role,
               e.exercise_type, e.venue, e.difficulty, e.notes_vi,
               mg.slug, mg.name_vi,
               COALESCE((
                 SELECT string_agg(eq.slug, ',' ORDER BY eq.slug)
                 FROM exercise_equipment ee
                 JOIN equipment eq ON eq.id = ee.equipment_id
                 WHERE ee.exercise_id = e.id
               ), '')
        FROM exercises e
        LEFT JOIN muscle_groups mg ON mg.id = e.muscle_group_id
        WHERE e.is_active IS TRUE
        ORDER BY e.name_en
        """
    )
    cols = [
        "id",
        "name_en",
        "name_vi",
        "movement_pattern",
        "movement_role",
        "exercise_type",
        "venue",
        "difficulty",
        "notes_vi",
        "muscle_slug",
        "muscle_vi",
        "equipment",
    ]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def patch_pack_json(path: Path, by_en: dict[str, dict[str, Any]]) -> None:
    if not path.is_file():
        return
    items = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for item in items:
        key = str(item.get("name_en") or "")
        src = by_en.get(key)
        if not src and key in OVERRIDES:
            cp = OVERRIDES[key]
            src = {
                "instruction_steps_vi": cp.steps,
                "common_mistakes_vi": cp.mistakes,
                "tips_vi": cp.tips,
            }
        if not src:
            continue
        item["instruction_steps_vi"] = src["instruction_steps_vi"]
        item["common_mistakes_vi"] = src["common_mistakes_vi"]
        item["tips_vi"] = src["tips_vi"]
        changed = True
    if changed:
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    sys.path.insert(0, str(ROOT / "api"))
    from app.services.exercise_copy_seed import validate_copy_seed

    rows = load_meta()
    out: list[dict[str, Any]] = []
    errors: list[str] = []
    for row in rows:
        try:
            cp = author(row)
            out.append(to_json_item(row, cp))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{row.get('name_en')}: {exc}")
    if errors:
        print("AUTHOR ERRORS", file=sys.stderr)
        for e in errors:
            print(" ", e, file=sys.stderr)
        return 1
    problems = validate_copy_seed(out)
    if problems:
        print("HYGIENE", file=sys.stderr)
        for p in problems:
            print(" ", p, file=sys.stderr)
        return 1
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    by_en = {x["name_en"]: x for x in out}
    patch_pack_json(RINGS_PATH, by_en)
    patch_pack_json(BAND_PATH, by_en)
    print(f"Wrote {len(out)} entries -> {SEED_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
