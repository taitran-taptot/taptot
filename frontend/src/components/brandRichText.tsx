import type { ReactNode } from "react";
import BrandWordmark from "@/components/BrandWordmark";

const BRAND_RE = /\bTAPTOT\b(?!-)/g;

/** Inline body-friendly wordmark so mid-sentence brand matches surrounding text size. */
const DEFAULT_WORDMARK_CLASS = "font-serif font-semibold text-[1em]";

/**
 * Replace whole-word TAPTOT in a string with the colored BrandWordmark.
 * Leaves order codes like TAPTOT-xxxxx untouched (no word boundary after T).
 */
export function brandRichText(
  text: string,
  wordmarkClassName: string = DEFAULT_WORDMARK_CLASS,
): ReactNode {
  const parts = text.split(BRAND_RE);
  if (parts.length === 1) return text;

  const nodes: ReactNode[] = [];
  let matchIndex = 0;
  for (let i = 0; i < parts.length; i++) {
    if (parts[i]) nodes.push(parts[i]);
    if (i < parts.length - 1) {
      nodes.push(
        <BrandWordmark
          key={`brand-${matchIndex++}`}
          className={wordmarkClassName}
        />,
      );
    }
  }
  return nodes.length === 1 ? nodes[0] : <>{nodes}</>;
}
