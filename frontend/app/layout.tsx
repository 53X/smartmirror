import type { Metadata } from "next";
import { Cormorant_Garamond, Outfit } from "next/font/google";
import { MotionRoot } from "@/components/MotionRoot";
import { cn } from "@/lib/utils";
import "./globals.css";

const display = Cormorant_Garamond({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const sans = Outfit({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Smartmirror — sari try-on kiosk",
  description:
    "In-store stills kiosk: reconstruct a sari from part photos, then show how it would look on you. Not a live overlay.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={cn("dark h-full antialiased", display.variable, sans.variable)}>
      <body className="min-h-full bg-background text-foreground">
        <MotionRoot>{children}</MotionRoot>
      </body>
    </html>
  );
}
