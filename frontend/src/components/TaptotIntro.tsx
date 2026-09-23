"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BRAND_INTRO_BG, BRAND_SLOGAN, BRAND_T_FIRST, BRAND_T_SECOND } from "@/lib/brand";

const PLAY_MS = 3800;
const FADE_MS = 700;
export const TAPTOT_INTRO_SEEN_KEY = "taptot_intro_seen";

export const TAPTOT_INTRO_BOOT_SCRIPT = `try{if(!window.matchMedia("(prefers-reduced-motion: reduce)").matches&&(new URLSearchParams(location.search).has("intro")||localStorage.getItem("${TAPTOT_INTRO_SEEN_KEY}")!=="1"))document.documentElement.classList.add("tt-intro-active")}catch(e){}`;

function introAlreadySeen() {
  try {
    return window.localStorage.getItem(TAPTOT_INTRO_SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

function markIntroSeen() {
  try {
    window.localStorage.setItem(TAPTOT_INTRO_SEEN_KEY, "1");
  } catch {
    /* ignore quota / private mode */
  }
}

function forceIntroReplay() {
  try {
    return new URLSearchParams(window.location.search).has("intro");
  } catch {
    return false;
  }
}

export default function TaptotIntro() {
  const [visible, setVisible] = useState(false);
  const [fading, setFading] = useState(false);
  const timerRef = useRef<number | null>(null);
  const doneRef = useRef(false);

  const clearTimer = () => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const hide = useCallback((immediate = false) => {
    if (doneRef.current) return;
    doneRef.current = true;
    markIntroSeen();
    clearTimer();
    document.documentElement.classList.remove("tt-intro-active");
    document.body.style.overflow = "";
    if (immediate) {
      setVisible(false);
      return;
    }
    setFading(true);
    window.setTimeout(() => setVisible(false), FADE_MS);
  }, []);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || (introAlreadySeen() && !forceIntroReplay())) {
      document.documentElement.classList.remove("tt-intro-active");
      return;
    }

    setVisible(true);
    document.documentElement.classList.add("tt-intro-active");
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    timerRef.current = window.setTimeout(() => hide(), PLAY_MS);
    return () => {
      clearTimer();
      document.body.style.overflow = prev;
      document.documentElement.classList.remove("tt-intro-active");
    };
  }, [hide]);

  if (!visible) return null;

  return (
    <div
      className={`fixed inset-0 z-[200] flex items-center justify-center overflow-hidden transition-opacity ease-out ${
        fading ? "pointer-events-none opacity-0" : "opacity-100"
      }`}
      style={{
        background: BRAND_INTRO_BG,
        transitionDuration: `${FADE_MS}ms`,
      }}
      role="dialog"
      aria-label="Giới thiệu TAPTOT"
      aria-modal="true"
    >
      {!fading && (
        <button
          type="button"
          onClick={() => hide(true)}
          className="absolute top-4 right-4 z-10 rounded-full bg-white/10 px-4 py-2 text-sm font-bold text-white/90 backdrop-blur-sm transition hover:bg-white/20"
        >
          Bỏ qua
        </button>
      )}

      <div className="flex h-full w-full items-center justify-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="520 50 880 913"
          preserveAspectRatio="xMidYMid meet"
          className="h-full w-full"
        >
          <defs>
            <filter id="tt-intro-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="6" stdDeviation="16" floodColor="#10B981" floodOpacity="0.35" />
            </filter>
            <linearGradient
              id="tt-intro-join"
              x1="910"
              y1="407"
              x2="960"
              y2="407"
              gradientUnits="userSpaceOnUse"
              spreadMethod="pad"
            >
              <stop offset="0%" stopColor={BRAND_T_FIRST} />
              <stop offset="100%" stopColor={BRAND_T_SECOND} />
            </linearGradient>
          </defs>
          <style>{`
            .tt-lifter { animation: ttLifter 3.8s cubic-bezier(0.2, 0.9, 0.3, 1) forwards; }
            .tt-bar {
              animation:
                ttBar 3.8s cubic-bezier(0.15, 0.85, 0.25, 1) forwards,
                ttCloseLeftBar 3.8s cubic-bezier(0.22, 1, 0.36, 1) forwards;
            }
            .tt-x-left-stem { animation: ttCloseLeftStem 3.8s cubic-bezier(0.22, 1, 0.36, 1) forwards; }
            .tt-x-right-bar { animation: ttCloseRightBar 3.8s cubic-bezier(0.22, 1, 0.36, 1) forwards; }
            .tt-x-right-stem { animation: ttCloseRightStem 3.8s cubic-bezier(0.22, 1, 0.36, 1) forwards; }
            .tt-nonla { transform-origin: 1037px 350px; animation: ttNonla 3.8s cubic-bezier(0.4, 0, 0.2, 1) forwards; }
            .tt-pan { transform-origin: 1140px 385px; animation: ttPan 3.8s cubic-bezier(0.25, 0.9, 0.2, 1) forwards; }
            .tt-toss-a,
            .tt-toss-b { transform-box: fill-box; transform-origin: center; }
            .tt-toss-a { animation: ttTossA 3.8s cubic-bezier(0.25, 0.85, 0.2, 1) forwards; }
            .tt-toss-b { animation: ttTossB 3.8s cubic-bezier(0.25, 0.85, 0.2, 1) forwards; }
            .tt-brand { animation: ttBrand 3.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
            @keyframes ttLifter {
              0% { transform: translateY(80px); opacity: 0; }
              12% { opacity: 1; }
              25%, 36% { transform: translateY(0); opacity: 1; }
              42%, 100% { transform: scale(0.2); opacity: 0; }
            }
            @keyframes ttBar {
              0% { transform: translateY(-90px); opacity: 0; }
              12% { opacity: 1; }
              25%, 36% { transform: translateY(-170px); }
              44% { transform: translateY(6px); }
              48% { transform: translateY(-4px); }
              52%, 100% { transform: translateY(0); opacity: 1; }
            }
            @keyframes ttNonla {
              0% { opacity: 1; transform: scale(1) rotate(0deg); }
              8% { transform: scale(1) rotate(2deg); }
              16% { transform: scale(1) rotate(-3deg); }
              28% { transform: scale(1) rotate(1deg); }
              36% { opacity: 1; transform: scale(1) rotate(0deg); }
              42%, 100% { opacity: 0; transform: scale(0.3) translateY(20px); }
            }
            @keyframes ttPan {
              0% { opacity: 1; transform: rotate(0deg) translateY(0); }
              8% { transform: rotate(8deg) translateY(3px); }
              16% { transform: rotate(-20deg) translateY(-8px); }
              24% { transform: rotate(5deg) translateY(2px); }
              32% { transform: rotate(-3deg) translateY(-2px); }
              38% { opacity: 1; transform: rotate(0deg) translateY(0); }
              44%, 100% { opacity: 0; transform: scale(0.4) translateX(20px); }
            }
            @keyframes ttTossA {
              0%, 10% { transform: translate(0, 0) rotate(0deg); }
              17% { transform: translate(0, -28px) rotate(-10deg); }
              25% { transform: translate(0, -5px) rotate(5deg); }
              33%, 100% { transform: translate(0, 0) rotate(0deg); }
            }
            @keyframes ttTossB {
              0%, 12% { transform: translate(0, 0) rotate(0deg); }
              19% { transform: translate(0, -22px) rotate(12deg); }
              27% { transform: translate(0, -4px) rotate(-4deg); }
              34%, 100% { transform: translate(0, 0) rotate(0deg); }
            }
            @keyframes ttCloseLeftBar {
              0%, 52% { x: 755px; }
              70%, 100% { x: 795px; }
            }
            @keyframes ttCloseLeftStem {
              0%, 52% { x: 805px; }
              70%, 100% { x: 845px; }
            }
            @keyframes ttCloseRightBar {
              0%, 52% { x: 960px; }
              70%, 100% { x: 920px; }
            }
            @keyframes ttCloseRightStem {
              0%, 52% { x: 1010px; }
              70%, 100% { x: 970px; }
            }
            @keyframes ttBrand {
              0%, 70% { opacity: 0; transform: translateY(30px); }
              82%, 100% { opacity: 1; transform: translateY(0); }
            }
          `}</style>
          <g filter="url(#tt-intro-glow)" transform="translate(25 0)">
            <g>
              <g className="tt-lifter">
                <circle cx="832.5" cy="305" r="16" fill={BRAND_T_FIRST} />
                <path
                  d="M 810 330 L 775 260 L 780 215"
                  stroke={BRAND_T_FIRST}
                  strokeWidth="12"
                  strokeLinecap="round"
                  fill="none"
                />
                <path
                  d="M 855 330 L 890 260 L 885 215"
                  stroke={BRAND_T_FIRST}
                  strokeWidth="12"
                  strokeLinecap="round"
                  fill="none"
                />
              </g>
              <rect className="tt-bar" x="755" y="380" width="155" height="55" rx="5" fill="url(#tt-intro-join)" />
              <rect className="tt-x-left-stem" x="805" y="435" width="55" height="195" fill={BRAND_T_FIRST} />
            </g>
            <g>
              <g className="tt-nonla">
                <path
                  d="M 1037 246 L 976 298 Q 1037 318 1098 298 Z"
                  fill={BRAND_T_SECOND}
                />
                <path
                  d="M 1004 276 L 1037 256 L 1070 276"
                  fill="none"
                  stroke={BRAND_INTRO_BG}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  opacity="0.35"
                />
                <path
                  d="M 988 292 L 1037 268 L 1086 292"
                  fill="none"
                  stroke={BRAND_INTRO_BG}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  opacity="0.22"
                />
                <path
                  d="M 1006 306 Q 1037 352 1068 306"
                  fill="none"
                  stroke={BRAND_T_SECOND}
                  strokeWidth="3"
                  strokeLinecap="round"
                />
                <circle cx="1037" cy="326" r="16" fill={BRAND_T_SECOND} />
              </g>
              <rect className="tt-x-right-bar" x="960" y="380" width="155" height="55" fill="url(#tt-intro-join)" />
              <rect className="tt-x-right-stem" x="1010" y="435" width="55" height="195" fill={BRAND_T_SECOND} />
              <g className="tt-pan">
                <circle cx="1175" cy="385" r="11" fill={BRAND_T_SECOND} />
                <rect x="1180" y="380" width="48" height="8" rx="3" fill={BRAND_T_SECOND} transform="rotate(-12 1180 380)" />
                <path
                  d="M 1225 360 C 1225 398, 1310 398, 1310 360 L 1300 360 C 1300 388, 1235 388, 1235 360 Z"
                  fill={BRAND_T_SECOND}
                />
                <path
                  className="tt-toss-a"
                  d="M 1251 367 C 1248 370 1250 376 1256 378 L 1274 376 C 1279 374 1279 368 1275 365 L 1256 364 C 1253 364 1252 365 1251 367 Z"
                  fill={BRAND_T_SECOND}
                />
                <path
                  className="tt-toss-b"
                  d="M 1269 371 C 1267 374 1269 379 1274 380 L 1287 378 C 1291 376 1290 371 1286 369 L 1273 369 C 1270 369 1269 370 1269 371 Z"
                  fill={BRAND_T_SECOND}
                />
              </g>
            </g>
          </g>
          <g className="tt-brand">
            <text
              x="960"
              y="735"
              fontFamily="Lora, ui-serif, Georgia, serif"
              fontSize="64"
              fontWeight="600"
              letterSpacing="0"
              textAnchor="middle"
            >
              <tspan fill={BRAND_T_FIRST}>T</tspan>
              <tspan fill="#FFFFFF">AP</tspan>
              <tspan fill={BRAND_T_SECOND}>T</tspan>
              <tspan fill="#FFFFFF">OT</tspan>
            </text>
            <text
              x="960"
              y="795"
              fontFamily="Nunito Sans, ui-sans-serif, system-ui, sans-serif"
              fontSize="20"
              fontWeight="500"
              letterSpacing="0"
              fill="#FFFFFF"
              textAnchor="middle"
            >
              {BRAND_SLOGAN}
            </text>
          </g>
        </svg>
      </div>
    </div>
  );
}
