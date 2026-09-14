"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { filterPublicEquipment, matchesPublicEquipmentSearch, equipmentImageFitClass } from "@/lib/equipmentCatalog";
import { equipmentCategoryLabel, mediaUrl } from "@/lib/labels";
import type { EquipmentImageItem, Label } from "@/lib/types";

type EquipRow = Label & { id: number };

function EquipThumb({ eq }: { eq: EquipRow }) {
  const src = mediaUrl(eq.image_url);
  if (!src) {
    return <div className="h-14 w-[4.5rem] shrink-0 rounded-lg bg-slate-100" aria-hidden />;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      className={`h-14 w-[4.5rem] shrink-0 rounded-lg bg-slate-50 ${equipmentImageFitClass(eq.key)}`}
    />
  );
}

export default function EquipmentLibrary() {
  const pathname = usePathname();
  const isAccount = pathname.startsWith("/tai-khoan");
  const exerciseBase = isAccount ? "/tai-khoan/bai-tap" : "/bai-tap";
  const shopBase = isAccount ? "/tai-khoan/mua-dung-cu" : "/mua-dung-cu";

  const [items, setItems] = useState<EquipRow[]>([]);
  const [selected, setSelected] = useState<EquipRow | null>(null);
  const [images, setImages] = useState<EquipmentImageItem[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [imgLoading, setImgLoading] = useState(false);
  const [error, setError] = useState("");
  const [imgError, setImgError] = useState("");
  const [filter, setFilter] = useState("");

  const pick = useCallback(async (eq: EquipRow) => {
    setSelected(eq);
    setImgLoading(true);
    setImgError("");
    setImages([]);
    try {
      const result = await api.equipmentImages(eq.key);
      setImages(result);
      if (result.length === 0 && !eq.image_url) {
        setImgError("Chưa có ảnh tham khảo cho dụng cụ này.");
      }
    } catch (e) {
      setImgError((e as Error).message || "Không tải được ảnh");
    } finally {
      setImgLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setListLoading(true);
      setError("");
      try {
        const data = await api.equipmentLabels();
        if (cancelled) return;
        const rows = filterPublicEquipment(
          (data.items || [])
            .filter((x): x is EquipRow => typeof x.id === "number")
            .map((x) => ({ ...x, id: x.id! })),
        );
        setItems(rows);
        if (rows[0]) void pick(rows[0]);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setListLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pick]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return items;
    return items.filter((i) => matchesPublicEquipmentSearch(i, q));
  }, [items, filter]);

  return (
    <section>
      <div className="mb-5">
        <h1 className="text-2xl font-extrabold tracking-tight">Kho dụng cụ</h1>
        <p className="mt-1 text-sm text-slate-500">
          Nhìn ảnh để có thể nhận biết dụng cụ, và mở các bài tập dùng dụng cụ đó.
        </p>
      </div>

      {error && <div className="mb-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-600">{error}</div>}

      <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="rounded-2xl bg-white shadow-soft lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto">
          <div className="border-b border-slate-100 p-3">
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              type="search"
              placeholder="Tìm tên dụng cụ…"
              className="field text-sm"
            />
          </div>

          {listLoading && (
            <div className="space-y-3 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-8 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          )}

          {!listLoading && filtered.length === 0 && (
            <p className="p-6 text-center text-sm text-slate-400">Không có dụng cụ nào</p>
          )}

          {!listLoading && filtered.length > 0 && (
            <ul className="pb-2">
              {filtered.map((eq) => {
                const active = selected?.id === eq.id;
                return (
                  <li key={eq.key}>
                    <button
                      type="button"
                      onClick={() => pick(eq)}
                      className={`flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-sm transition ${
                        active
                          ? "bg-brand-50 font-semibold text-brand-700"
                          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      }`}
                    >
                      <EquipThumb eq={eq} />
                      <span className="leading-snug">{eq.label_vi}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </aside>

        <div className="min-h-[420px] rounded-2xl bg-white p-4 shadow-soft sm:p-5">
          {!selected && (
            <div className="grid h-full min-h-[380px] place-items-center text-center text-slate-400">
              <div>
                <p className="font-medium text-slate-500">Chọn một dụng cụ bên trái</p>
                <p className="mt-1 text-sm">Ảnh tham khảo sẽ hiện ở đây</p>
              </div>
            </div>
          )}

          {selected && (
            <>
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-extrabold tracking-tight text-slate-800">
                    {selected.label_vi}
                  </h2>
                  {isAccount && selected.name_en && (
                    <p className="mt-0.5 text-sm text-slate-400">{selected.name_en}</p>
                  )}
                  {selected.category && (
                    <span className="badge badge-gray mt-2">
                      {equipmentCategoryLabel(selected.category)}
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`${exerciseBase}?equipment=${encodeURIComponent(selected.key)}`}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-700"
                  >
                    Xem bài tập
                  </Link>
                  <Link
                    href={
                      selected.key === "resistance-band"
                        ? `${shopBase}?category=resistance`
                        : `${shopBase}?product=${encodeURIComponent(selected.key)}`
                    }
                    className="rounded-xl bg-brand-500 px-3 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-brand-600"
                  >
                    Mua {selected.label_vi}
                  </Link>
                  {isAccount && (
                    <a
                      href={`https://www.google.com/search?tbm=isch&q=${encodeURIComponent(`${selected.name_en || selected.label_vi} gym equipment`)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-600"
                    >
                      Google Images
                    </a>
                  )}
                </div>
              </div>

              {imgLoading && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="aspect-[4/3] animate-pulse rounded-xl bg-slate-100" />
                  ))}
                </div>
              )}

              {!imgLoading && imgError && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {imgError}
                  {isAccount && (
                    <p className="mt-2 text-xs text-amber-700/80">
                      Thêm ảnh vào thư mục{" "}
                      <code>uploads/media/equipment/{selected.key}/</code> rồi chọn lại — mọi ảnh trong folder đều hiện.
                    </p>
                  )}
                </div>
              )}

              {!imgLoading && images.length === 0 && selected.image_url && !imgError && (
                <figure>
                  <div className="overflow-hidden rounded-xl bg-slate-100">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={mediaUrl(selected.image_url) || ""}
                      alt={selected.label_vi}
                      className={`aspect-[4/3] w-full ${equipmentImageFitClass(selected.key)}`}
                    />
                  </div>
                  {selected.image_attribution && (
                    <figcaption className="mt-2 text-xs text-slate-400">
                      Ảnh:{" "}
                      {selected.image_source ? (
                        <a
                          href={selected.image_source}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="underline decoration-slate-300 hover:text-brand-600"
                        >
                          {selected.image_attribution}
                        </a>
                      ) : (
                        selected.image_attribution
                      )}
                    </figcaption>
                  )}
                </figure>
              )}

              {!imgLoading && images.length > 0 && (
                <>
                  <div
                    className={`grid gap-3 ${
                      images.length === 1 ? "grid-cols-1" : "grid-cols-2 sm:grid-cols-3"
                    }`}
                  >
                    {images.map((img, idx) => (
                      <a
                        key={`${img.url}-${idx}`}
                        href={img.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group overflow-hidden rounded-xl bg-slate-100"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={img.thumb || img.url}
                          alt={img.alt || selected.label_vi}
                          loading="lazy"
                          className={`aspect-square w-full bg-white transition group-hover:scale-[1.03] ${equipmentImageFitClass(selected.key)}${
                            selected.key === "gymnastic-rings" ? "" : " p-2"
                          }`}
                        />
                      </a>
                    ))}
                  </div>
                  <p className="mt-3 text-xs text-slate-400">
                    {images.length} ảnh. Bấm để xem ảnh gốc.
                  </p>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
