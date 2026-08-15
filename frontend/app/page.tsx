import Link from "next/link";
import { Monitor, UserRound } from "lucide-react";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center gap-10 px-8 py-16">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-amber-200/80">Smartmirror</p>
        <h1 className="font-display mt-3 max-w-2xl text-5xl leading-tight text-zinc-50">
          Still-image sari try-on. How it would look — not a live overlay.
        </h1>
        <p className="mt-4 max-w-xl text-lg text-zinc-400">
          Staff photograph the parts. We reconstruct the sari. The kiosk captures one front still and
          generates looks. The cloth in hand remains the source of truth for hand-feel.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/kiosk/consent"
          className="rounded-3xl border border-white/10 bg-white/5 p-8 transition hover:border-amber-200/40"
        >
          <Monitor className="text-amber-200" />
          <h2 className="mt-4 font-display text-2xl">Kiosk</h2>
          <p className="mt-2 text-sm text-zinc-400">Consent, capture a still, swipe approved SKUs.</p>
        </Link>
        <Link
          href="/staff/login"
          className="rounded-3xl border border-white/10 bg-white/5 p-8 transition hover:border-amber-200/40"
        >
          <UserRound className="text-amber-200" />
          <h2 className="mt-4 font-display text-2xl">Staff</h2>
          <p className="mt-2 text-sm text-zinc-400">Sign in, guided part capture, reconstruct, approve.</p>
        </Link>
      </div>
    </main>
  );
}
