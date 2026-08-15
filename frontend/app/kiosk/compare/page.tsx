"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MessageCircle } from "lucide-react";
import { MediaImage } from "@/components/MediaImage";
import { fetchKioskResultBlob, kioskResultUrl } from "@/lib/api";
import { readKioskSession } from "@/lib/kioskSession";
import { shareOrOpenWhatsApp } from "@/lib/whatsappShare";

const kioskToken = process.env.NEXT_PUBLIC_KIOSK_DEVICE_TOKEN ?? "";

interface ComparePayload {
  skuId: string;
  skuName: string;
  resultUrl: string;
}

export default function KioskComparePage() {
  const router = useRouter();
  const [payload, setPayload] = useState<ComparePayload | null>(null);
  const [still, setStill] = useState<string | null>(null);
  const [phone, setPhone] = useState("");
  const [shareBusy, setShareBusy] = useState(false);
  const [shareMessage, setShareMessage] = useState<string | null>(null);

  useEffect(() => {
    const session = readKioskSession();
    if (!session?.stillDataUrl) {
      router.replace("/kiosk/consent");
      return;
    }
    setStill(session.stillDataUrl);
    const raw = sessionStorage.getItem("smartmirror.compare");
    if (!raw) {
      router.replace("/kiosk/browse");
      return;
    }
    setPayload(JSON.parse(raw) as ComparePayload);
  }, [router]);

  async function sendToWhatsApp(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!payload) {
      return;
    }
    setShareBusy(true);
    setShareMessage(null);
    try {
      const imageBlob = await fetchKioskResultBlob(payload.resultUrl);
      const outcome = await shareOrOpenWhatsApp({
        imageBlob,
        skuName: payload.skuName,
        phone,
      });
      setShareMessage(
        outcome === "shared"
          ? "Pick WhatsApp in the share sheet to send this look."
          : "Look saved on this device. Attach that image in the WhatsApp chat that opened.",
      );
    } catch (shareError) {
      setShareMessage(shareError instanceof Error ? shareError.message : "Could not send to WhatsApp");
    } finally {
      setShareBusy(false);
    }
  }

  if (!payload || !still) {
    return null;
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-10">
      <div>
        <h1 className="font-display text-4xl">Compare</h1>
        <p className="text-sm text-zinc-400">
          Left is you. Right is how {payload.skuName} would look. Ask staff to unfold the real sari
          before you buy.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <figure className="overflow-hidden rounded-3xl border border-white/10">
          <img src={still} alt="Your captured still" className="h-[520px] w-full object-cover" />
          <figcaption className="p-3 text-sm text-zinc-400">Your still (this session only)</figcaption>
        </figure>
        <figure className="overflow-hidden rounded-3xl border border-white/10">
          <MediaImage
            url={kioskResultUrl(payload.resultUrl)}
            alt={`Generated look for ${payload.skuName}`}
            kioskToken={kioskToken}
            className="h-[520px] w-full object-cover"
          />
          <figcaption className="p-3 text-sm text-zinc-400">Generated look</figcaption>
        </figure>
      </div>
      <form
        onSubmit={(event) => void sendToWhatsApp(event)}
        className="flex flex-col gap-3 rounded-3xl border border-white/10 bg-white/5 p-5 sm:flex-row sm:items-end"
      >
        <label className="flex min-w-0 flex-1 flex-col gap-2 text-sm text-zinc-300">
          WhatsApp number
          <input
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="98765 43210"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            className="rounded-full border border-white/15 bg-zinc-950 px-4 py-3 text-zinc-50 outline-none focus:border-amber-200/60"
          />
        </label>
        <button
          type="submit"
          disabled={shareBusy}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-amber-200 px-6 py-3 text-sm font-semibold text-zinc-950 disabled:opacity-40"
        >
          <MessageCircle size={16} />
          {shareBusy ? "Preparing…" : "Send look on WhatsApp"}
        </button>
      </form>
      {shareMessage ? <p className="text-sm text-zinc-400">{shareMessage}</p> : null}
      <div className="flex gap-3">
        <Link href="/kiosk/browse" className="rounded-full border border-white/15 px-5 py-3 text-sm">
          Try another sari
        </Link>
      </div>
    </main>
  );
}
