"use client";

import { FormEvent, type ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { ImageOff, MessageCircle } from "lucide-react";
import { KioskShell } from "@/components/KioskShell";
import { MediaImage } from "@/components/MediaImage";
import { MotionButton } from "@/components/MotionButton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { fetchKioskResultBlob, kioskResultUrl } from "@/lib/api";
import {
  compareCopy,
  isSariSku,
  parseComparePayload,
  type ComparePayload,
} from "@/lib/comparePayload";
import { kioskCompareStaggerSeconds, kioskImageTransition } from "@/lib/kioskMotion";
import { KIOSK_COMPARE_KEY, readKioskSession } from "@/lib/kioskSession";
import { shareOrOpenWhatsApp } from "@/lib/whatsappShare";
import { cn } from "@/lib/utils";

const kioskToken = process.env.NEXT_PUBLIC_KIOSK_DEVICE_TOKEN ?? "";

const triptychContainer = {
  hidden: {},
  show: {
    transition: { staggerChildren: kioskCompareStaggerSeconds },
  },
};

const triptychPanel = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: kioskImageTransition,
  },
};

const spotlightPanel = {
  hidden: { opacity: 0, y: 18, scale: 0.96 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1.03,
    transition: { ...kioskImageTransition, duration: 0.48 },
  },
};

/**
 * One lookbook panel in the compare triptych.
 */
function ComparePanel({
  label,
  children,
  spotlight = false,
}: {
  label: string;
  children: ReactNode;
  spotlight?: boolean;
}) {
  return (
    <motion.div
      variants={spotlight ? spotlightPanel : triptychPanel}
      className={cn("min-w-0 flex-1", spotlight && "relative z-10 lg:flex-[1.15]")}
    >
      <Card
        className={cn(
          "overflow-hidden py-0",
          spotlight && "ring-2 ring-primary/70 shadow-[0_0_0_1px_oklch(0.905_0.118_98_/_0.25)]",
        )}
      >
        <CardContent className="relative p-0">
          <div className="kiosk-frame-spotlight absolute inset-0 opacity-60" aria-hidden />
          <div className="relative aspect-[3/4] overflow-hidden bg-background">{children}</div>
        </CardContent>
        <CardFooter className="justify-center gap-2">
          <Badge variant={spotlight ? "default" : "secondary"}>{label}</Badge>
        </CardFooter>
      </Card>
    </motion.div>
  );
}

/**
 * Read compare payload and session still once on the client.
 */
function readCompareBootstrap(): {
  payload: ComparePayload | null;
  still: string | null;
  redirect: "/kiosk/attract" | "/kiosk/browse" | null;
} {
  if (typeof window === "undefined") {
    return { payload: null, still: null, redirect: null };
  }
  const session = readKioskSession();
  if (!session?.stillDataUrl) {
    return { payload: null, still: null, redirect: "/kiosk/attract" };
  }
  const raw = sessionStorage.getItem(KIOSK_COMPARE_KEY);
  if (!raw) {
    return { payload: null, still: session.stillDataUrl, redirect: "/kiosk/browse" };
  }
  const parsed = parseComparePayload(raw);
  if (!parsed) {
    return { payload: null, still: session.stillDataUrl, redirect: "/kiosk/browse" };
  }
  return { payload: parsed, still: session.stillDataUrl, redirect: null };
}

/**
 * Compare your still, the product, and the generated look — generated is spotlighted.
 */
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
          ? "Pick WhatsApp in the share sheet to send this look to your phone."
          : "Look saved on this device. Attach that image in the WhatsApp chat that opened.",
      );
    } catch (shareError) {
      setShareMessage(shareError instanceof Error ? shareError.message : "Could not send to your phone");
    } finally {
      setShareBusy(false);
    }
  }

  if (!payload || !still) {
    return null;
  }

  const copy = compareCopy(payload);
  const generatedUrl = kioskResultUrl(payload.resultUrl);
  const shareFailed = shareMessage !== null && /could not/i.test(shareMessage);

  return (
    <KioskShell
      className="max-w-[1600px]"
      place="Your look"
      title={copy.title}
      subtitle={copy.subtitle}
    >
      <motion.section
        aria-label="Compare your photo, the product, and the generated look"
        className="flex flex-col items-stretch gap-6 lg:flex-row lg:items-end"
        variants={triptychContainer}
        initial="hidden"
        animate="show"
      >
        <ComparePanel label={copy.photoLabel}>
          <motion.img
            src={still}
            alt="Your captured photo"
            className="h-full w-full object-cover opacity-90"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.9 }}
            transition={kioskImageTransition}
          />
        </ComparePanel>

        <ComparePanel label={copy.productLabel}>
          {payload.productImageUrl ? (
            <MediaImage
              url={payload.productImageUrl}
              alt={`Product for ${payload.skuName}`}
              kioskToken={kioskToken}
              className="h-full w-full object-cover opacity-90"
            />
          ) : (
            <Empty className="h-full justify-center border-0">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <ImageOff />
                </EmptyMedia>
                <EmptyTitle>Product photo unavailable</EmptyTitle>
                <EmptyDescription>{copy.productPlaceholder}</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </ComparePanel>

        <ComparePanel label={copy.generatedLabel} spotlight>
          <MediaImage
            url={generatedUrl}
            alt={`Generated look for ${payload.skuName}`}
            kioskToken={kioskToken}
            className="h-full w-full object-cover"
          />
        </ComparePanel>
      </motion.section>

      <Card>
        <CardHeader>
          <CardTitle>Send to my phone</CardTitle>
          <CardDescription>Optional — we'll open WhatsApp with this look.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={(event) => void sendToWhatsApp(event)}>
            <FieldGroup className="sm:flex-row sm:items-end">
              <Field>
                <FieldLabel htmlFor="whatsapp-phone">Mobile number</FieldLabel>
                <Input
                  id="whatsapp-phone"
                  name="whatsapp"
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="98765 43210…"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  className="h-14 min-h-14 text-base md:text-base"
                />
              </Field>
              <MotionButton type="submit" disabled={shareBusy}>
                {shareBusy ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <MessageCircle data-icon="inline-start" />
                )}
                {shareBusy ? "Preparing…" : "Send to my phone"}
              </MotionButton>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>

      {shareMessage ? (
        <Alert variant={shareFailed ? "destructive" : "default"}>
          <AlertTitle>{shareFailed ? "Couldn't send" : "On its way"}</AlertTitle>
          <AlertDescription>{shareMessage}</AlertDescription>
        </Alert>
      ) : null}

      <Button asChild variant="outline" size="kiosk">
        <Link href="/kiosk/browse">{copy.tryAnother}</Link>
      </Button>
    </KioskShell>
  );
}
