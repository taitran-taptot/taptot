"use client";

import { useId } from "react";
import { BRAND_NAME, BRAND_T_FIRST, BRAND_T_SECOND } from "@/lib/brand";

/** Joined TT: one shape, greens blend across the shared bar. */
export default function BrandMark({ className = "h-9 w-9" }: { className?: string }) {
  const uid = useId();
  const gradId = `tt-mark-blend-${uid}`;

  return (
    <svg
      viewBox="0 0 40 40"
      width={36}
      height={36}
      preserveAspectRatio="xMidYMid meet"
      className={`block shrink-0 ${className}`}
      role="img"
      aria-label={BRAND_NAME}
    >
      <defs>
        <linearGradient id={gradId} x1="6" y1="11" x2="34" y2="11" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor={BRAND_T_FIRST} />
          <stop offset="36%" stopColor={BRAND_T_FIRST} />
          <stop offset="64%" stopColor={BRAND_T_SECOND} />
          <stop offset="100%" stopColor={BRAND_T_SECOND} />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="10" fill="#FFFFFF" />
      <path
        fill={`url(#${gradId})`}
        d="M7.4 8H32.6A1.4 1.4 0 0 1 34 9.4v3.2A1.4 1.4 0 0 1 32.6 14H29.5v16.9a1.6 1.6 0 0 1-1.6 1.6h-1.8a1.6 1.6 0 0 1-1.6-1.6V14H15.5v16.9a1.6 1.6 0 0 1-1.6 1.6h-1.8a1.6 1.6 0 0 1-1.6-1.6V14H7.4A1.4 1.4 0 0 1 6 12.6V9.4A1.4 1.4 0 0 1 7.4 8Z"
      />
    </svg>
  );
}
