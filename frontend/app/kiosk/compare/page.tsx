"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MessageCircle } from "lucide-react";
import { MediaImage } from "@/components/MediaImage";
import { fetchKioskResultBlob, kioskResultUrl } from "@/lib/api";
import {
  compareCopy,
  isSariSku,
  parseComparePayload,
  type ComparePayload,
} from "@/lib/comparePayload";
import { readKioskSession } from "@/lib/kioskSession";
import { shareOrOpenWhatsApp } from "@/lib/whatsappShare";

const kioskToken = process.env.NEXT_PUBLIC_KIOSK_DEVICE_TOKEN ?? "";

/**
 * Read compare payload and session still once on the client.
 */
function readCompareBootstrap(): {
  payload: ComparePayload | null;
  still: string | null;
  redirect: "/kiosk/consent" | "/kiosk/browse" | null;
} {
  if (typeof window === "undefined") {
    return { payload: null, still: null, redirect: null };
  }
  const session = readKioskSession();
  if (!session?.stillDataUrl) {
    return { payload: null, still: null, redirect: "/kiosk/consent" };
  }
  const raw = sessionStorage.getItem("smartmirror.compare");
  if (!raw) {
    return { payload: null, still: session.stillDataUrl, redirect: "/kiosk/browse" };
  }
  const parsed = parseComparePayload(raw);
  if (!parsed) {
    return { payload: null, still: session.stillDataUrl, redirect: "/kiosk/browse" };
  }
  return { payload: parsed, still: session.stillDataUrl, redirect: null };
}

export default function KioskComparePage() {
  const router = useRouter();
  const [boot] = useState(readCompareBootstrap);
  const payload = boot.payload;
  const still = boot.still;
  const [phone, setPhone] = useState("");
  const [shareBusy, setShareBusy] = useState(false);
  const [shareMessage, setShareMessage] = useState<string | null>(null);

  useEffect(() => {
    if (boot.redirect) {
      router.replace(boot.redirect);
    }
  }, [boot.redirect, router]);

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
        isSari: isSariSku({
          garmentCategory: payload.garmentCategory,
          drapeStyle: payload.drapeStyle,
        }),
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

  const copy = compareCopy(payload);
  const generatedUrl = kioskResultUrl(payload.resultUrl);

  return (
    <main className="mx-auto flex min-h-screen max-w-[1600px] flex-col gap-8 px-8 py-10 lg:px-12">
      <header className="flex flex-col gap-3 border-b border-white/10 pb-6">
        <p className="text-[11px] uppercase tracking-[0.35em] text-amber-200/80">Fitting room</p>
        <h1 className="font-display text-5xl font-normal tracking-tight text-zinc-50 lg:text-6xl">
          {copy.title}
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-zinc-400">{copy.subtitle}</p>
      </header>

      <section
        aria-label="Compare your photo, the product, and the generated look"
        className="grid grid-cols-1 gap-0 border-y border-white/10 lg:grid-cols-3"
      >
        <figure className="flex flex-col border-white/10 lg:border-r">
          <div className="relative aspect-[3/4] overflow-hidden bg-zinc-950">
            {/* Session still is a data URL; next/image cannot optimize it. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={still} alt="Your captured photo" className="h-full w-full object-cover" />
          </div>
          <figcaption className="border-t border-white/10 px-1 py-3 text-[11px] uppercase tracking-[0.28em] text-zinc-500">
            {copy.photoLabel}
          </figcaption>
        </figure>

        <figure className="flex flex-col border-white/10 lg:border-r">
          <div className="relative aspect-[3/4] overflow-hidden bg-zinc-950">
            {payload.productImageUrl ? (
              <MediaImage
                url={payload.productImageUrl}
                alt={`Product for ${payload.skuName}`}
                kioskToken={kioskToken}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="grid h-full place-items-center px-6 text-center text-sm text-zinc-500">
                {copy.productPlaceholder}
              </div>
            )}
          </div>
          <figcaption className="border-t border-white/10 px-1 py-3 text-[11px] uppercase tracking-[0.28em] text-zinc-500">
            {copy.productLabel}
          </figcaption>
        </figure>

        <figure className="flex flex-col">
          <div className="relative aspect-[3/4] overflow-hidden bg-zinc-950">
            <MediaImage
              url={generatedUrl}
              alt={`Generated look for ${payload.skuName}`}
              kioskToken={kioskToken}
              className="h-full w-full object-cover"
            />
          </div>
          <figcaption className="border-t border-white/10 px-1 py-3 text-[11px] uppercase tracking-[0.28em] text-zinc-500">
            {copy.generatedLabel}
          </figcaption>
        </figure>
      </section>

      <form
        onSubmit={(event) => void sendToWhatsApp(event)}
        className="flex flex-col gap-4 border border-white/10 px-5 py-5 sm:flex-row sm:items-end"
      >
        <label className="flex min-w-0 flex-1 flex-col gap-2 text-[11px] uppercase tracking-[0.22em] text-zinc-400">
          WhatsApp number
          <input
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="98765 43210"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            className="rounded-none border-0 border-b border-white/20 bg-transparent px-0 py-3 text-base tracking-normal text-zinc-50 outline-none placeholder:text-zinc-600 focus:border-amber-200/70"
          />
        </label>
        <button
          type="submit"
          disabled={shareBusy}
          className="inline-flex items-center justify-center gap-2 border border-amber-200/80 bg-amber-200 px-6 py-3 text-sm font-semibold text-zinc-950 disabled:opacity-40"
        >
          <MessageCircle size={16} />
          {shareBusy ? "Preparing…" : "Send look on WhatsApp"}
        </button>
      </form>
      {shareMessage ? <p className="text-sm text-zinc-400">{shareMessage}</p> : null}
      <div>
        <Link
          href="/kiosk/browse"
          className="inline-flex border border-white/20 px-5 py-3 text-sm text-zinc-200"
        >
          {copy.tryAnother}
        </Link>
      </div>
    </main>
  );
}
