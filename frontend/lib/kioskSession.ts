/**
 * Kiosk session helpers: consent + customer still, with a hard timeout.
 * Face images stay in sessionStorage only and are never console.logged.
 */

export const KIOSK_SESSION_KEY = "smartmirror.kiosk.v1";

export interface KioskSession {
  sessionId: string;
  consentedAt: string;
  stillDataUrl: string | null;
  stillCapturedAt: string | null;
}

function timeoutMs(): number {
  const minutes = Number(process.env.NEXT_PUBLIC_SESSION_TIMEOUT_MINUTES ?? "10");
  return Math.max(1, minutes) * 60 * 1000;
}

export function createSessionId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `kiosk-${Date.now()}`;
}

export function readKioskSession(): KioskSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = sessionStorage.getItem(KIOSK_SESSION_KEY);
  if (!raw) {
    return null;
  }
  const parsed = JSON.parse(raw) as KioskSession;
  const started = Date.parse(parsed.consentedAt);
  if (Number.isNaN(started) || Date.now() - started > timeoutMs()) {
    clearKioskSession();
    return null;
  }
  return parsed;
}

export function writeKioskSession(session: KioskSession): void {
  sessionStorage.setItem(KIOSK_SESSION_KEY, JSON.stringify(session));
}

export function clearKioskSession(): void {
  sessionStorage.removeItem(KIOSK_SESSION_KEY);
}

export function sessionTimeoutMinutes(): number {
  return Math.max(1, Number(process.env.NEXT_PUBLIC_SESSION_TIMEOUT_MINUTES ?? "10"));
}
