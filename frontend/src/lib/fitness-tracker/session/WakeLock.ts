type WakeLockSentinelLike = { release: () => Promise<void> };

export class ScreenWakeLock {
  private sentinel: WakeLockSentinelLike | null = null;
  private onVis: (() => void) | null = null;

  async request(): Promise<void> {
    await this.acquire();
    if (typeof document === "undefined" || this.onVis) return;
    this.onVis = () => {
      if (document.visibilityState === "visible") void this.acquire();
    };
    document.addEventListener("visibilitychange", this.onVis);
  }

  private async acquire(): Promise<void> {
    if (typeof navigator === "undefined") return;
    const api = (navigator as Navigator & { wakeLock?: { request: (type: "screen") => Promise<WakeLockSentinelLike> } }).wakeLock;
    if (!api) return;
    try {
      this.sentinel = await api.request("screen");
    } catch {
      this.sentinel = null;
    }
  }

  async release(): Promise<void> {
    if (this.onVis && typeof document !== "undefined") {
      document.removeEventListener("visibilitychange", this.onVis);
      this.onVis = null;
    }
    if (!this.sentinel) return;
    try {
      await this.sentinel.release();
    } catch {
      /* ignore */
    }
    this.sentinel = null;
  }
}
