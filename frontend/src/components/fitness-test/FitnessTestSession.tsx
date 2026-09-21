"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Modal from "@/components/Modal";
import PoseOverlay from "@/components/fitness-test/PoseOverlay";
import {
  CAMERA_HEIGHT,
  CAMERA_WIDTH,
  PoseEngine,
  ProtocolClock,
  RunTracker,
  ScreenWakeLock,
  buildProtocol,
  createDetector,
  pullModeForGender,
  saveFitnessTestResult,
  savePushupDiscount,
  unlockBeeps,
  type ExerciseProgress,
  type FitnessTestResult,
  type Point2D,
  type ProtocolStation,
} from "@/lib/fitness-tracker";
import type { IExerciseDetector } from "@/lib/fitness-tracker";
import { formatCountdown } from "@/lib/fitness-tracker/session/offers";
import type { ChallengeOfferKey, GenderKey } from "@/lib/fitness-tracker";

type Phase = "countdown" | "running" | "feelings";

type Scores = {
  pushups: number;
  pullups: number;
  pullHold: number;
  squats: number;
  plank: number;
  runMeters: number;
};

const EMPTY_SCORES: Scores = {
  pushups: 0,
  pullups: 0,
  pullHold: 0,
  squats: 0,
  plank: 0,
  runMeters: 0,
};

export default function FitnessTestSession({
  code,
  offer,
  gender,
  onAbort,
  onFinished,
}: {
  code: string;
  offer: ChallengeOfferKey;
  gender: GenderKey;
  onAbort: () => void;
  onFinished: (result: FitnessTestResult) => void;
}) {
  const stations = useRef(buildProtocol(gender, offer)).current;
  const clockRef = useRef(new ProtocolClock(stations));
  const engineRef = useRef<PoseEngine | null>(null);
  const detectorRef = useRef<IExerciseDetector | null>(null);
  const runRef = useRef<RunTracker | null>(null);
  const wakeRef = useRef(new ScreenWakeLock());
  const videoRef = useRef<HTMLVideoElement>(null);
  const scoresRef = useRef<Scores>({ ...EMPTY_SCORES });
  const stretchSkippedRef = useRef(false);
  const stretchDoneRef = useRef(false);
  const startedAtRef = useRef(Date.now());
  const stationIdRef = useRef(stations[0]?.id ?? "");
  const lastUiAtRef = useRef(0);
  const lastUiKeyRef = useRef("");

  const [phase, setPhase] = useState<Phase>("countdown");
  const [countLeft, setCountLeft] = useState(15);
  const [station, setStation] = useState<ProtocolStation>(stations[0]);
  const [remain, setRemain] = useState(stations[0]?.durationSec ?? 0);
  const [progress, setProgress] = useState<ExerciseProgress | null>(null);
  const [landmarks, setLandmarks] = useState<Point2D[] | null>(null);
  const [camError, setCamError] = useState("");
  const [runText, setRunText] = useState("");
  const [feeling, setFeeling] = useState("");
  const [confirmAbort, setConfirmAbort] = useState(false);

  const attachDetector = useCallback(
    (next: ProtocolStation) => {
      detectorRef.current?.reset();
      detectorRef.current = next.detector
        ? createDetector(next.detector, pullModeForGender(gender, offer))
        : null;
      setProgress(null);
    },
    [gender, offer],
  );

  const freezeStationScore = useCallback((prev: ProtocolStation) => {
    const det = detectorRef.current?.getProgress();
    if (prev.detector === "pushup") scoresRef.current.pushups = det?.count ?? scoresRef.current.pushups;
    if (prev.detector === "pullup") {
      scoresRef.current.pullups = det?.count ?? scoresRef.current.pullups;
      scoresRef.current.pullHold = det?.durationSec ?? scoresRef.current.pullHold;
    }
    if (prev.detector === "squat") scoresRef.current.squats = det?.count ?? scoresRef.current.squats;
    if (prev.detector === "plank") scoresRef.current.plank = det?.durationSec ?? scoresRef.current.plank;
    if (prev.kind === "run") {
      const snap = runRef.current?.getSnapshot();
      if (snap) scoresRef.current.runMeters = snap.distanceKm * 1000;
    }
  }, []);

  const enterStation = useCallback(
    (next: ProtocolStation, prev?: ProtocolStation) => {
      if (prev) freezeStationScore(prev);
      stationIdRef.current = next.id;
      attachDetector(next);
      if (next.kind === "run") {
        runRef.current?.stop();
        const tracker = new RunTracker();
        runRef.current = tracker;
        try {
          tracker.start();
        } catch (err) {
          setRunText((err as Error).message);
        }
      } else if (prev?.kind === "run") {
        freezeStationScore(prev);
        runRef.current?.stop();
      }
      if (next.kind === "stretch") stretchDoneRef.current = false;
      setStation(next);
    },
    [attachDetector, freezeStationScore],
  );

  const finishToFeelings = useCallback(() => {
    freezeStationScore(clockRef.current.current);
    runRef.current?.stop();
    if (clockRef.current.current.kind === "stretch" && !stretchSkippedRef.current) {
      stretchDoneRef.current = true;
    }
    setPhase("feelings");
  }, [freezeStationScore]);

  useEffect(() => {
    startedAtRef.current = Date.now();
    void unlockBeeps();
    void wakeRef.current.request();
    const video = videoRef.current;
    if (!video) return;
    const engine = new PoseEngine();
    engineRef.current = engine;
    engine
      .start(video, (frame) => {
        const det = detectorRef.current;
        if (det) {
          det.process(frame.landmarks);
          const prog = det.getProgress();
          const current = clockRef.current.current;
          if (current.detector === "pushup") scoresRef.current.pushups = prog.count ?? 0;
          if (current.detector === "pullup") {
            scoresRef.current.pullups = prog.count ?? 0;
            scoresRef.current.pullHold = prog.durationSec ?? 0;
          }
          if (current.detector === "squat") scoresRef.current.squats = prog.count ?? 0;
          if (current.detector === "plank") scoresRef.current.plank = prog.durationSec ?? 0;
          const key = `${prog.count ?? ""}:${prog.state ?? ""}:${prog.isValidForm}`;
          const now = performance.now();
          if (key !== lastUiKeyRef.current || now - lastUiAtRef.current >= 100) {
            lastUiKeyRef.current = key;
            lastUiAtRef.current = now;
            setLandmarks(frame.landmarks);
            setProgress(prog);
          }
          return;
        }
        const now = performance.now();
        if (now - lastUiAtRef.current >= 100) {
          lastUiAtRef.current = now;
          setLandmarks(frame.landmarks);
        }
      })
      .catch((err) => setCamError((err as Error).message || "Không bật được camera."));
    attachDetector(stations[0]);
    return () => {
      engine.stop();
      runRef.current?.stop();
      void wakeRef.current.release();
    };
  }, [attachDetector, stations]);

  useEffect(() => {
    if (phase !== "countdown") return;
    setCountLeft(15);
    const id = window.setInterval(() => {
      setCountLeft((n) => {
        if (n <= 1) {
          window.clearInterval(id);
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
      const clock = clockRef.current;
      const prev = clock.current;
      clock.tick(performance.now());
      if (clock.done) {
        finishToFeelings();
        return;
      }
      if (clock.current.id !== stationIdRef.current) {
        enterStation(clock.current, prev);
      }
      setRemain(clock.remainingSec);
      if (clock.current.kind === "run") {
        const snap = runRef.current?.getSnapshot();
        if (snap) {
          scoresRef.current.runMeters = snap.distanceKm * 1000;
          const pace = snap.paceMinPerKm;
          const paceText =
            pace == null ? "—" : `${Math.floor(pace)}:${String(Math.round((pace % 1) * 60)).padStart(2, "0")}`;
          setRunText(
            `${snap.distanceKm.toFixed(2)} km · ${snap.speedKmh.toFixed(1)} km/h · pace ${paceText} /km`,
          );
        }
      }
    }, 200);
    return () => window.clearInterval(id);
  }, [enterStation, finishToFeelings, phase]);

  function skipStation() {
    const clock = clockRef.current;
    const prev = clock.current;
    if (prev.kind === "stretch") stretchSkippedRef.current = true;
    clock.skip();
    if (clock.done) {
      finishToFeelings();
      return;
    }
    enterStation(clock.current, prev);
    setRemain(clock.remainingSec);
  }

  function restart() {
    scoresRef.current = { ...EMPTY_SCORES };
    stretchSkippedRef.current = false;
    stretchDoneRef.current = false;
    startedAtRef.current = Date.now();
    clockRef.current.reset();
    runRef.current?.reset();
    attachDetector(stations[0]);
    stationIdRef.current = stations[0].id;
    setStation(stations[0]);
    setRemain(stations[0].durationSec);
    setPhase("countdown");
    setFeeling("");
    setConfirmAbort(false);
  }

  function submitFeeling() {
    const scores = scoresRef.current;
    savePushupDiscount(scores.pushups);
    const result: FitnessTestResult = {
      code,
      offer,
      gender,
      pushupsMax: scores.pushups,
      pullupsMax: scores.pullups,
      pullHoldSeconds: scores.pullHold,
      plankSeconds: scores.plank,
      squatsMax: scores.squats,
      run10MinMeters: scores.runMeters,
      stretchCompleted: stretchDoneRef.current && !stretchSkippedRef.current,
      stretchSkipped: stretchSkippedRef.current,
      feeling: feeling.trim(),
      startedAt: startedAtRef.current,
      finishedAt: Date.now(),
    };
    saveFitnessTestResult(result);
    onFinished(result);
  }

  const showCamera = station.kind === "exercise" || station.kind === "warmup_work" || phase === "countdown";
  const metric =
    station.detector === "plank" || (station.detector === "pullup" && gender === "female")
      ? `${Math.floor(progress?.durationSec ?? 0)}s`
      : station.kind === "run"
        ? runText || "Đang chờ GPS…"
        : `${progress?.count ?? 0} cái`;

  return (
    <div className="space-y-4">
      <div className="relative overflow-hidden rounded-3xl bg-slate-950 text-white shadow-soft">
        <div className="relative aspect-[4/3] w-full bg-black">
          <video
            ref={videoRef}
            className={`h-full w-full object-cover ${showCamera ? "opacity-100" : "opacity-40"}`}
            playsInline
            muted
            style={{ transform: "scaleX(-1)" }}
          />
          <div className="absolute inset-0" style={{ transform: "scaleX(-1)" }}>
            <PoseOverlay
              landmarks={showCamera ? landmarks : null}
              width={CAMERA_WIDTH}
              height={CAMERA_HEIGHT}
              valid={progress?.isValidForm ?? true}
            />
          </div>
          {phase === "countdown" && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/55">
              <p className="type-kicker text-brand-200">Chuẩn bị</p>
              <p className="mt-2 text-7xl font-bold tabular-nums">{countLeft}</p>
              <p className="mt-3 max-w-xs text-center text-sm text-slate-200">
                Đặt máy ngang, cách 2–3 m, toàn thân trong khung. Test bắt đầu sau 15 giây.
              </p>
            </div>
          )}
        </div>
        <div className="space-y-3 px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="type-kicker text-brand-300">
                {phase === "countdown" ? "Đếm ngược" : station.labelVi}
              </p>
              <p className="mt-1 text-sm text-slate-300">{station.hintVi}</p>
            </div>
            <p className="text-3xl font-bold tabular-nums text-white">{formatCountdown(remain)}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="rounded-full bg-white/10 px-3 py-1 font-bold">{metric}</span>
            {progress?.currentAngle != null && (
              <span className="text-slate-300">{Math.round(progress.currentAngle)}°</span>
            )}
            {progress && (
              <span className={progress.isValidForm ? "text-brand-300" : "text-rose-300"}>
                {progress.statusText}
              </span>
            )}
          </div>
          {camError && <p className="text-sm text-rose-300">{camError}</p>}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="rounded-xl bg-brand-500 px-4 py-3 text-sm font-bold text-white hover:bg-brand-600"
          onClick={skipStation}
          disabled={phase !== "running"}
        >
          {station.kind === "stretch" ? "Bỏ giãn cơ (failed thể lực)" : "Dừng / chuyển bài"}
        </button>
        <button
          type="button"
          className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-700"
          onClick={() => setConfirmAbort(true)}
        >
          Hủy và test lại
        </button>
      </div>

      <Modal open={confirmAbort} onClose={() => setConfirmAbort(false)} title="Hủy bài test">
        <div className="space-y-4 p-5">
          <h2 className="text-lg font-bold">Hủy và test lại?</h2>
          <p className="text-sm text-slate-600">Số rep và thời gian hiện tại sẽ bị xóa. Camera giữ nguyên.</p>
          <div className="flex gap-3">
            <button
              type="button"
              className="rounded-xl bg-rose-500 px-4 py-2.5 text-sm font-bold text-white"
              onClick={restart}
            >
              Test lại
            </button>
            <button type="button" className="rounded-xl px-4 py-2.5 text-sm font-bold text-slate-600" onClick={() => setConfirmAbort(false)}>
              Tiếp tục
            </button>
            <button type="button" className="ml-auto text-sm font-semibold text-slate-500" onClick={onAbort}>
              Thoát
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={phase === "feelings"} onClose={() => undefined} title="Cảm nhận sau bài test">
        <div className="space-y-4 p-5">
          <h2 className="text-lg font-bold">Bạn cảm thấy thế nào?</h2>
          <p className="text-sm text-slate-600">
            {stretchSkippedRef.current
              ? "Bạn đã bỏ giãn cơ — bài test thể lực bị đánh failed, vẫn xem được lời khuyên."
              : "Ghi nhanh cảm nhận để huấn luyện viên ảo tư vấn sát hơn."}
          </p>
          <textarea
            className="field min-h-28"
            value={feeling}
            onChange={(e) => setFeeling(e.target.value)}
            placeholder="Ví dụ: hơi mỏi vai, thở được, gối êm…"
          />
          <button type="button" className="w-full rounded-xl bg-brand-500 py-3 text-sm font-bold text-white" onClick={submitFeeling}>
            Xem lời khuyên
          </button>
        </div>
      </Modal>
    </div>
  );
}
