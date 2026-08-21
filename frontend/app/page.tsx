import Link from "next/link";
import { Monitor, UserRound } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center gap-10 px-8 py-16">
      <div className="flex flex-col gap-4">
        <p className="text-sm uppercase tracking-[0.25em] text-primary">Smartmirror</p>
        <h1 className="font-display max-w-2xl text-5xl leading-tight">
          Still-image sari try-on. How it would look — not a live overlay.
        </h1>
        <p className="max-w-xl text-lg text-muted-foreground">
          Staff photograph the parts. We reconstruct the sari. The kiosk captures one front still
          and generates looks. The cloth in hand remains the source of truth for hand-feel.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/kiosk/consent" className="block">
          <Card className="h-full">
            <CardHeader>
              <Monitor className="text-primary" />
              <CardTitle className="font-display text-2xl">Kiosk</CardTitle>
              <CardDescription>Consent, capture a still, swipe approved SKUs.</CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link href="/staff/login" className="block">
          <Card className="h-full">
            <CardHeader>
              <UserRound className="text-primary" />
              <CardTitle className="font-display text-2xl">Staff</CardTitle>
              <CardDescription>Sign in, guided part capture, reconstruct, approve.</CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </main>
  );
}
