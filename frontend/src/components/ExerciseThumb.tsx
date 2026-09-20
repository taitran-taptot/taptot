"use client";

import { useRef, useState } from "react";
import { bodyEmoji, gifUrl, mediaUrl } from "@/lib/labels";

function pickThumbSrc(
  gif?: string | null,
  image?: string | null,
  video?: string | null,
): string | null {
  const paths = [image, gif].filter(Boolean) as string[];
  for (const rel of paths) {
    if (/\.webp(\?|$)/i.test(rel) || rel.includes("posters/")) {
      const poster = mediaUrl(rel);
      if (poster) return poster;
    }
  }
  for (const rel of paths) {
    const src = gifUrl(rel) || mediaUrl(rel);
    if (src) return src;
  }
  const vidPoster = gifUrl(video) || mediaUrl(video);
  return vidPoster;
}

/**
 * Thumbnail sized by `className` (e.g. h-14 w-14).
 * Do not force w-full on the root — that breaks flex cards in plan picker.
 */
export default function ExerciseThumb({
  gif,
  image,
  video,
  bodyPart,
  className = "h-40 w-full",
  emojiSize = "text-5xl",
  alt = "",
  eager = false,
}: {
  gif?: string | null;
  image?: string | null;
  video?: string | null;
  bodyPart: string;
  className?: string;
  emojiSize?: string;
  alt?: string;
  eager?: boolean;
}) {
  const src = pickThumbSrc(gif, image, video);
  const emoji = bodyEmoji[bodyPart] || "🏋️";
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const loadedSrc = useRef<string | null>(null);
  const showPhoto = Boolean(src) && failedSrc !== src;

  return (
    <div
      className={`relative overflow-hidden bg-gradient-to-br from-brand-50 to-slate-100 ${className}`}
    >
      {src ? (
        // Keep <img> mounted so a re-render cannot abort the request and hide the photo.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={alt || bodyPart || "Hình bài tập"}
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          onLoad={() => {
            loadedSrc.current = src;
            setFailedSrc((prev) => (prev === src ? null : prev));
          }}
          onError={() => {
            if (loadedSrc.current === src) return;
            setFailedSrc(src);
          }}
          className={`h-full w-full object-cover ${showPhoto ? "" : "invisible"}`}
        />
      ) : null}
      {!showPhoto && (
        <div className={`absolute inset-0 grid place-items-center ${emojiSize}`}>{emoji}</div>
      )}
    </div>
  );
}
