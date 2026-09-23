import type { ChallengeOfferKey, DetectorMode, GenderKey } from "../types";
import type { DetectorKind } from "../detectors/createDetector";

export type StationKind =
  | "warmup_work"
  | "warmup_rest"
  | "exercise"
  | "rest"
  | "run"
  | "stretch";

export type ProtocolStation = {
  id: string;
  kind: StationKind;
  labelVi: string;
  hintVi: string;
  durationSec: number;
  detector?: DetectorKind;
  setIndex?: number;
};

export function pullModeForGender(gender: GenderKey, _offer?: ChallengeOfferKey): DetectorMode {
  return gender === "female" ? "hang" : "reps";
}

export function offerStandardLevel(_offer: ChallengeOfferKey): "basic" | "advanced" {
  return "advanced";
}

/** Thử thách 100 ngày: chỉ khởi động, 4 bài camera và giãn cơ — không chạy GPS. */
export function offerIncludesRun(_offer?: ChallengeOfferKey): boolean {
  return false;
}

export function buildProtocol(gender: GenderKey, offer?: ChallengeOfferKey): ProtocolStation[] {
  const pullReps = pullModeForGender(gender, offer) === "reps";
  const pullLabel = pullReps ? "Kéo xà" : "Treo xà";
  const pullHint = pullReps
    ? "Treo thẳng rồi kéo cằm lên trên đường cổ tay. Hết giờ hoặc bấm Dừng."
    : "Nắm xà, duỗi tay, nhấc chân. AI tích giây khi form treo chuẩn.";
  const restBetween = 60;
  const restHint = "Nghỉ 1 phút hoặc bấm chuyển bài khi sẵn sàng.";

  const stations: ProtocolStation[] = [];
  for (let set = 1; set <= 3; set += 1) {
    stations.push({
      id: `warmup-work-${set}`,
      kind: "warmup_work",
      labelVi: `Khởi động · Jumping jack (set ${set}/3)`,
      hintVi: "30 giây jumping jack — chưa cần camera nhận diện, làm theo đồng hồ.",
      durationSec: 30,
      setIndex: set,
    });
    stations.push({
      id: `warmup-rest-${set}`,
      kind: "warmup_rest",
      labelVi: `Nghỉ khởi động (set ${set}/3)`,
      hintVi: "Nghỉ 1 phút. Giữ máy trong khung, chuẩn bị set tiếp.",
      durationSec: 60,
      setIndex: set,
    });
  }

  const work: Array<{ id: string; label: string; hint: string; detector: DetectorKind; sec: number }> = [
    {
      id: "pushup",
      label: "Chống đẩy",
      hint: "Plank, thân không nghiêng quá 40°. Khuỷu xuống ≤ 90° rồi đẩy lên.",
      detector: "pushup",
      sec: 60,
    },
    {
      id: "pull",
      label: pullLabel,
      hint: pullHint,
      detector: "pullup",
      sec: 60,
    },
    {
      id: "squat",
      label: "Đứng lên ngồi xuống",
      hint: "Hạ hông ngang/thấp hơn gối (góc gối ≤ 90°) rồi đứng thẳng.",
      detector: "squat",
      sec: 60,
    },
    {
      id: "plank",
      label: "Plank",
      hint: "Thân 155–180°, song song sàn (< 20°). Võng lưng sẽ dừng đếm giờ.",
      detector: "plank",
      sec: 120,
    },
  ];

  work.forEach((item, i) => {
    stations.push({
      id: item.id,
      kind: "exercise",
      labelVi: item.label,
      hintVi: item.hint,
      durationSec: item.sec,
      detector: item.detector,
    });
    const includeRun = offerIncludesRun(offer);
    const needRest = i < work.length - 1 || (includeRun && i === work.length - 1);
    if (needRest) {
      stations.push({
        id: `${item.id}-rest`,
        kind: "rest",
        labelVi: `Nghỉ sau ${item.label}`,
        hintVi: restHint,
        durationSec: restBetween,
      });
    }
  });

  if (offerIncludesRun(offer)) {
    stations.push({
      id: "run",
      kind: "run",
      labelVi: "Chạy / đi bộ 10 phút",
      hintVi: "Bật GPS. Sai số > 20 m bị bỏ; chỉ cộng khi dịch chuyển ≥ 0,5 m.",
      durationSec: 600,
    });
  }
  stations.push({
    id: "stretch",
    kind: "stretch",
    labelVi: "Giãn cơ 3 phút",
    hintVi: "Bắt buộc. Bỏ qua sẽ đánh failed thể lực (vẫn xem được lời khuyên).",
    durationSec: 180,
  });
  return stations;
}

export class ProtocolClock {
  private index = 0;
  private remainingMs: number;
  private lastTick = 0;
  private paused = false;

  constructor(private readonly stations: ProtocolStation[]) {
    this.remainingMs = (stations[0]?.durationSec ?? 0) * 1000;
  }

  get current(): ProtocolStation {
    return this.stations[this.index] ?? this.stations[this.stations.length - 1];
  }

  get stationIndex(): number {
    return this.index;
  }

  get remainingSec(): number {
    return Math.max(0, Math.ceil(this.remainingMs / 1000));
  }

  get done(): boolean {
    return this.index >= this.stations.length;
  }

  get totalStations(): number {
    return this.stations.length;
  }

  tick(now: number): void {
    if (this.paused || this.done) return;
    if (!this.lastTick) {
      this.lastTick = now;
      return;
    }
    this.remainingMs -= now - this.lastTick;
    this.lastTick = now;
    if (this.remainingMs <= 0) this.advance();
  }

  skip(): void {
    this.advance();
  }

  pause(): void {
    this.paused = true;
    this.lastTick = 0;
  }

  resume(): void {
    this.paused = false;
  }

  reset(): void {
    this.index = 0;
    this.remainingMs = (this.stations[0]?.durationSec ?? 0) * 1000;
    this.lastTick = 0;
    this.paused = false;
  }

  private advance(): void {
    this.index += 1;
    this.lastTick = 0;
    if (this.index >= this.stations.length) {
      this.remainingMs = 0;
      return;
    }
    this.remainingMs = this.stations[this.index].durationSec * 1000;
  }
}
