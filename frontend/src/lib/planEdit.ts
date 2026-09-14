export function planAccountEditPath(
  planId: number,
  q?: { week?: number; day?: number; swap?: number },
): string {
  const params = new URLSearchParams();
  if (q?.week != null && q.week > 0) params.set("week", String(q.week));
  if (q?.day != null && q.day > 0) params.set("day", String(q.day));
  if (q?.swap != null && q.swap > 0) params.set("swap", String(q.swap));
  const qs = params.toString();
  return qs ? `/tai-khoan/lich/${planId}?${qs}` : `/tai-khoan/lich/${planId}`;
}

export function planAccountEditLoginPath(
  planId: number,
  q?: { week?: number; day?: number; swap?: number },
): string {
  return `/dang-nhap?next=${encodeURIComponent(planAccountEditPath(planId, q))}`;
}
