import Landing from "@/components/Landing";
import TaptotIntro from "@/components/TaptotIntro";
import { fetchSitePageMedia } from "@/lib/sitePageMedia";

export default async function Home() {
  const media = await fetchSitePageMedia();
  return (
    <>
      <TaptotIntro />
      <Landing media={media} />
    </>
  );
}
