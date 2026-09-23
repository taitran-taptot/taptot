import Landing from "@/components/Landing";
import TaptotIntro, { TAPTOT_INTRO_BOOT_SCRIPT } from "@/components/TaptotIntro";

export default function Home() {
  return (
    <>
      <script dangerouslySetInnerHTML={{ __html: TAPTOT_INTRO_BOOT_SCRIPT }} />
      <TaptotIntro />
      <Landing />
    </>
  );
}
