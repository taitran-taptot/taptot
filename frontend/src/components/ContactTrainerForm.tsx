"use client";

import { useState } from "react";
import { feedbackApi } from "@/lib/authApi";
import { brandRichText } from "@/components/brandRichText";
import Modal from "./Modal";
import {
  CONTACT_EMAIL,
  CONTACT_FACEBOOK,
  CONTACT_FACEBOOK_DISPLAY,
  CONTACT_TIKTOK,
  CONTACT_TIKTOK_DISPLAY,
  CONTACT_ZALO_DISPLAY,
  CONTACT_ZALO_HREF,
} from "@/lib/brand";

const GOAL_OPTS = [
  { value: "lose_fat", label: "Giảm cân / Giảm mỡ" },
  { value: "gain", label: "Tăng cân / Tăng cơ" },
] as const;

const CHANNELS = [
  {
    key: "facebook",
    label: "Facebook",
    value: CONTACT_FACEBOOK_DISPLAY,
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
  {
    key: "tiktok",
    label: "TikTok",
    value: CONTACT_TIKTOK_DISPLAY,
    href: CONTACT_TIKTOK,
    external: true,
  },
] as const;

type Goal = (typeof GOAL_OPTS)[number]["value"];

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
  if (kind === "tiktok") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5" aria-hidden>
        <path d="M19.6 8.2a5.6 5.6 0 0 1-3.2-1V15a5.2 5.2 0 1 1-5.2-5.2c.3 0 .6 0 .9.1v2.6a2.6 2.6 0 1 0 1.8 2.5V2.5h2.5a5.6 5.6 0 0 0 3.2 3.1v2.6Z" />
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
  const [goal, setGoal] = useState<Goal | "">("");
  const [message, setMessage] = useState("");
  const [err, setErr] = useState("");
  const [okOpen, setOkOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const note = message.trim() || undefined;
      await feedbackApi.contactTrainer({
        full_name: fullName.trim(),
        phone_zalo: phoneZalo.trim(),
        ...(goal ? { goal } : {}),
        ...(note ? { message: note } : {}),
      });
      setFullName("");
      setPhoneZalo("");
      setGoal("");
      setMessage("");
      setOkOpen(true);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div id="dang-ky-hlv" className="space-y-6">
      <form onSubmit={submit} className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-6">
        <h3 className="text-center text-lg font-bold text-slate-900">Đăng ký tư vấn</h3>
        {err && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

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

      <div>
        <p className="text-center text-sm font-semibold text-slate-800">
          Hoặc liên hệ với {brandRichText("TAPTOT")} qua
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
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

      <Modal open={okOpen} onClose={() => setOkOpen(false)} title="Đăng ký thành công">
        <div className="space-y-3 p-5 text-center">
          <p className="text-lg font-bold text-slate-800">Đăng ký tư vấn thành công</p>
          <p className="text-sm leading-relaxed text-slate-600">
            Chúng tôi sẽ liên hệ lại với bạn qua Zalo trong 24 giờ.
          </p>
          <button
            type="button"
            onClick={() => setOkOpen(false)}
            className="rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
          >
            Đóng
          </button>
        </div>
      </Modal>
    </div>
  );
}
