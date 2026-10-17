import BrandHero from "@/components/BrandHero";
import ContactTrainerForm from "@/components/ContactTrainerForm";
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
    <section className="space-y-10 py-2 sm:py-4">
      <BrandHero title="HLV" />
      <FeaturedTrainerIntro formHref="#dang-ky-hlv" photoSrc={media.contact_trainer_image_url} />
      <ContactTrainerForm />
    </section>
  );
}
