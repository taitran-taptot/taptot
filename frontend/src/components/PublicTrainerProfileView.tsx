"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { trainerProfileApi, type TrainerProfileData } from "@/lib/phase3Api";

export default function PublicTrainerProfileView() {
  const params = useParams();
  const token = String(params?.token || "");
  const [data, setData] = useState<TrainerProfileData | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setErr("Link không hợp lệ");
      setLoading(false);
      return;
    }
    let cancelled = false;
    trainerProfileApi
      .getPublic(token)
      .then((p) => {
        if (!cancelled) setData(p);
      })
      .catch((ex) => {
        if (!cancelled) setErr((ex as Error).message || "Không tìm thấy profile");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (loading) {
    return <p className="py-16 text-center text-sm text-slate-400">Đang tải profile…</p>;
  }

  if (err || !data) {
    return (
      <section className="mx-auto max-w-lg px-4 py-16 text-center">
        <h1 className="text-xl font-extrabold">Không tìm thấy</h1>
        <p className="mt-2 text-sm text-slate-500">{err || "Profile không tồn tại."}</p>
        <Link href="/" className="mt-4 inline-block font-semibold text-brand-600">
          Về trang chủ
        </Link>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <div className="rounded-2xl bg-white p-6 shadow-soft">
        <p className="text-xs font-semibold tracking-wide text-brand-600 uppercase">Huấn luyện viên TAPTOT</p>
        <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-slate-900">
          {data.full_name || data.business_name || "HLV"}
        </h1>
        <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-600">
          {data.age != null && <span>Tuổi: <b>{data.age}</b></span>}
          {data.years_experience != null && (
            <span>Kinh nghiệm: <b>{data.years_experience} năm</b></span>
          )}
          {data.gym_name && <span>Gym: <b>{data.gym_name}</b></span>}
          {data.is_verified && (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
              Đã xác minh
            </span>
          )}
        </div>
        {data.bio_vi && <p className="mt-4 text-sm leading-relaxed text-slate-600">{data.bio_vi}</p>}
      </div>

      <PublicCredSection title="Chứng chỉ" items={data.certificates} />
      <PublicCredSection title="Giải thưởng" items={data.awards} />

      <p className="text-center text-xs text-slate-400">
        <Link href="/lien-he" className="font-semibold text-brand-600">
          Liên hệ tìm HLV trên TAPTOT
        </Link>
      </p>
    </section>
  );
}

function PublicCredSection({
  title,
  items,
}: {
  title: string;
  items: TrainerProfileData["awards"];
}) {
  if (!items.length) return null;
  return (
    <div className="rounded-2xl bg-white p-5 shadow-soft">
      <h2 className="text-sm font-bold text-slate-800">
        {title} ({items.length})
      </h2>
      <ul className="mt-3 space-y-4">
        {items.map((c) => (
          <li key={c.id}>
            <p className="font-semibold text-slate-800">{c.title}</p>
            {c.description && <p className="text-xs text-slate-500">{c.description}</p>}
            <div className="mt-2 flex flex-wrap gap-2">
              {c.image_urls.map((url) => (
                // eslint-disable-next-line @next/next/no-img-element
                <a key={url} href={url} target="_blank" rel="noreferrer">
                  <img src={url} alt="" className="h-24 w-24 rounded-lg object-cover ring-1 ring-slate-100" />
                </a>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
