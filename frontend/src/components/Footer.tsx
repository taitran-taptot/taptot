import Link from "next/link";
import { BRAND_NAME, BRAND_SLOGAN } from "@/lib/brand";
import BrandWordmark from "./BrandWordmark";
import BrandMark from "./BrandMark";
import { TERMS_HREF } from "@/lib/terms";

const SOCIALS = [
  {
    name: "Facebook",
    href: "#",
    soon: true,
    path: "M13.5 9H15V6.5h-1.5c-1.7 0-3 1.3-3 3V11H9v2.5h1.5V19H13v-5.5h1.7l.3-2.5H13V9.5c0-.3.2-.5.5-.5Z",
  },
  {
    name: "Instagram",
    href: "#",
    soon: true,
    path: "M12 8.5A3.5 3.5 0 1 0 12 15.5 3.5 3.5 0 0 0 12 8.5Zm0 5.5a2 2 0 1 1 0-4 2 2 0 0 1 0 4Zm4-6.9a.8.8 0 1 1-1.6 0 .8.8 0 0 1 1.6 0ZM7.5 5h9A2.5 2.5 0 0 1 19 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 5 16.5v-9A2.5 2.5 0 0 1 7.5 5Z",
  },
];

const START_LINKS = [
  { label: "Về chúng tôi", href: "/ve-chung-toi" },
  { label: "Bắt đầu", href: "/batdau?moi=1" },
  { label: "Thử thách 100 ngày", href: "/thu-thach-100-ngay" },
  { label: "Gặp HLV", href: "/lien-he" },
];

const LIBRARY_LINKS = [
  { label: "Kho bài tập", href: "/kho-bai-tap" },
  { label: "Kho thực phẩm", href: "/kho-thuc-pham" },
  { label: "Kho kiến thức", href: "/kien-thuc" },
];

function LinkColumn({ title, links }: { title: string; links: { label: string; href: string }[] }) {
  return (
    <div>
      <p className="font-bold text-white">{title}</p>
      <ul className="mt-3 space-y-2 text-sm">
        {links.map((l) => (
          <li key={l.href}>
            <Link href={l.href} className="text-slate-400 transition hover:text-brand-400">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Footer() {
  return (
    <footer className="mt-8 rounded-3xl bg-slate-900 px-6 py-10 text-slate-300 sm:px-10">
      <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2 lg:col-span-1">
          <div className="flex items-center gap-2">
            <BrandMark className="h-9 w-9 shrink-0" />
            <p className="text-lg font-extrabold text-white">
              <BrandWordmark snow />
            </p>
          </div>
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-slate-400">
            {BRAND_SLOGAN}
            <br />
            Mang lối sống lành mạnh đến cho bạn.
          </p>
          <div className="mt-5 flex gap-3">
            {SOCIALS.map((s) =>
              s.soon ? (
                <span
                  key={s.name}
                  title="Sắp cập nhật"
                  aria-label={`${s.name} (sắp cập nhật)`}
                  className="grid h-10 w-10 cursor-default place-items-center rounded-full bg-slate-800 text-slate-500"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                    <path d={s.path} />
                  </svg>
                </span>
              ) : (
                <a
                  key={s.name}
                  href={s.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={s.name}
                  className="grid h-10 w-10 place-items-center rounded-full bg-slate-800 text-slate-300 transition hover:bg-brand-500 hover:text-white"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                    <path d={s.path} />
                  </svg>
                </a>
              ),
            )}
          </div>
        </div>

        <LinkColumn title="Bắt đầu" links={START_LINKS} />
        <LinkColumn title="Kho" links={LIBRARY_LINKS} />

        <div>
          <p className="font-bold text-white">Liên hệ</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-400">
            <li>
              <Link href={TERMS_HREF} className="transition hover:text-brand-400">
                Điều khoản & miễn trừ y tế
              </Link>
            </li>
            <li>
              <a href="mailto:hello@taptot.vn" className="transition hover:text-brand-400">
                hello@taptot.vn
              </a>
            </li>
            <li className="text-slate-500">Điện thoại — sắp cập nhật</li>
            <li>TP. Hồ Chí Minh</li>
          </ul>
        </div>
      </div>

      <div className="mt-8 flex flex-col items-center justify-between gap-2 border-t border-slate-800 pt-6 text-xs text-slate-500 sm:flex-row">
        <p>
          © {new Date().getFullYear()} {BRAND_NAME}. Bảo lưu mọi quyền.
        </p>
        <Link href={TERMS_HREF} className="transition hover:text-brand-400">
          Điều khoản sử dụng
        </Link>
      </div>
    </footer>
  );
}
