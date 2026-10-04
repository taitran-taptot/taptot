import type { ReactNode } from "react";
import BrandWordmark from "@/components/BrandWordmark";

type Props = {
  title: string;
  children?: ReactNode;
};

export default function BrandHero({ title, children }: Props) {
  return (
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-brand-900 px-6 py-9 text-white shadow-soft sm:px-10 sm:py-12">
      <div className="pointer-events-none absolute -top-24 right-0 h-64 w-64 rounded-full bg-brand-500/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-28 left-1/3 h-56 w-56 rounded-full bg-emerald-300/10 blur-3xl" />
      <div className="relative mx-auto max-w-2xl text-center">
        <h1 className="type-display flex flex-col items-center gap-1">
          <BrandWordmark snow />
          <span>{title}</span>
        </h1>
        {children}
      </div>
    </div>
  );
}
