"use client";

import { useEffect, useId, useRef, useState } from "react";
import { TURNSTILE_SITE_KEY } from "@/lib/config";

declare global {
  interface Window {
    turnstile?: {
      render: (
        el: HTMLElement,
        opts: {
          sitekey: string;
          callback?: (token: string) => void;
          "error-callback"?: () => void;
          "expired-callback"?: () => void;
          theme?: "light" | "dark" | "auto";
        },
      ) => string;
      reset: (widgetId?: string) => void;
      remove: (widgetId?: string) => void;
      getResponse: (widgetId?: string) => string;
    };
  }
}

type Props = {
  /** When false, widget is not required (e.g. challenge with redeem). */
  enabled?: boolean;
  onToken?: (token: string | null) => void;
};

let scriptPromise: Promise<void> | null = null;

function loadTurnstileScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.turnstile) return Promise.resolve();
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src*="challenges.cloudflare.com/turnstile"]',
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("turnstile script")));
      if (window.turnstile) resolve();
      return;
    }
    const s = document.createElement("script");
    s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("turnstile script"));
    document.head.appendChild(s);
  });
  return scriptPromise;
}

/**
 * Cloudflare Turnstile widget for free workout generation.
 * When site key is empty (local/dev), renders nothing and reports null token.
 */
export function TurnstileField({ enabled = true, onToken }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const onTokenRef = useRef(onToken);
  onTokenRef.current = onToken;
  const reactId = useId();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!enabled || !TURNSTILE_SITE_KEY) {
      onTokenRef.current?.(null);
      return;
    }
    let cancelled = false;
    loadTurnstileScript()
      .then(() => {
        if (cancelled || !hostRef.current || !window.turnstile) return;
        if (widgetIdRef.current) {
          try {
            window.turnstile.remove(widgetIdRef.current);
          } catch {
            /* ignore */
          }
          widgetIdRef.current = null;
        }
        widgetIdRef.current = window.turnstile.render(hostRef.current, {
          sitekey: TURNSTILE_SITE_KEY,
          theme: "light",
          callback: (token) => {
            onTokenRef.current?.(token);
          },
          "expired-callback": () => onTokenRef.current?.(null),
          "error-callback": () => onTokenRef.current?.(null),
        });
        setReady(true);
      })
      .catch(() => {
        onTokenRef.current?.(null);
      });
    return () => {
      cancelled = true;
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch {
          /* ignore */
        }
        widgetIdRef.current = null;
      }
    };
  }, [enabled, reactId]);

  if (!enabled || !TURNSTILE_SITE_KEY) return null;

  return (
    <div className="mt-3" data-ready={ready ? "1" : "0"}>
      <div ref={hostRef} />
    </div>
  );
}

/** Read current widget response if present; otherwise null. */
export function readTurnstileResponse(): string | null {
  if (typeof window === "undefined" || !window.turnstile) return null;
  try {
    const token = window.turnstile.getResponse();
    return token?.trim() || null;
  } catch {
    return null;
  }
}
