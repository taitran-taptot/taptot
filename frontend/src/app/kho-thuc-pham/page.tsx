import FoodHub from "@/components/FoodHub";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Kho thực phẩm${BRAND_TITLE_SUFFIX}`,
  description:
    "Thực phẩm, món truyền thống theo tỉnh và cách nấu món Việt quen — kho ăn uống TAPTOT.",
};

export default function KhoThucPhamPage() {
  return <FoodHub />;
}
