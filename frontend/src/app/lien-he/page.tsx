import BrandHero from "@/components/BrandHero";
import FeaturedTrainerIntro from "@/components/FeaturedTrainerIntro";
import { fetchSitePageMedia } from "@/lib/sitePageMedia";

export const metadata = {
  title: "Bắt đầu hành trình với HLV — TAPTOT",
  description:
    "Đăng ký tư vấn huấn luyện viên TAPTOT — để lại thông tin hoặc liên hệ Facebook, email, Zalo.",
};

export default async function ContactPage() {
  const media = await fetchSitePageMedia();
  return (
    <section className="mx-auto w-full space-y-10 py-2 sm:py-4 lg:max-w-4xl">
      <BrandHero title="LIÊN HỆ" />
      <FeaturedTrainerIntro photoSrc={media.contact_trainer_image_url} />
    </section>
  );
}
