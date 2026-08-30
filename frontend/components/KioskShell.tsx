"use client";

import { useEffect, useState, type ReactNode } from "react";
import { KioskPageEnter } from "@/components/KioskPageEnter";
import { Separator } from "@/components/ui/separator";
import { useKioskIdleReturn } from "@/hooks/useKioskIdleReturn";
import { exitKioskFullscreen, isKioskFullscreen } from "@/lib/kioskFullscreen";
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
  /** When false, skip idle return (rare). Defaults to true. */
  idleReturn?: boolean;
}

/**
 * Shared kiosk chrome: Smartmirror wordmark, gold Fitting room eyebrow,
 * serif display headline, muted subcopy, and a hairline separator.
 */
export function KioskShell({
  place,
  title,
  subtitle,
  actions,
  children,
  align = "start",
  className,
  idleReturn = true,
}: KioskShellProps) {
  useKioskIdleReturn(idleReturn);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    function syncFullscreen(): void {
      setFullscreen(isKioskFullscreen());
    }
    syncFullscreen();
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () => document.removeEventListener("fullscreenchange", syncFullscreen);
  }, []);

  return (
    <KioskPageEnter
      className={cn(
        "mx-auto flex min-h-dvh w-full flex-col gap-8 px-6 py-10 lg:gap-10 lg:px-12 lg:py-12",
        align === "center" && "justify-center",
        className,
      )}
    >
      <header className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <p className="font-display text-lg tracking-tight text-primary/90">Smartmirror</p>
            <p className="text-xs tracking-[0.32em] text-primary uppercase">
              Fitting room
              <span className="text-muted-foreground"> · {place}</span>
            </p>
          </div>
          <div className="-mt-1 flex shrink-0 items-center gap-3">
            {fullscreen ? (
              <button
                type="button"
                className="text-xs tracking-wide text-muted-foreground/70 underline-offset-4 hover:text-muted-foreground hover:underline"
                onClick={() => void exitKioskFullscreen()}
              >
                Exit fullscreen
              </button>
            ) : null}
            {actions ? <div>{actions}</div> : null}
          </div>
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
