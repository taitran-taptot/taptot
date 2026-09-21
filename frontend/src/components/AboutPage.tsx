import type { ReactNode } from "react";
import Link from "next/link";
import BrandWordmark from "./BrandWordmark";
import { BRAND_SLOGAN } from "@/lib/brand";
import { CONTACT_HREF, FEATURED_TRAINER } from "@/lib/trainers";

const SOURCE_TOP10 =
  "https://dantri.com.vn/suc-khoe/viet-nam-nam-trong-top-10-nuoc-luoi-van-dong-nhat-the-gioi-20240910124547968.htm";
const SOURCE_ADOLESCENTS =
  "https://www.thelancet.com/journals/lanchi/article/PIIS2352-4642(19)30323-2/fulltext";

function BeatLabel({ n, children }: { n: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="type-stat text-sm text-brand-600">{n}</span>
      <h2 className="text-sm font-semibold text-slate-900">{children}</h2>
    </div>
  );
}

function SourceLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="transition hover:text-brand-700"
    >
      {children}
    </a>
  );
}

function PersonPortrait({
  src,
  alt,
  position = "object-center",
}: {
  src: string;
  alt: string;
  position?: string;
}) {
  return (
    <div className="relative mx-auto aspect-[3/4] w-full max-w-[13rem] overflow-hidden rounded-2xl bg-gradient-to-br from-brand-50 to-brand-100">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        className={`absolute inset-0 h-full w-full object-cover ${position}`}
      />
    </div>
  );
}

export default function AboutPage() {
  const tien = FEATURED_TRAINER;

  return (
    <div className="space-y-12 pb-8">
      <header className="relative overflow-hidden rounded-3xl px-6 py-16 text-white shadow-soft sm:px-10 sm:py-20">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/hero-gym.jpg"
          alt=""
          aria-hidden
          className="absolute inset-0 h-full w-full object-cover object-center"
        />
        <div className="absolute inset-0 bg-[#0F172A]/75" />
        <div className="absolute inset-0 bg-brand-900/35" />
        <div className="relative max-w-2xl">
          <p className="type-kicker text-brand-300">Về chúng tôi</p>
          <h1 className="type-display mt-3 text-4xl sm:text-5xl">
            <BrandWordmark snow />
          </h1>
          <p className="mt-4 type-display">{BRAND_SLOGAN}</p>
          <p className="mt-3 max-w-xl text-base text-white/90 sm:text-lg">
            Mang lối sống lành mạnh đến cho bạn.
          </p>
        </div>
      </header>

      <section className="rounded-3xl bg-white p-6 shadow-soft sm:p-10">
        <div className="mx-auto max-w-3xl divide-y divide-slate-100">
          <article className="pb-10">
            <BeatLabel n="01">Điều chúng tôi thấy</BeatLabel>
            <p className="mt-6 text-base leading-relaxed text-slate-600">
              Việt Nam hiện nay thuộc top 10 quốc gia có tỷ lệ người dân ít vận động nhất thế giới,
              trong đó gần 9/10 thanh thiếu niên chưa đạt mức vận động thể chất theo khuyến nghị của
              Tổ chức Y tế Thế giới (WHO).
            </p>
            <p className="mt-3 text-xs text-slate-400">
              Nguồn:{" "}
              <SourceLink href={SOURCE_TOP10}>Dân trí</SourceLink>
              {" · "}
              <SourceLink href={SOURCE_ADOLESCENTS}>The Lancet / WHO</SourceLink>
            </p>
          </article>

          <article className="py-10">
            <BeatLabel n="02">Điều chúng tôi tin</BeatLabel>
            <p className="mt-6 text-lg leading-8 text-slate-600">
              Chúng tôi chắc rằng đây không phải vì chúng ta lười, mà vì chưa biết bắt đầu từ đâu, như
              thế nào. Vận động chia thành rất nhiều mảng nhỏ. Tự tìm hiểu mà không có lộ trình và mục
              tiêu — không chỉ trong tập luyện — khiến chúng ta khó duy trì và nhanh nhàm chán.
            </p>
          </article>

          <article className="pt-10">
            <BeatLabel n="03">Cách chúng tôi làm</BeatLabel>
            <ul className="mt-6 grid list-none gap-10 sm:grid-cols-2">
              <li className="text-center">
                <PersonPortrait
                  src={tien.imageSrc ?? ""}
                  alt={tien.name}
                  position="object-[center_62%]"
                />
                <p className="type-kicker mt-4 text-brand-600">Huấn luyện viên</p>
                <p className="mt-1 font-semibold text-slate-900">{tien.name}</p>
                <p className="mt-1 text-sm leading-relaxed text-slate-600">
                  Thấy người mới bỏ cuộc vì lịch quá sức, không biết chọn hướng nào.
                </p>
              </li>
              <li className="text-center">
                <PersonPortrait src="/tran-tai.jpg" alt="Trần Tài" position="object-[center_28%]" />
                <p className="type-kicker mt-4 text-brand-600">Lập trình viên</p>
                <p className="mt-1 font-semibold text-slate-900">Trần Tài</p>
                <p className="mt-1 text-sm leading-relaxed text-slate-600">
                  Kiến thức rải rác, khó biến thành lịch làm được mỗi ngày.
                </p>
              </li>
            </ul>
            <p className="mt-8 text-lg leading-8 text-slate-600">
              Vì vậy chúng tôi quyết định xây dựng một nền tảng mang tên{" "}
              <BrandWordmark className="font-serif text-[1.05em] font-semibold" /> giúp mọi người bắt
              đầu một hành trình của riêng mình để rèn luyện sức khỏe, thay đổi lối sống một cách đơn
              giản hơn.
            </p>
          </article>
        </div>
      </section>

      <section className="relative overflow-hidden rounded-[2rem] border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 text-center shadow-soft sm:px-10 sm:py-12">
        <div
          className="pointer-events-none absolute -right-16 -top-28 h-72 w-72 rounded-full bg-brand-200/45 blur-3xl"
          aria-hidden
        />
        <div className="relative mx-auto max-w-2xl">
          <h2 className="type-display text-slate-900">
            Bắt đầu ngay với <BrandWordmark />
          </h2>
          <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/batdau?moi=1"
              className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-brand-500 px-6 py-3 text-sm font-bold text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-brand-600 sm:w-auto"
            >
              Bắt đầu
            </Link>
            <Link
              href={CONTACT_HREF}
              className="inline-flex min-h-12 w-full items-center justify-center rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-slate-700 transition hover:border-brand-300 hover:text-brand-700 sm:w-auto"
            >
              Gặp HLV
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
