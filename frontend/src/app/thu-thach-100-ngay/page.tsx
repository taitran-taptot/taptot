import Challenge100Landing from "@/components/Challenge100Landing";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Thử thách 100 ngày${BRAND_TITLE_SUFFIX}`,
  description:
    "Cam kết 14 tuần với TAPTOT: lịch tập và ăn đổi theo ba giai đoạn, tuần nhẹ để hồi phục.",
};

export default function Challenge100Page() {
  return (
    <section className="py-2 sm:py-4">
      <Challenge100Landing />
    </section>
  );
}
