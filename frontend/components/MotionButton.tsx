"use client";

import type { ComponentProps } from "react";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";

const MotionButtonBase = motion.create(Button);

/**
 * Motion-enhanced Button for primary kiosk actions.
 *
 * Uses `motion.create` so tap feedback lives on the real shadcn Button.
 * Defaults to the kiosk size (56px) and a quiet 0.98 press scale.
 */
export function MotionButton({
  whileTap = { scale: 0.98 },
  size = "kiosk",
  ...props
}: ComponentProps<typeof MotionButtonBase>) {
  return <MotionButtonBase whileTap={whileTap} size={size} {...props} />;
}
