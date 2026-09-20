"use client";

import Link from "next/link";
import { WIZARD_EQUIPMENT_GROUPS, publicEquipmentImage } from "@/lib/equipmentCatalog";
import { EQUIPMENT_GROUP_UI } from "@/lib/equipmentGroupUi";
import { mediaUrl } from "@/lib/labels";

export default function EquipmentNodePanel() {
  return (
    <aside className="flex flex-col rounded-2xl border border-teal-100 bg-white/95 p-4 shadow-sm sm:p-5">
      <div className="overflow-hidden rounded-xl bg-gradient-to-br from-teal-100 via-emerald-50 to-lime-100 p-2.5 sm:p-3">
        <ul className="grid grid-cols-3 gap-2">
          {WIZARD_EQUIPMENT_GROUPS.map((group) => {
            const ui = EQUIPMENT_GROUP_UI[group.id];
            const thumbs = group.products?.length
              ? group.products
              : [{ slug: group.slugs[0], label_vi: group.label_vi }];
            return (
              <li
                key={group.id}
                className={`flex flex-col items-center rounded-xl bg-white/90 px-1.5 pb-2 pt-1.5 ring-1 ${ui.tint}`}
              >
                <span className="relative aspect-square w-full">
                  <span className="absolute inset-0 flex items-center justify-center gap-0.5 px-1">
                    {thumbs.map((item) => {
                      const src = mediaUrl(publicEquipmentImage(item.slug));
                      return src ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          key={item.slug}
                          src={src}
                          alt=""
                          className={`h-[86%] object-contain ${thumbs.length > 1 ? "w-[46%]" : "w-[86%]"}`}
                        />
                      ) : (
                        <span key={item.slug} className="text-xs text-slate-400">
                          —
                        </span>
                      );
                    })}
                  </span>
                </span>
                <span className={`badge ${ui.badge}`}>{ui.difficulty}</span>
                <span className="mt-1 text-center text-[10px] font-extrabold leading-tight text-slate-900 sm:text-xs">
                  {group.label_vi}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      <p className="mt-4 text-[11px] font-bold tracking-wide text-teal-700 uppercase">Tham khảo</p>
      <h2 className="mt-1 text-xl font-extrabold text-slate-900">Dụng cụ</h2>
      <p className="mt-1 text-sm text-slate-500">Cải thiện hiệu quả buổi tập</p>
      <p className="mt-3 text-sm leading-relaxed text-slate-600">
        Dụng cụ phù hợp giúp buổi tập chắc hơn, đỡ nhàm, và tiến bộ nhanh hơn so với tập không đồ.
      </p>
      <div className="mt-5">
        <Link
          href="/mua-dung-cu"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex w-full items-center justify-center rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600"
        >
          Tiếp tục
        </Link>
      </div>
    </aside>
  );
}
