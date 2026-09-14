import Link from "next/link";
import { publicEquipmentImage } from "@/lib/equipmentCatalog";
import { mediaUrl } from "@/lib/labels";

const FEATURED_EQUIPMENT = [
  { slug: "resistance-band", label: "Dây kháng lực" },
  { slug: "dumbbell", label: "Tạ đơn" },
  { slug: "pull-up-bar", label: "Xà đơn" },
] as const;

export default function HomeProductMockup() {
  return (
    <div className="relative mx-auto w-full max-w-[560px] py-3 sm:py-8">
      <div
        className="absolute inset-x-[6%] top-[8%] aspect-square rounded-full bg-brand-100/60"
        aria-hidden
      />
      <div
        className="absolute right-[3%] top-[4%] h-20 w-20 rounded-full border border-brand-200/70"
        aria-hidden
      />

      <div className="relative rounded-[2rem] border border-white/80 bg-white/85 p-4 shadow-[0_30px_70px_-36px_rgba(15,118,110,0.5)] backdrop-blur sm:p-6">
        <p className="text-center text-sm font-semibold text-slate-600">
          Chọn món bạn cần để bắt đầu tại nhà
        </p>

        <div className="mt-4 grid grid-cols-3 gap-2.5 sm:gap-4">
          {FEATURED_EQUIPMENT.map((item) => {
            const image = mediaUrl(publicEquipmentImage(item.slug));
            return (
              <div
                key={item.slug}
                className="rounded-2xl border border-slate-100 bg-white p-2.5 text-center shadow-sm sm:p-3"
              >
                <div className="grid aspect-square place-items-center rounded-xl bg-slate-50 p-1.5">
                  {image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={image}
                      alt={item.label}
                      className="h-full w-full object-contain"
                    />
                  ) : null}
                </div>
                <p className="mt-2 text-[10px] font-bold text-slate-700 sm:text-xs">
                  {item.label}
                </p>
              </div>
            );
          })}
        </div>

        <div className="relative mt-4 overflow-hidden rounded-2xl bg-brand-600 px-5 py-5 text-white sm:px-6 sm:py-6">
          <div
            className="absolute -right-8 -top-8 h-28 w-28 rounded-full border-[18px] border-white/10"
            aria-hidden
          />
          <div className="relative">
            <p className="text-sm font-extrabold text-white">
              TAPTOT <span className="font-semibold text-brand-100">tặng bạn</span>
            </p>
            <h2 className="mt-2 text-xl font-extrabold leading-tight tracking-tight sm:text-2xl">
              Lộ trình tập và ăn 100 ngày
            </h2>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-brand-50">
              Nhận hàng, quét mã trên tem và tạo lộ trình phù hợp với thể trạng của bạn.
            </p>

            <div className="mt-4 flex flex-col gap-3 border-t border-white/20 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs font-semibold text-brand-100">
                1 sản phẩm · 1 mã trên tem
              </p>
              <Link
                href="/mua-dung-cu?from=hero"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-extrabold text-brand-700 shadow-sm transition hover:-translate-y-0.5 hover:bg-brand-50"
              >
                Chọn dụng cụ phù hợp
                <span aria-hidden>→</span>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
