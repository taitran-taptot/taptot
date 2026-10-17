import Link from "next/link";
import { brandRichText } from "@/components/brandRichText";
import { FEATURED_TRAINER } from "@/lib/trainers";
import { siteImageSrc } from "@/lib/sitePageMedia";

type Props = {
  /** Anchor for the contact form on the same page */
  formHref?: string;
  photoSrc?: string | null;
};

export default function FeaturedTrainerIntro({ formHref = "#dang-ky-hlv", photoSrc }: Props) {
  const t = FEATURED_TRAINER;
  const src = siteImageSrc(photoSrc || t.imageSrc);

  return (
    <section className="rounded-3xl bg-white p-6 shadow-soft sm:p-10">
      <div className="mx-auto max-w-xl text-center">
        {src ? (
          <div className="relative mx-auto mb-6 aspect-[3/4] w-full max-w-[13rem] overflow-hidden rounded-2xl bg-slate-100">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={src} alt={t.name} className="absolute inset-0 h-full w-full object-cover object-center" />
          </div>
        ) : null}
        <p className="type-kicker text-brand-600">HLV đồng hành</p>
        <h2 className="mt-2 type-display">Nguyễn Văn A</h2>
        <p className="mt-1.5 text-sm font-medium text-slate-600">{brandRichText(t.role)}</p>
        <p className="mt-4 text-sm leading-relaxed text-slate-500 sm:text-base">{t.bio}</p>
        <Link
          href={formHref}
          className="mt-6 inline-flex w-full items-center justify-center rounded-xl bg-brand-500 px-7 py-3.5 text-base font-bold text-white shadow-soft transition hover:bg-brand-600 sm:w-auto"
        >
          Đăng ký tư vấn
        </Link>
      </div>
    </section>
  );
}
