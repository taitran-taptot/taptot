"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BRAND_INTRO_BG, BRAND_SLOGAN, BRAND_T_FIRST, BRAND_T_SECOND } from "@/lib/brand";

const PLAY_MS = 3800;
const FADE_MS = 700;

export default function TaptotIntro() {
  const [visible, setVisible] = useState(true);
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
    if (reduce) {
      setVisible(false);
      return;
    }

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
            .tt-chef { transform-origin: 1037px 350px; animation: ttChef 3.8s cubic-bezier(0.4, 0, 0.2, 1) forwards; }
            .tt-pan { transform-origin: 1140px 385px; animation: ttPan 3.8s cubic-bezier(0.4, 0, 0.2, 1) forwards; }
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
            @keyframes ttChef {
              0%, 36% { opacity: 1; transform: scale(1); }
              42%, 100% { opacity: 0; transform: scale(0.3) translateY(20px); }
            }
            @keyframes ttPan {
              0% { opacity: 1; transform: rotate(0deg) translateY(0); }
              12% { transform: rotate(-10deg) translateY(-10px); }
              22% { transform: rotate(6deg) translateY(4px); }
              32% { transform: rotate(-6deg) translateY(-6px); }
              38% { opacity: 1; transform: rotate(0deg) translateY(0); }
              44%, 100% { opacity: 0; transform: scale(0.4) translateX(20px); }
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
              <g className="tt-chef">
                <path
                  d="M 1008 295 C 1000 295, 995 282, 1004 272 C 1014 260, 1034 260, 1037 268 C 1040 260, 1060 260, 1070 272 C 1079 282, 1074 295, 1066 295 Z"
                  fill={BRAND_T_SECOND}
                />
                <rect x="1007" y="296" width="60" height="9" rx="2" fill={BRAND_T_SECOND} />
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
              </g>
            </g>
          </g>
          <g className="tt-brand">
            <text
              x="960"
              y="735"
              fontFamily="Be Vietnam Pro, system-ui, sans-serif"
              fontSize="64"
              fontWeight="800"
              letterSpacing="-1.6"
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
              fontFamily="Be Vietnam Pro, system-ui, sans-serif"
              fontSize="20"
              fontWeight="800"
              letterSpacing="-0.5"
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
