import { apiFetch } from "./http";
import { mediaUrl, storedMediaPath } from "./labels";

export const DEFAULT_YOUTUBE_ID = "EngW7tLk6R8";
export const SUCCESS_STORY_COUNT = 7;
export const DEFAULT_SUCCESS_LOGO = "/brand/taptot-logo-vuong.png";

export type SuccessStory = {
  image_url: string;
  logo_url: string;
  name: string;
  occupation: string;
  quote: string;
};

const SAMPLE_PEOPLE: Array<Pick<SuccessStory, "name" | "occupation" | "quote">> = [
  { name: "Lan Phương", occupation: "Nhân viên văn phòng", quote: "Lịch vừa sức nên tôi đi hết 100 ngày." },
  { name: "Minh Khoa", occupation: "Kỹ sư", quote: "Tập ở nhà vẫn thấy người chắc hơn từng tuần." },
  { name: "Hà My", occupation: "Giáo viên", quote: "Vẫn ăn món quen mà cân nặng giảm đều." },
  { name: "Quốc Bảo", occupation: "Tài xế", quote: "Đau lưng đỡ hẳn sau khi tập đúng cách." },
  { name: "Thu Trang", occupation: "Mẹ bỉm sữa", quote: "Mỗi buổi khoảng 30 phút, tôi vẫn theo được." },
  { name: "Đức Anh", occupation: "Sinh viên", quote: "Nhìn nhật ký mới thấy mình tiến bộ rõ." },
  { name: "Ngọc Anh", occupation: "Chủ quán", quote: "Không cần phòng gym vẫn hoàn thành lịch." },
];

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
  success_stories: SuccessStory[];
  success_stories_visible: boolean;
};

const STORY_PHOTOS = ["/brand/taptot-bia-vuong.png", "/brand/taptot-logo-vuong.png"];

export function defaultSuccessStories(): SuccessStory[] {
  return SAMPLE_PEOPLE.map((person, index) => ({
    image_url: STORY_PHOTOS[index % STORY_PHOTOS.length],
    logo_url: DEFAULT_SUCCESS_LOGO,
    ...person,
  }));
}

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
  success_stories: defaultSuccessStories(),
  success_stories_visible: true,
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

function storyFromPartial(raw: Partial<SuccessStory> | undefined, index: number): SuccessStory {
  const fallback = defaultSuccessStories()[index];
  return {
    image_url: storedMediaPath(raw?.image_url ?? fallback.image_url),
    logo_url: storedMediaPath(raw?.logo_url ?? fallback.logo_url),
    name: raw?.name ?? "",
    occupation: raw?.occupation ?? "",
    quote: raw?.quote ?? "",
  };
}

function withSampleCopy(stories: SuccessStory[]): SuccessStory[] {
  const hasCopy = stories.some((story) => story.name.trim() || story.occupation.trim() || story.quote.trim());
  if (hasCopy) return stories;
  return defaultSuccessStories().map((sample, index) => ({
    ...sample,
    image_url: stories[index]?.image_url || sample.image_url,
    logo_url: stories[index]?.logo_url || sample.logo_url,
  }));
}

function withStoredImagePaths(media: SitePageMedia): SitePageMedia {
  const incoming = Array.isArray(media.success_stories) ? media.success_stories : [];
  return {
    ...media,
    service_lo_trinh_image_url: storedMediaPath(media.service_lo_trinh_image_url),
    service_dung_cu_image_url: storedMediaPath(media.service_dung_cu_image_url),
    service_hlv_image_url: storedMediaPath(media.service_hlv_image_url),
    about_hero_image_url: storedMediaPath(media.about_hero_image_url),
    about_founder_image_url: storedMediaPath(media.about_founder_image_url),
    about_trainer_image_url: storedMediaPath(media.about_trainer_image_url),
    contact_trainer_image_url: storedMediaPath(media.contact_trainer_image_url),
    success_stories: withSampleCopy(
      Array.from({ length: SUCCESS_STORY_COUNT }, (_, index) => storyFromPartial(incoming[index], index)),
    ),
    success_stories_visible: media.success_stories_visible !== false,
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

export function patchSitePageMedia(
  body: Partial<Omit<SitePageMedia, "success_stories">> & {
    success_stories?: SuccessStory[];
    home_challenge_youtube?: string;
    shop_guide_youtube?: string;
  },
) {
  const payload: Record<string, unknown> = { ...body };
  for (const [key, value] of Object.entries(payload)) {
    if (typeof value === "string" && key.endsWith("_image_url")) payload[key] = storedMediaPath(value);
  }
  if (body.success_stories) {
    payload.success_stories = body.success_stories.map((story) => ({
      ...story,
      image_url: storedMediaPath(story.image_url),
      logo_url: storedMediaPath(story.logo_url),
    }));
  }
  return apiFetch<SitePageMedia>("/admin/site/page-media", { method: "PATCH", body: JSON.stringify(payload) }, {
    auth: true,
  });
}
