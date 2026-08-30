/**
 * Fullscreen helpers for the floor kiosk. Failures are silent — browsers often
 * block requestFullscreen outside a user gesture or in iframe embeds.
 */

/**
 * Enter fullscreen on the document element when the API allows it.
 */
export async function requestKioskFullscreen(): Promise<boolean> {
  if (typeof document === "undefined") {
    return false;
  }
  const root = document.documentElement;
  if (document.fullscreenElement) {
    return true;
  }
  if (typeof root.requestFullscreen !== "function") {
    return false;
  }
  try {
    await root.requestFullscreen();
    return true;
  } catch {
    return false;
  }
}

/**
 * Leave fullscreen when the document is currently fullscreen.
 */
export async function exitKioskFullscreen(): Promise<void> {
  if (typeof document === "undefined") {
    return;
  }
  if (!document.fullscreenElement || typeof document.exitFullscreen !== "function") {
    return;
  }
  try {
    await document.exitFullscreen();
  } catch {
    // Ignore — user or browser may already have exited.
  }
}

/**
 * Whether the document is currently in fullscreen mode.
 */
export function isKioskFullscreen(): boolean {
  if (typeof document === "undefined") {
    return false;
  }
  return Boolean(document.fullscreenElement);
}
