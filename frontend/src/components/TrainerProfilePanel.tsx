"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getStoredUser } from "@/lib/auth";
import {
  trainerProfileApi,
  type TrainerCredential,
  type TrainerProfileData,
} from "@/lib/phase3Api";

type CredKind = "award" | "certificate";

export default function TrainerProfilePanel() {
  const user = getStoredUser();
  const isTrainer = user?.role === "trainer" || user?.role === "admin";

  const [data, setData] = useState<TrainerProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const [fullName, setFullName] = useState("");
  const [age, setAge] = useState("");
  const [years, setYears] = useState("");
  const [bio, setBio] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [gymName, setGymName] = useState("");

  const [credKind, setCredKind] = useState<CredKind>("certificate");
  const [credTitle, setCredTitle] = useState("");
  const [credDesc, setCredDesc] = useState("");
  const [credFiles, setCredFiles] = useState<File[]>([]);
  const [addingCred, setAddingCred] = useState(false);
  const [copied, setCopied] = useState(false);

  const applyProfile = useCallback((p: TrainerProfileData) => {
    setData(p);
    setFullName(p.full_name ?? "");
    setAge(p.age != null ? String(p.age) : "");
    setYears(p.years_experience != null ? String(p.years_experience) : "");
    setBio(p.bio_vi ?? "");
    setBusinessName(p.business_name ?? "");
    setGymName(p.gym_name ?? "");
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      applyProfile(await trainerProfileApi.get());
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }, [applyProfile]);

  useEffect(() => {
    if (isTrainer) void load();
    else setLoading(false);
  }, [isTrainer, load]);

  async function onSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr("");
    setMsg("");
    try {
      const ageN = age.trim() ? Math.round(Number(age)) : null;
      const yearsN = years.trim() ? Math.round(Number(years)) : null;
      if (age.trim() && !Number.isFinite(ageN)) throw new Error("Tuổi không hợp lệ");
      if (years.trim() && !Number.isFinite(yearsN)) throw new Error("Số năm kinh nghiệm không hợp lệ");
      const updated = await trainerProfileApi.update({
        full_name: fullName.trim() || null,
        age: ageN,
        years_experience: yearsN,
        bio_vi: bio.trim() || null,
        business_name: businessName.trim() || null,
        gym_name: gymName.trim() || null,
      });
      applyProfile(updated);
      setMsg("Đã lưu profile.");
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function onAddCredential(e: React.FormEvent) {
    e.preventDefault();
    if (!credTitle.trim()) {
      setErr("Nhập tiêu đề giải thưởng / chứng chỉ.");
      return;
    }
    if (!credFiles.length) {
      setErr("Cần chụp / chọn ít nhất 1 ảnh minh chứng.");
      return;
    }
    setAddingCred(true);
    setErr("");
    setMsg("");
    try {
      const urls: string[] = [];
      for (const file of credFiles) {
        const up = await trainerProfileApi.uploadImage(file);
        urls.push(up.url);
      }
      await trainerProfileApi.addCredential({
        kind: credKind,
        title: credTitle.trim(),
        description: credDesc.trim() || null,
        image_urls: urls,
      });
      setCredTitle("");
      setCredDesc("");
      setCredFiles([]);
      setMsg(credKind === "award" ? "Đã thêm giải thưởng." : "Đã thêm chứng chỉ.");
      await load();
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setAddingCred(false);
    }
  }

  async function onRemoveCredential(id: number) {
    try {
      await trainerProfileApi.removeCredential(id);
      await load();
    } catch (ex) {
      setErr((ex as Error).message);
    }
  }

  async function copyShareLink() {
    if (!data?.share_url_path) return;
    const url = `${window.location.origin}${data.share_url_path}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setErr("Không copy được link — hãy copy thủ công.");
    }
  }

  if (!user) {
    return (
      <section className="mx-auto max-w-lg px-4 py-10 text-center">
        <h1 className="text-xl font-extrabold">Hồ sơ HLV</h1>
        <p className="mt-2 text-sm text-slate-500">Vui lòng đăng nhập bằng tài khoản huấn luyện viên.</p>
        <Link href="/dang-nhap" className="mt-4 inline-block font-semibold text-brand-600">
          Đăng nhập
        </Link>
      </section>
    );
  }

  if (!isTrainer) {
    return (
      <section className="mx-auto max-w-lg px-4 py-10 text-center">
        <h1 className="text-xl font-extrabold">Hồ sơ HLV</h1>
        <p className="mt-2 text-sm text-slate-500">Chỉ tài khoản huấn luyện viên mới dùng được chức năng này.</p>
      </section>
    );
  }

  const [shareOrigin, setShareOrigin] = useState("");
  useEffect(() => {
    setShareOrigin(window.location.origin);
  }, []);

  const shareUrl = data?.share_url_path
    ? `${shareOrigin || ""}${data.share_url_path}`
    : "";

  return (
    <section className="mx-auto max-w-3xl space-y-5 px-4 py-8">
      <div>
        <h1 className="text-xl font-extrabold tracking-tight sm:text-2xl">Hồ sơ HLV</h1>
        <p className="mt-1 text-sm text-slate-500">
          Hồ sơ công khai: tên, tuổi, năm kinh nghiệm, giải thưởng & chứng chỉ (kèm ảnh).
        </p>
      </div>

      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
      {msg && <p className="rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-700">{msg}</p>}

      {loading || !data ? (
        <p className="text-sm text-slate-400">Đang tải…</p>
      ) : (
        <>
          <div className="rounded-2xl bg-white p-5 shadow-soft">
            <p className="mb-2 text-sm font-semibold text-slate-700">Link share</p>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <input className="field flex-1 text-xs sm:text-sm" readOnly value={shareUrl} />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => void copyShareLink()}
                  className="rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white"
                >
                  {copied ? "Đã copy" : "Copy link"}
                </button>
                {data.share_url_path && (
                  <Link
                    href={data.share_url_path}
                    target="_blank"
                    className="rounded-xl border border-brand-200 px-4 py-2.5 text-sm font-semibold text-brand-700"
                  >
                    Xem
                  </Link>
                )}
              </div>
            </div>
          </div>

          <form onSubmit={(e) => void onSaveProfile(e)} className="space-y-4 rounded-2xl bg-white p-5 shadow-soft">
            <p className="text-sm font-semibold text-slate-700">Thông tin cá nhân</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="space-y-1">
                <span className="text-xs font-semibold text-slate-600">Họ tên</span>
                <input className="field" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold text-slate-600">Tuổi</span>
                <input
                  className="field"
                  type="number"
                  min={16}
                  max={100}
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold text-slate-600">Năm kinh nghiệm</span>
                <input
                  className="field"
                  type="number"
                  min={0}
                  max={60}
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold text-slate-600">Phòng gym / studio</span>
                <input className="field" value={gymName} onChange={(e) => setGymName(e.target.value)} />
              </label>
              <label className="space-y-1 sm:col-span-2">
                <span className="text-xs font-semibold text-slate-600">Tên thương hiệu</span>
                <input
                  className="field"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                />
              </label>
              <label className="space-y-1 sm:col-span-2">
                <span className="text-xs font-semibold text-slate-600">Giới thiệu</span>
                <textarea
                  className="field min-h-[90px]"
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                />
              </label>
            </div>
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {saving ? "Đang lưu…" : "Lưu profile"}
            </button>
          </form>

          <form onSubmit={(e) => void onAddCredential(e)} className="space-y-4 rounded-2xl bg-white p-5 shadow-soft">
            <p className="text-sm font-semibold text-slate-700">Thêm giải thưởng / chứng chỉ</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="space-y-1">
                <span className="text-xs font-semibold text-slate-600">Loại</span>
                <select
                  className="field"
                  value={credKind}
                  onChange={(e) => setCredKind(e.target.value as CredKind)}
                >
                  <option value="certificate">Chứng chỉ</option>
                  <option value="award">Giải thưởng</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold text-slate-600">Tiêu đề</span>
                <input
                  className="field"
                  value={credTitle}
                  onChange={(e) => setCredTitle(e.target.value)}
                  placeholder="VD: CPT NASM"
                  required
                />
              </label>
              <label className="space-y-1 sm:col-span-2">
                <span className="text-xs font-semibold text-slate-600">Mô tả (tuỳ chọn)</span>
                <input className="field" value={credDesc} onChange={(e) => setCredDesc(e.target.value)} />
              </label>
              <label className="space-y-1 sm:col-span-2">
                <span className="text-xs font-semibold text-slate-600">
                  Ảnh minh chứng <span className="font-normal text-rose-500">(≥ 1 ảnh)</span>
                </span>
                <input
                  className="field"
                  type="file"
                  accept="image/*"
                  multiple
                  capture="environment"
                  onChange={(e) => setCredFiles(Array.from(e.target.files || []))}
                />
                {credFiles.length > 0 && (
                  <p className="text-xs text-slate-400">Đã chọn {credFiles.length} ảnh</p>
                )}
              </label>
            </div>
            <button
              type="submit"
              disabled={addingCred}
              className="rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {addingCred ? "Đang tải ảnh…" : "Thêm"}
            </button>
          </form>

          <CredentialList
            title="Chứng chỉ"
            items={data.certificates}
            onRemove={(id) => void onRemoveCredential(id)}
          />
          <CredentialList
            title="Giải thưởng"
            items={data.awards}
            onRemove={(id) => void onRemoveCredential(id)}
          />
        </>
      )}
    </section>
  );
}

function CredentialList({
  title,
  items,
  onRemove,
}: {
  title: string;
  items: TrainerCredential[];
  onRemove: (id: number) => void;
}) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-soft">
      <p className="mb-3 text-sm font-semibold text-slate-700">
        {title} ({items.length})
      </p>
      {!items.length ? (
        <p className="text-sm text-slate-400">Chưa có mục nào.</p>
      ) : (
        <ul className="space-y-4">
          {items.map((c) => (
            <li key={c.id} className="rounded-xl border border-slate-100 p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-slate-800">{c.title}</p>
                  {c.description && <p className="mt-0.5 text-xs text-slate-500">{c.description}</p>}
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(c.id)}
                  className="text-xs font-semibold text-rose-500"
                >
                  Xoá
                </button>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {c.image_urls.map((url) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <a key={url} href={url} target="_blank" rel="noreferrer">
                    <img src={url} alt="" className="h-20 w-20 rounded-lg object-cover ring-1 ring-slate-100" />
                  </a>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
