"use client";

import type { ReactNode } from "react";
import { KioskPageEnter } from "@/components/KioskPageEnter";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

interface KioskShellProps {
  /** Quiet, non-interactive hint of place in the session (e.g. "Consent"). */
  place: string;
  title: ReactNode;
  subtitle?: ReactNode;
  /** Optional header-level action, e.g. an "End session" link. */
  actions?: ReactNode;
  children: ReactNode;
  /** Vertically center short forms; keep editorial pages top-aligned. */
  align?: "center" | "start";
  className?: string;
}

/**
 * Shared kiosk chrome: gold "Fitting room" eyebrow, serif display headline,
 * muted subcopy, and a hairline separator. Gives all four try-on screens one
 * editorial lookbook voice without adding wizard-style stepper navigation.
 */
export function KioskShell({
  place,
  title,
  subtitle,
  actions,
  children,
  align = "start",
  className,
}: KioskShellProps) {
  return (
    <KioskPageEnter
      className={cn(
        "mx-auto flex min-h-screen w-full flex-col gap-10 px-8 py-12 lg:px-14 lg:py-16",
        align === "center" && "justify-center",
        className,
      )}
    >
      <header className="flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <p className="text-xs tracking-[0.32em] text-primary uppercase">
            Fitting room
            <span className="text-muted-foreground"> · {place}</span>
          </p>
          {actions ? <div className="-mt-1 shrink-0">{actions}</div> : null}
        </div>
        <h1 className="max-w-4xl font-display text-5xl font-normal tracking-tight text-pretty lg:text-6xl">
          {title}
        </h1>
        {subtitle ? (
          <p className="max-w-2xl text-base leading-relaxed text-muted-foreground lg:text-lg">
            {subtitle}
          </p>
        ) : null}
      </header>
      <Separator />
      <div className="flex flex-col gap-8">{children}</div>
    </KioskPageEnter>
  );
}
