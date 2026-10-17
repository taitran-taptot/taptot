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
  return "Lịch mới chỉ còn Nhập môn hoặc Thử thách 100 ngày. Tăng nhẹ khi làm hết số cái: có tạ khoảng 2.5 kg.";
}