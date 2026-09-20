"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import PoseOverlay from "@/components/fitness-test/PoseOverlay";
import {
  CAMERA_HEIGHT,
  CAMERA_WIDTH,
  PoseEngine,
  PushUpDetector,
  ScreenWakeLock,
  savePushupDiscount,
  unlockBeeps,
  type ExerciseProgress,
  type Point2D,
} from "@/lib/fitness-tracker";
import { discountPercentForReps } from "@/lib/fitness-tracker";
import { formatCountdown } from "@/lib/fitness-tracker/session/offers";

export default function PushupDiscountSession() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const engineRef = useRef<PoseEngine | null>(null);
  const detectorRef = useRef(new PushUpDetector());
  const wakeRef = useRef(new ScreenWakeLock());
  const lastUiAtRef = useRef(0);
  const lastUiKeyRef = useRef("");
  const [phase, setPhase] = useState<"idle" | "countdown" | "running" | "done">("idle");
  const [left, setLeft] = useState(15);
  const [remain, setRemain] = useState(60);
  const [progress, setProgress] = useState<ExerciseProgress | null>(null);
  const [landmarks, setLandmarks] = useState<Point2D[] | null>(null);
  const [error, setError] = useState("");
  const [reps, setReps] = useState(0);

  useEffect(() => {
    return () => {
      engineRef.current?.stop();
      void wakeRef.current.release();
    };
  }, []);

  async function startCam() {
    setError("");
    const video = videoRef.current;
    if (!video) return;
    await unlockBeeps();
    await wakeRef.current.request();
    const engine = new PoseEngine();
    engineRef.current = engine;
    detectorRef.current.reset();
    try {
      await engine.start(video, (frame) => {
        detectorRef.current.process(frame.landmarks);
        const prog = detectorRef.current.getProgress();
        const key = `${prog.count ?? 0}:${prog.state ?? ""}:${prog.isValidForm}`;
        const now = performance.now();
        if (key !== lastUiKeyRef.current || now - lastUiAtRef.current >= 100) {
          lastUiKeyRef.current = key;
          lastUiAtRef.current = now;
          setLandmarks(frame.landmarks);
          setProgress(prog);
          setReps(prog.count ?? 0);
        }
      });
      setPhase("countdown");
    } catch (err) {
      setError((err as Error).message || "Không bật được camera.");
    }
  }

  useEffect(() => {
    if (phase !== "countdown") return;
    setLeft(15);
    const id = window.setInterval(() => {
      setLeft((n) => {
        if (n <= 1) {
          window.clearInterval(id);
          setPhase("running");
          setRemain(60);
          return 0;
        }
        return n - 1;
      });
    }, 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  useEffect(() => {
    if (phase !== "running") return;
    setRemain(60);
    const id = window.setInterval(() => {
      setRemain((n) => {
        if (n <= 1) {
          window.clearInterval(id);
          const count = detectorRef.current.getProgress().count ?? 0;
          savePushupDiscount(count);
          setReps(count);
          setPhase("done");
          engineRef.current?.stop();
          void wakeRef.current.release();
          return 0;
        }
        return n - 1;
      });
    }, 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  const percent = discountPercentForReps(reps);

  return (
    <div className="space-y-5">
      <header className="rounded-3xl bg-gradient-to-br from-orange-50 to-white px-6 py-8 shadow-soft ring-1 ring-orange-100">
        <p className="text-xs font-bold tracking-wide text-orange-600 uppercase">Giảm giá phụ kiện</p>
        <h1 className="mt-2 text-2xl font-extrabold">Chống đẩy 1 phút</h1>
        <p className="mt-2 text-sm text-slate-600">0–20 cái: 5% · 21–50 cái: 7% · trên 50 cái: 10%.</p>
        {phase === "idle" && (
          <button type="button" className="mt-4 rounded-xl bg-orange-500 px-5 py-3 text-sm font-extrabold text-white" onClick={() => void startCam()}>
            Bật camera
          </button>
        )}
      </header>

      <div className="relative overflow-hidden rounded-3xl bg-slate-950 text-white shadow-soft">
        <div className="relative aspect-[4/3] bg-black">
          <video ref={videoRef} className="h-full w-full object-cover" playsInline muted style={{ transform: "scaleX(-1)" }} />
          <div className="absolute inset-0" style={{ transform: "scaleX(-1)" }}>
            <PoseOverlay landmarks={landmarks} width={CAMERA_WIDTH} height={CAMERA_HEIGHT} valid={progress?.isValidForm ?? true} />
          </div>
          {phase === "idle" && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/40">
              <p className="text-sm text-slate-200">Bấm Bật camera ở trên để bắt đầu 15 giây chuẩn bị.</p>
            </div>
          )}
          {phase === "countdown" && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/55">
              <p className="text-7xl font-extrabold">{left}</p>
              <p className="mt-2 text-sm">Vào plank, đếm ngược xong bắt đầu 1 phút.</p>
            </div>
          )}
        </div>
        <div className="flex items-center justify-between px-5 py-4">
          <p className="text-3xl font-extrabold tabular-nums">{reps} cái</p>
          <p className="text-xl font-bold">{phase === "running" ? formatCountdown(remain) : phase === "done" ? "Hết giờ" : "1:00"}</p>
        </div>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {progress && phase === "running" && (
        <p className={progress.isValidForm ? "text-sm text-brand-700" : "text-sm text-rose-600"}>{progress.statusText}</p>
      )}

      {phase === "done" && (
        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
          <p className="text-lg font-extrabold">
            {reps} cái → giảm {percent}% phụ kiện tập
          </p>
          <p className="mt-2 text-sm text-slate-600">Mức giảm được lưu trên máy này và hiện trên trang mua dụng cụ.</p>
          <Link href="/mua-dung-cu" className="mt-4 inline-flex rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white">
            Sang mua dụng cụ
          </Link>
        </div>
      )}
    </div>
  );
}
