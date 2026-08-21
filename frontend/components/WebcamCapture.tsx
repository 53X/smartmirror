"use client";

import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import { Camera } from "lucide-react";
import { captureVideoFrame } from "@/lib/captureFrame";
import { MotionButton } from "@/components/MotionButton";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { kioskImageTransition } from "@/lib/kioskMotion";

interface WebcamCaptureProps {
  onCapture: (dataUrl: string) => void;
  facingMode?: "user" | "environment";
  instruction: string;
  buttonLabel: string;
}

/**
 * Front-facing still capture. The stream is local to the device; pixels are not logged.
 */
export function WebcamCapture({
  onCapture,
  facingMode = "user",
  instruction,
  buttonLabel,
}: WebcamCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function start(): Promise<void> {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      if (cancelled) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    }
    void start().catch(() => {
      /* UI shows permission guidance via missing video */
    });
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [facingMode]);

  function handleCapture(): void {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) {
      return;
    }
    onCapture(captureVideoFrame(video));
  }

  return (
    <Card className="overflow-hidden py-0">
      <CardHeader className="py-5">
        <CardTitle>Camera</CardTitle>
        <CardDescription>{instruction}</CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        <div className="relative aspect-[3/4] overflow-hidden bg-background">
          <motion.video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="h-full w-full object-cover"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={kioskImageTransition}
          />
          <div className="pointer-events-none absolute inset-x-[18%] top-[8%] h-[28%] rounded-[46%] border-2 border-primary/70" />
          <div className="pointer-events-none absolute inset-x-[12%] top-[34%] bottom-[10%] rounded-[28px] border border-primary/35" />
          <p className="pointer-events-none absolute inset-x-0 bottom-4 text-center text-sm text-primary">
            Head in the oval · shoulders in the box · nothing on the face
          </p>
        </div>
      </CardContent>
      <CardFooter>
        <MotionButton type="button" className="w-full" onClick={handleCapture}>
          <Camera data-icon="inline-start" />
          {buttonLabel}
        </MotionButton>
      </CardFooter>
    </Card>
  );
}
