"use client";

import { useEffect, useState } from "react";
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
import { Spinner } from "@/components/ui/spinner";
import {
  createTryOnJob,
  kioskMediaUrl,
  listKioskSkus,
  pollKioskJob,
  type SkuRecord,
} from "@/lib/api";
import { dataUrlToJpegBlob } from "@/lib/captureFrame";
import { filenameFromUrl, isSariSku } from "@/lib/comparePayload";
import { kioskSlideTransition } from "@/lib/kioskMotion";
import { clearKioskSession, readKioskSession } from "@/lib/kioskSession";

const kioskToken = process.env.NEXT_PUBLIC_KIOSK_DEVICE_TOKEN ?? "";

export default function KioskBrowsePage() {
  const router = useRouter();
  const [skus, setSkus] = useState<SkuRecord[]>([]);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const session = readKioskSession();
    if (!session?.stillDataUrl) {
      router.replace("/kiosk/consent");
      return;
    }
    void listKioskSkus()
      .then(setSkus)
      .catch((loadError: Error) => setError(loadError.message))
      .finally(() => setLoading(false));
  }, [router]);

  const sku = skus[index];

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
            "smartmirror.compare",
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

  return (
    <KioskShell
      className="max-w-5xl"
      place="The collection"
      title="Swipe the collection"
      subtitle="Each generated still shows how the piece would look on you. The physical garment stays the source of truth."
      actions={
        <Button
          type="button"
          variant="link"
          onClick={() => {
            clearKioskSession();
            router.push("/kiosk/consent");
          }}
        >
          End session
        </Button>
      }
    >
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Could not generate the look</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
          {showRecapture ? (
            <AlertAction>
              <Button type="button" variant="link" onClick={() => router.push("/kiosk/capture")}>
                Recapture photo
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
            <EmptyTitle>No approved garments yet</EmptyTitle>
            <EmptyDescription>
              Staff must capture, reconstruct, and approve before shoppers can browse.
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
            disabled={busy}
            onClick={() => setIndex((current) => Math.max(0, current - 1))}
          >
            <ChevronLeft />
          </MotionButton>
          <AnimatePresence mode="wait">
            <motion.div
              key={sku.id}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={kioskSlideTransition}
              aria-busy={busy}
              className="min-w-0 flex-1"
            >
              <Card className="overflow-hidden py-0">
                {reconstructedFilename ? (
                  <CardContent className="relative p-0">
                    <MediaImage
                      url={kioskMediaUrl(sku.id, reconstructedFilename)}
                      alt={`Canonical reconstructed ${skuIsSari ? "sari" : "garment"} for ${sku.name}`}
                      kioskToken={kioskToken}
                      className="aspect-[3/4] max-h-[min(68vh,760px)] w-full object-cover"
                    />
                    {busy ? (
                      <Skeleton
                        className="absolute inset-0 rounded-none opacity-40"
                        aria-hidden
                      />
                    ) : null}
                  </CardContent>
                ) : null}
                <CardHeader className="py-5">
                  <Badge variant="secondary">{sku.barcode}</Badge>
                  <CardTitle>{sku.name}</CardTitle>
                  <CardDescription>
                    {sku.fabric ?? "Fabric unset"}
                    {sku.drape_style === "nivi" ? " · Nivi drape" : ""}
                    {" · garment photo sent to try-on"}
                  </CardDescription>
                </CardHeader>
              </Card>
            </motion.div>
          </AnimatePresence>
          <MotionButton
            type="button"
            variant="outline"
            size="icon-kiosk"
            aria-label={skuIsSari ? "Next sari" : "Next garment"}
            disabled={busy}
            onClick={() => setIndex((current) => Math.min(skus.length - 1, current + 1))}
          >
            <ChevronRight />
          </MotionButton>
        </div>
      ) : null}

      <MotionButton
        type="button"
        className="w-full"
        disabled={!sku || busy}
        aria-live="polite"
        onClick={() => void generateLook()}
      >
        {busy ? <Spinner data-icon="inline-start" /> : null}
        {busy ? "Generating look… this can take a minute" : "See how it would look"}
      </MotionButton>
    </KioskShell>
  );
}
