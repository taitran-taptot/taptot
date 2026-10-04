// Lightweight markdown -> HTML for trusted, short article content.
// Supports: # h1, ## h2, ### h3, - / * lists, 1. ordered lists, **bold**,
// _italic_, [text](url) links, > blockquotes, and ![alt](url|pending:key) figures.

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escAttr(s: string): string {
  return esc(s).replace(/"/g, "&quot;");
}

function decodeEntities(s: string): string {
  return s
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function inline(s: string): string {
  const linked = esc(s).replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="font-medium text-brand-600 underline decoration-brand-200 underline-offset-2 hover:text-brand-700">$1</a>',
  );
  return linked
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>')
    .replace(/_([^_]+)_/g, "<em>$1</em>");
}

function isSafeMediaUrl(url: string): boolean {
  if (url.startsWith("/media/")) return true;
  if (/^https?:\/\//i.test(url)) {
    try {
      const u = new URL(url);
      return u.protocol === "http:" || u.protocol === "https:";
    } catch {
      return false;
    }
  }
  return false;
}

function renderFigure(alt: string, url: string): string {
  const caption = esc(alt);
  const pending = /^pending:([a-z0-9][a-z0-9_-]*)$/i.exec(url.trim());
  if (pending) {
    const key = escAttr(pending[1]);
    return (
      `<figure class="my-4 overflow-hidden rounded-lg border border-dashed border-slate-300 bg-[#F8F9FA]" data-pending-image="${key}">` +
      `<div class="flex min-h-[180px] flex-col items-center justify-center gap-2 px-4 py-8 text-center">` +
      `<span class="text-xs font-medium uppercase tracking-wide text-slate-400">Ảnh minh họa</span>` +
      `<span class="max-w-sm text-sm font-medium text-slate-600">${caption}</span>` +
      `</div>` +
      `<figcaption class="border-t border-dashed border-slate-200 px-3 py-2 text-center text-xs text-slate-500">${caption}</figcaption>` +
      `</figure>`
    );
  }
  if (!isSafeMediaUrl(url)) {
    return `<p class="my-2 leading-relaxed text-slate-600">${caption}</p>`;
  }
  const src = escAttr(url);
  return (
    `<figure class="my-4 overflow-hidden rounded-lg bg-[#F8F9FA]">` +
    `<img src="${src}" alt="${escAttr(alt)}" class="mx-auto h-auto w-full max-w-3xl object-contain" loading="lazy" decoding="async" />` +
    (alt
      ? `<figcaption class="px-3 py-2 text-center text-xs text-slate-500">${caption}</figcaption>`
      : "") +
    `</figure>`
  );
}

export function renderMarkdown(md: string): string {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const html: string[] = [];
  let list: "ul" | "ol" | null = null;

  const closeList = () => {
    if (list) {
      html.push(`</${list}>`);
      list = null;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      closeList();
      continue;
    }

    const figure = /^!\[([^\]]*)\]\((.+)\)$/.exec(line);
    if (figure) {
      closeList();
      html.push(renderFigure(figure[1], figure[2].trim()));
      continue;
    }

    const h = /^(#{1,3})\s+(.*)$/.exec(line);
    if (h) {
      closeList();
      const level = h[1].length;
      const cls =
        level === 1
          ? "type-display mt-1 mb-3"
          : level === 2
            ? "type-title mt-5 mb-2"
            : "mt-4 mb-1.5 font-semibold";
      html.push(`<h${level} class="${cls}">${inline(h[2])}</h${level}>`);
      continue;
    }

    if (line.startsWith("> ")) {
      closeList();
      html.push(
        `<blockquote class="my-3 border-l-4 border-brand-200 bg-slate-50 px-3 py-2 text-sm leading-relaxed text-slate-600">${inline(line.slice(2))}</blockquote>`,
      );
      continue;
    }

    const ol = /^\d+\.\s+(.*)$/.exec(line);
    if (ol) {
      if (list !== "ol") {
        closeList();
        list = "ol";
        html.push('<ol class="my-2 list-decimal space-y-1 pl-5">');
      }
      html.push(`<li>${inline(ol[1])}</li>`);
      continue;
    }

    const ul = /^[-*]\s+(.*)$/.exec(line);
    if (ul) {
      if (list !== "ul") {
        closeList();
        list = "ul";
        html.push('<ul class="my-2 list-disc space-y-1 pl-5">');
      }
      html.push(`<li>${inline(ul[1])}</li>`);
      continue;
    }

    closeList();
    html.push(`<p class="my-2 leading-relaxed text-slate-600">${inline(line)}</p>`);
  }
  closeList();
  return html.join("");
}

function stripTags(s: string): string {
  return decodeEntities(s.replace(/<[^>]+>/g, "")).replace(/\s+/g, " ").trim();
}

function inlineHtmlToMd(s: string): string {
  let out = s.replace(/\u00a0/g, " ");
  for (let i = 0; i < 8; i += 1) {
    const next = out
      .replace(/<(em|i)\b[^>]*>([\s\S]*?)<\/\1>/gi, (_m, _t, inner) => `_${inner}_`)
      .replace(/<(strong|b)\b[^>]*>([\s\S]*?)<\/\1>/gi, (_m, _t, inner) => `**${inner}**`)
      .replace(
        /<span\b[^>]*style="[^"]*font-style:\s*italic[^"]*"[^>]*>([\s\S]*?)<\/span>/gi,
        (_m, inner) => `_${inner}_`,
      )
      .replace(
        /<span\b[^>]*style="[^"]*font-weight:\s*(bold|[6-9]00)[^"]*"[^>]*>([\s\S]*?)<\/span>/gi,
        (_m, _w, inner) => `**${inner}**`,
      );
    if (next === out) break;
    out = next;
  }
  return stripTags(out);
}

function listItems(inner: string): string[] {
  return [...inner.matchAll(/<li\b[^>]*>([\s\S]*?)<\/li>/gi)].map((m) => inlineHtmlToMd(m[1]));
}

/** Convert contentEditable / pasted HTML to the markdown subset `renderMarkdown` understands. */
export function htmlToMarkdown(html: string): string {
  let s = (html || "").replace(/\r\n/g, "\n").replace(/\u00a0/g, " ");
  s = s.replace(/<ul\b[^>]*>([\s\S]*?)<\/ul>/gi, (_m, inner) => {
    const items = listItems(inner).filter(Boolean);
    return items.length ? `${items.map((t) => `- ${t}`).join("\n")}\n` : "";
  });
  s = s.replace(/<ol\b[^>]*>([\s\S]*?)<\/ol>/gi, (_m, inner) => {
    const items = listItems(inner).filter(Boolean);
    return items.length ? `${items.map((t, i) => `${i + 1}. ${t}`).join("\n")}\n` : "";
  });
  s = s.replace(/<h([1-3])\b[^>]*>([\s\S]*?)<\/h\1>/gi, (_m, n, inner) => {
    const text = inlineHtmlToMd(inner);
    return text ? `${"#".repeat(Number(n))} ${text}\n` : "";
  });
  s = s.replace(/<blockquote\b[^>]*>([\s\S]*?)<\/blockquote>/gi, (_m, inner) => {
    const text = inlineHtmlToMd(inner);
    return text ? `> ${text}\n` : "";
  });
  s = s.replace(/<br\s*\/?>/gi, "\n");
  s = s.replace(/<\/(p|div|h[1-3])>/gi, "\n");
  s = s.replace(/<(p|div)[^>]*>/gi, "");
  s = s
    .split("\n")
    .map((line) => inlineHtmlToMd(line))
    .join("\n");
  return s.replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
}
