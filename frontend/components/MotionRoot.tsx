"use client";

import type { ReactElement, ReactNode } from "react";
import { MotionConfig } from "motion/react";

/**
 * Apply Motion accessibility defaults for the whole app.
 */
export function MotionRoot({ children }: { children: ReactNode }): ReactElement {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
