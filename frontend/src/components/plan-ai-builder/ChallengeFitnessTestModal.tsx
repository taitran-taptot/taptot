"use client";

import { useEffect, useState } from "react";
import Modal from "@/components/Modal";
import ChallengeFitnessCards from "@/components/plan-ai-builder/ChallengeFitnessCards";
import {
  challengeSpecsComplete,
  type ChallengeTestDraft,
  type ChallengeTestSpec,
} from "@/lib/challengeFitnessTests";

export default function ChallengeFitnessTestModal({
  open,
  onClose,
  tests,
  values,
  onSave,
}: {
  open: boolean;
  onClose: () => void;
  tests: ChallengeTestSpec[];
  values: ChallengeTestDraft;
  onSave: (next: ChallengeTestDraft) => void;
}) {
  const [draft, setDraft] = useState<ChallengeTestDraft>(values);

  useEffect(() => {
    if (!open) return;
    setDraft(values);
  }, [open, values]);

  const complete = challengeSpecsComplete(tests, draft);

  function confirm() {
    if (!complete) return;
    onSave(draft);
    onClose();
  }

  return (
    <Modal open={open} onClose={onClose} size="lg" lockScroll title="Kiểm tra thể lực">
      <div className="flex min-h-0 flex-1 flex-col" style={{ maxHeight: "min(92vh, 880px)" }}>
        <div className="shrink-0 border-b border-slate-100 px-4 pb-3 pt-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-bold sm:text-lg">Kiểm tra thể lực</h3>
              <p className="mt-1 text-xs text-slate-400">
                Làm tối đa đúng form mỗi bài, rồi xác nhận. Cần nhập đủ 4 bài.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-100 text-xl leading-none text-slate-600 hover:bg-slate-200"
              aria-label="Đóng"
            >
              ×
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4">
          <ChallengeFitnessCards
            tests={tests}
            values={draft}
            hideIntro
            onChange={(patch) => setDraft((prev) => ({ ...prev, ...patch }))}
          />
        </div>

        <div className="flex shrink-0 gap-2 border-t border-slate-100 px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-50"
          >
            Huỷ
          </button>
          <button
            type="button"
            onClick={confirm}
            disabled={!complete}
            className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
          >
            Xác nhận
          </button>
        </div>
      </div>
    </Modal>
  );
}
