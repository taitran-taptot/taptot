import { Suspense } from "react";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import FitnessTestRoute from "@/components/fitness-test/FitnessTestRoute";

export const metadata = {
  title: `Bài test thể lực${BRAND_TITLE_SUFFIX}`,
};

type PageProps = {
  params: Promise<{ code: string }>;
  searchParams: Promise<{ goi?: string; gender?: string; from?: string }>;
};

export default async function FitnessTestCodePage({ params, searchParams }: PageProps) {
  const { code } = await params;
  const query = await searchParams;
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Đang tải…</p>}>
      <FitnessTestRoute code={code} goi={query.goi} gender={query.gender} from={query.from} />
    </Suspense>
  );
}
