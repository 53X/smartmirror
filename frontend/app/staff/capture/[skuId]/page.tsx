"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { WebcamCapture } from "@/components/WebcamCapture";
import { MediaImage } from "@/components/MediaImage";
import { useStaffTokenOrBypass } from "@/components/StaffAuthProvider";
import {
  approveSku,
  listStaffSkus,
  pollStaffJob,
  saveReconstructedAsset,
  staffMediaUrl,
  staffResultUrl,
  startReconstructJob,
  uploadStaffPart,
  type SkuRecord,
} from "@/lib/api";
import { dataUrlToJpegBlob } from "@/lib/captureFrame";
import { OPTIONAL_PART_TYPES, PART_TYPE_LABELS, REQUIRED_PART_TYPES } from "@/lib/partTypes";

const CAPTURE_STEPS = [...REQUIRED_PART_TYPES, ...OPTIONAL_PART_TYPES];

export default function StaffCapturePage() {
  const params = useParams<{ skuId: string }>();
  const router = useRouter();
  const token = useStaffTokenOrBypass();
  const [sku, setSku] = useState<SkuRecord | null>(null);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) {
      router.replace("/staff/login");
      return;
    }
    void listStaffSkus(token)
      .then((skus) => {
        const match = skus.find((item) => item.id === params.skuId) ?? null;
        setSku(match);
      })
      .catch((loadError: Error) => setError(loadError.message));
  }, [token, params.skuId, router]);

  const partType = CAPTURE_STEPS[step];

  async function savePartFromDataUrl(dataUrl: string): Promise<void> {
    if (!token || !sku) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const blob = await dataUrlToJpegBlob(dataUrl);
      const updated = await uploadStaffPart(token, sku.id, partType, blob);
      setSku(updated);
      setStep((current) => Math.min(CAPTURE_STEPS.length - 1, current + 1));
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function savePartFromFile(file: File): Promise<void> {
    if (!token || !sku) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await uploadStaffPart(token, sku.id, partType, file);
      setSku(updated);
      setStep((current) => Math.min(CAPTURE_STEPS.length - 1, current + 1));
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function runReconstruct(): Promise<void> {
    if (!token || !sku) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await startReconstructJob(token, sku.id);
      let job = created;
      for (let attempt = 0; attempt < 40; attempt += 1) {
        if (job.status === "succeeded" && job.result_url) {
          const imageResponse = await fetch(staffResultUrl(job.result_url), {
            headers: { Authorization: `Bearer ${token}` },
          });
          const blob = await imageResponse.blob();
          const updated = await saveReconstructedAsset(token, sku.id, blob);
          setSku(updated);
          return;
        }
        if (job.status === "failed") {
          throw new Error(job.error_message || "Reconstruct failed");
        }
        await new Promise((resolve) => setTimeout(resolve, 400));
        job = await pollStaffJob(token, job.id);
      }
      throw new Error("Timed out waiting for reconstruct");
    } catch (reconstructError) {
      setError(reconstructError instanceof Error ? reconstructError.message : "Reconstruct failed");
    } finally {
      setBusy(false);
    }
  }

  async function onApprove(): Promise<void> {
    if (!token || !sku) {
      return;
    }
    setBusy(true);
    try {
      setSku(await approveSku(token, sku.id, true));
    } catch (approveError) {
      setError(approveError instanceof Error ? approveError.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  if (!sku) {
    return <main className="p-8 text-zinc-400">Loading SKU…</main>;
  }

  const reconstructedName = sku.reconstructed_asset_url?.split("/").pop();

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-8 px-6 py-10">
      <Link href="/staff/skus" className="text-sm text-zinc-400 underline">
        Back to catalog
      </Link>
      <div>
        <p className="text-xs uppercase tracking-widest text-amber-200/80">{sku.barcode}</p>
        <h1 className="font-display text-4xl">{sku.name}</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Step {step + 1} of {CAPTURE_STEPS.length}: {PART_TYPE_LABELS[partType]}
        </p>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <WebcamCapture
            facingMode="environment"
            instruction="Keep the cloth taut. Borders must be fully visible. Skip live overlay — this is a still."
            buttonLabel={busy ? "Saving…" : "Capture this part"}
            onCapture={(dataUrl) => void savePartFromDataUrl(dataUrl)}
          />
          <label className="mt-4 block text-sm text-zinc-400">
            Or upload a file
            <input
              type="file"
              accept="image/*"
              className="mt-2 block"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  void savePartFromFile(file);
                }
              }}
            />
          </label>
        </div>
        <div className="space-y-4">
          <h2 className="font-display text-2xl">Uploaded parts</h2>
          <ul className="grid grid-cols-2 gap-3">
            {sku.parts.map((part) => {
              const filename = part.media_url.split("/").pop() ?? "";
              return (
                <li key={part.part_type} className="overflow-hidden rounded-xl border border-white/10">
                  {token ? (
                    <MediaImage
                      url={staffMediaUrl(sku.id, filename)}
                      alt={part.part_type}
                      authHeader={token}
                      className="h-28 w-full object-cover"
                    />
                  ) : null}
                  <p className="p-2 text-xs text-zinc-400">{PART_TYPE_LABELS[part.part_type]}</p>
                </li>
              );
            })}
          </ul>
          {reconstructedName && token ? (
            <div>
              <h2 className="font-display text-2xl">Canonical reconstruct</h2>
              <MediaImage
                url={staffMediaUrl(sku.id, reconstructedName)}
                alt="Reconstructed sari"
                authHeader={token}
                className="mt-2 h-64 w-full rounded-xl object-cover"
              />
            </div>
          ) : null}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => void runReconstruct()}
              className="rounded-full bg-amber-200 px-5 py-3 text-sm font-semibold text-zinc-950"
            >
              Run Stage A reconstruct
            </button>
            <button
              type="button"
              disabled={busy || !sku.reconstructed_asset_url}
              onClick={() => void onApprove()}
              className="rounded-full border border-white/15 px-5 py-3 text-sm"
            >
              {sku.approved_for_kiosk ? "Approved for kiosk" : "Approve for kiosk"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
