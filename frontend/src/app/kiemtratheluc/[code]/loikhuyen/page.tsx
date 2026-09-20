import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import FitnessAdviceView from "@/components/fitness-test/FitnessAdviceView";
import { formatGiftCodeInput } from "@/lib/giftCode";
import { FITNESS_TEST_GUEST_SLUG } from "@/lib/fitness-tracker/session/offers";

export const metadata = {
  title: `Lời khuyên thể lực${BRAND_TITLE_SUFFIX}`,
};

type PageProps = {
  params: Promise<{ code: string }>;
  searchParams: Promise<{ from?: string }>;
};

export default async function LoiKhuyenPage({ params, searchParams }: PageProps) {
  const { code } = await params;
  const query = await searchParams;
  const raw = decodeURIComponent(code);
  const guest = raw.toLowerCase() === FITNESS_TEST_GUEST_SLUG;
  return (
    <FitnessAdviceView
      code={guest ? FITNESS_TEST_GUEST_SLUG : formatGiftCodeInput(raw)}
      from={query.from}
    />
  );
}
