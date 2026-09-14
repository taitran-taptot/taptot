"use client";

import { useState } from "react";
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
}: {
  gif?: string | null;
  image?: string | null;
  video?: string | null;
  bodyPart: string;
  className?: string;
  emojiSize?: string;
  alt?: string;
}) {
  const [failed, setFailed] = useState(false);
  const src = pickThumbSrc(gif, image, video);
  const emoji = bodyEmoji[bodyPart] || "🏋️";

  if (!src || failed) {
    return (
      <div
        className={`grid place-items-center overflow-hidden bg-gradient-to-br from-brand-50 to-slate-100 ${emojiSize} ${className}`}
      >
        {emoji}
      </div>
    );
  }

  return (
    <div className={`overflow-hidden bg-slate-100 ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt || bodyPart || "Hình bài tập"}
        loading="lazy"
        onError={() => setFailed(true)}
        className="h-full w-full object-cover"
      />
    </div>
  );
}
