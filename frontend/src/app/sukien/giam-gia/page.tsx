import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import PushupDiscountSession from "@/components/fitness-test/PushupDiscountSession";

export const metadata = {
  title: `Chống đẩy giảm giá${BRAND_TITLE_SUFFIX}`,
};

export default function SukienGiamGiaPage() {
  return (
    <section className="mx-auto w-full lg:max-w-4xl">
      <PushupDiscountSession />
    </section>
  );
}
