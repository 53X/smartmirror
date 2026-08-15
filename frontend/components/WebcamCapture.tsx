"use client";

import { useEffect, useRef } from "react";
import { Camera } from "lucide-react";
import { captureVideoFrame } from "@/lib/captureFrame";

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
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-300">{instruction}</p>
      <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-black aspect-[3/4]">
        <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
        <div className="pointer-events-none absolute inset-x-8 top-10 bottom-16 rounded-[40%] border border-amber-200/40" />
      </div>
      <button
        type="button"
        onClick={handleCapture}
        className="inline-flex items-center justify-center gap-2 rounded-full bg-amber-200 px-6 py-3 text-sm font-semibold text-zinc-950"
      >
        <Camera size={18} />
        {buttonLabel}
      </button>
    </div>
  );
}
