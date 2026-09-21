"use client";

import { useState } from "react";
import { DIRECTION_COMING_SOON, DIRECTION_SPECIALIZATION_PENDING, isDirectionReady, SPECIALIZATION_BRANCHES, type DirectionSelection } from "@/lib/directionTree";
import type { DirectionNodeContent } from "@/lib/directionTreeContent";
import { panelTheme } from "@/lib/directionTreeUi";

export default function DirectionNodePanel({
  selection,
  content,
  onContinue,
}: {
  selection: DirectionSelection;
  content: DirectionNodeContent;
  onContinue: () => void;
}) {
  const ready = isDirectionReady(selection);
  const isSpec = selection.kind === "specialization";
  const theme = panelTheme(selection);
  const [imgFailed, setImgFailed] = useState(false);
  const specLeaves = isSpec
    ? SPECIALIZATION_BRANCHES.find((item) => item.key === selection.branch)?.leaves ?? []
    : [];
  const pendingText = isSpec ? DIRECTION_SPECIALIZATION_PENDING : DIRECTION_COMING_SOON;

  return (
    <aside
      className={`dir-panel-in flex flex-col rounded-2xl border bg-white/95 p-4 shadow-sm sm:p-5 ${theme.panel}`}
    >
      {!isSpec ? (
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-brand-100 via-lime-100 to-amber-100">
          {imgFailed ? (
            <div className="flex aspect-[16/10] items-center justify-center px-4 py-8 text-center">
              <p className="text-sm font-bold text-brand-800">{content.title}</p>
            </div>
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={content.image}
              alt=""
              className="aspect-[16/10] w-full object-cover"
              onError={() => setImgFailed(true)}
            />
          )}
        </div>
      ) : null}

      <p
        className={`${isSpec ? "" : "mt-4"} type-kicker ${theme.kicker}`}
      >
        {content.kicker}
      </p>
      <h2 className="mt-1 type-title text-slate-900">{content.title}</h2>
      {content.meta ? <p className="mt-1 text-sm text-slate-500">{content.meta}</p> : null}

      <div className="mt-3 space-y-2 text-sm leading-relaxed text-slate-600">
        {content.intro.map((paragraph) => (
          <p key={paragraph.slice(0, 48)}>{paragraph}</p>
        ))}
      </div>

      {content.benefits && content.benefits.length > 0 ? (
        <div className="mt-4">
          <p className="text-sm font-bold text-slate-800">Lợi ích chính:</p>
          <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-slate-600">
            {content.benefits.map((item) => (
              <li key={item.title}>
                <span className="font-semibold text-slate-700">{item.title}:</span> {item.body}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5">
        {ready ? (
          <button
            type="button"
            onClick={onContinue}
            className={`w-full rounded-xl py-3 text-sm font-bold text-white ${theme.continueBtn}`}
          >
            Tiếp tục
          </button>
        ) : (
          <div className="space-y-3">
            {specLeaves.length > 0 ? (
              <ul className="grid grid-cols-2 gap-1.5">
                {specLeaves.map((leaf) => (
                  <li
                    key={leaf.id}
                    className={`rounded-lg border border-dashed px-2.5 py-1.5 text-xs font-semibold ${theme.leaf}`}
                  >
                    {leaf.label_vi}
                  </li>
                ))}
              </ul>
            ) : null}
            <p className="rounded-xl border border-dashed border-brand-200 bg-brand-50/70 px-3 py-3 text-sm text-slate-600">
              {pendingText}
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
