import FoodLibrary from "@/components/FoodLibrary";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Món truyền thống Việt${BRAND_TITLE_SUFFIX}`,
  description:
    "Phở, bún, cơm tấm và món Việt theo tỉnh — tra calo từng suất, xem trên bản đồ.",
};

export default function MonTruyenThongPage() {
  return <FoodLibrary />;
}
