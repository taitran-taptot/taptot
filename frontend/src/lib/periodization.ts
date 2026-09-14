/** UX helpers for tiered progressive overload (mirrors backend periodization tiers). */

export const MIN_DURATION_WEEKS = 4;
export const MAX_DURATION_WEEKS = 8;

export function defaultDurationWeeks(_level?: number): number {
  void _level;
  return MIN_DURATION_WEEKS;
}

export function progressionHintVi(level: number, challenge = false): string {
  if (challenge) {
    return "Thử thách 100 ngày (14 tuần): 3 giai đoạn · tuần 4, 8 và 14 tập nhẹ hơn để cơ thể hồi; lịch tập/ăn đổi theo giai đoạn.";
  }
  if (level <= 2) {
    return "Lặp tuần mẫu. Làm hết số cái trên lịch mà vẫn dễ thì buổi sau tăng nhẹ: có tạ thì khoảng 2.5 kg, không dụng cụ thì thêm 1–2 cái. Tuần cuối tập nhẹ nếu lịch dài từ 6 tuần.";
  }
  if (level === 3) {
    return "Tăng dần vừa phải: thêm một hiệp mỗi 3 tuần; tuần cuối tập nhẹ nếu lịch dài từ 4 tuần.";
  }
  return "Tăng dần mạnh hơn: thêm một hiệp mỗi 2 tuần; tuần cuối tập nhẹ nếu lịch dài từ 4 tuần.";
}