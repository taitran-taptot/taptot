import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import PlankDiscountSession from "@/components/fitness-test/PlankDiscountSession";

export const metadata = {
  title: `Plank giảm giá${BRAND_TITLE_SUFFIX}`,
};

export default function SukienPlankPage() {
  return (
    <section className="mx-auto w-full lg:max-w-4xl">
      <PlankDiscountSession />
    </section>
  );
}
