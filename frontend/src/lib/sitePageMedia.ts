import { apiFetch } from "./http";
import { mediaUrl, storedMediaPath } from "./labels";

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
  if (raw.startsWith("/") && !raw.startsWith("/media/")) return raw;
  return mediaUrl(raw) || raw;
}

function withStoredImagePaths(media: SitePageMedia): SitePageMedia {
  return {
    ...media,
    service_lo_trinh_image_url: storedMediaPath(media.service_lo_trinh_image_url),
    service_dung_cu_image_url: storedMediaPath(media.service_dung_cu_image_url),
    service_hlv_image_url: storedMediaPath(media.service_hlv_image_url),
    about_hero_image_url: storedMediaPath(media.about_hero_image_url),
    about_founder_image_url: storedMediaPath(media.about_founder_image_url),
    about_trainer_image_url: storedMediaPath(media.about_trainer_image_url),
    contact_trainer_image_url: storedMediaPath(media.contact_trainer_image_url),
  };
}

export async function fetchSitePageMedia(): Promise<SitePageMedia> {
  try {
    const data = await apiFetch<Partial<SitePageMedia>>("/site/page-media");
    return withStoredImagePaths({ ...SITE_PAGE_MEDIA_DEFAULTS, ...data });
  } catch {
    return SITE_PAGE_MEDIA_DEFAULTS;
  }
}

export function patchSitePageMedia(body: Record<string, string>) {
  const payload = { ...body };
  for (const [key, value] of Object.entries(payload)) {
    if (key.endsWith("_image_url")) payload[key] = storedMediaPath(value);
  }
  return apiFetch<SitePageMedia>("/admin/site/page-media", { method: "PATCH", body: JSON.stringify(payload) }, {
    auth: true,
  });
}
