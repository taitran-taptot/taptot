let pending: ((ok: boolean) => void) | null = null;

export function requestAdminStepUp(): Promise<boolean> {
  if (typeof window === "undefined") return Promise.resolve(false);
  if (pending) return Promise.resolve(false);
  return new Promise((resolve) => {
    pending = resolve;
    window.dispatchEvent(new CustomEvent("taptot:admin-step-up"));
  });
}

export function completeAdminStepUp(ok: boolean) {
  pending?.(ok);
  pending = null;
}
