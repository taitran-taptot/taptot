// Lightweight markdown -> HTML for trusted, short article content.
// Supports: # h1, ## h2, ### h3, - / * lists, 1. ordered lists, **bold**,
// [text](url) links, and > blockquotes.

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inline(s: string): string {
  const linked = esc(s).replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="font-medium text-brand-600 underline decoration-brand-200 underline-offset-2 hover:text-brand-700">$1</a>',
  );
    return linked.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>');
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
