"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { FamiliarizationCatalog } from "@/lib/authApi";
import DirectionNodePanel from "@/components/DirectionNodePanel";
import {
  CHALLENGE_BRANCHES,
  FOUNDATION_NODES,
  SPECIALIZATION_BRANCHES,
  type ChallengeOffer,
  type DirectionSelection,
  type FamiliarizationPath,
  type SpecializationBranchKey,
} from "@/lib/directionTree";
import { contentForSelection } from "@/lib/directionTreeContent";
import { SPEC_THEME } from "@/lib/directionTreeUi";

type NodeRef = (element: HTMLButtonElement | null) => void;

const TREE_COLS =
  "grid w-full min-w-0 grid-cols-[minmax(0,1fr)_max-content_minmax(0,1fr)]";

const SPEC_FORK: SpecializationBranchKey[][] = [
  ["gym", "calisthenic"],
  ["sport", "martial"],
  ["hybrid", "other"],
];

const SPEC_SHORT_VI: Record<SpecializationBranchKey, string> = {
  gym: "Gym",
  calisthenic: "Calisthenic",
  martial: "Võ thuật",
  sport: "Thể thao",
  other: "Khác",
  hybrid: "Hybrid",
};

function foundationClasses(selected: boolean) {
  if (selected) {
    return "dir-select-pulse border-transparent bg-gradient-to-b from-brand-200 to-brand-400 text-brand-950 ring-2 ring-brand-600 shadow-md";
  }
  return "border-brand-200 bg-white text-brand-950 shadow-sm hover:-translate-y-px hover:border-brand-400 hover:bg-brand-50 hover:shadow-md";
}

function specClasses(branchKey: SpecializationBranchKey, selected: boolean) {
  const theme = SPEC_THEME[branchKey];
  return selected
    ? theme.selected
    : `${theme.idle} shadow-sm hover:-translate-y-px hover:shadow-md`;
}

function challengeClasses(opts: { selected: boolean; ready: boolean }) {
  if (opts.selected && opts.ready) {
    return "border-amber-400 bg-amber-100 text-amber-950 ring-2 ring-amber-500 shadow-md";
  }
  if (opts.selected) {
    return "border-dashed border-amber-300 bg-amber-50 text-amber-900 ring-2 ring-amber-200";
  }
  if (!opts.ready) {
    return "border-dashed border-slate-300 bg-white text-slate-500 hover:border-slate-400";
  }
  return "border-amber-300 bg-amber-50 text-amber-950 shadow-sm hover:-translate-y-px hover:border-amber-400 hover:bg-amber-100/80 hover:shadow-md";
}

function TrunkLine({ className = "h-3" }: { className?: string }) {
  return (
    <div
      className={`dir-line-y mx-auto w-0.5 bg-gradient-to-b from-brand-400 to-slate-400 ${className}`}
      aria-hidden
    />
  );
}

function LineDot({ className = "border-slate-400" }: { className?: string }) {
  return (
    <span
      className={`pointer-events-none z-[1] block h-2.5 w-2.5 rounded-full border-2 bg-white ${className}`}
      aria-hidden
    />
  );
}

function Junction() {
  return <LineDot className="mx-auto border-slate-400" />;
}

function BranchIcon({ name }: { name: SpecializationBranchKey }) {
  const common = {
    width: 13,
    height: 13,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (name === "gym") {
    return (
      <svg {...common}>
        <path d="M5 9v6M19 9v6M7 12h10M3 10.5v3M21 10.5v3" />
      </svg>
    );
  }
  if (name === "calisthenic") {
    return (
      <svg {...common}>
        <circle cx="12" cy="6" r="2.2" />
        <path d="M8 21l4-7 4 7M8 12h8M9 12l-3 4M15 12l3 4" />
      </svg>
    );
  }
  if (name === "martial") {
    return (
      <svg {...common}>
        <path d="M8 11c1.5-2 3-3 4-6 1 3 2.5 4 4 6M7 20l5-7 5 7M12 5v3" />
      </svg>
    );
  }
  if (name === "sport") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="8" />
        <path d="M4.5 10c3 1 8 1 15 0M4.5 14c3-1 8-1 15 0M12 4c2 3 3 7 3 8s-1 5-3 8c-2-3-3-7-3-8s1-5 3-8" />
      </svg>
    );
  }
  if (name === "other") {
    return (
      <svg {...common}>
        <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <rect x="4" y="4" width="7" height="7" rx="1.2" />
      <rect x="13" y="4" width="7" height="7" rx="1.2" />
      <rect x="4" y="13" width="7" height="7" rx="1.2" />
      <rect x="13" y="13" width="7" height="7" rx="1.2" />
    </svg>
  );
}

function FoundationCard({
  path,
  stage,
  title,
  blurb,
  selected,
  nodeRef,
  onSelect,
}: {
  path: FamiliarizationPath;
  stage: string;
  title: string;
  blurb: string;
  selected: boolean;
  nodeRef: NodeRef;
  onSelect: () => void;
}) {
  const descId = `direction-${path}-desc`;
  return (
    <button
      ref={nodeRef}
      type="button"
      role="radio"
      aria-checked={selected}
      aria-describedby={descId}
      onClick={onSelect}
      className={`relative z-10 flex w-max max-w-full items-center gap-2 rounded-xl border px-2.5 py-2 text-left transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 ${foundationClasses(selected)}`}
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-b from-brand-500 to-brand-700 text-[10px] font-bold text-white shadow-sm">
        {stage}
      </span>
      <span className="min-w-0">
        <span className="block whitespace-nowrap text-xs font-bold leading-none sm:text-sm">{title}</span>
      </span>
      <span id={descId} className="sr-only">
        {blurb}
      </span>
    </button>
  );
}

function ChallengeCard({
  label,
  short,
  ready,
  selected,
  nodeRef,
  onSelect,
}: {
  offer: ChallengeOffer;
  label: string;
  short: string;
  ready: boolean;
  selected: boolean;
  nodeRef: NodeRef;
  onSelect: () => void;
}) {
  return (
    <button
      ref={nodeRef}
      type="button"
      role="radio"
      aria-checked={selected}
      aria-label={label}
      aria-disabled={!ready}
      title={label}
      onClick={onSelect}
      className={`relative z-10 min-w-0 max-w-[10rem] rounded-xl border px-2 py-1.5 text-left transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 ${challengeClasses({ selected, ready })}`}
    >
      <span className={`type-kicker block ${ready ? "text-amber-700" : "text-slate-400"}`}>
        Thử thách
      </span>
      <span className="mt-0.5 block text-[10px] font-bold leading-snug sm:text-xs">{short}</span>
      {!ready ? (
        <span className="mt-0.5 block text-[9px] font-bold">Sắp ra mắt</span>
      ) : null}
    </button>
  );
}

function TreeRow({ trunk }: { trunk: ReactNode }) {
  return (
    <div className={`${TREE_COLS} items-center`}>
      <div />
      <div className="flex justify-center">{trunk}</div>
      <div />
    </div>
  );
}

function TrunkSpan({ className = "h-3" }: { className?: string }) {
  return (
    <div className={`${TREE_COLS} items-center`}>
      <div />
      <TrunkLine className={className} />
      <div />
    </div>
  );
}

function SideBranch({
  challenges,
  selectedOffer,
  bindNode,
  onOpen,
}: {
  challenges: { key: ChallengeOffer; label_vi: string; short_vi: string; ready: boolean }[];
  selectedOffer: ChallengeOffer | null;
  bindNode: (id: string) => NodeRef;
  onOpen: (offer: ChallengeOffer) => void;
}) {
  if (challenges.length === 0) {
    return <TrunkSpan className="h-3" />;
  }

  const ready = challenges.some((branch) => branch.ready);
  const arm = ready ? "bg-amber-500" : "bg-slate-500";

  return (
    <div className={`${TREE_COLS} min-h-[4.75rem] items-stretch`}>
      <div />
      <div className="relative flex justify-center self-stretch">
        <div className="dir-line-y w-0.5 self-stretch bg-gradient-to-b from-brand-400 to-slate-400" aria-hidden />
        <div
          className={`pointer-events-none absolute top-[calc(50%-1px)] -right-px left-1/2 h-0.5 ${arm}`}
          aria-hidden
        />
        <span
          className="pointer-events-none absolute top-1/2 left-1/2 z-[1] -translate-x-1/2 -translate-y-1/2"
          aria-hidden
        >
          <LineDot className={ready ? "border-amber-500" : "border-slate-400"} />
        </span>
      </div>
      <div className="flex min-w-0 items-center self-stretch">
        <div className={`dir-line-x h-0.5 w-10 shrink-0 sm:w-14 ${arm}`} aria-hidden />
        <div className="flex min-w-0 flex-col justify-center gap-1.5 py-1">
          {challenges.map((branch) => (
            <ChallengeCard
              key={branch.key}
              offer={branch.key}
              label={branch.label_vi}
              short={branch.short_vi}
              ready={branch.ready}
              selected={selectedOffer === branch.key}
              nodeRef={bindNode(branch.key)}
              onSelect={() => onOpen(branch.key)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function SpecCard({
  branchKey,
  selected,
  nodeRef,
  onSelect,
}: {
  branchKey: SpecializationBranchKey;
  selected: boolean;
  nodeRef: NodeRef;
  onSelect: () => void;
}) {
  const branch = SPECIALIZATION_BRANCHES.find((item) => item.key === branchKey);
  const theme = SPEC_THEME[branchKey];
  return (
    <button
      ref={nodeRef}
      type="button"
      aria-label={branch?.label_vi}
      onClick={onSelect}
      className={`flex min-h-10 w-full items-center justify-center gap-1.5 rounded-xl border px-2 py-1.5 text-center text-[10px] font-semibold leading-tight transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 sm:text-[11px] ${specClasses(branchKey, selected)}`}
    >
      <span className={`shrink-0 ${theme.icon}`}>
        <BranchIcon name={branchKey} />
      </span>
      <span className="min-w-0 truncate">{SPEC_SHORT_VI[branchKey]}</span>
    </button>
  );
}

function SpecFork({
  selection,
  bindNode,
  onOpen,
}: {
  selection: DirectionSelection;
  bindNode: (id: string) => NodeRef;
  onOpen: (branch: SpecializationBranchKey) => void;
}) {
  return (
    <>
      <div className={`${TREE_COLS} items-center`}>
        <div />
        <div className="flex flex-col items-center">
          <TrunkLine className="h-2.5" />
          <Junction />
          <p className="relative z-10 mt-2 w-max rounded-full bg-brand-600 px-3 py-1 text-center text-xs font-bold text-white shadow-sm sm:text-sm">
            Chuyên sâu
          </p>
          <TrunkLine className="h-3" />
        </div>
        <div />
      </div>

      <div className="relative">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-5" aria-hidden>
          <div className="dir-line-x absolute top-0 right-[16.666%] left-[16.666%] h-0.5 bg-slate-400" />
          <div className="dir-line-y absolute top-0 left-[16.666%] h-5 w-0.5 -translate-x-1/2 bg-slate-400" />
          <div className="dir-line-y absolute top-0 left-1/2 h-5 w-0.5 -translate-x-1/2 bg-slate-400" />
          <div className="dir-line-y absolute top-0 left-[83.334%] h-5 w-0.5 -translate-x-1/2 bg-slate-400" />
          <span className="absolute top-0 left-[16.666%] -translate-x-1/2 -translate-y-1/2">
            <LineDot />
          </span>
          <span className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2">
            <LineDot />
          </span>
          <span className="absolute top-0 left-[83.334%] -translate-x-1/2 -translate-y-1/2">
            <LineDot />
          </span>
        </div>
        <div className="grid grid-cols-3 pt-5">
          {SPEC_FORK.map((keys) => (
            <div key={keys.join("-")} className="flex min-w-0 flex-col gap-1.5 px-1">
              {keys.map((branchKey) => {
                const viewing =
                  selection.kind === "specialization" && selection.branch === branchKey;
                return (
                  <SpecCard
                    key={branchKey}
                    branchKey={branchKey}
                    selected={viewing}
                    nodeRef={bindNode(`spec:${branchKey}`)}
                    onSelect={() => onOpen(branchKey)}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

export default function DirectionTree({
  selection,
  onSelect,
  onContinue,
}: {
  selection: DirectionSelection;
  onSelect: (selection: DirectionSelection) => void;
  onContinue: () => void;
  catalog?: FamiliarizationCatalog | null;
}) {
  const nodeRefs = useRef(new Map<string, HTMLButtonElement>());
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);

  useEffect(() => {
    // Clear any leftover body lock from a previous session/HMR.
    document.body.style.overflow = "";
  }, []);

  const bindNode = useCallback((id: string): NodeRef => {
    return (element) => {
      if (element) nodeRefs.current.set(id, element);
      else nodeRefs.current.delete(id);
    };
  }, []);

  const selectedChallenge = selection.kind === "challenge" ? selection.offer : null;

  const intro = FOUNDATION_NODES[0];
  const base = FOUNDATION_NODES[1];
  const challenge100 = CHALLENGE_BRANCHES.find((branch) => branch.key === "challenge_100");

  function openNode(next: DirectionSelection) {
    onSelect(next);
    if (typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches) {
      setMobileDetailOpen(true);
    }
  }

  function closeMobileDetail() {
    setMobileDetailOpen(false);
  }

  useEffect(() => {
    if (!mobileDetailOpen) return;

    const mq = window.matchMedia("(max-width: 1023px)");
    const closeIfDesktop = () => {
      if (!mq.matches) setMobileDetailOpen(false);
    };
    closeIfDesktop();
    mq.addEventListener("change", closeIfDesktop);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileDetailOpen(false);
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);

    return () => {
      mq.removeEventListener("change", closeIfDesktop);
      document.body.style.overflow = prevOverflow;
      document.removeEventListener("keydown", onKey);
    };
  }, [mobileDetailOpen]);

  const content = contentForSelection(selection);

  return (
    <div className="space-y-3">
      <div>
        <p className="text-sm font-semibold text-slate-600">Bạn đang ở đâu trên lộ trình?</p>
        <p className="mt-1 text-sm text-slate-500 lg:hidden">
          Chạm một mục trên sơ đồ để xem chi tiết.
        </p>
      </div>

      <div className="flex min-w-0 flex-col gap-4 lg:grid lg:grid-cols-[minmax(0,46%)_minmax(0,54%)] lg:items-start lg:gap-5">
        <div
          role="radiogroup"
          aria-label="Hướng đi"
          className="relative min-w-0 overflow-x-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-brand-50/50 px-1.5 py-3 sm:px-3 sm:py-4"
        >
          <div className="relative z-10 mx-auto w-full min-w-0 max-w-2xl">
            <div className="dir-enter" style={{ animationDelay: "0ms" }}>
              <TreeRow
                trunk={
                  <FoundationCard
                    path={intro.key}
                    stage="01"
                    title={intro.label_vi}
                    blurb={intro.blurb_vi}
                    selected={selection.kind === "foundation" && selection.path === intro.key}
                    nodeRef={bindNode(intro.key)}
                    onSelect={() => openNode({ kind: "foundation", path: intro.key })}
                  />
                }
              />
            </div>

            <div className="dir-enter" style={{ animationDelay: "80ms" }}>
              <SideBranch
                challenges={challenge100 ? [challenge100] : []}
                selectedOffer={selectedChallenge}
                bindNode={bindNode}
                onOpen={(offer) => openNode({ kind: "challenge", offer })}
              />
            </div>

            <div className="dir-enter" style={{ animationDelay: "160ms" }}>
              <TreeRow
                trunk={
                  <FoundationCard
                    path={base.key}
                    stage="02"
                    title={base.label_vi}
                    blurb={base.blurb_vi}
                    selected={selection.kind === "foundation" && selection.path === base.key}
                    nodeRef={bindNode(base.key)}
                    onSelect={() => openNode({ kind: "foundation", path: base.key })}
                  />
                }
              />
            </div>

            <div className="dir-enter" style={{ animationDelay: "320ms" }}>
              <SpecFork
                selection={selection}
                bindNode={bindNode}
                onOpen={(branch) => openNode({ kind: "specialization", branch })}
              />
            </div>
          </div>
        </div>

        <div className="hidden lg:sticky lg:top-24 lg:block lg:self-start">
          <DirectionNodePanel
            key={content.id}
            selection={selection}
            content={content}
            onContinue={onContinue}
          />
        </div>
      </div>

      {mobileDetailOpen && typeof document !== "undefined"
        ? createPortal(
            <div
              className="fixed inset-0 z-[100] lg:hidden"
              role="dialog"
              aria-modal="true"
              aria-label={content.title}
            >
              <button
                type="button"
                className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
                aria-label="Đóng"
                onClick={closeMobileDetail}
              />
              <div className="absolute inset-x-0 bottom-0 flex max-h-[92vh] justify-center pointer-events-none">
                <div className="pointer-events-auto flex w-full max-h-[92vh] flex-col rounded-t-3xl bg-white shadow-2xl">
                  <div className="flex shrink-0 items-center justify-between border-b border-slate-100 px-4 py-3">
                    <p className="text-sm font-bold text-slate-800">Chi tiết lộ trình</p>
                    <button
                      type="button"
                      onClick={closeMobileDetail}
                      className="rounded-lg px-2.5 py-1.5 text-sm font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                      aria-label="Đóng"
                    >
                      Đóng
                    </button>
                  </div>
                  <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-3 sm:p-4">
                    <DirectionNodePanel
                      key={`mobile-${content.id}`}
                      selection={selection}
                      content={content}
                      onContinue={() => {
                        closeMobileDetail();
                        onContinue();
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>,
            document.body,
          )
        : null}
    </div>
  );
}
