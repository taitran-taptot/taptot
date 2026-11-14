"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import {
  cloneLegalDocument,
  fetchLegalDocument,
  isLegalDocument,
  LEGAL_DEFAULTS,
  LEGAL_PAGES,
  resetLegalDocument,
  saveLegalDocument,
  type LegalDocumentBody,
  type LegalDocumentSection,
  type LegalSlug,
} from "@/lib/legalDocuments";

function moveItem<T>(items: T[], index: number, direction: -1 | 1): T[] {
  const next = index + direction;
  if (next < 0 || next >= items.length) return items;
  const copy = items.slice();
  const [item] = copy.splice(index, 1);
  copy.splice(next, 0, item);
  return copy;
}

function nextSectionId(sections: LegalDocumentSection[]): string {
  const used = new Set(sections.map((section) => section.id));
  let number = sections.length + 1;
  let id = String(number);
  while (used.has(id)) {
    number += 1;
    id = String(number);
  }
  return id;
}

export default function CatalogLegalAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [slug, setSlug] = useState<LegalSlug>("dieu-khoan");
  const [doc, setDoc] = useState<LegalDocumentBody>(() => cloneLegalDocument(LEGAL_DEFAULTS["dieu-khoan"]));
  const [source, setSource] = useState<"default" | "saved">("default");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan/ke-hoach");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAllowed(true);
  }, [router]);

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    fetchLegalDocument(slug)
      .then((data) => {
        if (cancelled) return;
        if (data.source === "saved" && isLegalDocument(data.document)) {
          setDoc(cloneLegalDocument(data.document));
          setSource("saved");
        } else {
          setDoc(cloneLegalDocument(LEGAL_DEFAULTS[slug]));
          setSource("default");
        }
        setError("");
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setDoc(cloneLegalDocument(LEGAL_DEFAULTS[slug]));
        setSource("default");
        setError(e instanceof Error ? e.message : "Không tải được chính sách");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [allowed, slug]);

  function updateSection(index: number, patch: Partial<LegalDocumentSection>) {
    setDoc((current) => ({
      ...current,
      sections: current.sections.map((section, i) => (i === index ? { ...section, ...patch } : section)),
    }));
  }

  function updateLine(
    index: number,
    field: "paragraphs" | "bullets",
    lineIndex: number,
    value: string,
  ) {
    setDoc((current) => ({
      ...current,
      sections: current.sections.map((section, i) => {
        if (i !== index) return section;
        const lines = section[field].slice();
        lines[lineIndex] = value;
        return { ...section, [field]: lines };
      }),
    }));
  }

  function addLine(index: number, field: "paragraphs" | "bullets") {
    setDoc((current) => ({
      ...current,
      sections: current.sections.map((section, i) =>
        i === index ? { ...section, [field]: [...section[field], ""] } : section,
      ),
    }));
  }

  function removeLine(index: number, field: "paragraphs" | "bullets", lineIndex: number) {
    setDoc((current) => ({
      ...current,
      sections: current.sections.map((section, i) => {
        if (i !== index) return section;
        return { ...section, [field]: section[field].filter((_, n) => n !== lineIndex) };
      }),
    }));
  }

  async function save() {
    setSaving(true);
    setError("");
    setOk("");
    try {
      const data = await saveLegalDocument(slug, doc);
      if (isLegalDocument(data.document)) setDoc(cloneLegalDocument(data.document));
      setSource("saved");
      setOk("Đã lưu chính sách.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function restore() {
    if (!window.confirm("Xóa bản đã sửa và hiện lại nội dung gốc trên web?")) return;
    setSaving(true);
    setError("");
    setOk("");
    try {
      await resetLegalDocument(slug);
      setDoc(cloneLegalDocument(LEGAL_DEFAULTS[slug]));
      setSource("default");
      setOk("Đã khôi phục bản gốc.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!allowed) return null;

  return (
    <div>
      <p className="text-sm text-slate-500">
        Sửa nội dung sáu trang trong cột Điều khoản ở chân trang. Tiêu đề trang và đường dẫn giữ nguyên.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {LEGAL_PAGES.map((page) => (
          <button
            key={page.slug}
            type="button"
            className={
              slug === page.slug
                ? "rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
                : "rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-600 ring-1 ring-slate-200"
            }
            onClick={() => {
              if (page.slug === slug) return;
              setLoading(true);
              setError("");
              setOk("");
              setSlug(page.slug);
            }}
          >
            {page.label}
          </button>
        ))}
      </div>
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      {ok ? <p className="mt-3 text-sm text-emerald-700">{ok}</p> : null}
      <p className="mt-3 text-sm text-slate-500">
        {source === "saved" ? "Đang sửa bản đã lưu." : "Đang hiện bản gốc trong code. Bấm Lưu để ghi đè lên web."}
      </p>
      {loading ? <p className="mt-4 text-sm text-slate-400">Đang tải…</p> : null}

      {!loading ? (
        <div className="mt-4 space-y-4">
          <label className="block rounded-2xl border border-slate-200 bg-white p-5">
            <span className="text-sm font-semibold">Dòng cập nhật</span>
            <input
              className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={doc.updated_label}
              onChange={(e) => setDoc((current) => ({ ...current, updated_label: e.target.value }))}
            />
          </label>
          <label className="block rounded-2xl border border-slate-200 bg-white p-5">
            <span className="text-sm font-semibold">Đoạn mở đầu</span>
            <textarea
              className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              rows={4}
              value={doc.intro}
              onChange={(e) => setDoc((current) => ({ ...current, intro: e.target.value }))}
            />
          </label>
          <label className="block rounded-2xl border border-slate-200 bg-white p-5">
            <span className="text-sm font-semibold">Đoạn đồng ý</span>
            <p className="mt-1 text-xs text-slate-500">Hiện đậm dưới đoạn mở đầu. Để trống nếu trang không có câu này.</p>
            <textarea
              className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              rows={3}
              value={doc.agreement}
              onChange={(e) => setDoc((current) => ({ ...current, agreement: e.target.value }))}
            />
          </label>

          {doc.sections.map((section, index) => (
            <section key={`${section.id}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-base font-bold">Mục {index + 1}</h2>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40"
                    disabled={index === 0}
                    onClick={() =>
                      setDoc((current) => ({ ...current, sections: moveItem(current.sections, index, -1) }))
                    }
                  >
                    Lên
                  </button>
                  <button
                    type="button"
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40"
                    disabled={index === doc.sections.length - 1}
                    onClick={() =>
                      setDoc((current) => ({ ...current, sections: moveItem(current.sections, index, 1) }))
                    }
                  >
                    Xuống
                  </button>
                  <button
                    type="button"
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-red-600 disabled:opacity-40"
                    disabled={doc.sections.length === 1}
                    onClick={() =>
                      setDoc((current) => ({
                        ...current,
                        sections: current.sections.filter((_, i) => i !== index),
                      }))
                    }
                  >
                    Xóa mục
                  </button>
                </div>
              </div>
              <label className="mt-3 block text-sm font-semibold">
                Tiêu đề
                <input
                  className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal"
                  value={section.title}
                  onChange={(e) => updateSection(index, { title: e.target.value })}
                />
              </label>
              <div className="mt-4 space-y-2">
                <p className="text-sm font-semibold">Đoạn văn</p>
                {section.paragraphs.map((paragraph, lineIndex) => (
                  <div key={`p-${lineIndex}`} className="flex gap-2">
                    <textarea
                      className="min-h-20 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                      rows={3}
                      value={paragraph}
                      onChange={(e) => updateLine(index, "paragraphs", lineIndex, e.target.value)}
                    />
                    <button
                      type="button"
                      className="self-start rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600"
                      onClick={() => removeLine(index, "paragraphs", lineIndex)}
                    >
                      Xóa
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="text-sm font-semibold text-brand-600"
                  onClick={() => addLine(index, "paragraphs")}
                >
                  Thêm đoạn
                </button>
              </div>
              <div className="mt-4 space-y-2">
                <p className="text-sm font-semibold">Gạch đầu dòng</p>
                {section.bullets.map((bullet, lineIndex) => (
                  <div key={`b-${lineIndex}`} className="flex gap-2">
                    <textarea
                      className="min-h-16 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                      rows={2}
                      value={bullet}
                      onChange={(e) => updateLine(index, "bullets", lineIndex, e.target.value)}
                    />
                    <button
                      type="button"
                      className="self-start rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600"
                      onClick={() => removeLine(index, "bullets", lineIndex)}
                    >
                      Xóa
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="text-sm font-semibold text-brand-600"
                  onClick={() => addLine(index, "bullets")}
                >
                  Thêm gạch đầu dòng
                </button>
              </div>
            </section>
          ))}

          <button
            type="button"
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
            onClick={() =>
              setDoc((current) => ({
                ...current,
                sections: [
                  ...current.sections,
                  { id: nextSectionId(current.sections), title: "", paragraphs: [""], bullets: [] },
                ],
              }))
            }
          >
            Thêm mục
          </button>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={saving}
              className="rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
              onClick={() => void save()}
            >
              {saving ? "Đang lưu…" : "Lưu"}
            </button>
            <button
              type="button"
              disabled={saving}
              className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50"
              onClick={() => void restore()}
            >
              Khôi phục bản gốc
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
