"use client";

import { useEffect, useMemo, useState } from "react";
import Modal from "./Modal";
import { api } from "@/lib/api";
import {
  WIZARD_EQUIPMENT_GROUPS,
  type WizardEquipmentGroup,
  collapsePublicEquipmentKeys,
  equipmentImageFitClass,
  filterPublicEquipment,
  isWizardEquipmentSlug,
  publicEquipmentImage,
  syncWizardEquipmentSelection,
  wizardEquipmentGroupSelected,
} from "@/lib/equipmentCatalog";
import { EQUIPMENT_GROUP_UI } from "@/lib/equipmentGroupUi";
import { mediaUrl } from "@/lib/labels";
import type { Label } from "@/lib/types";

type EquipRow = Label & { id?: number };

type Props = {
  open: boolean;
  onClose: () => void;
  selectedKeys: string[];
  onSave: (keys: string[], items: EquipRow[]) => void;
};

export default function EquipmentPickerModal({ open, onClose, selectedKeys, onSave }: Props) {
  const [items, setItems] = useState<EquipRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<Set<string>>(new Set());
  const [draftSyncedForOpen, setDraftSyncedForOpen] = useState(false);

  // Sync draft when the modal opens (adjust state during render — avoids set-state-in-effect).
  if (open && !draftSyncedForOpen) {
    const synced = syncWizardEquipmentSelection(
      collapsePublicEquipmentKeys(selectedKeys).filter(isWizardEquipmentSlug),
    );
    // Single-select: keep only the first selected group (by difficulty order).
    const first = WIZARD_EQUIPMENT_GROUPS.find((g) => wizardEquipmentGroupSelected(synced, g));
    setDraftSyncedForOpen(true);
    setDraft(new Set(first ? first.slugs : []));
    setError("");
  } else if (!open && draftSyncedForOpen) {
    setDraftSyncedForOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await api.equipmentLabels();
        if (!cancelled) setItems(filterPublicEquipment(data.items || []));
      } catch (e) {
        if (!cancelled) setError((e as Error).message || "Không tải được kho dụng cụ.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  const byKey = useMemo(() => new Map(items.map((item) => [item.key, item])), [items]);

  const groups = WIZARD_EQUIPMENT_GROUPS;

  const selectedGroupCount = useMemo(
    () => WIZARD_EQUIPMENT_GROUPS.filter((g) => wizardEquipmentGroupSelected(draft, g)).length,
    [draft],
  );

  function toggleGroup(group: WizardEquipmentGroup) {
    if (wizardEquipmentGroupSelected(draft, group)) {
      setDraft(new Set());
      return;
    }
    setDraft(new Set(group.slugs));
  }

  function imageFor(slug: string): string | null {
    const fromCatalog = publicEquipmentImage(slug);
    if (fromCatalog) return mediaUrl(fromCatalog);
    const row = byKey.get(slug);
    return row?.image_url ? mediaUrl(row.image_url) : null;
  }

  function confirm() {
    const keys = syncWizardEquipmentSelection([...draft]);
    const selected = items.filter((i) => keys.includes(i.key));
    for (const group of WIZARD_EQUIPMENT_GROUPS) {
      if (!wizardEquipmentGroupSelected(keys, group)) continue;
      for (const slug of group.slugs) {
        if (selected.some((i) => i.key === slug)) continue;
        selected.push({
          key: slug,
          label_vi: group.products?.find((p) => p.slug === slug)?.label_vi || group.label_vi,
        } as EquipRow);
      }
    }
    onSave(keys, selected);
    onClose();
  }

  return (
    <Modal open={open} onClose={onClose} size="md" lockScroll>
      <div className="flex min-h-0 flex-1 flex-col" style={{ maxHeight: "min(92vh, 640px)" }}>
        <div className="shrink-0 border-b border-brand-100 bg-gradient-to-br from-brand-50 via-white to-emerald-50/80 px-4 pb-3 pt-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="type-kicker text-brand-600">
                Dụng cụ tại nhà
              </p>
              <h3 className="mt-0.5 text-base font-bold text-slate-900 sm:text-lg">
                Bạn đang có dụng cụ nào?
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                Chạm để chọn <b className="text-brand-600">1</b> loại dụng cụ
                {selectedGroupCount > 0 ? " · đã chọn" : ""}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white text-xl leading-none text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
              aria-label="Đóng"
            >
              ×
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4">
          {error && <p className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>}
          {loading && <p className="py-10 text-center text-sm text-slate-400">Đang tải…</p>}
          {!loading && (
            <ul className="mx-auto flex max-w-md flex-col gap-3">
              {groups.map((group) => {
                const on = wizardEquipmentGroupSelected(draft, group);
                const dual = Boolean(group.products && group.products.length >= 2);
                const ui = EQUIPMENT_GROUP_UI[group.id];
                return (
                  <li key={group.id}>
                    <button
                      type="button"
                      onClick={() => toggleGroup(group)}
                      aria-pressed={on}
                      className={`relative flex w-full items-center gap-3 overflow-hidden rounded-2xl border px-3 py-3 text-left transition ${
                        on
                          ? ui.cardSelected
                          : `border-slate-200 bg-white ${ui.cardHover}`
                      }`}
                    >
                      <span
                        className={`absolute inset-y-0 left-0 w-1 ${ui.accentBar}`}
                        aria-hidden
                      />
                      {dual ? (
                        <span
                          className={`flex h-[4.5rem] w-[6.75rem] shrink-0 items-center gap-1 rounded-xl p-1 ring-1 sm:h-20 sm:w-[7.25rem] ${
                            on ? ui.tintSelected : ui.tint
                          }`}
                        >
                          {group.products!.map((product, idx) => {
                            const src = imageFor(product.slug);
                            return (
                              <span key={product.slug} className="contents">
                                {idx > 0 && (
                                  <span className="text-[10px] font-bold text-slate-400" aria-hidden>
                                    +
                                  </span>
                                )}
                                <span className="grid h-full flex-1 place-items-center rounded-lg bg-white/70">
                                  {src ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img
                                      src={src}
                                      alt={product.label_vi}
                                      className={`max-h-[90%] max-w-[90%] ${
                                        product.slug === "gymnastic-rings"
                                          ? equipmentImageFitClass(product.slug)
                                          : "object-contain"
                                      }`}
                                    />
                                  ) : (
                                    <span className="text-[10px] text-slate-400">—</span>
                                  )}
                                </span>
                              </span>
                            );
                          })}
                        </span>
                      ) : (
                        <span
                          className={`grid h-[4.5rem] w-[4.5rem] shrink-0 place-items-center rounded-xl ring-1 sm:h-20 sm:w-20 ${
                            on ? ui.tintSelected : ui.tint
                          }`}
                        >
                          {(() => {
                            const slug = group.slugs[0];
                            const src = imageFor(slug);
                            return src ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={src}
                                alt=""
                                className={`max-h-[88%] max-w-[88%] ${
                                  slug === "gymnastic-rings"
                                    ? equipmentImageFitClass(slug)
                                    : "object-contain"
                                }`}
                              />
                            ) : (
                              <span className="text-xs text-slate-400">—</span>
                            );
                          })()}
                        </span>
                      )}

                      <span className="min-w-0 flex-1 pr-1">
                        <span className="flex flex-wrap items-center gap-1.5">
                          <span className={`badge ${ui.badge}`}>{ui.difficulty}</span>
                        </span>
                        <span className="mt-1.5 block text-[15px] font-bold leading-snug text-slate-900">
                          {group.label_vi}
                        </span>
                        <span className="mt-0.5 block text-xs leading-relaxed text-slate-500">
                          {ui.hint}
                        </span>
                      </span>

                      <span
                        className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold transition ${
                          on ? ui.checkSelected : "bg-white text-transparent ring-2 ring-slate-300"
                        }`}
                        aria-hidden
                      >
                        ✓
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="flex shrink-0 gap-2 border-t border-slate-100 bg-slate-50/80 px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-50"
          >
            Huỷ
          </button>
          <button
            type="button"
            onClick={confirm}
            className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white shadow-soft hover:bg-brand-600"
          >
            {selectedGroupCount > 0 ? "Xong · đã chọn" : "Xong"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
