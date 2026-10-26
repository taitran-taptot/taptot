import Link from "next/link";
import {
  BRAND_SLOGAN,
  CONTACT_EMAIL,
  CONTACT_FACEBOOK,
  CONTACT_FACEBOOK_DISPLAY,
  CONTACT_PHONE_DISPLAY,
  CONTACT_PHONE_HREF,
  CONTACT_TIKTOK,
  CONTACT_TIKTOK_DISPLAY,
  CONTACT_ZALO_HREF,
} from "@/lib/brand";
import BrandWordmark from "./BrandWordmark";
import BrandMark from "./BrandMark";
import { brandRichText } from "./brandRichText";
import {
  COMPLAINT_HREF,
  OPERATOR_HREF,
  PAYMENT_POLICY_HREF,
  PRIVACY_HREF,
  SALES_POLICY_HREF,
  TERMS_HREF,
} from "@/lib/legalMeta";

const SOCIALS = [
  {
    name: "Facebook",
    href: CONTACT_FACEBOOK,
    external: true,
    path: "M13.5 9H15V6.5h-1.5c-1.7 0-3 1.3-3 3V11H9v2.5h1.5V19H13v-5.5h1.7l.3-2.5H13V9.5c0-.3.2-.5.5-.5Z",
  },
  {
    name: "Email",
    href: `mailto:${CONTACT_EMAIL}`,
    external: false,
    path: "M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Zm0 4-8 5L4 8V6l8 5 8-5v2Z",
  },
  {
    name: "Zalo",
    href: CONTACT_ZALO_HREF,
    external: true,
    path: "M4 4h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H8l-4 3V6a2 2 0 0 1 2-2Z",
  },
  {
    name: "TikTok",
    href: CONTACT_TIKTOK,
    external: true,
    path: "M19.6 8.2a5.6 5.6 0 0 1-3.2-1V15a5.2 5.2 0 1 1-5.2-5.2c.3 0 .6 0 .9.1v2.6a2.6 2.6 0 1 0 1.8 2.5V2.5h2.5a5.6 5.6 0 0 0 3.2 3.1v2.6Z",
  },
];

const START_LINKS = [
  { label: "Về TAPTOT", href: "/ve-taptot" },
  { label: "Bắt đầu", href: "/batdau?moi=1" },
  { label: "Thử thách 100 ngày", href: "/thu-thach-100-ngay" },
  { label: "Gặp HLV", href: "/lien-he" },
  { label: "Góp ý", href: "/gop-y" },
];

const LEGAL_LINKS = [
  { label: "Điều khoản & miễn trừ y tế", href: TERMS_HREF },
  { label: "Chính sách bảo mật", href: PRIVACY_HREF },
  { label: "Chính sách bán hàng", href: SALES_POLICY_HREF },
  { label: "Thanh toán và hoàn tiền", href: PAYMENT_POLICY_HREF },
  { label: "Khiếu nại", href: COMPLAINT_HREF },
  { label: "Thông tin đơn vị", href: OPERATOR_HREF },
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
    <footer className="mt-4 rounded-3xl bg-slate-900 px-6 py-10 text-slate-300 sm:px-10">
      <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2 lg:col-span-1">
          <div className="flex items-center gap-2">
            <BrandMark className="h-9 w-9 shrink-0" />
            <p className="text-lg font-bold text-white">
              <BrandWordmark snow />
            </p>
          </div>
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-slate-400">
            {BRAND_SLOGAN}
            <br />
            Mang lối sống lành mạnh đến cho bạn.
          </p>
          <div className="mt-5 flex gap-3">
            {SOCIALS.map((s) => (
              <a
                key={s.name}
                href={s.href}
                {...(s.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                aria-label={s.name}
                className="grid h-10 w-10 place-items-center rounded-full bg-slate-800 text-slate-300 transition hover:bg-brand-500 hover:text-white"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                  <path d={s.path} />
                </svg>
              </a>
            ))}
          </div>
        </div>

        <LinkColumn title="Bắt đầu" links={START_LINKS} />

        <div>
          <p className="font-bold text-white">Liên hệ</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-400">
            <li>
              <a href={CONTACT_PHONE_HREF} className="transition hover:text-brand-400">
                SĐT: {CONTACT_PHONE_DISPLAY}
              </a>
            </li>
            <li>
              <a href={`mailto:${CONTACT_EMAIL}`} className="transition hover:text-brand-400">
                Email: {CONTACT_EMAIL}
              </a>
            </li>
            <li>Facebook: {CONTACT_FACEBOOK_DISPLAY}</li>
            <li>TikTok: {CONTACT_TIKTOK_DISPLAY}</li>
          </ul>
        </div>

        <LinkColumn title="Điều khoản" links={LEGAL_LINKS} />
      </div>

      <div className="mt-8 border-t border-slate-800 pt-6 text-xs text-slate-500">
        <p>
          © {new Date().getFullYear()} {brandRichText("TAPTOT")}. Bảo lưu mọi quyền.
        </p>
      </div>
    </footer>
  );
}
