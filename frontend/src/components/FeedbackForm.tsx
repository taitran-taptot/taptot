"use client";

import Link from "next/link";
import { useState } from "react";
import { feedbackApi, type FeedbackCategory } from "@/lib/authApi";
import BrandWordmark from "@/components/BrandWordmark";

const CATEGORIES: { value: FeedbackCategory; label: string }[] = [
  { value: "equipment", label: "Dụng cụ" },
  { value: "workout_plan", label: "Lịch tập" },
  { value: "meal_plan", label: "Lịch ăn" },
  { value: "food_catalog", label: "Kho thực phẩm" },
  { value: "exercise_catalog", label: "Kho bài tập" },
  { value: "knowledge", label: "Kho kiến thức" },
  { value: "trainer", label: "Huấn luyện viên" },
  { value: "other", label: "Khác" },
];

const PLAN_LINK_CATEGORIES = new Set<FeedbackCategory>(["workout_plan", "meal_plan"]);

export default function FeedbackForm() {
  const [category, setCategory] = useState<FeedbackCategory>("equipment");
  const [planUrl, setPlanUrl] = useState("");
  const [content, setContent] = useState("");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const [loading, setLoading] = useState(false);
  const needsPlanLink = PLAN_LINK_CATEGORIES.has(category);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setOk("");
    if (needsPlanLink && !planUrl.trim()) {
      setErr("Hãy dán link lịch tập khi góp ý về lịch tập hoặc lịch ăn.");
      return;
    }
    setLoading(true);
    try {
      const res = await feedbackApi.submit({
        category,
        content: content.trim(),
        plan_url: needsPlanLink ? planUrl.trim() : undefined,
      });
      setOk(res.message || "Đã gửi góp ý. Cảm ơn bạn!");
      setContent("");
      setPlanUrl("");
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-8 pb-8">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-brand-900 px-6 py-9 text-white shadow-soft sm:px-10 sm:py-12">
        <div className="pointer-events-none absolute -top-24 right-0 h-64 w-64 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 left-1/3 h-56 w-56 rounded-full bg-emerald-300/10 blur-3xl" />
        <div className="relative mx-auto max-w-2xl text-center">
          <h1 className="type-display flex flex-col items-center">
            <BrandWordmark snow />
            <span className="sr-only">Góp ý</span>
          </h1>
          <p className="mt-6 text-sm leading-relaxed text-white/80 sm:text-base">
            Cảm ơn bạn đã sử dụng dịch vụ của TAPTOT.
          </p>
          <p className="mt-2 text-sm leading-relaxed text-white/80 sm:text-base">
            Để tiếp tục cải thiện chất lượng dịch vụ nhằm mang lại trải nghiệm tốt hơn nữa, TAPTOT
            xin đón nhận góp ý đến từ bạn.
          </p>
        </div>
      </div>

      <form onSubmit={submit} className="mx-auto max-w-2xl space-y-5 rounded-3xl bg-white p-6 shadow-soft sm:p-8">
        {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
        {ok && <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{ok}</p>}

        <fieldset>
          <legend className="mb-2 block text-sm font-semibold text-slate-700">Chủ đề</legend>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => {
              const active = category === c.value;
              return (
                <label
                  key={c.value}
                  className={`cursor-pointer rounded-xl border px-3 py-2 text-sm font-semibold transition ${
                    active
                      ? "border-brand-500 bg-brand-50 text-brand-800"
                      : "border-slate-200 text-slate-600 hover:border-brand-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="feedback-category"
                    value={c.value}
                    checked={active}
                    onChange={() => setCategory(c.value)}
                    className="sr-only"
                  />
                  {c.label}
                </label>
              );
            })}
          </div>
        </fieldset>

        {needsPlanLink && (
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-700">Dán link lịch</label>
            <input
              required
              type="url"
              value={planUrl}
              onChange={(e) => setPlanUrl(e.target.value)}
              placeholder="https://taptot.vn/lich/…"
              className="field"
            />
          </div>
        )}

        <div>
          <label className="mb-1.5 block text-sm font-semibold text-slate-700">Nội dung góp ý</label>
          <textarea
            required
            minLength={5}
            maxLength={4000}
            rows={10}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Viết góp ý của bạn…"
            className="field min-h-48 resize-y"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-brand-500 py-3 font-bold text-white hover:bg-brand-600 disabled:opacity-50"
        >
          {loading ? "Đang gửi…" : "Gửi góp ý"}
        </button>
        <p className="text-center text-sm text-slate-500">
          Cần huấn luyện viên?{" "}
          <Link href="/lien-he" className="font-semibold text-brand-600 hover:underline">
            Tìm huấn luyện viên
          </Link>
        </p>
      </form>
    </section>
  );
}
