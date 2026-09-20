import Link from "next/link";
import { FEATURED_TRAINER } from "@/lib/trainers";

type Props = {
  /** Anchor for the contact form on the same page */
  formHref?: string;
};

export default function FeaturedTrainerIntro({ formHref = "#dang-ky-hlv" }: Props) {
  const t = FEATURED_TRAINER;

  return (
    <section className="rounded-3xl bg-white p-6 shadow-soft sm:p-10">
      <div className="grid items-center gap-8 md:grid-cols-2 md:gap-10">
        <div className="relative mx-auto aspect-[4/5] w-full max-w-sm overflow-hidden rounded-2xl bg-gradient-to-br from-brand-50 to-brand-100 md:mx-0 md:max-w-none">
          {t.imageSrc ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={t.imageSrc}
              alt={t.name}
              className="absolute inset-0 h-full w-full object-cover object-top"
            />
          ) : (
            <div className="absolute inset-0 grid place-items-center" aria-hidden>
              <span className="text-5xl font-extrabold tracking-tight text-brand-600/40 sm:text-6xl">
                {t.initials}
              </span>
            </div>
          )}
        </div>
        <div>
          <p className="text-sm font-semibold tracking-wide text-brand-600 uppercase">
            HLV đồng hành
          </p>
          <h1 className="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">{t.name}</h1>
          <p className="mt-1.5 text-sm font-medium text-slate-600">{t.role}</p>
          <p className="mt-0.5 text-sm text-slate-500">
            {t.city} · {t.regionLabel}
          </p>
          <p className="mt-4 text-sm leading-relaxed text-slate-500 sm:text-base">{t.bio}</p>
          <Link
            href={formHref}
            className="mt-6 inline-flex w-full items-center justify-center rounded-xl bg-brand-500 px-7 py-3.5 text-base font-bold text-white shadow-soft transition hover:bg-brand-600 sm:w-auto"
          >
            Đăng ký tư vấn
          </Link>
        </div>
      </div>
    </section>
  );
}
