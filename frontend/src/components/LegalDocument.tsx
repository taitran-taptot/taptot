import type { LegalSection } from "@/lib/legalMeta";
import { brandRichText } from "@/components/brandRichText";

export default function LegalDocument({
  title,
  updatedLabel,
  intro,
  agreement,
  sections,
  sectionIdPrefix,
  compact = false,
  heading = true,
}: {
  title: string;
  updatedLabel: string;
  intro?: string;
  agreement?: string;
  sections: LegalSection[];
  sectionIdPrefix: string;
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <article
      className={
        compact
          ? "space-y-5 text-sm leading-relaxed text-slate-600"
          : "space-y-8 text-base leading-relaxed text-slate-600"
      }
    >
      {heading && !compact && (
        <header className="space-y-2">
          <p className="type-kicker text-brand-600">Pháp lý</p>
          <h1 className="type-display text-slate-900">{brandRichText(title)}</h1>
          <p className="text-sm text-slate-500">{updatedLabel}</p>
        </header>
      )}
      {(compact || !heading) && (
        <p className="text-xs font-medium text-slate-400">{updatedLabel}</p>
      )}
      {intro ? <p>{brandRichText(intro)}</p> : null}
      {agreement ? (
        <p className="font-medium text-slate-700">{brandRichText(agreement)}</p>
      ) : null}
      {sections.map((s) => (
        <section key={s.id} id={`${sectionIdPrefix}-${s.id}`} className="space-y-3">
          <h2
            className={`font-bold tracking-tight text-slate-900 ${
              compact ? "text-base" : "text-lg sm:text-xl"
            }`}
          >
            {s.id}. {brandRichText(s.title)}
          </h2>
          {s.paragraphs.map((p) => (
            <p key={p.slice(0, 48)}>{brandRichText(p)}</p>
          ))}
          {s.bullets && (
            <ul className="list-disc space-y-2 pl-5">
              {s.bullets.map((b) => (
                <li key={b.slice(0, 48)}>{brandRichText(b)}</li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </article>
  );
}
