"use client";

import Link from "next/link";
import { brandRichText } from "@/components/brandRichText";
import { DIRECTION_COMING_SOON, DIRECTION_SPECIALIZATION_PENDING, isDirectionReady, type DirectionSelection } from "@/lib/directionTree";
import type { DirectionNodeContent } from "@/lib/directionTreeContent";
import { panelTheme } from "@/lib/directionTreeUi";
import { CONTACT_HREF } from "@/lib/trainers";

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
  const pendingText = isSpec ? DIRECTION_SPECIALIZATION_PENDING : DIRECTION_COMING_SOON;
  const gymContact = isSpec && selection.branch === "gym";

  return (
    <aside
      className={`dir-panel-in flex flex-col rounded-2xl border bg-white/95 p-4 shadow-sm sm:p-5 ${theme.panel}`}
    >
      <p className={`type-kicker ${theme.kicker}`}>{content.kicker}</p>
      <h2 className="mt-1 type-title text-slate-900">{content.title}</h2>
      {content.meta ? <p className="mt-1 text-sm text-slate-500">{content.meta}</p> : null}

      <div className="mt-3 space-y-2 text-sm leading-relaxed text-slate-600">
        {content.intro.map((paragraph) => (
          <p key={paragraph.slice(0, 48)}>{brandRichText(paragraph)}</p>
        ))}
      </div>

      {content.benefits && content.benefits.length > 0 ? (
        <div className="mt-4">
          <p className="text-sm font-bold text-slate-800">Lợi ích chính:</p>
          <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-slate-600">
            {content.benefits.map((item) => (
              <li key={item.title}>
                <span className="font-semibold text-slate-700">{item.title}:</span>{" "}
                {brandRichText(item.body)}
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
            {gymContact ? (
              <Link
                href={CONTACT_HREF}
                className={`block w-full rounded-xl py-3 text-center text-sm font-bold text-white ${theme.continueBtn}`}
              >
                Liên hệ với huấn luyện viên
              </Link>
            ) : (
              <p className="rounded-xl border border-dashed border-brand-200 bg-brand-50/70 px-3 py-3 text-sm text-slate-600">
                {brandRichText(pendingText)}
              </p>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
