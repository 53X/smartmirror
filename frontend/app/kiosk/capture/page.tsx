"use client";

import { ChangeEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { Camera, ImageUp, UserRound } from "lucide-react";
import { CaptureGuidance } from "@/components/CaptureGuidance";
import { KioskShell } from "@/components/KioskShell";
import { MotionButton } from "@/components/MotionButton";
import { WebcamCapture } from "@/components/WebcamCapture";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { fileToStillDataUrl } from "@/lib/captureFrame";
import { CAMERA_INSTRUCTION, CAPTURE_HEADLINE } from "@/lib/captureGuidance";
import { kioskFadeTransition, kioskImageTransition } from "@/lib/kioskMotion";
import { readKioskSession, writeKioskSession } from "@/lib/kioskSession";

type Source = "camera" | "upload" | "demo";

const DEMO_MODEL_SRC = "/demo-model.jpg";

const sourceFade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: kioskFadeTransition,
};

export default function KioskCapturePage() {
  const router = useRouter();
  const [source, setSource] = useState<Source>("demo");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function commitStill(dataUrl: string): void {
    const session = readKioskSession();
    if (!session) {
      router.replace("/kiosk/attract");
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

  async function applyDemoModelStill(): Promise<void> {
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
    <KioskShell
      align="center"
      className="max-w-2xl"
      place="Your still"
      title="Who are we dressing?"
      subtitle={CAPTURE_HEADLINE}
    >
      <CaptureGuidance />

      <ToggleGroup
        type="single"
        variant="outline"
        size="kiosk"
        spacing={2}
        value={source}
        onValueChange={(value) => {
          if (value === "upload" || value === "demo" || value === "camera") {
            setSource(value);
          }
        }}
        className="w-full"
        aria-label="Photo source"
      >
        <ToggleGroupItem value="upload" className="flex-1">
          <ImageUp data-icon="inline-start" />
          Upload
        </ToggleGroupItem>
        <ToggleGroupItem value="demo" className="flex-1">
          <UserRound data-icon="inline-start" />
          Demo model
        </ToggleGroupItem>
        <ToggleGroupItem value="camera" className="flex-1">
          <Camera data-icon="inline-start" />
          Camera
        </ToggleGroupItem>
      </ToggleGroup>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>We couldn't use that photo</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <AnimatePresence mode="wait">
        {source === "upload" ? (
          <motion.label key="upload" {...sourceFade} className="block cursor-pointer">
            <Empty className="border border-dashed py-20">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  {busy ? <Spinner /> : <ImageUp />}
                </EmptyMedia>
                <EmptyTitle>
                  {busy ? "Opening your photo…" : "Add a front-facing photo"}
                </EmptyTitle>
                <EmptyDescription>
                  Tap to choose a file — face clear, one person, nothing covering the face.
                </EmptyDescription>
              </EmptyHeader>
              <input
                type="file"
                accept="image/*"
                className="sr-only"
                onChange={(event) => void handleUpload(event)}
              />
            </Empty>
          </motion.label>
        ) : null}

        {source === "demo" ? (
          <motion.div key="demo" {...sourceFade}>
            <Card className="overflow-hidden py-0">
              <CardHeader className="py-5">
                <CardTitle>Demo model</CardTitle>
                <CardDescription>
                  Prefer a private try-on? Use our model instead of your own photo.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <motion.img
                  src={DEMO_MODEL_SRC}
                  alt="Demo model for sari try-on"
                  className="max-h-[min(56vh,520px)] w-full object-cover"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={kioskImageTransition}
                />
              </CardContent>
              <CardFooter>
                <MotionButton
                  type="button"
                  className="w-full"
                  disabled={busy}
                  onClick={() => void applyDemoModelStill()}
                >
                  {busy ? <Spinner data-icon="inline-start" /> : null}
                  {busy ? "Loading…" : "Dress this model"}
                </MotionButton>
              </CardFooter>
            </Card>
          </motion.div>
        ) : null}

        {source === "camera" ? (
          <motion.div key="camera" {...sourceFade}>
            <WebcamCapture
              instruction={CAMERA_INSTRUCTION}
              buttonLabel="Take my photo"
              onCapture={commitStill}
            />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </KioskShell>
  );
}
