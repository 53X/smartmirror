"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ImageOff } from "lucide-react";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { kioskImageTransition } from "@/lib/kioskMotion";
import { cn } from "@/lib/utils";

interface MediaImageProps {
  url: string;
  alt: string;
  authHeader?: string;
  kioskToken?: string;
  className?: string;
}

/**
 * Load gateway media with auth headers into a blob URL so <img> works.
 */
export function MediaImage({ url, alt, authHeader, kioskToken, className }: MediaImageProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let revoked: string | null = null;
    let cancelled = false;
    async function load(): Promise<void> {
      const headers: HeadersInit = {};
      if (authHeader) {
        headers.Authorization = `Bearer ${authHeader}`;
      }
      if (kioskToken) {
        headers["X-Kiosk-Token"] = kioskToken;
      }
      try {
        const response = await fetch(url, { headers });
        if (!response.ok) {
          throw new Error("Image could not be loaded");
        }
        const blob = await response.blob();
        const created = URL.createObjectURL(blob);
        revoked = created;
        if (!cancelled) {
          setObjectUrl(created);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Image failed");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
      if (revoked) {
        URL.revokeObjectURL(revoked);
      }
    };
  }, [url, authHeader, kioskToken]);

  if (error) {
    return (
      <Empty className={cn("h-full justify-center border-0", className)}>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <ImageOff />
          </EmptyMedia>
          <EmptyTitle>Photo unavailable</EmptyTitle>
          <EmptyDescription>{error}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  if (!objectUrl) {
    return <Skeleton className={cn("rounded-none", className)} aria-hidden />;
  }
  return (
    <motion.img
      src={objectUrl}
      alt={alt}
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={kioskImageTransition}
    />
  );
}
