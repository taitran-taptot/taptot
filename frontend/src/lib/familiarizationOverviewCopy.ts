import type { PlanInsights } from "@/lib/plansApi";

export const FAMILIARIZATION_MISSION_VI =
  "Bạn đang ở cấp 1 — nhập môn.\n" +
  "Mỗi tuần 3 buổi xen kẽ tập toàn thân.\n" +
  "Tuần 1–2 học form với chống đẩy tường hoặc ghế và kéo balo;\n" +
  "Tuần 3 bắt đầu kéo người nằm (bàn hoặc xà); tuần 4 giảm tải để hồi phục;\n" +
  "Tuần 5–7 treo xà / siết bả vai và tích lũy; tuần 8 giảm tải; tuần 9 kiểm tra đầu ra.";

export const FAMILIARIZATION_HERO_RECAP_VI =
  "Lộ trình cho người làm công việc văn phòng, muốn cải thiện sức khỏe cho cuộc sống hàng ngày nhưng lại chưa có kinh nghiệm tập luyện, chưa từng hoặc rất ít vận động";

const OUTCOME_CLOSING_VI =
  "Đây sẽ là nền tảng để bạn tiếp tục tập luyện lên cao hơn hoặc tham gia các thử thách của TAPTOT.";

export const FAMILIARIZATION_NUTRITION_PRINCIPLES_VI =
  "Nạp đủ đạm 1,6–2,0 g/kg cân nặng mỗi ngày từ món quen (trứng, thịt nạc, cá, đậu).\n" +
  "Uống khoảng 40–45 ml nước/kg, ngủ 7–8,5 tiếng trước 23h.\n" +
  "Ngày nghỉ đi bộ nhẹ 15–20 phút.";

function viInt(value: number): string {
  return Math.round(value).toLocaleString("vi-VN");
}

function viKg(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  if (rounded === Math.trunc(rounded)) return String(Math.trunc(rounded));
  return String(rounded).replace(".", ",");
}

export function familiarizationOutcomeVi(gender: string | null | undefined): string {
  const female = String(gender || "").trim().toLowerCase() === "female";
  if (female) {
    return [
      "Chống đẩy quỳ 4–10 cái.",
      "Treo xà 20–45 giây.",
      "Squat 10–20 cái.",
      "Plank 15–40 giây.",
      "Đi/chạy 0,7–1,0 km trong 10 phút.",
      OUTCOME_CLOSING_VI,
    ].join("\n");
  }
  return [
    "Chống đẩy sàn 3–8 cái (hoặc kê ghế).",
    "Kéo xà 1–2 lần hoặc kéo người nằm 6–10 cái.",
    "Squat 12–25 cái.",
    "Plank 20–50 giây.",
    "Đi/chạy 0,8–1,2 km trong 10 phút.",
    OUTCOME_CLOSING_VI,
  ].join("\n");
}

export function familiarizationWeightGoalCopyVi(
  weightGoal: NonNullable<PlanInsights["weight_goal"]>,
): string {
  const band = (weightGoal.band_vi || "").toLowerCase();
  const currentKg = weightGoal.current_kg;
  const targetKg = weightGoal.target_kg;
  const dailyKcal = weightGoal.daily_kcal;
  if (
    currentKg == null ||
    targetKg == null ||
    dailyKcal == null ||
    !band
  ) {
    return stripProteinClause((weightGoal.copy_vi || "").trim());
  }
  const currentS = viKg(currentKg);
  const targetS = viKg(targetKg);
  const kcalS = viInt(dailyKcal);
  const bmiS =
    weightGoal.target_bmi != null ? viKg(weightGoal.target_bmi) : null;
  const header = `Do BMI của bạn đang là ${band}.`;
  const prefix = `${currentS} kg — ăn khoảng ${kcalS} kcal/ngày`;
  if (weightGoal.goal === "lose_weight") {
    return (
      `${header}\n${prefix} để giảm còn khoảng ${targetS} kg` +
      (bmiS ? ` (BMI ${bmiS})` : "") +
      ` trong 2 tháng, hướng về BMI bình thường 18,5–22,9 với tốc độ an toàn.`
    );
  }
  if (weightGoal.goal === "gain_weight") {
    return (
      `${header}\n${prefix} để tăng lên khoảng ${targetS} kg` +
      (bmiS ? ` (BMI ${bmiS})` : "") +
      ` trong 2 tháng, hướng về BMI bình thường 18,5–22,9 với tốc độ an toàn.`
    );
  }
  return `${header}\n${prefix} để duy trì BMI trong vùng bình thường 18,5–22,9 trong 2 tháng.`;
}

function stripProteinClause(text: string): string {
  return text.replace(/\s*\(đạm [^)]+\)/gi, "");
}

export function familiarizationNutritionVi(
  weightGoal: PlanInsights["weight_goal"] | null | undefined,
): string {
  if (!weightGoal) return FAMILIARIZATION_NUTRITION_PRINCIPLES_VI;
  return `${familiarizationWeightGoalCopyVi(weightGoal)}\n${FAMILIARIZATION_NUTRITION_PRINCIPLES_VI}`;
}
