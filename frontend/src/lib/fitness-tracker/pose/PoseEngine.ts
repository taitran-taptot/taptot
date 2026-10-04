import type { Point2D } from "../types";

export const CAMERA_WIDTH = 640;
export const CAMERA_HEIGHT = 480;

const LOCAL_WASM = "/mediapipe/wasm";
const LOCAL_MODEL = "/mediapipe/pose_landmarker_lite.task";

type PoseLandmarkerLike = {
  detectForVideo: (
    video: HTMLVideoElement,
    timestamp: number,
  ) => { landmarks?: Array<Array<{ x: number; y: number; z?: number; visibility?: number }>> };
  close: () => void;
};

export type PoseFrame = {
  landmarks: Point2D[];
  timestamp: number;
};

function absUrl(path: string): string {
  if (typeof window === "undefined") return path;
  return new URL(path, window.location.origin).href;
}

export function cameraErrorMessage(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  const raw = err instanceof Error ? err.message : String(err || "");
  if (name === "NotAllowedError" || /notallowed|permission|denied/i.test(raw)) {
    return "Trình duyệt đang chặn camera. Bấm biểu tượng camera trên thanh địa chỉ, cho phép, rồi thử lại.";
  }
  if (name === "NotFoundError" || /notfound/i.test(raw)) {
    return "Không tìm thấy camera trên máy này.";
  }
  if (name === "NotReadableError" || /notreadable|device in use|in use/i.test(raw)) {
    return "Camera đang được app khác dùng. Đóng Zoom/Teams/camera khác rồi bấm lại.";
  }
  if (name === "OverconstrainedError") {
    return "Camera không mở được với cấu hình hiện tại. Thử lại, hoặc dùng camera khác.";
  }
  if (/csp|content security|refused to connect|failed to fetch|networkerror|load failed/i.test(raw)) {
    return "Không tải được mô hình nhận dạng chống đẩy. Tải lại trang rồi thử lại.";
  }
  return raw || "Không bật được camera.";
}

async function getCameraStream(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Trình duyệt này không hỗ trợ camera.");
  }
  const attempts: MediaStreamConstraints[] = [
    {
      audio: false,
      video: { width: { ideal: CAMERA_WIDTH }, height: { ideal: CAMERA_HEIGHT }, facingMode: "user" },
    },
    { audio: false, video: { facingMode: "user" } },
    { audio: false, video: true },
  ];
  let last: unknown;
  for (const constraints of attempts) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (err) {
      last = err;
    }
  }
  throw last instanceof Error ? last : new Error("Không bật được camera.");
}

export class PoseEngine {
  private landmarker: PoseLandmarkerLike | null = null;
  private stream: MediaStream | null = null;
  private raf = 0;
  private running = false;
  private onFrame: ((frame: PoseFrame) => void) | null = null;
  private lastDetectTs = 0;
  private loggedDetectError = false;

  async startCamera(video: HTMLVideoElement): Promise<void> {
    this.stream = await getCameraStream();
    video.srcObject = this.stream;
    video.playsInline = true;
    video.muted = true;
    video.setAttribute("playsinline", "true");
    video.autoplay = true;
    await video.play();
  }

  async startPose(video: HTMLVideoElement, onFrame: (frame: PoseFrame) => void): Promise<void> {
    this.onFrame = onFrame;
    const vision = await import("@mediapipe/tasks-vision");
    const fileset = await vision.FilesetResolver.forVisionTasks(absUrl(LOCAL_WASM));
    const options = {
      runningMode: "VIDEO" as const,
      numPoses: 1,
    };
    const modelPath = absUrl(LOCAL_MODEL);
    try {
      this.landmarker = await vision.PoseLandmarker.createFromOptions(fileset, {
        ...options,
        baseOptions: { modelAssetPath: modelPath, delegate: "GPU" },
      });
    } catch {
      this.landmarker = await vision.PoseLandmarker.createFromOptions(fileset, {
        ...options,
        baseOptions: { modelAssetPath: modelPath, delegate: "CPU" },
      });
    }

    this.running = true;
    this.lastDetectTs = 0;
    const loop = () => {
      if (!this.running || !this.landmarker) return;
      if (video.readyState >= 2) {
        let ts = Math.floor(performance.now());
        if (ts <= this.lastDetectTs) ts = this.lastDetectTs + 1;
        this.lastDetectTs = ts;
        try {
          const result = this.landmarker.detectForVideo(video, ts);
          const raw = result.landmarks?.[0];
          if (raw?.length) {
            const landmarks: Point2D[] = raw.map((p) => ({
              x: p.x,
              y: p.y,
              z: p.z,
              visibility: p.visibility,
            }));
            this.onFrame?.({ landmarks, timestamp: ts });
          }
        } catch (err) {
          if (!this.loggedDetectError) {
            this.loggedDetectError = true;
            console.warn("Pose detectForVideo failed", err);
          }
        }
      }
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }

  /** Camera first, then pose. Pose failure does not turn the camera off. */
  async start(video: HTMLVideoElement, onFrame: (frame: PoseFrame) => void): Promise<void> {
    await this.startCamera(video);
    await this.startPose(video, onFrame);
  }

  stop(): void {
    this.running = false;
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
    try {
      this.landmarker?.close();
    } catch {
      /* ignore */
    }
    this.landmarker = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.onFrame = null;
    this.lastDetectTs = 0;
    this.loggedDetectError = false;
  }
}
