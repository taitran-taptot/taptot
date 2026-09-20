import type { BeepKind } from "../types";

let ctx: AudioContext | null = null;

function audio(): AudioContext | null {
  if (typeof window === "undefined") return null;
  const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  if (!ctx) ctx = new Ctor();
  return ctx;
}

/** Unlock audio on a user gesture (iOS). */
export async function unlockBeeps(): Promise<void> {
  const ac = audio();
  if (!ac) return;
  if (ac.state === "suspended") {
    try {
      await ac.resume();
    } catch {
      /* ignore */
    }
  }
}

/**
 * Short oscillator beep.
 * depth = lower confirmation when the bottom of a rep is reached
 * rep = higher pitch when a full cycle completes
 */
export function playBeep(kind: BeepKind = "rep"): void {
  const ac = audio();
  if (!ac) return;
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = "sine";
  osc.frequency.value = kind === "depth" ? 520 : 880;
  gain.gain.value = 0.08;
  osc.connect(gain);
  gain.connect(ac.destination);
  const now = ac.currentTime;
  gain.gain.setValueAtTime(0.08, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
  osc.start(now);
  osc.stop(now + 0.13);
}
