import BrandWordmark from "./BrandWordmark";
import { BRAND_SLOGAN } from "@/lib/brand";

export default function HeroBrandLockup({
  animated = true,
}: {
  animated?: boolean;
}) {
  return (
    <div
      id={animated ? "hero-brand-lockup" : undefined}
      className="text-center text-white"
    >
      <p
        id={animated ? "hero-wordmark" : undefined}
        className={`${animated ? "hero-copy-in hero-copy-in-1 " : ""}text-4xl font-extrabold tracking-tight sm:text-6xl`}
      >
        <BrandWordmark snow />
      </p>
      <h1
        className={`${animated ? "hero-copy-in hero-copy-in-2 " : ""}mt-4 text-2xl leading-snug font-extrabold tracking-tight sm:text-4xl`}
      >
        {BRAND_SLOGAN}
      </h1>
    </div>
  );
}
