import { brandRichText } from "@/components/brandRichText";
import ContactTrainerForm from "@/components/ContactTrainerForm";
import { FEATURED_TRAINER } from "@/lib/trainers";
import { siteImageSrc } from "@/lib/sitePageMedia";

type Props = {
  photoSrc?: string | null;
};

export default function FeaturedTrainerIntro({ photoSrc }: Props) {
  const t = FEATURED_TRAINER;
  const src = siteImageSrc(photoSrc || t.imageSrc);

  return (
    <section className="grid items-center gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:gap-12">
      <div className="mx-auto max-w-md text-center">
        {src ? (
          <div className="relative mx-auto mb-6 aspect-[3/4] w-full max-w-[16rem] overflow-hidden rounded-3xl bg-slate-100 shadow-soft">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={src} alt={t.name} className="absolute inset-0 h-full w-full object-cover object-center" />
          </div>
        ) : null}
        <p className="type-kicker text-brand-600">HLV đồng hành</p>
        <h2 className="mt-2 type-display">Nguyễn Văn A</h2>
        <p className="mt-1.5 text-sm font-medium text-slate-600">{brandRichText(t.role)}</p>
        <p className="mt-4 text-sm leading-relaxed text-slate-500 sm:text-base">{t.bio}</p>
      </div>
      <ContactTrainerForm />
    </section>
  );
}
