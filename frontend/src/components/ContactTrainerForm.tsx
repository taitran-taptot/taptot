"use client";

import { useState } from "react";
import { feedbackApi } from "@/lib/authApi";
import {
  CONTACT_EMAIL,
  CONTACT_FACEBOOK,
  CONTACT_ZALO_DISPLAY,
  CONTACT_ZALO_HREF,
} from "@/lib/brand";

const GOAL_OPTS = [
  { value: "lose_weight", label: "Giảm cân" },
  { value: "maintain", label: "Giữ cân / khỏe hơn" },
  { value: "gain_weight", label: "Tăng cân / tăng cơ" },
  { value: "compete", label: "Thi đấu" },
] as const;

const LOCATION_OPTS = [
  { value: "home", label: "Tập tại nhà" },
  { value: "gym", label: "Phòng gym" },
  { value: "either", label: "Linh hoạt" },
] as const;

const BENEFITS = [
  { title: "Tư vấn 1-1", desc: "HLV hiểu mục tiêu và lịch sống của bạn." },
  {
    title: "Lịch tập cá nhân hóa",
    desc: "Linh hoạt phù hợp với cơ thể, kinh nghiệm và sở thích của bạn.",
  },
  {
    title: "Lịch ăn theo sở thích",
    desc: "Phù hợp vị giác khiến bạn dù ăn chế độ cũng không nhàm chán.",
  },
];

const CHANNELS = [
  {
    key: "facebook",
    label: "Facebook",
    value: "Nhắn tin trên Facebook",
    href: CONTACT_FACEBOOK,
    external: true,
  },
  {
    key: "email",
    label: "Email",
    value: CONTACT_EMAIL,
    href: `mailto:${CONTACT_EMAIL}`,
    external: false,
  },
  {
    key: "zalo",
    label: "Zalo",
    value: CONTACT_ZALO_DISPLAY,
    href: CONTACT_ZALO_HREF,
    external: true,
  },
] as const;

type Goal = (typeof GOAL_OPTS)[number]["value"];
type Location = (typeof LOCATION_OPTS)[number]["value"];

function chipClass(active: boolean) {
  return [
    "rounded-xl border px-3 py-2 text-sm font-semibold transition",
    active ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-600 hover:border-slate-300",
  ].join(" ");
}

function ChannelIcon({ kind }: { kind: (typeof CHANNELS)[number]["key"] }) {
  if (kind === "facebook") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5" aria-hidden>
        <path d="M13.5 9H15V6.5h-1.5c-1.7 0-3 1.3-3 3V11H9v2.5h1.5V19H13v-5.5h1.7l.3-2.5H13V9.5c0-.3.2-.5.5-.5Z" />
      </svg>
    );
  }
  if (kind === "email") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5" aria-hidden>
        <path d="M4 6h16v12H4z" />
        <path d="m4 7 8 6 8-6" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5" aria-hidden>
      <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
    </svg>
  );
}

export default function ContactTrainerForm() {
  const [fullName, setFullName] = useState("");
  const [phoneZalo, setPhoneZalo] = useState("");
  const [email, setEmail] = useState("");
  const [goal, setGoal] = useState<Goal | "">("");
  const [location, setLocation] = useState<Location | "">("");
  const [message, setMessage] = useState("");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setOk("");
    setLoading(true);
    try {
      const goalLabel = GOAL_OPTS.find((o) => o.value === goal)?.label;
      const locationLabel = LOCATION_OPTS.find((o) => o.value === location)?.label;
      const bits = [
        goalLabel ? `Mục tiêu: ${goalLabel}` : null,
        locationLabel ? `Nơi tập: ${locationLabel}` : null,
        message.trim() || null,
      ].filter(Boolean);
      const composed = bits.join("\n") || undefined;
      const emailTrim = email.trim();

      const res = await feedbackApi.contactTrainer({
        full_name: fullName.trim(),
        phone_zalo: phoneZalo.trim(),
        ...(emailTrim ? { email: emailTrim } : {}),
        message: composed,
      });
      setOk(res.message || "Đã nhận đăng ký. Chúng tôi sẽ liên hệ sớm!");
      setFullName("");
      setPhoneZalo("");
      setEmail("");
      setGoal("");
      setLocation("");
      setMessage("");
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div id="dang-ky-hlv" className="mx-auto max-w-3xl scroll-mt-24 space-y-6">
      <div className="text-center">
        <h2 className="type-display">Bắt đầu hành trình với HLV</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500 sm:text-base">
          Để lại thông tin. HLV sẽ tư vấn lịch tập và ăn uống phù hợp bạn.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {BENEFITS.map((b) => (
          <div key={b.title} className="rounded-2xl border border-slate-100 bg-white/70 px-4 py-3">
            <p className="text-sm font-bold text-slate-900">{b.title}</p>
            <p className="mt-0.5 text-xs leading-snug text-slate-500">{b.desc}</p>
          </div>
        ))}
      </div>

      <form onSubmit={submit} className="space-y-3 rounded-2xl bg-white p-4 shadow-soft sm:p-6">
        {err && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
        {ok && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{ok}</p>}

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">Họ và tên</label>
          <input
            required
            minLength={2}
            maxLength={120}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="field !py-2.5"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">Số điện thoại</label>
          <input
            required
            minLength={8}
            maxLength={30}
            value={phoneZalo}
            onChange={(e) => setPhoneZalo(e.target.value)}
            placeholder="09xxxxxxxx"
            inputMode="tel"
            className="field !py-2.5"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">
            Email <span className="font-normal text-slate-400">(tuỳ chọn)</span>
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="field !py-2.5"
          />
        </div>

        <div>
          <p className="mb-1.5 text-xs font-semibold text-slate-600">Mục tiêu (tuỳ chọn)</p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {GOAL_OPTS.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setGoal((prev) => (prev === o.value ? "" : o.value))}
                className={chipClass(goal === o.value)}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="mb-1.5 text-xs font-semibold text-slate-600">Nơi tập (tuỳ chọn)</p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {LOCATION_OPTS.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setLocation((prev) => (prev === o.value ? "" : o.value))}
                className={chipClass(location === o.value)}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">
            Ghi chú <span className="font-normal text-slate-400">(tuỳ chọn)</span>
          </label>
          <textarea
            maxLength={1800}
            rows={3}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Thời gian rảnh, kinh nghiệm tập…"
            className="field !py-2.5 resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-brand-500 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600 disabled:opacity-50"
        >
          {loading ? "Đang gửi…" : "Đăng ký tư vấn"}
        </button>
      </form>

      <div className="rounded-2xl bg-white p-4 shadow-soft sm:p-6">
        <p className="text-center text-sm font-semibold text-slate-800">Hoặc liên hệ với chúng tôi qua</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {CHANNELS.map((ch) => (
            <a
              key={ch.key}
              href={ch.href}
              {...(ch.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
              className="flex items-center gap-3 rounded-xl border border-slate-200 px-3 py-3 transition hover:border-brand-300 hover:bg-brand-50"
            >
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-100 text-brand-700">
                <ChannelIcon kind={ch.key} />
              </span>
              <span className="min-w-0 text-left">
                <span className="block text-xs font-medium text-slate-500">{ch.label}</span>
                <span className="block truncate text-sm font-semibold text-slate-900">{ch.value}</span>
              </span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
