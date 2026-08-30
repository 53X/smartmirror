"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { exitKioskFullscreen, requestKioskFullscreen } from "@/lib/kioskFullscreen";
import { clearKioskSession } from "@/lib/kioskSession";
import { kioskEase, kioskFadeTransition } from "@/lib/kioskMotion";

const ATTRACT_LOOKS = [
  {
    src: "/demo-003-look.png",
    alt: "Styled look on the mirror",
  },
  {
    src: "/demo-model.jpg",
    alt: "Fitting room model",
  },
] as const;

const LOOK_ROTATE_MS = 5200;

/**
 * Idle / entry surface for the floor kiosk — tap to enter the fitting room.
 */
export default function KioskAttractPage() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const [lookIndex, setLookIndex] = useState(0);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (reduceMotion) {
      return;
    }
    const timer = window.setInterval(() => {
      setLookIndex((current) => (current + 1) % ATTRACT_LOOKS.length);
    }, LOOK_ROTATE_MS);
    return () => window.clearInterval(timer);
  }, [reduceMotion]);

  function startSession(): void {
    if (starting) {
      return;
    }
    setStarting(true);
    try {
      clearKioskSession();
    } catch {
      // sessionStorage can throw in locked-down kiosk profiles — still enter.
    }

    const goConsent = (): void => {
      router.push("/kiosk/consent");
    };

    // Attempt fullscreen in this gesture, but never wait longer than 400ms —
    // some embeds hang the Fullscreen API and would freeze "Opening…".
    void Promise.race([
      requestKioskFullscreen(),
      new Promise<boolean>((resolve) => {
        window.setTimeout(() => resolve(false), 400);
      }),
    ]).finally(goConsent);
  }

  const look = ATTRACT_LOOKS[lookIndex] ?? ATTRACT_LOOKS[0];

  return (
    <main className="relative flex min-h-dvh w-full flex-col overflow-hidden bg-background">
      <div
        className="pointer-events-none absolute inset-0 kiosk-frame-spotlight opacity-90"
        aria-hidden
      />

      <div className="relative flex min-h-dvh flex-1 flex-col">
        <header className="relative z-20 flex items-start justify-between px-6 pt-8 sm:px-10 lg:px-14">
          <div className="flex flex-col gap-2">
            <p className="font-display text-2xl tracking-tight text-primary sm:text-3xl">
              Smartmirror
            </p>
            <p className="text-xs tracking-[0.32em] text-muted-foreground uppercase">
              Fitting room
            </p>
          </div>
          <button
            type="button"
            className="text-xs tracking-wide text-muted-foreground/70 underline-offset-4 hover:text-muted-foreground hover:underline"
            onClick={() => void exitKioskFullscreen()}
          >
            Exit fullscreen
          </button>
        </header>

        <button
          type="button"
          className="group relative z-10 flex min-h-0 flex-1 cursor-pointer flex-col items-center justify-center gap-10 px-4 pb-16 pt-6 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-4 focus-visible:ring-offset-background"
          onClick={startSession}
          disabled={starting}
          aria-label="Tap to start your fitting room session"
        >
          <div className="relative mx-auto w-full max-w-[min(92vw,420px)]">
            <div className="kiosk-frame-spotlight absolute -inset-[18%] rounded-full opacity-80" aria-hidden />
            <div className="relative aspect-[3/4] overflow-hidden rounded-sm shadow-[0_24px_80px_-24px_oklch(0_0_0_/_0.85)]">
              <AnimatePresence mode="wait">
                <motion.img
                  key={look.src}
                  src={look.src}
                  alt={look.alt}
                  className="absolute inset-0 h-full w-full object-cover"
                  initial={reduceMotion ? false : { opacity: 0, scale: 1.04 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={reduceMotion ? undefined : { opacity: 0, scale: 0.98 }}
                  transition={{ duration: 0.9, ease: kioskEase }}
                  draggable={false}
                />
              </AnimatePresence>
              <div
                className="pointer-events-none absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-background/20"
                aria-hidden
              />
            </div>
          </div>

          <div className="relative z-10 flex flex-col items-center gap-3 text-center">
            <motion.p
              className="font-display text-4xl tracking-tight text-foreground sm:text-5xl"
              animate={
                reduceMotion
                  ? undefined
                  : {
                      opacity: [0.72, 1, 0.72],
                    }
              }
              transition={
                reduceMotion
                  ? undefined
                  : { duration: 2.8, repeat: Infinity, ease: "easeInOut" }
              }
            >
              {starting ? "Opening…" : "Tap to start"}
            </motion.p>
            <motion.p
              className="max-w-sm text-sm tracking-[0.18em] text-muted-foreground uppercase"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={kioskFadeTransition}
            >
              See how it looks on you
            </motion.p>
          </div>
        </button>

        <footer className="relative z-20 px-6 pb-8 text-center sm:px-10">
          <p className="text-sm text-muted-foreground/80">
            Staff?{" "}
            <a href="/staff/login" className="text-primary/90 underline-offset-4 hover:underline">
              Sign in
            </a>
          </p>
        </footer>
      </div>
    </main>
  );
}
