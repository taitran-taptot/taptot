import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import FitnessTestHub from "@/components/fitness-test/FitnessTestHub";

export const metadata = {
  title: `Sự kiện${BRAND_TITLE_SUFFIX}`,
  description: "Sự kiện TAPTOT đang diễn ra — chống đẩy giảm giá và các thử thách cộng đồng.",
};

export default function SukienPage() {
  return <FitnessTestHub />;
}
