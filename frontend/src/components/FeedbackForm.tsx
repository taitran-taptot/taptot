"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { feedbackApi } from "@/lib/authApi";

const CATEGORIES = [
  { value: "food" as const, label: "Thiếu món ăn / thực đơn" },
  { value: "exercise" as const, label: "Thiếu bài tập" },
  { value: "other" as const, label: "Khác" },
];

export default function FeedbackForm() {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [category, setCategory] = useState<"food" | "exercise" | "other">("food");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace(`/dang-nhap?next=${encodeURIComponent(pathname || "/gop-y")}`);
      return;
    }
    setReady(true);
  }, [pathname, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setOk("");
    setLoading(true);
    try {
      const res = await feedbackApi.submit({ category, title: title.trim(), content: content.trim() });
      setOk(res.message || "Đã gửi góp ý. Cảm ơn bạn!");
      setTitle("");
      setContent("");
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl bg-white p-6 text-sm text-slate-500 shadow-soft">
        Đang kiểm tra đăng nhập…
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-lg space-y-4 rounded-2xl bg-white p-6 shadow-soft">
      <div>
        <h1 className="type-display">Góp ý</h1>
        <p className="mt-1 text-sm text-slate-500">
          Báo cho chúng tôi nếu thiếu món ăn, bài tập hoặc nội dung khác trong kho dữ liệu.
        </p>
      </div>
      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
      {ok && <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{ok}</p>}
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Loại góp ý</label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as "food" | "exercise" | "other")}
          className="field"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Tiêu đề</label>
        <input
          required
          minLength={2}
          maxLength={200}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="VD: Thiếu ức gà / khoai lang"
          className="field"
        />
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Nội dung</label>
        <textarea
          required
          minLength={5}
          maxLength={4000}
          rows={5}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Mô tả chi tiết món ăn / bài tập bạn muốn bổ sung…"
          className="field resize-y"
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
  );
}
