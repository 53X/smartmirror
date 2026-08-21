"use client";

import type { ReactElement, ReactNode } from "react";
import { motion } from "motion/react";
import { kioskEnterTransition } from "@/lib/kioskMotion";
import { cn } from "@/lib/utils";

interface KioskPageEnterProps {
  children: ReactNode;
  className?: string;
}

/**
 * Subtle page-enter for kiosk routes: fade plus a short vertical ease.
 */
export function KioskPageEnter({ children, className }: KioskPageEnterProps): ReactElement {
  return (
    <motion.main
      className={cn(className)}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={kioskEnterTransition}
    >
      {children}
    </motion.main>
  );
}
