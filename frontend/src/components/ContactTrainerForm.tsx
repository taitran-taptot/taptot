"use client";

import Link from "next/link";
import { useState } from "react";
import { feedbackApi } from "@/lib/authApi";

const CHALLENGE_HREF = "/thu-thach-100-ngay";
const PLAN_HREF = "/tao-lich-tap/taptot";

const GOAL_OPTS = [
  { value: "lose_weight", label: "Giảm cân" },
  { value: "maintain", label: "Giữ cân / khỏe hơn" },
  { value: "gain_weight", label: "Tăng cân / tăng cơ" },
] as const;

const LOCATION_OPTS = [
  { value: "home", label: "Tập tại nhà" },
  { value: "gym", label: "Phòng gym" },
  { value: "either", label: "Linh hoạt" },
] as const;

const STEPS = [
  { n: "1", title: "Để lại liên hệ", desc: "Zalo là đủ để chúng tôi gọi lại." },
  { n: "2", title: "HLV gọi lại", desc: "Thường trong 24 giờ làm việc." },
  { n: "3", title: "Bắt đầu tập", desc: "Lịch vừa sức, kèm gợi ý ăn món Việt." },
];

const BENEFITS = [
  { title: "Tư vấn 1-1", desc: "HLV hiểu mục tiêu và lịch sống của bạn." },
  { title: "Lịch vừa sức", desc: "Không ép pro — tập ở nhà hay gym đều được." },
  { title: "Ăn món quen", desc: "Gợi ý từ cơm, thịt, rau — không đếm gram." },
];

type Goal = (typeof GOAL_OPTS)[number]["value"];
type Location = (typeof LOCATION_OPTS)[number]["value"];

function chipClass(active: boolean) {
  return [
    "rounded-xl border px-3 py-2 text-sm font-semibold transition",
    active ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-600 hover:border-slate-300",
  ].join(" ");
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
      setOk(res.message || "Đã nhận đăng ký. Chúng tôi sẽ liên hệ qua Zalo sớm!");
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
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">Bắt đầu hành trình với HLV</h1>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500 sm:text-base">
          Để lại thông tin. HLV sẽ tư vấn lịch tập và ăn uống phù hợp bạn.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {STEPS.map((s) => (
          <div key={s.n} className="rounded-2xl bg-white px-4 py-3 text-center shadow-soft">
            <p className="mx-auto grid h-8 w-8 place-items-center rounded-full bg-brand-100 text-sm font-extrabold text-brand-700">
              {s.n}
            </p>
            <p className="mt-2 text-sm font-bold text-slate-900">{s.title}</p>
            <p className="mt-0.5 text-xs leading-snug text-slate-500">{s.desc}</p>
          </div>
        ))}
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
          <label className="mb-1 block text-xs font-semibold text-slate-600">Số điện thoại Zalo</label>
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
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
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

      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-center sm:px-6">
        <p className="text-sm font-semibold text-slate-800">Muốn tự bắt đầu ngay?</p>
        <p className="mt-1 text-xs text-slate-500">Tạo lịch 1 tháng miễn phí, hoặc thử thách 100 ngày.</p>
        <div className="mt-3 flex flex-col items-center justify-center gap-2 sm:flex-row">
          <Link
            href={PLAN_HREF}
            className="w-full rounded-xl bg-white px-5 py-2.5 text-sm font-bold text-brand-700 shadow-soft ring-1 ring-brand-200 transition hover:bg-brand-50 sm:w-auto"
          >
            Tự tạo lịch
          </Link>
          <Link
            href={CHALLENGE_HREF}
            className="w-full rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600 sm:w-auto"
          >
            Thử thách 100 ngày
          </Link>
        </div>
      </div>
    </div>
  );
}
