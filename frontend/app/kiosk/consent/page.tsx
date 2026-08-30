"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { KioskShell } from "@/components/KioskShell";
import { MotionButton } from "@/components/MotionButton";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { Separator } from "@/components/ui/separator";
import { kioskEnterTransition } from "@/lib/kioskMotion";
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
    <KioskShell
      align="center"
      className="max-w-3xl"
      place="Welcome"
      title="Step into the fitting room"
      subtitle={
        <>
          We'll take <strong className="text-foreground">one front-facing still</strong> so you can
          see how a piece would look on you — camera, upload, or our demo model. The garment in hand
          is still the real thing for fabric and fall.
        </>
      }
    >
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={kioskEnterTransition}
      >
        <Card>
          <CardHeader>
            <Badge variant="secondary">This visit only</Badge>
            <CardTitle>A quick word about your photo</CardTitle>
            <CardDescription>
              Your still stays on this mirror for the visit. Face images are not written to server
              logs.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-8">
            <ul className="flex flex-col gap-3 text-base text-muted-foreground">
              <li>We don't keep your face by default.</li>
              <li>
                The visit clears after {timeoutMinutes} minutes of stillness, or when you finish.
              </li>
              <li>Sending a look to your phone is optional — only if you ask.</li>
            </ul>
            <Separator />
            <FieldSet>
              <FieldLegend className="sr-only">Session consent</FieldLegend>
              <FieldGroup className="gap-5">
                <Field orientation="horizontal" className="items-start">
                  <Checkbox
                    id="consent-photo"
                    className="size-6"
                    checked={photoOk}
                    onCheckedChange={(value) => setPhotoOk(value === true)}
                  />
                  <FieldLabel htmlFor="consent-photo" className="text-base font-normal leading-relaxed">
                    I'm fine using a front-facing photo (camera, upload, or demo model) for this
                    try-on.
                  </FieldLabel>
                </Field>
                <Field orientation="horizontal" className="items-start">
                  <Checkbox
                    id="consent-storage"
                    className="size-6"
                    checked={noKeep}
                    onCheckedChange={(value) => setNoKeep(value === true)}
                  />
                  <FieldLabel htmlFor="consent-storage" className="text-base font-normal leading-relaxed">
                    I understand the photo isn't kept after this visit unless I choose to send a look.
                  </FieldLabel>
                </Field>
              </FieldGroup>
            </FieldSet>
          </CardContent>
          <CardFooter>
            <MotionButton
              type="button"
              className="w-full"
              disabled={!ready}
              onClick={continueToCapture}
            >
              Begin
            </MotionButton>
          </CardFooter>
        </Card>
      </motion.div>
      <p className="text-center text-sm text-muted-foreground">
        Staff?{" "}
        <a href="/staff/login" className="text-primary underline-offset-4 hover:underline">
          Sign in
        </a>
      </p>
    </KioskShell>
  );
}
