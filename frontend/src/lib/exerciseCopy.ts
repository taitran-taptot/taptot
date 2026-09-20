/** Split catalog coaching copy into readable lines for the exercise sheet. */

export function splitCoachLines(raw?: string | null): string[] {
  if (!raw) return [];
  const text = raw.trim();
  if (!text) return [];

  if (text.startsWith("[")) {
    const parsed = parseListString(text);
    if (parsed.length) return parsed;
  }

  return text
    .split(/\n+/)
    .map((line) => line.replace(/^[-•*\d]+[.)]\s*/, "").trim())
    .filter(Boolean);
}

function parseListString(text: string): string[] {
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      return parsed.map((item) => String(item).trim()).filter(Boolean);
    }
  } catch {
    // Python list repr uses single quotes.
  }
  const quoted = [...text.matchAll(/'((?:\\'|[^'])*)'/g)].map((match) =>
    match[1].replace(/\\'/g, "'").trim(),
  );
  if (quoted.length) return quoted.filter(Boolean);
  return [...text.matchAll(/"((?:\\"|[^"])*)"/g)]
    .map((match) => match[1].trim())
    .filter(Boolean);
}
