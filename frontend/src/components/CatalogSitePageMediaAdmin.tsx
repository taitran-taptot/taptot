"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { uploadAdminMedia } from "@/lib/shopApi";
import {
  SITE_PAGE_MEDIA_DEFAULTS,
  fetchSitePageMedia,
  patchSitePageMedia,
  siteImageSrc,
  youtubeEmbedSrc,
  type SitePageMedia,
} from "@/lib/sitePageMedia";

export default function CatalogSitePageMediaAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [form, setForm] = useState<SitePageMedia>(SITE_PAGE_MEDIA_DEFAULTS);
  const [homeYoutube, setHomeYoutube] = useState("");
  const [shopYoutube, setShopYoutube] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan/ke-hoach");
      return;
    }
    setAllowed(true);
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const d = await fetchSitePageMedia();
      setForm(d);
      setHomeYoutube(d.home_challenge_youtube_id);
      setShopYoutube(d.shop_guide_youtube_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  async function save() {
    setSaving(true);
    setError("");
    setOk("");
    try {
      const d = await patchSitePageMedia({
        home_challenge_youtube: homeYoutube,
        shop_guide_youtube: shopYoutube,
        service_lo_trinh_image_url: form.service_lo_trinh_image_url,
        service_dung_cu_image_url: form.service_dung_cu_image_url,
        service_hlv_image_url: form.service_hlv_image_url,
        about_hero_image_url: form.about_hero_image_url,
        about_founder_image_url: form.about_founder_image_url,
        about_trainer_image_url: form.about_trainer_image_url,
        contact_trainer_image_url: form.contact_trainer_image_url,
        success_stories: form.success_stories,
        success_stories_visible: form.success_stories_visible,
      });
      setForm(d);
      setHomeYoutube(d.home_challenge_youtube_id);
      setShopYoutube(d.shop_guide_youtube_id);
      setOk("Đã lưu nội dung trang.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function setStoriesVisible(visible: boolean) {
    setForm((current) => ({ ...current, success_stories_visible: visible }));
    setError("");
    setOk("");
    try {
      const d = await patchSitePageMedia({ success_stories_visible: visible });
      setForm(d);
      setOk(visible ? "Đã hiện khối trên trang chủ." : "Đã ẩn khối trên trang chủ.");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function updateStory(index: number, patch: Partial<(typeof form.success_stories)[number]>) {
    setForm((current) => ({
      ...current,
      success_stories: current.success_stories.map((story, i) => (i === index ? { ...story, ...patch } : story)),
    }));
  }

  async function uploadStoryImage(index: number, field: "image_url" | "logo_url", file: File) {
    const token = `${index}-${field}`;
    setUploading(token);
    setError("");
    setOk("");
    try {
      const url = await uploadAdminMedia(file);
      const next = form.success_stories.map((story, i) => (i === index ? { ...story, [field]: url } : story));
      setForm((current) => ({ ...current, success_stories: next }));
      const d = await patchSitePageMedia({ success_stories: next });
      setForm(d);
      setOk("Đã lưu ảnh.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(null);
    }
  }

  async function onUpload(key: Exclude<keyof SitePageMedia, "success_stories">, file: File) {
    setUploading(key);
    setError("");
    setOk("");
    try {
      const url = await uploadAdminMedia(file);
      setForm((f) => ({ ...f, [key]: url }));
      const d = await patchSitePageMedia({ [key]: url });
      setForm(d);
      setHomeYoutube(d.home_challenge_youtube_id);
      setShopYoutube(d.shop_guide_youtube_id);
      setOk("Đã lưu ảnh.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(null);
    }
  }

  if (!allowed) return null;

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Nội dung web</h1>
      <p className="mt-1 text-sm text-slate-500">
        Đổi video YouTube và ảnh các block trên trang chủ / mua dụng cụ. Giữ đúng tỉ lệ bên dưới để không bị vỡ khi lên web.
      </p>
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      {ok ? <p className="mt-3 text-sm text-emerald-700">{ok}</p> : null}
      {loading ? <p className="mt-4 text-sm text-slate-400">Đang tải…</p> : null}

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-bold">Video trang chủ — Nhận giáo án 100 ngày (999k)</h2>
        <p className="mt-1 text-sm text-slate-500">
          YouTube ngang <strong>16:9</strong> · khuyến nghị <strong>1920×1080</strong> (tối thiểu 1280×720). Dán link video
          hoặc ID.
        </p>
        <input
          className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={homeYoutube}
          onChange={(e) => setHomeYoutube(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=…"
        />
        <div className="mt-3 overflow-hidden rounded-xl bg-slate-900">
          <div className="relative aspect-video w-full">
            {form.home_challenge_youtube_id ? (
              <iframe
                className="absolute inset-0 h-full w-full"
                src={youtubeEmbedSrc(form.home_challenge_youtube_id)}
                title="Preview video trang chủ"
                allowFullScreen
              />
            ) : null}
          </div>
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-bold">Video mua dụng cụ — Hướng dẫn tạo giáo án 100 ngày</h2>
        <p className="mt-1 text-sm text-slate-500">
          YouTube ngang <strong>16:9</strong> · khuyến nghị <strong>1920×1080</strong> (tối thiểu 1280×720). Có thể khác video
          trang chủ.
        </p>
        <input
          className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={shopYoutube}
          onChange={(e) => setShopYoutube(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=…"
        />
        <div className="mt-3 overflow-hidden rounded-xl bg-slate-900">
          <div className="relative aspect-video w-full">
            {form.shop_guide_youtube_id ? (
              <iframe
                className="absolute inset-0 h-full w-full"
                src={youtubeEmbedSrc(form.shop_guide_youtube_id)}
                title="Preview video mua dụng cụ"
                allowFullScreen
              />
            ) : null}
          </div>
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-bold">Ảnh — Dịch vụ của TAPTOT</h2>
        <p className="mt-1 text-sm text-slate-500">
          Khung <strong>4:3</strong> · khuyến nghị <strong>1600×1200</strong> JPG/PNG/WebP. Lộ trình dùng chứa vừa (contain);
          Dụng cụ và HLV cắt phủ khung (cover).
        </p>
        <div className="mt-4 grid gap-5 md:grid-cols-3">
          {(
            [
              {
                key: "service_lo_trinh_image_url" as const,
                label: "01 Lộ trình",
                fit: "object-cover object-center",
              },
              {
                key: "service_dung_cu_image_url" as const,
                label: "02 Dụng cụ",
                fit: "object-cover object-center",
              },
              {
                key: "service_hlv_image_url" as const,
                label: "03 Huấn luyện viên",
                fit: "object-cover object-center",
              },
            ] as const
          ).map((slot) => (
            <div key={slot.key}>
              <p className="text-sm font-semibold">{slot.label}</p>
              <div className="relative mt-2 aspect-[4/3] overflow-hidden rounded-xl bg-slate-100">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={siteImageSrc(form[slot.key])}
                  alt={slot.label}
                  className={`absolute inset-0 h-full w-full ${slot.fit}`}
                />
              </div>
              <label className="mt-2 inline-flex cursor-pointer rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700">
                {uploading === slot.key ? "Đang tải…" : "Chọn ảnh"}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  disabled={!!uploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void onUpload(slot.key, file);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-bold">Ảnh — Về TAPTOT</h2>
        <p className="mt-1 text-sm text-slate-500">
          Banner ngang phủ khung · khuyến nghị <strong>1920×1080</strong> (16:9) JPG/PNG/WebP. Chân dung khung{" "}
          <strong>3:4</strong> · khuyến nghị <strong>900×1200</strong>.
        </p>
        <div className="mt-4 grid gap-5 md:grid-cols-3">
          {(
            [
              {
                key: "about_hero_image_url" as const,
                label: "Banner đầu trang",
                box: "aspect-video",
                fit: "object-cover object-center",
              },
              {
                key: "about_founder_image_url" as const,
                label: "Chân dung Trần Tài",
                box: "aspect-[3/4] max-w-[13rem]",
                fit: "object-cover object-[center_28%]",
              },
              {
                key: "about_trainer_image_url" as const,
                label: "Chân dung HLV Nguyễn Văn A",
                box: "aspect-[3/4] max-w-[13rem]",
                fit: "object-cover object-center",
              },
            ] as const
          ).map((slot) => (
            <div key={slot.key}>
              <p className="text-sm font-semibold">{slot.label}</p>
              <div className={`relative mt-2 overflow-hidden rounded-xl bg-slate-100 ${slot.box}`}>
                {form[slot.key] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={siteImageSrc(form[slot.key])}
                    alt={slot.label}
                    className={`absolute inset-0 h-full w-full ${slot.fit}`}
                  />
                ) : (
                  <p className="absolute inset-0 grid place-items-center px-3 text-center text-xs text-slate-400">
                    Chưa có ảnh
                  </p>
                )}
              </div>
              <label className="mt-2 inline-flex cursor-pointer rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700">
                {uploading === slot.key ? "Đang tải…" : "Chọn ảnh"}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  disabled={!!uploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void onUpload(slot.key, file);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-bold">Ảnh — Liên hệ / HLV</h2>
        <p className="mt-1 text-sm text-slate-500">
          Chân dung HLV trên trang liên hệ · khung <strong>3:4</strong> · khuyến nghị <strong>900×1200</strong> JPG/PNG/WebP.
        </p>
        <div className="mt-4 max-w-[13rem]">
          <p className="text-sm font-semibold">Chân dung HLV đồng hành</p>
          <div className="relative mt-2 aspect-[3/4] overflow-hidden rounded-xl bg-slate-100">
            {form.contact_trainer_image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={siteImageSrc(form.contact_trainer_image_url)}
                alt="HLV đồng hành"
                className="absolute inset-0 h-full w-full object-cover object-center"
              />
            ) : (
              <p className="absolute inset-0 grid place-items-center text-xs text-slate-400">Chưa có ảnh</p>
            )}
          </div>
          <label className="mt-2 inline-flex cursor-pointer rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700">
            {uploading === "contact_trainer_image_url" ? "Đang tải…" : "Chọn ảnh"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={!!uploading}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void onUpload("contact_trainer_image_url", file);
                e.target.value = "";
              }}
            />
          </label>
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold">Trải nghiệm của mọi người</h2>
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input
              type="checkbox"
              checked={form.success_stories_visible}
              onChange={(e) => void setStoriesVisible(e.target.checked)}
            />
            Hiện trên trang chủ
          </label>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          7 người trên trang chủ. Máy tính hiện 3 người một lần, vuốt hoặc bấm mũi tên để xem tiếp, hết người cuối thì
          quay lại người đầu. Bỏ chọn “Hiện trên trang chủ” để ẩn cả khối. Ảnh dọc <strong>4:5</strong> · khuyến nghị{" "}
          <strong>800×1000</strong>. Logo nhỏ khuyến nghị <strong>200×200</strong>.
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {form.success_stories.map((story, index) => (
            <div key={index} className="rounded-xl border border-slate-100 p-4">
              <p className="text-sm font-semibold">Người {index + 1}</p>
              <div className="mt-2 flex gap-4">
                <div>
                  <div className="relative aspect-[4/5] w-28 overflow-hidden rounded-xl bg-slate-100">
                    {story.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={siteImageSrc(story.image_url)} alt="" className="absolute inset-0 h-full w-full object-cover" />
                    ) : (
                      <p className="absolute inset-0 grid place-items-center text-xs text-slate-400">Ảnh</p>
                    )}
                  </div>
                  <label className="mt-2 inline-flex cursor-pointer rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700">
                    {uploading === `${index}-image_url` ? "Đang tải…" : "Ảnh người"}
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      className="hidden"
                      disabled={!!uploading}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) void uploadStoryImage(index, "image_url", file);
                        e.target.value = "";
                      }}
                    />
                  </label>
                </div>
                <div>
                  <div className="relative h-16 w-16 overflow-hidden rounded-xl bg-slate-100">
                    {story.logo_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={siteImageSrc(story.logo_url)} alt="" className="absolute inset-0 h-full w-full object-contain p-1" />
                    ) : (
                      <p className="absolute inset-0 grid place-items-center text-[10px] text-slate-400">Logo</p>
                    )}
                  </div>
                  <label className="mt-2 inline-flex cursor-pointer rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700">
                    {uploading === `${index}-logo_url` ? "Đang tải…" : "Logo nhỏ"}
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      className="hidden"
                      disabled={!!uploading}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) void uploadStoryImage(index, "logo_url", file);
                        e.target.value = "";
                      }}
                    />
                  </label>
                </div>
              </div>
              <input
                className="mt-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={story.name}
                onChange={(e) => updateStory(index, { name: e.target.value })}
                placeholder="Tên"
              />
              <input
                className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={story.occupation}
                onChange={(e) => updateStory(index, { occupation: e.target.value })}
                placeholder="Nghề nghiệp"
              />
              <textarea
                className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                rows={3}
                value={story.quote}
                onChange={(e) => updateStory(index, { quote: e.target.value })}
                placeholder="Một câu họ nói về lịch tập"
              />
              <button
                type="button"
                className="mt-2 text-xs font-semibold text-slate-500 underline"
                onClick={() => updateStory(index, { image_url: "", logo_url: "", name: "", occupation: "", quote: "" })}
              >
                Xóa nội dung người này
              </button>
            </div>
          ))}
        </div>
      </section>

      <button
        type="button"
        disabled={saving}
        className="mt-5 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
        onClick={() => void save()}
      >
        {saving ? "Đang lưu…" : "Lưu tất cả"}
      </button>
    </div>
  );
}
