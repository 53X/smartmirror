"use client";

import { ChangeEvent, ReactNode, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera, ImageUp, UserRound } from "lucide-react";
import { WebcamCapture } from "@/components/WebcamCapture";
import { CaptureGuidance } from "@/components/CaptureGuidance";
import { fileToStillDataUrl } from "@/lib/captureFrame";
import { CAMERA_INSTRUCTION, CAPTURE_HEADLINE } from "@/lib/captureGuidance";
import { readKioskSession, writeKioskSession } from "@/lib/kioskSession";

type Source = "camera" | "upload" | "demo";

const DEMO_MODEL_SRC = "/demo-model.jpg";

export default function KioskCapturePage() {
  const router = useRouter();
  const [source, setSource] = useState<Source>("upload");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function commitStill(dataUrl: string): void {
    const session = readKioskSession();
    if (!session) {
      router.replace("/kiosk/consent");
      return;
    }
    writeKioskSession({
      ...session,
      stillDataUrl: dataUrl,
      stillCapturedAt: new Date().toISOString(),
    });
    router.push("/kiosk/browse");
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      commitStill(await fileToStillDataUrl(file));
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not read that photo");
    } finally {
      setBusy(false);
    }
  }

  async function useDemoModel(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(DEMO_MODEL_SRC);
      if (!response.ok) {
        throw new Error("Demo model photo is missing");
      }
      const blob = await response.blob();
      const file = new File([blob], "demo-model.jpg", { type: blob.type || "image/jpeg" });
      commitStill(await fileToStillDataUrl(file));
    } catch (demoError) {
      setError(demoError instanceof Error ? demoError.message : "Could not load the demo model");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-6 px-6 py-10">
      <div>
        <h1 className="font-display text-4xl">Choose the person</h1>
        <p className="mt-2 text-zinc-400">{CAPTURE_HEADLINE}</p>
      </div>
      <CaptureGuidance />
      <div className="grid grid-cols-3 gap-2">
        <SourceButton active={source === "upload"} onClick={() => setSource("upload")} icon={<ImageUp size={16} />} label="Upload" />
        <SourceButton active={source === "demo"} onClick={() => setSource("demo")} icon={<UserRound size={16} />} label="Demo model" />
        <SourceButton active={source === "camera"} onClick={() => setSource("camera")} icon={<Camera size={16} />} label="Camera" />
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      {source === "upload" ? (
        <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-3xl border border-dashed border-white/20 bg-zinc-900 px-6 py-16 text-center">
          <ImageUp className="text-amber-200" />
          <span className="text-sm text-zinc-300">
            {busy ? "Reading photo…" : "Upload a front-facing photo. Face clear, one person, nothing covering the face."}
          </span>
          <input type="file" accept="image/*" className="hidden" onChange={(event) => void handleUpload(event)} />
        </label>
      ) : null}
      {source === "demo" ? (
        <div className="flex flex-col gap-4">
          <img
            src={DEMO_MODEL_SRC}
            alt="Demo model for sari try-on"
            className="max-h-[420px] w-full rounded-3xl object-cover"
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => void useDemoModel()}
            className="rounded-full bg-amber-200 px-6 py-3 text-sm font-semibold text-zinc-950 disabled:opacity-40"
          >
            {busy ? "Loading…" : "Use this demo model"}
          </button>
        </div>
      ) : null}
      {source === "camera" ? (
        <WebcamCapture
          instruction={CAMERA_INSTRUCTION}
          buttonLabel="Capture still"
          onCapture={commitStill}
        />
      ) : null}
    </main>
  );
}

function SourceButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-3 py-2 text-xs ${
        active ? "bg-amber-200 font-semibold text-zinc-950" : "border border-white/15 text-zinc-300"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
