import AboutPage from "@/components/AboutPage";
import { BRAND_NAME, BRAND_TITLE_SUFFIX } from "@/lib/brand";
import { fetchSitePageMedia } from "@/lib/sitePageMedia";

export const metadata = {
  title: `Về TAPTOT${BRAND_TITLE_SUFFIX}`,
  description: `${BRAND_NAME} giúp người Việt bắt đầu tập và ăn lành mạnh — lịch vừa sức, món quen, đồng hành khi bạn cần người kèm.`,
};

export default async function VeTaptotPage() {
  const media = await fetchSitePageMedia();
  return <AboutPage media={media} />;
}
