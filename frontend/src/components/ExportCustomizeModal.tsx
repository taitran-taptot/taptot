"use client";

import { useEffect, useState } from "react";
import Modal from "./Modal";
import type { ExportFormat, ExportImagePosition, PlanExportOptions } from "@/lib/plansApi";

const MAX_IMAGE_BYTES = 1.5 * 1024 * 1024;
const POSITIONS: { value: ExportImagePosition; label: string }[] = [
  { value: "header", label: "Đầu tài liệu" },
  { value: "before_days", label: "Trước nội dung ngày" },
  { value: "footer", label: "Cuối tài liệu" },
];

const FORMAT_LABEL: Record<"csv" | "xlsx" | "pdf" | "word", string> = {
  csv: "CSV",
  xlsx: "Excel",
  pdf: "PDF (In)",
  word: "Word",
};

type ModalFormat = "csv" | "xlsx" | "pdf" | "word";

type Props = {
  open: boolean;
  onClose: () => void;
  format: ModalFormat | null;
  defaultStartDate?: string | null;
  onExport: (format: ExportFormat, options: PlanExportOptions) => Promise<void>;
};

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

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

export default function ExportCustomizeModal({
  open,
  onClose,
  format,
  defaultStartDate,
  onExport,
}: Props) {
  const [customerName, setCustomerName] = useState("");
  const [startDate, setStartDate] = useState(todayIso());
  const [headerText, setHeaderText] = useState("");
  const [footerText, setFooterText] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [imagePosition, setImagePosition] = useState<ExportImagePosition>("header");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const isExcel = format === "xlsx";

  useEffect(() => {
    if (!open) return;
    const fromPlan = (defaultStartDate || "").slice(0, 10);
    setStartDate(fromPlan || todayIso());
  }, [open, defaultStartDate]);

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
    if (!format) return;
    setErr("");
    setLoading(true);
    try {
      const options: PlanExportOptions = {
        customer_name: customerName.trim() || undefined,
        header_text: headerText.trim() || undefined,
        footer_text: footerText.trim() || undefined,
        start_date: startDate || undefined,
        image_data_urls: !isExcel && images.length ? images : undefined,
        image_position: imagePosition,
      };
      await onExport(format, options);
      resetAndClose();
    } catch (ex) {
      setErr((ex as Error).message || "Xuất file thất bại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open && !!format} onClose={resetAndClose} size="lg">
      <form onSubmit={(e) => void submit(e)} className="space-y-3 p-5">
        <div>
          <h2 className="text-lg font-extrabold tracking-tight">Tùy chỉnh xuất file</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            Định dạng: <span className="font-semibold text-slate-700">{format ? FORMAT_LABEL[format] : ""}</span>
            {isExcel
              ? " — file Excel: đổi Ngày bắt đầu, lịch buổi tự cập nhật."
              : format === "csv"
                ? " — bảng phẳng, mở được bằng Excel."
                : ""}
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

        {isExcel && (
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-600">Ngày bắt đầu lịch</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="field !py-2"
            />
            <p className="mt-1 text-[11px] text-slate-400">
              Có thể sửa lại trong file Excel (ô vàng). Các buổi 3 ngày/tuần mặc định cách ngày (VD: T2–T4–T6).
            </p>
          </div>
        )}

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

        {!isExcel && (
          <>
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
              <label className="mb-1 block text-xs font-semibold text-slate-600">Vị trí ảnh (PDF / Word)</label>
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
          </>
        )}

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
            disabled={loading || !format}
            className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {loading ? "Đang xuất…" : "Xuất file"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
