import Landing from "@/components/Landing";
import TaptotIntro, { TAPTOT_INTRO_BOOT_SCRIPT } from "@/components/TaptotIntro";
import { fetchSitePageMedia } from "@/lib/sitePageMedia";

export default async function Home() {
  const media = await fetchSitePageMedia();
  return (
    <>
      <script dangerouslySetInnerHTML={{ __html: TAPTOT_INTRO_BOOT_SCRIPT }} />
      <TaptotIntro />
      <Landing media={media} />
    </>
  );
}
