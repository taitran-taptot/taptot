"use client";

import { useState } from "react";
import Modal from "./Modal";
import type { ExportImagePosition, PlanExportOptions } from "@/lib/plansApi";

const MAX_IMAGE_BYTES = 1.5 * 1024 * 1024;
const POSITIONS: { value: ExportImagePosition; label: string }[] = [
  { value: "header", label: "Đầu tài liệu" },
  { value: "before_days", label: "Trước nội dung ngày" },
  { value: "footer", label: "Cuối tài liệu" },
];

type Props = {
  open: boolean;
  onClose: () => void;
  onExport: (options: PlanExportOptions) => Promise<void>;
};

async function fileToDataUrl(file: File): Promise<string> {
  if (!file.type.startsWith("image/")) {
    throw new Error("Chỉ chấp nhận file ảnh.");
  }
  if (file.size > MAX_IMAGE_BYTES) {
    throw new Error("Mỗi ảnh tối đa khoảng 1.5MB.");
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Không đọc được ảnh."));
    reader.readAsDataURL(file);
  });
}

export default function ExportCustomizeModal({ open, onClose, onExport }: Props) {
  const [customerName, setCustomerName] = useState("");
  const [headerText, setHeaderText] = useState("");
  const [footerText, setFooterText] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [imagePosition, setImagePosition] = useState<ExportImagePosition>("header");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  function resetAndClose() {
    setErr("");
    onClose();
  }

  async function onPickImages(files: FileList | null) {
    if (!files?.length) return;
    setErr("");
    try {
      const next = [...images];
      for (const file of Array.from(files)) {
        if (next.length >= 2) break;
        next.push(await fileToDataUrl(file));
      }
      setImages(next.slice(0, 2));
    } catch (ex) {
      setErr((ex as Error).message);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const options: PlanExportOptions = {
        customer_name: customerName.trim() || undefined,
        header_text: headerText.trim() || undefined,
        footer_text: footerText.trim() || undefined,
        image_data_urls: images.length ? images : undefined,
        image_position: imagePosition,
      };
      await onExport(options);
      resetAndClose();
    } catch (ex) {
      setErr((ex as Error).message || "Xuất file thất bại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open} onClose={resetAndClose} size="lg">
      <form onSubmit={(e) => void submit(e)} className="space-y-3 p-5">
        <div>
          <h2 className="text-lg font-bold tracking-tight">Xuất PDF</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            File PDF có watermark TAPTOT trên mỗi trang.
          </p>
        </div>

        {err && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">Tên khách hàng</label>
          <input
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            maxLength={200}
            placeholder="VD: Nguyễn Văn A"
            className="field !py-2"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">Text đầu (lời chào / intro)</label>
          <textarea
            value={headerText}
            onChange={(e) => setHeaderText(e.target.value)}
            maxLength={2000}
            rows={2}
            placeholder="VD: Chào bạn, đây là lịch tập tuần này…"
            className="field !py-2 resize-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">Text cuối (ghi chú)</label>
          <textarea
            value={footerText}
            onChange={(e) => setFooterText(e.target.value)}
            maxLength={2000}
            rows={2}
            placeholder="VD: Liên hệ Zalo nếu cần điều chỉnh…"
            className="field !py-2 resize-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">Ảnh (tối đa 2, mỗi ảnh ≤ 1.5MB)</label>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => void onPickImages(e.target.files)}
            className="block w-full text-sm text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-brand-700"
          />
          {images.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {images.map((src, i) => (
                <div key={i} className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src} alt="" className="h-16 w-16 rounded-lg object-cover ring-1 ring-slate-200" />
                  <button
                    type="button"
                    onClick={() => setImages((prev) => prev.filter((_, j) => j !== i))}
                    className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-rose-500 text-[10px] font-bold text-white"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">Vị trí ảnh</label>
          <select
            className="field !py-2"
            value={imagePosition}
            onChange={(e) => setImagePosition(e.target.value as ExportImagePosition)}
          >
            {POSITIONS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-2 pt-1">
          <button
            type="button"
            onClick={resetAndClose}
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-50"
          >
            Huỷ
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {loading ? "Đang xuất…" : "Xuất PDF"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
