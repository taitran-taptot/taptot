import { apiFetch } from "./http";
import { mediaUrl } from "./labels";

export const DEFAULT_YOUTUBE_ID = "EngW7tLk6R8";

export type SitePageMedia = {
  home_challenge_youtube_id: string;
  shop_guide_youtube_id: string;
  service_lo_trinh_image_url: string;
  service_dung_cu_image_url: string;
  service_hlv_image_url: string;
  about_hero_image_url: string;
  about_founder_image_url: string;
  about_trainer_image_url: string;
  contact_trainer_image_url: string;
};

export const SITE_PAGE_MEDIA_DEFAULTS: SitePageMedia = {
  home_challenge_youtube_id: DEFAULT_YOUTUBE_ID,
  shop_guide_youtube_id: DEFAULT_YOUTUBE_ID,
  service_lo_trinh_image_url: "/home-lo-trinh.png",
  service_dung_cu_image_url: "/home-dung-cu.jpg",
  service_hlv_image_url: "/home-hlv.png",
  about_hero_image_url: "/hero-gym.jpg",
  about_founder_image_url: "/tran-tai.jpg",
  about_trainer_image_url: "",
  contact_trainer_image_url: "/hlv-nguyen-van-tien.jpg",
};

export function youtubeEmbedSrc(id: string): string {
  return `https://www.youtube-nocookie.com/embed/${id}`;
}

export function siteImageSrc(url: string | null | undefined): string {
  const raw = (url || "").trim();
  if (!raw) return "";
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith("/media/")) return raw;
  if (raw.startsWith("/")) return raw;
  return mediaUrl(raw) || raw;
}

export async function fetchSitePageMedia(): Promise<SitePageMedia> {
  try {
    const data = await apiFetch<Partial<SitePageMedia>>("/site/page-media");
    return { ...SITE_PAGE_MEDIA_DEFAULTS, ...data };
  } catch {
    return SITE_PAGE_MEDIA_DEFAULTS;
  }
}

export function patchSitePageMedia(body: Record<string, string>) {
  return apiFetch<SitePageMedia>("/admin/site/page-media", { method: "PATCH", body: JSON.stringify(body) }, {
    auth: true,
  });
}
