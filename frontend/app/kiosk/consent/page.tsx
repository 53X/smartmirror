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
      place="Consent"
      title="Before we take a photo"
      subtitle={
        <>
          This kiosk uses <strong className="text-foreground">one front-facing still</strong> to
          show how a sari would look. Take it with the camera, upload a photo, or use the demo model.
          It is not a live overlay — the physical sari is the source of truth for fabric and fall.
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
            <Badge variant="secondary">Session only</Badge>
            <CardTitle>How we handle your photo</CardTitle>
            <CardDescription>
              The still lives in this kiosk session only. Face images are not written to server logs.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-8">
            <ul className="flex flex-col gap-3 text-base text-muted-foreground">
              <li>We do not keep your face by default.</li>
              <li>
                The session clears after {timeoutMinutes} minutes of inactivity, or when you finish.
              </li>
              <li>Sharing a look on WhatsApp is optional and happens only if you choose it.</li>
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
                    I agree to use a front-facing photo (camera, upload, or demo model) for this try-on
                    session.
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
                    I understand the photo is not stored after this session unless I choose to share a
                    look.
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
              Continue
            </MotionButton>
          </CardFooter>
        </Card>
      </motion.div>
    </KioskShell>
  );
}
