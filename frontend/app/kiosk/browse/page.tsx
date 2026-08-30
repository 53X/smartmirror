"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { ChevronLeft, ChevronRight, Shirt } from "lucide-react";
import { KioskShell } from "@/components/KioskShell";
import { MediaImage } from "@/components/MediaImage";
import { MotionButton } from "@/components/MotionButton";
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import {
  createTryOnJob,
  kioskMediaUrl,
  listKioskSkus,
  pollKioskJob,
  type SkuRecord,
} from "@/lib/api";
import { dataUrlToJpegBlob } from "@/lib/captureFrame";
import { filenameFromUrl, isSariSku } from "@/lib/comparePayload";
import { kioskFadeTransition, kioskSlideTransition, kioskSwipeThresholdPx } from "@/lib/kioskMotion";
import { clearKioskSession, KIOSK_COMPARE_KEY, readKioskSession } from "@/lib/kioskSession";

const kioskToken = process.env.NEXT_PUBLIC_KIOSK_DEVICE_TOKEN ?? "";

/** Editorial status lines shown while try-on generation polls. */
const STYLING_STATUS_LINES = [
  "Styling your look…",
  "Laying the drape…",
  "Matching the fall…",
  "Finishing the still…",
] as const;

/**
 * Kiosk browse: swipe approved SKUs and generate a try-on still.
 */
export default function KioskBrowsePage() {
  const router = useRouter();
  const [skus, setSkus] = useState<SkuRecord[]>([]);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [statusTick, setStatusTick] = useState(0);
  const pointerStartXRef = useRef<number | null>(null);
  const swipeHandledRef = useRef(false);

  useEffect(() => {
    const session = readKioskSession();
    if (!session?.stillDataUrl) {
      router.replace("/kiosk/attract");
      return;
    }
    void listKioskSkus()
      .then(setSkus)
      .catch((loadError: Error) => setError(loadError.message))
      .finally(() => setLoading(false));
  }, [router]);

  useEffect(() => {
    if (!busy) {
      return;
    }
    const timer = window.setInterval(() => {
      setStatusTick((tick) => tick + 1);
    }, 2800);
    return () => window.clearInterval(timer);
  }, [busy]);

  const sku = skus[index];

  function goPrevious(): void {
    setIndex((current) => Math.max(0, current - 1));
  }

  function goNext(): void {
    setIndex((current) => Math.min(skus.length - 1, current + 1));
  }

  function handlePointerDown(clientX: number): void {
    if (busy || skus.length < 2) {
      return;
    }
    pointerStartXRef.current = clientX;
    swipeHandledRef.current = false;
  }

  function handlePointerMove(clientX: number): void {
    if (busy || pointerStartXRef.current === null || swipeHandledRef.current) {
      return;
    }
    const deltaX = clientX - pointerStartXRef.current;
    if (Math.abs(deltaX) < kioskSwipeThresholdPx) {
      return;
    }
    swipeHandledRef.current = true;
    pointerStartXRef.current = null;
    if (deltaX < 0) {
      goNext();
    } else {
      goPrevious();
    }
  }

  function handlePointerUp(): void {
    pointerStartXRef.current = null;
  }

  async function generateLook(): Promise<void> {
    const session = readKioskSession();
    if (!session?.stillDataUrl || !sku) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const blob = await dataUrlToJpegBlob(session.stillDataUrl);
      const created = await createTryOnJob(sku, session.sessionId, blob);
      let job = created;
      for (let attempt = 0; attempt < 180; attempt += 1) {
        if (job.status === "succeeded" && job.result_url) {
          const reconstructedName = filenameFromUrl(sku.reconstructed_asset_url);
          sessionStorage.setItem(
            KIOSK_COMPARE_KEY,
            JSON.stringify({
              skuId: sku.id,
              skuName: sku.name,
              resultUrl: job.result_url,
              productImageUrl: reconstructedName ? kioskMediaUrl(sku.id, reconstructedName) : "",
              drapeStyle: sku.drape_style,
              garmentCategory:
                sku.garment_category ?? (sku.drape_style === "nivi" ? "saree" : undefined),
            }),
          );
          router.push("/kiosk/compare");
          return;
        }
        if (job.status === "failed") {
          throw new Error(job.error_message || "Try-on failed");
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
        job = await pollKioskJob(job.id);
      }
      throw new Error("Timed out waiting for the look. Generation can take up to three minutes.");
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "Could not generate look");
    } finally {
      setBusy(false);
    }
  }

  const skuIsSari = sku
    ? isSariSku({ garmentCategory: sku.garment_category, drapeStyle: sku.drape_style })
    : false;
  const reconstructedFilename = sku ? filenameFromUrl(sku.reconstructed_asset_url) : null;
  const showRecapture = error ? /recapture|face|person/i.test(error) : false;
  const stylingCopy =
    STYLING_STATUS_LINES[statusTick % STYLING_STATUS_LINES.length] ?? STYLING_STATUS_LINES[0];

  return (
    <KioskShell
      className="max-w-5xl"
      place="The collection"
      title="Browse the lookbook"
      subtitle="Swipe through the pieces. Each still shows how it would look on you — the garment in hand stays the source of truth."
      actions={
        <Button
          type="button"
          variant="link"
          onClick={() => {
            clearKioskSession();
            router.push("/kiosk/attract");
          }}
        >
          End visit
        </Button>
      }
    >
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>We couldn't style that look</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
          {showRecapture ? (
            <AlertAction>
              <Button type="button" variant="link" onClick={() => router.push("/kiosk/capture")}>
                Take another photo
              </Button>
            </AlertAction>
          ) : null}
        </Alert>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-5">
          <Skeleton className="size-14 shrink-0 rounded-lg" aria-hidden />
          <Card className="min-w-0 flex-1 overflow-hidden py-0">
            <Skeleton className="aspect-[3/4] max-h-[min(68vh,760px)] w-full rounded-none" aria-hidden />
            <CardHeader className="gap-2 py-5">
              <Skeleton className="h-5 w-24" aria-hidden />
              <Skeleton className="h-9 w-56" aria-hidden />
              <Skeleton className="h-5 w-72" aria-hidden />
            </CardHeader>
          </Card>
          <Skeleton className="size-14 shrink-0 rounded-lg" aria-hidden />
        </div>
      ) : null}

      {!loading && skus.length === 0 && !error ? (
        <Empty className="border border-dashed py-16">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Shirt />
            </EmptyMedia>
            <EmptyTitle>The lookbook is empty</EmptyTitle>
            <EmptyDescription>
              Ask staff to approve a few pieces — then the collection appears here.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : null}

      {sku ? (
        <div className="flex items-center gap-5">
          <MotionButton
            type="button"
            variant="outline"
            size="icon-kiosk"
            aria-label={skuIsSari ? "Previous sari" : "Previous garment"}
            disabled={busy || index === 0}
            onClick={goPrevious}
          >
            <ChevronLeft />
          </MotionButton>
          <div
            className="min-w-0 flex-1 touch-pan-y"
            onPointerDown={(event) => {
              if (event.pointerType === "mouse" && event.button !== 0) {
                return;
              }
              handlePointerDown(event.clientX);
            }}
            onPointerMove={(event) => handlePointerMove(event.clientX)}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            onPointerLeave={handlePointerUp}
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={sku.id}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={kioskSlideTransition}
                aria-busy={busy}
                className="min-w-0"
              >
                <Card className="overflow-hidden py-0">
                  {reconstructedFilename ? (
                    <CardContent className="relative p-0">
                      <div className="kiosk-frame-spotlight absolute inset-0 opacity-70" aria-hidden />
                      <MediaImage
                        url={kioskMediaUrl(sku.id, reconstructedFilename)}
                        alt={`Canonical reconstructed ${skuIsSari ? "sari" : "garment"} for ${sku.name}`}
                        kioskToken={kioskToken}
                        className="relative aspect-[3/4] max-h-[min(72vh,820px)] w-full select-none object-cover"
                      />
                      {busy ? (
                        <motion.div
                          className="absolute inset-0 flex flex-col items-center justify-end gap-3 bg-background/55 p-8 backdrop-blur-[2px]"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={kioskFadeTransition}
                          aria-hidden
                        >
                          <Skeleton className="absolute inset-0 rounded-none opacity-50" />
                          <div className="relative z-10 w-full max-w-sm space-y-3 text-center">
                            <Skeleton className="mx-auto h-2 w-2/3 rounded-full bg-primary/35" />
                            <Skeleton className="mx-auto h-2 w-1/2 rounded-full bg-primary/20" />
                          </div>
                        </motion.div>
                      ) : null}
                    </CardContent>
                  ) : null}
                  <CardHeader className="py-5">
                    <Badge variant="secondary">{sku.barcode}</Badge>
                    <CardTitle>{sku.name}</CardTitle>
                    <CardDescription>
                      {sku.fabric ?? "Fabric unset"}
                      {sku.drape_style === "nivi" ? " · Nivi drape" : ""}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </motion.div>
            </AnimatePresence>
          </div>
          <MotionButton
            type="button"
            variant="outline"
            size="icon-kiosk"
            aria-label={skuIsSari ? "Next sari" : "Next garment"}
            disabled={busy || index >= skus.length - 1}
            onClick={goNext}
          >
            <ChevronRight />
          </MotionButton>
        </div>
      ) : null}

      <div className="flex w-full flex-col gap-3" aria-live="polite">
        {busy ? (
          <motion.p
            key={stylingCopy}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={kioskFadeTransition}
            className="font-display text-center text-xl text-primary"
          >
            {stylingCopy}
          </motion.p>
        ) : null}
        <MotionButton
          type="button"
          className="w-full"
          disabled={!sku || busy}
          onClick={() => void generateLook()}
        >
          {busy ? "Please wait" : "See it on me"}
        </MotionButton>
      </div>
    </KioskShell>
  );
}
