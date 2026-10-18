"""Vietnamese titles for exercises — no leftover English in name_vi."""

from __future__ import annotations

import re

# Longer phrases first.
_PHRASES: tuple[tuple[str, str], ...] = (
    ("single legged romanian deadlifts", "nhấc tạ chân thẳng một chân"),
    ("single-leg dumbbell romanian deadlift", "nhấc tạ chân thẳng một chân tạ đơn"),
    ("dumbbell cross body romanian deadlift", "nhấc tạ chân thẳng chéo người tạ đơn"),
    ("dumbbell figure four heels elevated hip thrust", "đẩy hông tạ đơn chân số 4 gót nâng"),
    ("barbell front rack step up knee drive", "bước lên bục nhấc gối tạ đòn trước ngực"),
    ("barbell step up knee drive", "bước lên bục nhấc gối tạ đòn"),
    ("hip hinge speed romanian deadlift", "nhấc tạ chân thẳng gập hông nhanh"),
    ("smith machine sumo romanian deadlift", "nhấc tạ chân thẳng chân rộng máy trượt tạ"),
    ("cable standing single arm chest press", "ép ngực đứng một tay cáp"),
    ("cable standing low to high wood chopper", "chẻ gỗ đứng cáp từ thấp lên cao"),
    ("cable seated rope face pull", "kéo dây về mặt ngồi"),
    ("cable rope kneeling face pull", "kéo cáp về mặt quỳ dây thừng"),
    ("cable rope face pulls", "kéo dây về mặt cáp"),
    ("band high face pull", "kéo dây về mặt"),
    ("cable bench straight leg kickback", "đá chân thẳng nằm cáp"),
    ("cable single arm underhand grip row", "chèo cáp một tay ngửa"),
    ("cable single arm neutral grip row", "chèo cáp một tay cầm giữa"),
    ("cable single arm rope pushdown", "đẩy cáp xuống một tay dây thừng"),
    ("cable single leg laying leg curl", "cuốn đùi sau nằm một chân cáp"),
    ("cable low single arm lateral raise", "dang tay một bên cáp thấp"),
    ("cable rope overhead tricep extension", "duỗi tay sau trên đầu cáp dây thừng"),
    ("cable row bar standing row", "chèo đứng cáp thanh ngang"),
    ("machine plate loaded front military press", "đẩy vai máy đĩa tạ"),
    ("machine plate loaded t bar row", "chèo thanh chữ T máy"),
    ("machine cable v bar push downs", "đẩy cáp xuống thanh chữ V"),
    ("dumbbell seated overhead tricep extension", "duỗi tay sau ngồi tạ đơn"),
    ("dumbbell standing single arm hammer curl", "cuốn tay kiểu búa một bên tạ đơn"),
    ("dumbbell standing single arm curl", "cuốn tay một bên tạ đơn"),
    ("dumbbell single arm clean and press", "cử tạ rồi đẩy một tay tạ đơn"),
    ("dumbbell goblet bulgarian split squat", "ngồi xổm chân sau kê ghế ôm tạ đơn"),
    ("kettlebell assisted bulgarian split squat", "ngồi xổm chân sau kê ghế tạ ấm có trợ"),
    ("dumbbell feet elevated glute bridge", "cầu mông tạ đơn chân nâng"),
    ("dumbbell heels elevated hip thrust", "đẩy hông tạ đơn gót nâng"),
    ("single-arm overhead cable extension", "duỗi tay sau một tay trên đầu cáp"),
    ("single-arm dumbbell overhead press", "đẩy vai một tay tạ đơn"),
    ("single-arm landmine press", "đẩy vai một tay thanh cắm đất"),
    ("single-arm lat pulldown", "kéo xô một tay"),
    ("single-arm tricep extension", "duỗi tay sau một tay"),
    ("single-arm cable fly", "mở ngực một tay cáp"),
    ("single-leg standing calf raise", "nhón bắp chân đứng một chân"),
    ("single-leg press", "đẩy chân máy một chân"),
    ("power clean no overhead press", "cử tạ lực không đẩy trên đầu"),
    ("power clean - no overhead press", "cử tạ lực không đẩy trên đầu"),
    ("barbell behind the back 30 degree shrug", "nhún vai tạ đòn sau lưng 30 độ"),
    ("cable 30 degree shrug", "nhún vai cáp 30 độ"),
    ("reverse-grip barbell bench press", "ép ngực tạ đòn ngửa tay"),
    ("reverse-grip tricep pushdown", "đẩy cáp xuống ngửa tay"),
    ("reverse grip barbell curl", "cuốn tay tạ đòn sấp"),
    ("wide-grip seated cable row", "chèo cáp ngồi tay rộng"),
    ("wide-grip barbell bench press", "ép ngực tạ đòn tay rộng"),
    ("wide-grip barbell curl", "cuốn tay tạ đòn cầm rộng"),
    ("wide-grip lat pulldown", "kéo xô tay rộng"),
    ("wide-grip pull-up", "hít xà tay rộng"),
    ("straight-arm lat pulldown", "kéo xô tay thẳng"),
    ("close-grip barbell curl", "cuốn tay tạ đòn cầm hẹp"),
    ("smith machine close grip bench press", "ép ngực tay hẹp máy trượt tạ"),
    ("smith machine seated overhead press", "đẩy vai ngồi máy trượt tạ"),
    ("smith machine standing shrugs", "nhún vai đứng máy trượt tạ"),
    ("barbell close grip bench press", "ép ngực tạ đòn tay hẹp"),
    ("barbell high incline bench press", "ép ngực dốc cao tạ đòn"),
    ("barbell banded back squat", "ngồi xổm tạ đòn có dây kháng lực"),
    ("barbell spinal jefferson curl", "cuộn cột sống tạ đòn"),
    ("dumbbell spinal jefferson curl", "cuộn cột sống tạ đơn"),
    ("kettlebell spinal jefferson curl", "cuộn cột sống tạ ấm"),
    ("bodyweight spinal jefferson curl", "cuộn cột sống không tạ"),
    ("spinal jefferson curl", "cuộn cột sống"),
    ("jefferson curl", "cuộn cột sống"),
    ("bodyweight alternating reverse lunges", "chùng chân ra sau xen kẽ"),
    ("bodyweight alternating lateral lunge", "chùng chân sang ngang xen kẽ"),
    ("dumbbell alternating forward lunge", "chùng chân ra trước xen kẽ tạ đơn"),
    ("dumbbell goblet reverse lunge", "chùng chân ra sau ôm tạ đơn"),
    ("barbell reverse lunge", "chùng chân ra sau tạ đòn"),
    ("bodyweight reverse lunge", "chùng chân ra sau"),
    ("bodyweight elevated push up", "chống đẩy tay hoặc chân nâng"),
    ("incline push up", "chống đẩy tay trên ghế"),
    ("diamond push ups", "chống đẩy kim cương"),
    ("pike push-up", "chống đẩy mông cao"),
    ("pike push up", "chống đẩy mông cao"),
    ("behind-the-neck press", "đẩy vai sau gáy"),
    ("ez bar reverse preacher curl", "cuốn tay tựa ghế sấp thanh cong"),
    ("ez bar preacher curl", "cuốn tay tựa ghế thanh cong"),
    ("machine preacher curl", "cuốn tay tựa ghế máy"),
    ("dumbbell preacher curl", "cuốn tay tựa ghế tạ đơn"),
    ("dumbbell concentration curl", "cuốn tay tập trung tạ đơn"),
    ("dumbbell incline hammer curl", "cuốn tay kiểu búa tạ đơn ghế dốc"),
    ("dumbbell incline front raise", "nâng tay trước tạ đơn ghế dốc"),
    ("dumbbell incline curl", "cuốn tay tạ đơn ghế dốc"),
    ("dumbbell seated rear delt fly", "mở vai sau ngồi tạ đơn"),
    ("dumbbell seated overhead press", "đẩy vai ngồi tạ đơn"),
    ("dumbbell seated shrug", "nhún vai ngồi tạ đơn"),
    ("dumbbell laying reverse fly", "mở vai sau nằm tạ đơn"),
    ("dumbbell rear delt fly", "mở vai sau tạ đơn"),
    ("dumbbell tricep kickback", "đá tay sau tạ đơn"),
    ("dumbbell single arm chest press", "ép ngực một tay tạ đơn"),
    ("dumbbell single arm row", "chèo tạ đơn một tay"),
    ("dumbbell goblet split squat", "ngồi xổm chân trước-sau ôm tạ đơn"),
    ("dumbbell cossack squat", "ngồi xổm sang bên tạ đơn"),
    ("dumbbell bulgarian split squat", "ngồi xổm chân sau kê ghế tạ đơn"),
    ("dumbbell lateral lunge", "chùng chân sang ngang tạ đơn"),
    ("dumbbell decline skullcrusher", "đập tạ sau đầu ghế dốc xuống"),
    ("dumbbell wrist extension", "duỗi cổ tay tạ đơn"),
    ("dumbbell wrist curl", "cuốn cổ tay tạ đơn"),
    ("kettlebell seated overhead press", "đẩy vai ngồi tạ ấm"),
    ("kettlebell single arm row", "chèo tạ ấm một tay"),
    ("kettlebell row (single)", "chèo tạ ấm một tay"),
    ("kettlebell gorilla row", "chèo tạ ấm luân phiên cúi người"),
    ("kettlebell goblet curl", "cuốn tay ôm tạ ấm"),
    ("cable high-to-low fly", "mở ngực cáp từ cao xuống thấp"),
    ("cable low-to-high fly", "mở ngực cáp từ thấp lên cao"),
    ("cable overhead press", "đẩy vai trên đầu với cáp"),
    ("cable external rotation", "xoay ngoài vai cáp"),
    ("cable bar face pull", "kéo cáp về mặt thanh ngang"),
    ("cable bar pushdown", "đẩy cáp xuống thanh ngang"),
    ("cable bar curl", "cuốn tay cáp thanh ngang"),
    ("cable rope hammer curl", "cuốn tay kiểu búa cáp dây thừng"),
    ("cable rope pullover", "kéo cáp qua đầu dây thừng"),
    ("cable pull through", "kéo cáp qua háng"),
    ("cable front raise", "nâng tay trước với cáp"),
    ("cable wrist curl", "cuốn cổ tay cáp"),
    ("band single arm lateral raise", "dang tay một bên với dây"),
    ("band overhead tricep extension", "duỗi tay sau trên đầu với dây"),
    ("band overhead press", "đẩy vai trên đầu với dây"),
    ("band seated row", "kéo ngang ngồi với dây kháng lực"),
    ("band external rotation", "xoay ngoài vai với dây"),
    ("band lateral raise", "dang tay với dây"),
    ("band tricep kickback", "đá tay sau với dây"),
    ("band pallof press", "đẩy chống xoay với dây kháng lực"),
    ("band good morning", "cúi người với dây kháng lực"),
    ("band pull-apart", "kéo dây ra hai bên"),
    ("pull-apart", "kéo ra hai bên"),
    ("pull apart", "kéo ra hai bên"),
    ("band pullover", "kéo tạ qua đầu với dây"),
    ("band leg curl", "cuốn đùi sau với dây"),
    ("band shrug", "nhún vai với dây"),
    ("band curl", "cuốn tay với dây"),
    ("indoor cycling (spin bike)", "đạp xe trong nhà"),
    ("indoor cycling spin bike", "đạp xe trong nhà"),
    ("abdominals stretch variation four", "giãn bụng biến thể 4"),
    ("abdominals stretch variation three", "giãn bụng nghiêng (cơ liên sườn)"),
    ("abdominals stretch variation two", "giãn bụng đứng, tay lên cao"),
    ("abdominals stretch variation one", "giãn bụng biến thể 1"),
    ("standing/seated hamstring stretch", "giãn đùi sau đứng hoặc ngồi"),
    ("overhead shoulder/triceps stretch", "giãn vai và tay sau trên đầu"),
    ("wrist flexor/extensor stretch", "giãn cổ tay gập và duỗi"),
    ("cross-body shoulder stretch", "giãn vai kéo tay ngang ngực"),
    ("standing chest opener", "giãn ngực đứng, đan tay sau lưng"),
    ("doorway chest stretch", "giãn ngực tại khung cửa"),
    ("floor chest stretch", "giãn ngực nằm sấp, xoay người"),
    ("standing calf stretch", "giãn bắp chân đứng"),
    ("standing quad stretch", "giãn đùi trước đứng"),
    ("ring lat stretch", "giãn xô vòng treo"),
    ("ring pec stretch", "giãn ngực vòng treo"),
    ("cat-cow stretch", "giãn lưng mèo–bò"),
    ("child's pose", "tư thế em bé (giãn lưng)"),
    ("seated spinal twist", "xoay cột sống ngồi"),
    ("donkey calf raise", "nhón bắp chân kiểu lừa"),
    ("stability ball leg curl", "cuốn đùi sau trên bóng"),
    ("towel slide leg curl", "cuốn đùi sau trượt khăn"),
    ("nordic hamstring curl", "cuốn đùi sau gối cố định"),
    ("lying leg curl", "cuốn đùi sau nằm"),
    ("seated leg curl", "cuốn đùi sau ngồi"),
    ("hamstring curl", "cuốn đùi sau"),
    ("ring hamstring curl", "cuốn đùi sau vòng treo"),
    ("ring hanging knee raise", "nâng gối treo vòng"),
    ("ring hanging leg raise", "nâng chân treo vòng"),
    ("ring face-down row", "kéo ngang sấp vòng treo"),
    ("bulgarian ring squat", "ngồi xổm chân sau kê ghế vòng treo"),
    ("bulgarian split squat", "ngồi xổm chân sau kê ghế"),
    ("captain's chair knee raise", "nâng gối ghế treo"),
    ("chest-supported t-bar row", "chèo thanh chữ T chống ngực"),
    ("landmine t bar rows", "chèo thanh chữ T cắm đất"),
    ("hammer strength high row", "chèo cao máy từng bên"),
    ("machine underhand row", "chèo máy ngửa tay"),
    ("machine tricep extension", "duỗi tay sau máy"),
    ("machine lat pullover", "kéo xô tay thẳng máy"),
    ("machine lateral raise", "dang tay máy"),
    ("reverse pec deck", "mở vai sau máy"),
    ("reverse hyperextension", "duỗi lưng ngược"),
    ("leaning cable lateral raise", "dang tay cáp nghiêng người"),
    ("cross-body hammer curl", "cuốn tay kiểu búa chéo người"),
    ("seated dumbbell curl", "cuốn tay ngồi tạ đơn"),
    ("trap bar deadlift", "nhấc tạ thanh lục giác từ đất"),
    ("trap bar shrug", "nhún vai thanh lục giác"),
    ("snatch-grip deadlift", "nhấc tạ từ đất cầm giật rộng"),
    ("snatch-grip high pull", "kéo cao cầm giật rộng"),
    ("deficit deadlift", "nhấc tạ từ đất đứng trên bục"),
    ("bodyweight deadlift", "nhấc tạ từ đất không tạ"),
    ("barbell stiff leg deadlifts", "nhấc tạ chân thẳng tạ đòn"),
    ("romanian deadlift", "nhấc tạ chân thẳng gập hông"),
    ("barbell muscle snatch", "giật tạ cơ tạ đòn"),
    ("barbell power snatch", "giật tạ lực tạ đòn"),
    ("barbell snatch", "giật tạ đòn"),
    ("barbell clean and press", "cử tạ rồi đẩy tạ đòn"),
    ("barbell drag curl", "cuốn tay kéo sát thân tạ đòn"),
    ("barbell overhead press", "đẩy vai tạ đòn trên đầu"),
    ("barbell split squat", "ngồi xổm chân trước-sau tạ đòn"),
    ("barbell pullover", "kéo tạ đòn qua đầu"),
    ("barbell wrist curl", "cuốn cổ tay tạ đòn"),
    ("barbell thruster", "ngồi xổm đẩy vai tạ đòn"),
    ("barbell shrug", "nhún vai tạ đòn"),
    ("barbell curl", "cuốn tay tạ đòn"),
    ("bent-over backpack row", "chèo cặp sách hai tay"),
    ("one-arm backpack row", "chèo cặp sách một tay"),
    ("chin-over-bar hold negative", "giữ cằm qua xà rồi hạ chậm"),
    ("split squat isometric hold", "giữ ngồi xổm chân trước-sau"),
    ("front plank on elbows", "chống người chống khuỷu"),
    ("elbow side plank", "chống người nghiêng chống khuỷu"),
    ("hanging knee raises", "nâng gối treo xà"),
    ("swim sprint intervals", "bơi nước rút ngắt quãng"),
    ("swim kick drill", "bơi chỉ đạp chân"),
    ("swim pull drill", "bơi chỉ kéo tay"),
    ("cycling intervals", "đạp xe ngắt quãng"),
    ("cycling sprint", "đạp xe nước rút"),
    ("rowing sprint", "chèo máy nước rút"),
    ("running cooldown", "chạy thả lỏng"),
    ("hill climb repeats", "leo dốc lặp lại"),
    ("steady state ride", "đạp xe đều"),
    ("tempo run", "chạy đều theo nhịp"),
    ("backstroke swim", "bơi ngửa"),
    ("breaststroke swim", "bơi ếch"),
    ("butterfly swim", "bơi bướm"),
    ("freestyle swim", "bơi sải"),
    ("assault bike", "xe đạp không khí"),
    ("arc trainer", "máy cung tròn"),
    ("versa climber", "máy leo dọc"),
    ("versaclimber", "máy leo dọc"),
    ("stair climber", "máy leo cầu thang"),
    ("ski erg", "máy trượt tuyết"),
    ("shadow boxing", "đấm bóng tưởng tượng"),
    ("mountain climber", "leo núi tại chỗ"),
    ("jumping jack", "nhảy dang chân"),
    ("high knees", "nâng gối cao"),
    ("jump rope", "nhảy dây"),
    ("frog pump", "bơm mông tư thế ếch"),
    ("bird dog", "giơ tay chân đối diện"),
    ("dead bug", "nằm ngửa giơ tay chân"),
    ("dead hang", "treo xà thả lỏng"),
    ("good mornings", "cúi người tạ sau gáy"),
    ("good morning", "cúi người tạ sau gáy"),
    ("pallof press", "đẩy chống xoay"),
    ("arnold press", "đẩy vai xoay cổ tay"),
    ("cuban press", "đẩy vai xoay cổ tay từ dưới"),
    ("landmine press", "đẩy vai thanh cắm đất"),
    ("meadows row", "chèo thanh cắm đất một tay"),
    ("inverted row", "chèo người nằm"),
    ("seal row", "chèo nằm sấp ghế"),
    ("yates row", "chèo tạ đòn ngửa thân cao"),
    ("underhand barbell row", "chèo tạ đòn ngửa tay"),
    ("barbell bent over row overhand", "chèo tạ đòn cúi người sấp tay"),
    ("hang power clean", "cử tạ lực từ treo"),
    ("hang clean", "cử tạ từ treo"),
    ("hang snatch", "giật tạ từ treo"),
    ("power clean", "cử tạ lực"),
    ("split jerk", "đẩy giật chân trước-sau"),
    ("snatch pull", "kéo giật tạ"),
    ("jm press", "ép tay sau sát ngực"),
    ("tate press", "ép tay sau nằm xoay cổ tay"),
    ("z press", "đẩy vai ngồi sàn chân duỗi"),
    ("zottman curl", "cuốn tay ngửa rồi sấp"),
    ("spider curl", "cuốn tay nằm sấp ghế dốc"),
    ("bayesian curl", "cuốn tay dây sau lưng"),
    ("neck extension", "duỗi cổ"),
    ("neck curl", "cuốn cổ"),
    ("wrist roller", "lăn cổ tay"),
    ("plate forward lunge", "chùng chân ra trước đĩa tạ"),
    ("plate front raise", "nâng tay trước đĩa tạ"),
    ("plate pinch", "kẹp đĩa tạ"),
    ("pendulum squat", "ngồi xổm con lắc"),
    ("v-squat", "ngồi xổm chữ V"),
    ("sissy squat", "ngồi xổm ngả người sau"),
    ("zercher squat", "ngồi xổm kẹp tạ khuỷu tay"),
    ("cossack squat", "ngồi xổm sang bên"),
    ("narrow pulldown", "kéo xô tay hẹp"),
    ("skin the cat", "lộn mèo vòng treo"),
    ("ring l-sit", "ngồi chữ L vòng treo"),
    ("ring hold", "giữ vòng treo"),
    ("ring dip", "chống song song vòng treo"),
    ("ring lat", "xô vòng treo"),
    ("b-stance back extension", "duỗi lưng thế chân lệch"),
    ("b-stance", "thế chân lệch"),
    ("chin ups", "hít xà lòng bàn tay hướng vào"),
    ("hand plank", "chống người chống thẳng tay"),
    ("supermans", "nằm sấp giơ tay chân"),
    ("superman", "nằm sấp giơ tay chân"),
    ("russian twist", "xoay người"),
    ("trail run", "chạy bền"),
    ("hiking", "đi bộ đường mòn"),
    ("elliptical", "máy elip"),
    ("variation one", "biến thể 1"),
    ("variation two", "biến thể 2"),
    ("variation three", "biến thể 3"),
    ("variation four", "biến thể 4"),
    ("resistance band", "dây kháng lực"),
    ("smith machine", "máy trượt tạ"),
    ("stability ball", "bóng ổn định"),
    ("close grip", "tay hẹp"),
    ("wide grip", "tay rộng"),
    ("neutral grip", "cầm giữa"),
    ("reverse lunge", "chùng chân ra sau"),
    ("forward lunge", "chùng chân ra trước"),
    ("lateral lunge", "chùng chân sang ngang"),
    ("split squat", "ngồi xổm chân trước-sau"),
    ("calf raise", "nhón bắp chân"),
    ("hip thrust", "đẩy hông"),
    ("glute bridge", "cầu mông"),
    ("push press", "đẩy vai bật chân"),
    ("overhead press", "đẩy vai trên đầu"),
    ("bench press", "ép ngực"),
    ("chest press", "ép ngực"),
    ("front raise", "nâng tay trước"),
    ("lateral raise", "dang tay"),
    ("rear delt fly", "mở vai sau"),
    ("face pull", "kéo về mặt"),
    ("pull through", "kéo qua háng"),
    ("tricep kickback", "đá tay sau"),
    ("tricep extension", "duỗi tay sau"),
    ("skullcrusher", "đập tạ sau đầu"),
    ("preacher curl", "cuốn tay tựa ghế"),
    ("hammer curl", "cuốn tay kiểu búa"),
    ("drag curl", "cuốn tay kéo sát thân"),
    ("wrist curl", "cuốn cổ tay"),
    ("wrist extension", "duỗi cổ tay"),
    ("leg curl", "cuốn đùi sau"),
    ("external rotation", "xoay ngoài"),
    ("internal rotation", "xoay trong"),
    ("wood chopper", "chẻ gỗ"),
    ("lat pulldown", "kéo xô"),
    ("lat pullover", "kéo qua đầu"),
    ("muscle snatch", "giật tạ cơ"),
    ("power snatch", "giật tạ lực"),
    ("clean and press", "cử tạ rồi đẩy"),
    ("step up", "bước lên bục"),
    ("knee drive", "nhấc gối"),
    ("front rack", "trước ngực"),
    ("heels elevated", "gót nâng"),
    ("feet elevated", "chân nâng"),
    ("figure four", "chân số 4"),
    ("straight leg", "chân thẳng"),
    ("stiff leg", "chân thẳng"),
    ("single arm", "một tay"),
    ("single-arm", "một tay"),
    ("single leg", "một chân"),
    ("single-leg", "một chân"),
    ("one-arm", "một tay"),
    ("one arm", "một tay"),
    ("cross-body", "chéo người"),
    ("cross body", "chéo người"),
    ("face-down", "sấp"),
    ("face down", "sấp"),
    ("behind-the-neck", "sau gáy"),
    ("chest-supported", "chống ngực"),
    ("chest supported", "chống ngực"),
    ("kettlebell windmill", "cối xay tạ ấm"),
    ("windmill", "cối xay"),
    ("backpack", "cặp sách"),
    ("overhead", "trên đầu"),
    ("flexor", "gập"),
    ("extensor", "duỗi"),
    ("high-to-low", "từ cao xuống thấp"),
    ("low-to-high", "từ thấp lên cao"),
    ("behind the back", "sau lưng"),
    ("bent over", "cúi người"),
    ("overhand", "sấp tay"),
    ("underhand", "ngửa tay"),
    ("reverse-grip", "ngửa tay"),
    ("bodyweight", "không tạ"),
    ("dumbbell", "tạ đơn"),
    ("barbell", "tạ đòn"),
    ("kettlebell", "tạ ấm"),
    ("cable", "cáp"),
    ("machine", "máy"),
    ("banded", "có dây kháng lực"),
    ("deadlift", "nhấc tạ từ đất"),
    ("push-up", "chống đẩy"),
    ("push up", "chống đẩy"),
    ("pull-up", "hít xà"),
    ("pull up", "hít xà"),
    ("chin-up", "hít xà sấp tay"),
    ("stretch", "giãn"),
    ("seated", "ngồi"),
    ("standing", "đứng"),
    ("incline", "dốc lên"),
    ("decline", "dốc xuống"),
    ("elevated", "nâng cao"),
    ("kneeling", "quỳ"),
    ("lying", "nằm"),
    ("laying", "nằm"),
    ("goblet", "ôm tạ"),
    ("shrug", "nhún vai"),
    ("pullover", "kéo qua đầu"),
    ("pushdown", "đẩy xuống"),
    ("row", "chèo"),
    ("curl", "cuốn tay"),
    ("fly", "mở"),
    ("press", "đẩy"),
    ("squat", "ngồi xổm"),
    ("lunge", "chùng chân"),
    ("snatch", "giật tạ"),
    ("thruster", "ngồi xổm đẩy vai"),
    ("dip", "chống song song"),
    ("plank", "chống người"),
    ("hiking", "đi bộ đường mòn"),
    ("swim", "bơi"),
    ("cycling", "đạp xe"),
    ("running", "chạy"),
    ("rowing", "chèo máy"),
    ("sprint", "nước rút"),
    ("cooldown", "thả lỏng"),
    ("intervals", "ngắt quãng"),
    ("assisted", "có trợ"),
    ("alternating", "xen kẽ"),
    ("bilateral", "hai tay"),
    ("unilateral", "một bên"),
    ("isometric", "tĩnh"),
    ("hold", "giữ"),
    ("negative", "hạ chậm"),
    ("deficit", "đứng trên bục"),
    ("sumo", "chân rộng"),
    ("degree", "độ"),
    ("bar", "thanh"),
    ("rope", "dây thừng"),
    ("plate", "đĩa tạ"),
    ("band", "dây kháng lực"),
    ("ring", "vòng treo"),
    ("sit", "ngồi"),
    ("chin", "cằm"),
    ("behind", "sau"),
    ("supported", "chống"),
    ("apart", "ra hai bên"),
    ("backpack", "cặp sách"),
    ("windmill", "cối xay"),
    ("overhead", "trên đầu"),
    ("flexor", "gập"),
    ("extensor", "duỗi"),
    ("cross", "chéo"),
    ("body", "người"),
)

_WORDS: tuple[tuple[str, str], ...] = (
    ("abdominals", "bụng"),
    ("hamstring", "đùi sau"),
    ("triceps", "tay sau"),
    ("tricep", "tay sau"),
    ("shoulder", "vai"),
    ("chest", "ngực"),
    ("back", "lưng"),
    ("neck", "cổ"),
    ("wrist", "cổ tay"),
    ("quad", "đùi trước"),
    ("calf", "bắp chân"),
    ("glute", "mông"),
    ("lat", "xô"),
    ("pec", "ngực"),
    ("delt", "vai"),
    ("clean", "cử tạ"),
    ("jerk", "đẩy giật"),
    ("extension", "duỗi"),
    ("raise", "nâng"),
    ("kickback", "đá sau"),
    ("pulldown", "kéo xô"),
    ("hyperextension", "duỗi lưng"),
    ("woodchopper", "chẻ gỗ"),
    ("chopper", "chẻ"),
    ("supinating", "xoay lòng bàn tay"),
    ("leaning", "nghiêng người"),
    ("captain", "ghế treo"),
    ("chair", "ghế"),
    ("knee", "gối"),
    ("raises", "nâng"),
    ("hanging", "treo"),
    ("inverted", "ngược"),
    ("seal", "nằm sấp"),
    ("meadows", "một tay cắm đất"),
    ("yates", "ngửa thân cao"),
    ("bayesian", "dây sau lưng"),
    ("zottman", "ngửa rồi sấp"),
    ("spider", "nằm sấp ghế dốc"),
    ("sissy", "ngả người sau"),
    ("zercher", "kẹp khuỷu"),
    ("cossack", "sang bên"),
    ("bulgarian", "chân sau kê ghế"),
    ("nordic", "gối cố định"),
    ("jefferson", "cuộn cột sống"),
    ("arnold", "xoay cổ tay"),
    ("cuban", "xoay cổ tay"),
    ("landmine", "thanh cắm đất"),
    ("pendulum", "con lắc"),
    ("elliptical", "máy elip"),
    ("versaclimber", "máy leo dọc"),
    ("hiking", "đi bộ đường mòn"),
    ("backstroke", "bơi ngửa"),
    ("breaststroke", "bơi ếch"),
    ("butterfly", "bơi bướm"),
    ("freestyle", "bơi sải"),
    ("tempo", "theo nhịp"),
    ("drill", "bài kỹ thuật"),
    ("kick", "đạp chân"),
    ("pull", "kéo"),
    ("push", "đẩy"),
    ("hold", "giữ"),
    ("negative", "hạ chậm"),
    ("assisted", "có trợ"),
    ("banded", "có dây"),
    ("single", "một"),
    ("legged", "chân"),
    ("arm", "tay"),
    ("leg", "chân"),
    ("low", "thấp"),
    ("high", "cao"),
    ("close", "hẹp"),
    ("wide", "rộng"),
    ("narrow", "hẹp"),
    ("straight", "thẳng"),
    ("stiff", "thẳng"),
    ("reverse", "ngược"),
    ("overhand", "sấp"),
    ("underhand", "ngửa"),
    ("neutral", "giữa"),
    ("grip", "cầm"),
    ("seated", "ngồi"),
    ("standing", "đứng"),
    ("incline", "dốc"),
    ("decline", "dốc xuống"),
    ("machine", "máy"),
    ("cable", "cáp"),
    ("barbell", "tạ đòn"),
    ("dumbbell", "tạ đơn"),
    ("kettlebell", "tạ ấm"),
    ("bodyweight", "không tạ"),
    ("smith", "trượt tạ"),
    ("plate", "đĩa tạ"),
    ("rope", "dây thừng"),
    ("bar", "thanh"),
    ("ez", "cong"),
    ("v", "chữ V"),
    ("t", "chữ T"),
    ("no", "không"),
    ("and", "và"),
    ("the", ""),
    ("of", ""),
    ("to", "đến"),
    ("from", "từ"),
)

_VI_CHAR = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    re.I,
)
_UNICODE_WORD = re.compile(r"[A-Za-zÀ-ỹà-ỹĐđ]+")
_SKIP_NAME = re.compile(r"^e2e\b", re.I)
_EN_VOCAB: frozenset[str] | None = None


def _english_vocab() -> frozenset[str]:
    global _EN_VOCAB
    if _EN_VOCAB is None:
        words: set[str] = set()
        for en, _vi in _PHRASES + _WORDS:
            words.update(re.findall(r"[a-z]{3,}", en.lower().replace("-", " ")))
        words.update(
            {
                "backpack",
                "windmill",
                "flexor",
                "extensor",
                "opener",
                "supported",
                "apart",
                "bulgaria",
                "loaded",
                "military",
                "downs",
                "spin",
                "bike",
                "face",
                "down",
                "over",
                "chin",
                "sit",
                "ring",
                "behind",
                "cross",
                "body",
                "overhead",
                "one",
                "cat",
                "dog",
                "bug",
                "jack",
                "trainer",
                "assault",
                "versa",
                "erg",
                "steady",
                "state",
                "ride",
                "trail",
                "interval",
                "repeats",
                "climb",
                "hill",
                "shadow",
                "boxing",
                "mountain",
                "jumping",
                "frog",
                "pump",
                "pallof",
                "arnold",
                "cuban",
                "landmine",
                "inverted",
                "seal",
                "yates",
                "meadows",
                "power",
                "split",
                "jerk",
                "snatch",
                "press",
                "curl",
                "row",
                "fly",
                "squat",
                "lunge",
                "stretch",
                "variation",
                "bodyweight",
                "dumbbell",
                "barbell",
                "kettlebell",
                "machine",
                "cable",
                "band",
                "plate",
            }
        )
        _EN_VOCAB = frozenset(words)
    return _EN_VOCAB


def looks_english(name: str) -> bool:
    t = (name or "").strip()
    if not t:
        return True
    if _VI_CHAR.search(t):
        return False
    return bool(re.search(r"[A-Za-z]", t))


def leftover_english_tokens(name: str) -> list[str]:
    vocab = _english_vocab()
    out: list[str] = []
    for tok in _UNICODE_WORD.findall(name or ""):
        if _VI_CHAR.search(tok):
            continue
        low = tok.lower()
        if len(low) < 3:
            continue
        if low in vocab:
            out.append(tok)
    return out


def looks_mixed_english(name: str) -> bool:
    return bool(leftover_english_tokens(name))


def _normalize_en(name_en: str) -> str:
    raw = (name_en or "").strip().lower()
    raw = raw.replace("&", " and ")
    raw = raw.replace("—", " ").replace("–", " ")
    raw = re.sub(r"[()]", " ", raw)
    raw = raw.replace("/", " ")
    raw = raw.replace("-", " ")
    return re.sub(r"\s+", " ", raw).strip()


def translate_exercise_name_en(name_en: str) -> str:
    raw = re.sub(r"\s+", " ", (name_en or "").strip())
    if not raw:
        return raw
    low = f" {_normalize_en(raw)} "
    # Also try original hyphenated form for phrase keys that include hyphens.
    hyphen_low = f" {re.sub(r'\s+', ' ', raw.lower())} "
    working = hyphen_low
    for en, vi in _PHRASES:
        padded = f" {en} "
        repl = f" {vi} " if vi else " "
        working = working.replace(padded, repl)
        low = low.replace(padded, repl)
    if leftover_english_tokens(working.strip()):
        merged = working
        for en, vi in _PHRASES:
            merged = merged.replace(f" {en} ", f" {vi} " if vi else " ")
            merged = merged.replace(f" {_normalize_en(en)} ", f" {vi} " if vi else " ")
        working = merged if not leftover_english_tokens(merged.strip()) else low
        for en, vi in _PHRASES:
            working = working.replace(f" {en} ", f" {vi} " if vi else " ")
            working = working.replace(f" {_normalize_en(en)} ", f" {vi} " if vi else " ")
    for en, vi in _WORDS:
        working = re.sub(rf"\b{re.escape(en)}\b", vi, working)
    out = re.sub(r"\s+", " ", working).strip(" -/,")
    out = re.sub(r"\s+", " ", out)
    if not out:
        return raw
    return out[0].upper() + out[1:]


def preferred_name_vi(*, name_en: str, name_vi: str | None, copy_vi: str | None) -> str:
    for candidate in (copy_vi, name_vi):
        text = (candidate or "").strip()
        if text and not looks_mixed_english(text) and text.lower() != (name_en or "").strip().lower():
            return text
    translated = translate_exercise_name_en(name_en)
    if translated and not looks_mixed_english(translated):
        return translated
    current = (name_vi or "").strip()
    if current and not looks_mixed_english(current):
        return current
    return translated or current or name_en


def should_skip_exercise_name(*, name_en: str | None, name_vi: str | None, owner_user_id: str | None) -> bool:
    if owner_user_id:
        return True
    blob = f"{name_en or ''} {name_vi or ''}"
    return bool(
        _SKIP_NAME.search((name_en or "").strip())
        or _SKIP_NAME.search((name_vi or "").strip())
        or "e2e hlv" in blob.lower()
    )


def apply_catalog_names_vi(db) -> int:
    """Rewrite mixed English in public catalog name_vi. Returns updated row count."""
    from datetime import UTC, datetime

    from app.models.entities import Exercise
    from app.services.exercise_copy_seed import load_exercise_copy_seed

    copies: dict[str, str] = {}
    for row in load_exercise_copy_seed():
        key = str(row.get("name_en") or "").strip().lower()
        vi = str(row.get("name_vi") or "").strip()
        if key and vi:
            copies[key] = vi
    now = datetime.now(UTC).replace(tzinfo=None)
    updated = 0
    for row in db.query(Exercise).all():
        if should_skip_exercise_name(
            name_en=row.name_en,
            name_vi=row.name_vi,
            owner_user_id=str(row.owner_user_id) if row.owner_user_id else None,
        ):
            continue
        copy_vi = copies.get(str(row.name_en or "").strip().lower())
        new_vi = preferred_name_vi(
            name_en=str(row.name_en or ""),
            name_vi=row.name_vi,
            copy_vi=copy_vi,
        )
        if not new_vi or new_vi == (row.name_vi or "").strip():
            continue
        row.name_vi = new_vi
        row.updated_at = now
        updated += 1
    return updated
