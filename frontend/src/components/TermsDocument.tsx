import {
  TERMS_AGREEMENT,
  TERMS_INTRO,
  TERMS_SECTIONS,
  TERMS_TITLE,
  TERMS_UPDATED_LABEL,
} from "@/lib/terms";

export default function TermsDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <article className={compact ? "space-y-5 text-sm leading-relaxed text-slate-600" : "space-y-8 text-base leading-relaxed text-slate-600"}>
      {heading && !compact && (
        <header className="space-y-2">
          <p className="text-xs font-semibold tracking-wide text-brand-600 uppercase">Pháp lý</p>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">{TERMS_TITLE}</h1>
          <p className="text-sm text-slate-500">{TERMS_UPDATED_LABEL}</p>
        </header>
      )}
      {(compact || !heading) && <p className="text-xs font-medium text-slate-400">{TERMS_UPDATED_LABEL}</p>}
      <p>{TERMS_INTRO}</p>
      <p className="font-medium text-slate-700">{TERMS_AGREEMENT}</p>
      {TERMS_SECTIONS.map((s) => (
        <section key={s.id} id={`dieu-khoan-${s.id}`} className="space-y-3">
          <h2 className={`font-extrabold tracking-tight text-slate-900 ${compact ? "text-base" : "text-lg sm:text-xl"}`}>
            {s.id}. {s.title}
          </h2>
          {s.paragraphs.map((p) => (
            <p key={p.slice(0, 48)}>{p}</p>
          ))}
          {s.bullets && (
            <ul className="list-disc space-y-2 pl-5">
              {s.bullets.map((b) => (
                <li key={b.slice(0, 48)}>{b}</li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </article>
  );
}
