"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PoseOverlay from "@/components/fitness-test/PoseOverlay";
import { brandRichText } from "@/components/brandRichText";
import { PRIVACY_HREF, TERMS_HREF } from "@/lib/legalMeta";
import {
  CAMERA_HEIGHT,
  CAMERA_WIDTH,
  PoseEngine,
  cameraErrorMessage,
  PushUpDetector,
  PUSHUP_PREP_SEC,
  PUSHUP_ROUND_MS,
  ScreenWakeLock,
  discountPercentForReps,
  savePushupDiscount,
  savePushupTicket,
  unlockBeeps,
  pushupRoundExpired,
  type ExerciseProgress,
  type Point2D,
} from "@/lib/fitness-tracker";
import { formatCountdown } from "@/lib/fitness-tracker/session/offers";
import { pushupChallengeApi } from "@/lib/pushupChallengeApi";

export default function PushupDiscountSession() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const engineRef = useRef<PoseEngine | null>(null);
  const detectorRef = useRef(new PushUpDetector());
  const wakeRef = useRef(new ScreenWakeLock());
  const lastUiAtRef = useRef(0);
  const lastUiKeyRef = useRef("");
  const phaseRef = useRef<"idle" | "loading" | "countdown" | "running" | "done">("idle");
  const lastRepRef = useRef(0);
  const runningStartedAtRef = useRef(0);
  const finishingRef = useRef(false);
  const sessionIdRef = useRef("");

  const [phase, setPhase] = useState<"idle" | "loading" | "countdown" | "running" | "done">("idle");
  const [left, setLeft] = useState(PUSHUP_PREP_SEC);
  const [elapsed, setElapsed] = useState(0);
  const [progress, setProgress] = useState<ExerciseProgress | null>(null);
  const [landmarks, setLandmarks] = useState<Point2D[] | null>(null);
  const [error, setError] = useState("");
  const [reps, setReps] = useState(0);
  const [ticketState, setTicketState] = useState<"idle" | "pending" | "ready" | "failed">("idle");
  const [camBusy, setCamBusy] = useState(false);

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
    setCamBusy(true);
    engineRef.current?.stop();
    const engine = new PoseEngine();
    engineRef.current = engine;
    detectorRef.current.reset();
    lastRepRef.current = 0;
    let cameraOn = false;
    try {
      void pushupChallengeApi
        .startSession()
        .then((started) => {
          sessionIdRef.current = started.session_id;
        })
        .catch(() => {
          /* ticket may fail later; camera still works */
        });
      await unlockBeeps();
      await wakeRef.current.request();
      await engine.startCamera(video);
      cameraOn = true;
      setPhase("loading");
      phaseRef.current = "loading";
      await engine.startPose(video, (frame) => {
        detectorRef.current.process(frame.landmarks);
        const prog = detectorRef.current.getProgress();
        const count = prog.count ?? 0;
        if (phaseRef.current === "running" && count > lastRepRef.current) {
          lastRepRef.current = count;
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
      if (!cameraOn) {
        engine.stop();
        engineRef.current = null;
        setPhase("idle");
        phaseRef.current = "idle";
      }
      setError(cameraErrorMessage(err));
    } finally {
      setCamBusy(false);
    }
  }

  useEffect(() => {
    if (phase !== "countdown") return;
    setLeft(PUSHUP_PREP_SEC);
    const id = window.setInterval(() => {
      setLeft((n) => {
        if (n <= 1) {
          window.clearInterval(id);
          runningStartedAtRef.current = performance.now();
          lastRepRef.current = detectorRef.current.getProgress().count ?? 0;
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
      if (pushupRoundExpired(runningStartedAtRef.current, now)) {
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
        <button
          type="button"
          className="mb-4 inline-flex min-h-11 items-center rounded-xl border border-orange-200 bg-white px-4 py-2 text-sm font-bold text-orange-800 transition hover:bg-orange-50"
          onClick={() => {
            if (typeof window !== "undefined" && window.history.length > 1) {
              router.back();
              return;
            }
            router.push("/sukien");
          }}
        >
          ← Quay lại
        </button>
        <h1 className="type-display">Quy tắc thử thách:</h1>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-slate-600">
          <li>Bạn có 15 giây để chuẩn bị và 1 phút để chống đẩy nhanh, nhiều hết sức có thể.</li>
          <li>Nếu {brandRichText("TAPTOT")} nhận diện bạn không làm gì trong 10 giây thì thử thách sẽ tự động kết thúc.</li>
          <li>
            Để bắt đầu bạn hãy nhấp chuột vào nút{" "}
            <span className="whitespace-nowrap">「Bật camera」</span> bên dưới.
          </li>
          <li>
            Các mức ưu đãi là như sau:
            <ul className="mt-1 list-disc space-y-0.5 pl-5">
              <li>0–20 cái: 5%</li>
              <li>21–50 cái: 10%</li>
              <li>Trên 50 cái: 15%</li>
            </ul>
          </li>
          <li>
            Cách đặt camera:
            <ul className="mt-1 list-disc space-y-0.5 pl-5">
              <li>Đặt điện thoại hoặc máy tính ngang, tựa tường hoặc giá, cách người 2–3 mét.</li>
              <li>Máy nhìn nghiêng bên hông khi bạn chống đẩy.</li>
              <li>Toàn thân từ đầu đến chân nằm trong khung. Bật đèn phòng.</li>
            </ul>
          </li>
          <li>
            Camera chỉ dùng để đếm động tác trên thiết bị của bạn; video/khung hình không được tải lên máy chủ
            {brandRichText("TAPTOT")}. Chi tiết xem{" "}
            <Link
              href={PRIVACY_HREF}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800"
            >
              Chính sách bảo mật
            </Link>
            .
          </li>
          <li>
            Bằng cách nhấp chuột vào nút{" "}
            <span className="whitespace-nowrap">「Bật camera」</span> là bạn đã đồng ý với{" "}
            <Link
              href={TERMS_HREF}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800"
            >
              điều khoản
            </Link>{" "}
            và{" "}
            <Link
              href={PRIVACY_HREF}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800"
            >
              chính sách bảo mật
            </Link>{" "}
            của {brandRichText("TAPTOT")}.
          </li>
        </ol>
        {error && <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        {(phase === "idle" || (phase === "loading" && error)) && (
          <button
            type="button"
            className="mt-4 rounded-xl bg-orange-500 px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
            disabled={camBusy}
            onClick={() => void startCam()}
          >
            {camBusy ? "Đang bật camera…" : error ? "Thử lại" : "Bật camera"}
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
          {phase === "idle" && !camBusy && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/40">
              <p className="text-sm text-slate-200">
                Bấm <span className="whitespace-nowrap">「Bật camera」</span> ở trên để bắt đầu.
              </p>
            </div>
          )}
          {(phase === "loading" || (phase === "idle" && camBusy)) && !error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/45">
              <p className="text-lg font-bold">{camBusy && phase === "idle" ? "Đang bật camera…" : "Đang tải nhận dạng…"}</p>
              <p className="mt-2 px-4 text-center text-sm text-slate-200">Giữ người trong khung hình.</p>
            </div>
          )}
          {phase === "countdown" && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/55">
              <p className="text-7xl font-bold">{left}</p>
              <p className="mt-2 text-sm">Vào plank, đếm ngược xong chống trong 1 phút.</p>
            </div>
          )}
        </div>
        <div className="flex items-center justify-between px-5 py-4">
          <p className="text-3xl font-bold tabular-nums">{reps} cái</p>
          <div className="text-right">
            <p className="text-xl font-bold">
              {phase === "running"
                ? formatCountdown(Math.max(0, PUSHUP_ROUND_MS / 1000 - elapsed))
                : phase === "done"
                  ? "Kết thúc"
                  : "—"}
            </p>
            {phase === "running" && (
              <p className="mt-0.5 text-xs font-semibold text-orange-200">Còn lại trong vòng 1 phút</p>
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
              ? "Giảm giá sẽ tự hiện trên giỏ hàng khi đặt dụng cụ. Phiếu tối đa 1 ngày; đóng tab hoặc trình duyệt thì mất trên máy này."
              : ticketState === "pending"
                ? "Đang lưu phiếu giảm giá…"
                : "Mức giảm đang lưu trên máy. Máy chủ chưa cấp phiếu — giỏ hàng có thể không trừ được."}
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
