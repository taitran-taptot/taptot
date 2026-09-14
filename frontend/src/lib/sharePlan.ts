import type { PlanDetail } from "./plansApi";
import { BRAND_NAME } from "./brand";

export function planShareUrl(token: string, origin?: string): string {
  const base =
    origin ||
    (typeof window !== "undefined" ? window.location.origin : "");
  return `${base}/lich/${token}`;
}

export function buildShareMessage(
  plan: Pick<PlanDetail, "title_vi" | "target_calories" | "days">,
  absoluteUrl: string,
): string {
  const dayCount = plan.days?.length ?? 0;
  const lines = [`🏋️ Lịch tập ${BRAND_NAME}: ${plan.title_vi}`];
  const meta: string[] = [];
  if (dayCount > 0) meta.push(`📅 ${dayCount} buổi`);
  if (plan.target_calories != null) meta.push(`🔥 ~${plan.target_calories} kcal/ngày`);
  if (meta.length) lines.push(meta.join(" · "));
  lines.push("👉 Xem chi tiết & tập theo lịch:");
  lines.push(absoluteUrl);
  return lines.join("\n");
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export async function sharePlanNative(opts: {
  title: string;
  text: string;
  url: string;
}): Promise<"shared" | "copied" | "failed"> {
  if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
    try {
      await navigator.share({
        title: opts.title,
        text: opts.text,
        url: opts.url,
      });
      return "shared";
    } catch {
      // user cancelled or share failed — fall through to copy
    }
  }
  const ok = await copyText(opts.text);
  return ok ? "copied" : "failed";
}

/** YouTube watch/short/youtu.be → embed URL, or null. */
export function youtubeEmbedUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    let id: string | null = null;
    if (u.hostname.includes("youtu.be")) {
      id = u.pathname.replace(/^\//, "").split("/")[0] || null;
    } else if (u.hostname.includes("youtube.com")) {
      if (u.pathname.startsWith("/embed/")) {
        id = u.pathname.split("/")[2] || null;
      } else {
        id = u.searchParams.get("v");
      }
    }
    if (id && /^[\w-]{6,}$/.test(id)) {
      return `https://www.youtube.com/embed/${id}?mute=1`;
    }
  } catch {
    return null;
  }
  return null;
}

export function isDirectVideoUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  return /\.(mp4|webm|ogg)(\?|$)/i.test(url);
}
