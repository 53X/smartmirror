"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import {
  clearKioskSession,
  createSessionId,
  sessionTimeoutMinutes,
  writeKioskSession,
} from "@/lib/kioskSession";

export default function ConsentPage() {
  const router = useRouter();
  const [photoOk, setPhotoOk] = useState(false);
  const [noKeep, setNoKeep] = useState(false);
  const timeoutMinutes = sessionTimeoutMinutes();

  function continueToCapture(): void {
    clearKioskSession();
    writeKioskSession({
      sessionId: createSessionId(),
      consentedAt: new Date().toISOString(),
      stillDataUrl: null,
      stillCapturedAt: null,
    });
    router.push("/kiosk/capture");
  }

  const ready = photoOk && noKeep;

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-8 px-6 py-12">
      <ShieldCheck className="text-amber-200" size={36} />
      <div>
        <h1 className="font-display text-4xl">Before we take a photo</h1>
        <p className="mt-3 text-zinc-400">
          This kiosk uses <strong className="text-zinc-200">one front-facing still</strong> so we can
          show how a sari would look. You can take it with the camera, upload a photo, or use the
          demo model. It is not a live overlay. The physical sari is the source of truth for fabric
          and fall.
        </p>
      </div>
      <ul className="space-y-3 text-sm text-zinc-300">
        <li>We do not keep your face by default. The still lives in this kiosk session only.</li>
        <li>The session clears after {timeoutMinutes} minutes of inactivity, or when you finish.</li>
        <li>Face images are not written to server logs.</li>
      </ul>
      <label className="flex items-start gap-3 text-sm">
        <input type="checkbox" checked={photoOk} onChange={(event) => setPhotoOk(event.target.checked)} />
        I agree to use a front-facing photo (camera, upload, or demo model) for this try-on session.
      </label>
      <label className="flex items-start gap-3 text-sm">
        <input type="checkbox" checked={noKeep} onChange={(event) => setNoKeep(event.target.checked)} />
        I understand the photo is not stored after this session unless I choose to share a look.
      </label>
      <button
        type="button"
        disabled={!ready}
        onClick={continueToCapture}
        className="rounded-full bg-amber-200 px-6 py-3 text-sm font-semibold text-zinc-950 disabled:opacity-40"
      >
        Continue
      </button>
    </main>
  );
}
