"use client";

import { useEffect, useEffectEvent } from "react";
import { useRouter } from "next/navigation";
import { exitKioskFullscreen } from "@/lib/kioskFullscreen";
import { clearKioskSession, idleTimeoutMs } from "@/lib/kioskSession";

const ACTIVITY_EVENTS = [
  "pointerdown",
  "pointermove",
  "keydown",
  "touchstart",
  "scroll",
  "wheel",
] as const;

/**
 * After inactivity on a kiosk flow screen, clear the session and return to attract.
 */
export function useKioskIdleReturn(enabled = true): void {
  const router = useRouter();

  const returnToAttract = useEffectEvent(() => {
    clearKioskSession();
    void exitKioskFullscreen();
    router.replace("/kiosk/attract");
  });

  useEffect(() => {
    if (!enabled || typeof window === "undefined") {
      return;
    }

    let idleTimer: number | null = null;

    function armIdleTimer(): void {
      if (idleTimer !== null) {
        window.clearTimeout(idleTimer);
      }
      idleTimer = window.setTimeout(() => {
        returnToAttract();
      }, idleTimeoutMs());
    }

    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, armIdleTimer, { passive: true });
    }
    armIdleTimer();

    return () => {
      if (idleTimer !== null) {
        window.clearTimeout(idleTimer);
      }
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, armIdleTimer);
      }
    };
  }, [enabled]);
}
