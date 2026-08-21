/**
 * Shared quiet Motion timings for kiosk screens.
 *
 * Keep tweens short and easeOut-only. Springs and overshoot fight
 * `MotionConfig reducedMotion="user"` and make tap targets feel unstable.
 */

export const kioskEase = "easeOut" as const;

export const kioskEnterTransition = { duration: 0.4, ease: kioskEase };
export const kioskFadeTransition = { duration: 0.24, ease: kioskEase };
export const kioskSlideTransition = { duration: 0.28, ease: kioskEase };
export const kioskImageTransition = { duration: 0.35, ease: kioskEase };
