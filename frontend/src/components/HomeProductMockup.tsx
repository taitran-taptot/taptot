import { publicEquipmentImage } from "@/lib/equipmentCatalog";
import { mediaUrl } from "@/lib/labels";

const FEATURED_EQUIPMENT = [
  { slug: "resistance-band", label: "Dây kháng lực", float: "home-float-a" },
  { slug: "dumbbell", label: "Tạ đơn", float: "home-float-b" },
  { slug: "pull-up-bar", label: "Xà đơn", float: "home-float-c" },
] as const;

export default function HomeProductMockup() {
  return (
    <div className="relative mx-auto min-h-[320px] w-full max-w-[540px] sm:min-h-[400px]">
      <div
        className="absolute inset-x-[8%] top-[4%] aspect-square rounded-full bg-gradient-to-br from-brand-50 via-emerald-50 to-white"
        aria-hidden
      />
      <div
        className="absolute right-[5%] top-[3%] h-16 w-16 rounded-full border border-brand-200/70 sm:h-24 sm:w-24"
        aria-hidden
      />
      <div
        className="absolute bottom-[9%] left-[12%] right-[8%] h-[14%] rounded-[50%] bg-brand-200/35 blur-xl"
        aria-hidden
      />

      {FEATURED_EQUIPMENT.map((item, index) => {
        const image = mediaUrl(publicEquipmentImage(item.slug));
        const position = [
          "left-[2%] top-[12%] z-10 w-[47%] -rotate-6 sm:left-[1%] sm:top-[8%]",
          "bottom-[5%] left-[27%] z-30 w-[48%] rotate-3 sm:bottom-[2%]",
          "right-[1%] top-[7%] z-20 w-[39%] rotate-2 sm:right-[2%] sm:top-[3%]",
        ][index];

        return image ? (
          <div key={item.slug} className={`absolute aspect-square ${position}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={image}
              alt={item.label}
              className={`${item.float} h-full w-full object-contain drop-shadow-[0_24px_22px_rgba(15,23,42,0.16)]`}
            />
          </div>
        ) : null;
      })}

      <div
        className="home-pulse-dot absolute bottom-[2%] right-[8%] h-3 w-3 rounded-full bg-brand-400/70 sm:h-4 sm:w-4"
        aria-hidden
      />
      <div
        className="home-pulse-dot absolute left-[17%] top-[4%] h-2 w-2 rounded-full bg-amber-300/80 sm:h-3 sm:w-3"
        aria-hidden
        style={{ animationDelay: "0.9s" }}
      />
      <div
        className="absolute bottom-[14%] left-[5%] h-10 w-10 rounded-full border border-brand-200/80 sm:h-14 sm:w-14"
        aria-hidden
      />
    </div>
  );
}
