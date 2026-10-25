"use client";

import Link from "next/link";
import { useState } from "react";
import { feedbackApi, type FeedbackCategory } from "@/lib/authApi";
import BrandHero from "@/components/BrandHero";
import { brandRichText } from "@/components/brandRichText";
import Modal from "./Modal";

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
  const [okOpen, setOkOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const needsPlanLink = PLAN_LINK_CATEGORIES.has(category);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (needsPlanLink && !planUrl.trim()) {
      setErr("Hãy dán link lịch tập khi góp ý về lịch tập hoặc lịch ăn.");
      return;
    }
    setLoading(true);
    try {
      await feedbackApi.submit({
        category,
        content: content.trim(),
        plan_url: needsPlanLink ? planUrl.trim() : undefined,
      });
      setContent("");
      setPlanUrl("");
      setOkOpen(true);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-8 pb-8">
      <BrandHero title="GÓP Ý" />

      <div className="mx-auto max-w-2xl rounded-3xl bg-white p-6 shadow-soft sm:p-8">
        <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
          Cảm ơn bạn đã sử dụng dịch vụ của {brandRichText("TAPTOT")}.
        </p>
        <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
          Để tiếp tục cải thiện chất lượng dịch vụ nhằm mang lại trải nghiệm tốt hơn nữa,{" "}
          {brandRichText("TAPTOT")} xin đón nhận góp ý đến từ bạn.
        </p>
      </div>

      <form onSubmit={submit} className="mx-auto max-w-2xl space-y-5 rounded-3xl bg-white p-6 shadow-soft sm:p-8">
        {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

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

      <Modal open={okOpen} onClose={() => setOkOpen(false)} title="Đã gửi góp ý">
        <div className="space-y-3 p-5 text-center">
          <p className="text-lg font-bold text-slate-800">Gửi góp ý thành công</p>
          <p className="text-sm leading-relaxed text-slate-600">
            Cảm ơn bạn. Chúng tôi đã nhận góp ý và sẽ xem xét để cải thiện dịch vụ.
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
    </section>
  );
}
