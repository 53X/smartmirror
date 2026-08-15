"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { MediaImage } from "@/components/MediaImage";
import {
  createTryOnJob,
  kioskMediaUrl,
  listKioskSkus,
  pollKioskJob,
  type SkuRecord,
} from "@/lib/api";
import { dataUrlToJpegBlob } from "@/lib/captureFrame";
import { clearKioskSession, readKioskSession } from "@/lib/kioskSession";

const kioskToken = process.env.NEXT_PUBLIC_KIOSK_DEVICE_TOKEN ?? "";

export default function KioskBrowsePage() {
  const router = useRouter();
  const [skus, setSkus] = useState<SkuRecord[]>([]);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const session = readKioskSession();
    if (!session?.stillDataUrl) {
      router.replace("/kiosk/consent");
      return;
    }
    void listKioskSkus()
      .then(setSkus)
      .catch((loadError: Error) => setError(loadError.message));
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
          sessionStorage.setItem(
            "smartmirror.compare",
            JSON.stringify({ skuId: sku.id, skuName: sku.name, resultUrl: job.result_url }),
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

  function filenameFromUrl(url: string | null): string | null {
    if (!url) {
      return null;
    }
    return url.split("/").pop() ?? null;
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-4xl">Swipe saris</h1>
          <p className="text-sm text-zinc-400">Generated stills show how it would look.</p>
        </div>
        <button
          type="button"
          className="text-sm text-zinc-400 underline"
          onClick={() => {
            clearKioskSession();
            router.push("/kiosk/consent");
          }}
        >
          End session
        </button>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      {skus.length === 0 && !error ? (
        <p className="text-zinc-400">No approved saris yet. Staff must capture, reconstruct, and approve.</p>
      ) : null}
      {sku ? (
        <div className="flex items-center gap-4">
          <button
            type="button"
            aria-label="Previous sari"
            onClick={() => setIndex((current) => Math.max(0, current - 1))}
            className="rounded-full border border-white/15 p-3"
          >
            <ChevronLeft />
          </button>
          <AnimatePresence mode="wait">
            <motion.div
              key={sku.id}
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              className="flex-1 overflow-hidden rounded-3xl border border-white/10 bg-zinc-900"
            >
              {filenameFromUrl(sku.reconstructed_asset_url) ? (
                <MediaImage
                  url={kioskMediaUrl(sku.id, filenameFromUrl(sku.reconstructed_asset_url) as string)}
                  alt={`Canonical reconstructed sari for ${sku.name}`}
                  kioskToken={kioskToken}
                  className="h-[520px] w-full object-cover"
                />
              ) : null}
              <div className="p-5">
                <p className="text-xs uppercase tracking-widest text-amber-200/80">{sku.barcode}</p>
                <h2 className="font-display text-3xl">{sku.name}</h2>
                <p className="mt-1 text-sm text-zinc-400">
                  {sku.fabric ?? "Fabric unset"} · Nivi drape · garment photo sent to try-on
                </p>
              </div>
            </motion.div>
          </AnimatePresence>
          <button
            type="button"
            aria-label="Next sari"
            onClick={() => setIndex((current) => Math.min(skus.length - 1, current + 1))}
            className="rounded-full border border-white/15 p-3"
          >
            <ChevronRight />
          </button>
        </div>
      ) : null}
      <button
        type="button"
        disabled={!sku || busy}
        onClick={() => void generateLook()}
        className="rounded-full bg-amber-200 px-6 py-3 text-sm font-semibold text-zinc-950 disabled:opacity-40"
      >
        {busy ? "Generating look… this can take a minute" : "See how it would look"}
      </button>
    </main>
  );
}
