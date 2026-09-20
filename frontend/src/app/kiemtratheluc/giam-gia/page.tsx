import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import PushupDiscountSession from "@/components/fitness-test/PushupDiscountSession";

export const metadata = {
  title: `Chống đẩy giảm giá${BRAND_TITLE_SUFFIX}`,
};

export default function GiamGiaPage() {
  return <PushupDiscountSession />;
}
