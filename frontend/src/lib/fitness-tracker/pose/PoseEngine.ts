import type { Point2D } from "../types";

export const CAMERA_WIDTH = 640;
export const CAMERA_HEIGHT = 480;

const WASM_CDN = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.32/wasm";
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

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

export class PoseEngine {
  private landmarker: PoseLandmarkerLike | null = null;
  private stream: MediaStream | null = null;
  private raf = 0;
  private running = false;
  private onFrame: ((frame: PoseFrame) => void) | null = null;

  async start(video: HTMLVideoElement, onFrame: (frame: PoseFrame) => void, facingMode: VideoFacingModeEnum = "user"): Promise<void> {
    this.onFrame = onFrame;
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        width: { ideal: CAMERA_WIDTH },
        height: { ideal: CAMERA_HEIGHT },
        facingMode,
      },
    });
    video.srcObject = this.stream;
    video.playsInline = true;
    video.muted = true;
    await video.play();

    const vision = await import("@mediapipe/tasks-vision");
    const fileset = await vision.FilesetResolver.forVisionTasks(WASM_CDN);
    const options = {
      runningMode: "VIDEO" as const,
      numPoses: 1,
    };
    try {
      this.landmarker = await vision.PoseLandmarker.createFromOptions(fileset, {
        ...options,
        baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" },
      });
    } catch {
      this.landmarker = await vision.PoseLandmarker.createFromOptions(fileset, {
        ...options,
        baseOptions: { modelAssetPath: MODEL_URL, delegate: "CPU" },
      });
    }

    this.running = true;
    const loop = () => {
      if (!this.running || !this.landmarker) return;
      if (video.readyState >= 2) {
        const ts = performance.now();
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
        } catch {
          /* drop a bad frame */
        }
      }
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
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
  }
}
