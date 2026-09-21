"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import PoseOverlay from "@/components/fitness-test/PoseOverlay";
import {
  CAMERA_HEIGHT,
  CAMERA_WIDTH,
  PoseEngine,
  PushUpDetector,
  PUSHUP_IDLE_MS,
  ScreenWakeLock,
  discountPercentForReps,
  savePushupDiscount,
  savePushupTicket,
  unlockBeeps,
  pushupIdleExpired,
  type ExerciseProgress,
  type Point2D,
} from "@/lib/fitness-tracker";
import { formatCountdown } from "@/lib/fitness-tracker/session/offers";
import { pushupChallengeApi } from "@/lib/pushupChallengeApi";

export default function PushupDiscountSession() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const engineRef = useRef<PoseEngine | null>(null);
  const detectorRef = useRef(new PushUpDetector());
  const wakeRef = useRef(new ScreenWakeLock());
  const lastUiAtRef = useRef(0);
  const lastUiKeyRef = useRef("");
  const phaseRef = useRef<"idle" | "countdown" | "running" | "done">("idle");
  const lastRepRef = useRef(0);
  const lastActivityAtRef = useRef(0);
  const runningStartedAtRef = useRef(0);
  const finishingRef = useRef(false);
  const sessionIdRef = useRef("");

  const [phase, setPhase] = useState<"idle" | "countdown" | "running" | "done">("idle");
  const [left, setLeft] = useState(15);
  const [elapsed, setElapsed] = useState(0);
  const [idleLeft, setIdleLeft] = useState(Math.round(PUSHUP_IDLE_MS / 1000));
  const [progress, setProgress] = useState<ExerciseProgress | null>(null);
  const [landmarks, setLandmarks] = useState<Point2D[] | null>(null);
  const [error, setError] = useState("");
  const [reps, setReps] = useState(0);
  const [ticketState, setTicketState] = useState<"idle" | "pending" | "ready" | "failed">("idle");

  phaseRef.current = phase;

  useEffect(() => {
    return () => {
      engineRef.current?.stop();
      void wakeRef.current.release();
    };
  }, []);

  const finish = useCallback(() => {
    if (finishingRef.current || phaseRef.current === "done") return;
    finishingRef.current = true;
    const count = detectorRef.current.getProgress().count ?? 0;
    setReps(count);
    setPhase("done");
    phaseRef.current = "done";
    engineRef.current?.stop();
    void wakeRef.current.release();
    setTicketState("pending");
    const sid = sessionIdRef.current;
    if (!sid) {
      savePushupDiscount(count);
      setTicketState("failed");
      return;
    }
    void pushupChallengeApi
      .finishSession(sid, count)
      .then((out) => {
        savePushupTicket(out.ticket);
        setTicketState("ready");
      })
      .catch(() => {
        savePushupDiscount(count);
        setTicketState("failed");
      });
  }, []);

  async function startCam() {
    setError("");
    finishingRef.current = false;
    setTicketState("idle");
    sessionIdRef.current = "";
    const video = videoRef.current;
    if (!video) return;
    try {
      const started = await pushupChallengeApi.startSession();
      sessionIdRef.current = started.session_id;
    } catch (err) {
      setError((err as Error).message || "Không mở được phiên tập.");
      return;
    }
    await unlockBeeps();
    await wakeRef.current.request();
    const engine = new PoseEngine();
    engineRef.current = engine;
    detectorRef.current.reset();
    lastRepRef.current = 0;
    try {
      await engine.start(video, (frame) => {
        detectorRef.current.process(frame.landmarks);
        const prog = detectorRef.current.getProgress();
        const count = prog.count ?? 0;
        if (phaseRef.current === "running" && count > lastRepRef.current) {
          lastRepRef.current = count;
          lastActivityAtRef.current = performance.now();
        }
        const key = `${count}:${prog.state ?? ""}:${prog.isValidForm}`;
        const now = performance.now();
        if (key !== lastUiKeyRef.current || now - lastUiAtRef.current >= 100) {
          lastUiKeyRef.current = key;
          lastUiAtRef.current = now;
          setLandmarks(frame.landmarks);
          setProgress(prog);
          setReps(count);
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
          lastActivityAtRef.current = performance.now();
          runningStartedAtRef.current = performance.now();
          lastRepRef.current = detectorRef.current.getProgress().count ?? 0;
          setIdleLeft(Math.round(PUSHUP_IDLE_MS / 1000));
          setElapsed(0);
          setPhase("running");
          return 0;
        }
        return n - 1;
      });
    }, 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  useEffect(() => {
    if (phase !== "running") return;
    const id = window.setInterval(() => {
      const now = performance.now();
      setElapsed(Math.max(0, Math.floor((now - runningStartedAtRef.current) / 1000)));
      const remainMs = Math.max(0, PUSHUP_IDLE_MS - (now - lastActivityAtRef.current));
      setIdleLeft(Math.ceil(remainMs / 1000));
      if (pushupIdleExpired(lastActivityAtRef.current, now)) {
        window.clearInterval(id);
        finish();
      }
    }, 200);
    return () => window.clearInterval(id);
  }, [finish, phase]);

  const percent = discountPercentForReps(reps);

  return (
    <div className="space-y-5">
      <header className="rounded-3xl bg-gradient-to-br from-orange-50 to-white px-6 py-8 shadow-soft ring-1 ring-orange-100">
        <p className="type-kicker text-orange-600">Giảm giá phụ kiện</p>
        <h1 className="type-display mt-2">Chống đẩy không giới hạn giờ</h1>
        <p className="mt-2 text-sm text-slate-600">
          0–20 cái: 5% · 21–50 cái: 7% · trên 50 cái: 10%. Dừng 10 giây không chống thêm thì kết thúc. Camera đếm trên
          máy bạn.
        </p>
        {phase === "idle" && (
          <button
            type="button"
            className="mt-4 rounded-xl bg-orange-500 px-5 py-3 text-sm font-bold text-white"
            onClick={() => void startCam()}
          >
            Bật camera
          </button>
        )}
      </header>

      <div className="relative overflow-hidden rounded-3xl bg-slate-950 text-white shadow-soft">
        <div className="relative aspect-[4/3] bg-black">
          <video
            ref={videoRef}
            className="h-full w-full object-cover"
            playsInline
            muted
            style={{ transform: "scaleX(-1)" }}
          />
          <div className="absolute inset-0" style={{ transform: "scaleX(-1)" }}>
            <PoseOverlay
              landmarks={landmarks}
              width={CAMERA_WIDTH}
              height={CAMERA_HEIGHT}
              valid={progress?.isValidForm ?? true}
            />
          </div>
          {phase === "idle" && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/40">
              <p className="text-sm text-slate-200">Bấm Bật camera ở trên để bắt đầu 15 giây chuẩn bị.</p>
            </div>
          )}
          {phase === "countdown" && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/55">
              <p className="text-7xl font-bold">{left}</p>
              <p className="mt-2 text-sm">Vào plank, đếm ngược xong bắt đầu chống. Dừng 10 giây là hết bài.</p>
            </div>
          )}
        </div>
        <div className="flex items-center justify-between px-5 py-4">
          <p className="text-3xl font-bold tabular-nums">{reps} cái</p>
          <div className="text-right">
            <p className="text-xl font-bold">
              {phase === "running"
                ? formatCountdown(elapsed)
                : phase === "done"
                  ? "Kết thúc"
                  : "—"}
            </p>
            {phase === "running" && (
              <p className="mt-0.5 text-xs font-semibold text-orange-200">Còn {idleLeft}s nếu không chống thêm</p>
            )}
          </div>
        </div>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {progress && phase === "running" && (
        <p className={progress.isValidForm ? "text-sm text-brand-700" : "text-sm text-rose-600"}>
          {progress.statusText}
        </p>
      )}

      {phase === "done" && (
        <div className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
          <p className="text-lg font-bold">
            {reps} cái → giảm {percent}% phụ kiện tập
          </p>
          <p className="mt-2 text-sm text-slate-600">
            {ticketState === "ready"
              ? "Phiếu giảm giá đã lưu trên máy này. Đưa phiếu cho TAPTOT khi xác nhận đơn."
              : ticketState === "pending"
                ? "Đang lưu phiếu giảm giá…"
                : "Mức giảm đang lưu trên máy. Máy chủ chưa cấp phiếu — TAPTOT có thể không xác nhận được."}
          </p>
          <Link
            href="/mua-dung-cu"
            className="mt-4 inline-flex rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white"
          >
            Sang mua dụng cụ
          </Link>
        </div>
      )}
    </div>
  );
}
