export function planPublicPath(plan: {
  share_url_path?: string | null;
  redeem_code?: string | null;
  share_token?: string | null;
}): string | null {
  if (plan.share_url_path) return plan.share_url_path;
  if (plan.redeem_code) return `/lich/${plan.redeem_code}`;
  if (plan.share_token) return `/lich/${plan.share_token}`;
  return null;
}

export function planShareUrl(tokenOrPath: string, origin?: string): string {
  const path = tokenOrPath.startsWith("/") ? tokenOrPath : `/lich/${tokenOrPath}`;
  const base =
    origin ||
    (typeof window !== "undefined" ? window.location.origin : "");
  return `${base}${path}`;
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
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

export function youtubeThumbnailUrl(url: string | null | undefined): string | null {
  const embed = youtubeEmbedUrl(url);
  if (!embed) return null;
  const id = embed.split("/embed/")[1]?.split("?")[0];
  if (!id) return null;
  return `https://i.ytimg.com/vi/${id}/mqdefault.jpg`;
}

export function isDirectVideoUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  return /\.(mp4|webm|ogg)(\?|$)/i.test(url);
}
