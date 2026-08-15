"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useStaffAuth } from "@/components/StaffAuthProvider";
import {
  DEV_STAFF_TOKEN,
  getSupabaseBrowserClient,
  isAuthDevBypass,
  isSupabaseConfigured,
} from "@/lib/supabase/browser";

export default function StaffLoginPage() {
  const router = useRouter();
  const { setAccessToken } = useStaffAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const supabaseReady = isSupabaseConfigured();

  async function onSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      const supabase = getSupabaseBrowserClient();
      const { data, error: authError } = await supabase.auth.signInWithPassword({ email, password });
      if (authError || !data.session) {
        throw new Error(authError?.message || "Sign-in failed");
      }
      setAccessToken(data.session.access_token);
      router.push("/staff/skus");
    } catch (signInError) {
      setError(signInError instanceof Error ? signInError.message : "Sign-in failed");
    }
  }

  function useLocalBypass(): void {
    setAccessToken(DEV_STAFF_TOKEN);
    router.push("/staff/skus");
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6">
      <h1 className="font-display text-4xl">Staff sign in</h1>
      <p className="text-sm text-zinc-400">Shoppers do not create accounts. This is for store associates only.</p>
      {supabaseReady ? (
        <form onSubmit={(event) => void onSubmit(event)} className="flex flex-col gap-3">
          <input
            type="email"
            required
            placeholder="Work email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded-xl border border-white/10 bg-zinc-900 px-4 py-3"
          />
          <input
            type="password"
            required
            placeholder="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded-xl border border-white/10 bg-zinc-900 px-4 py-3"
          />
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          <button type="submit" className="rounded-full bg-amber-200 py-3 text-sm font-semibold text-zinc-950">
            Sign in
          </button>
        </form>
      ) : (
        <p className="text-sm text-zinc-400">
          Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in
          frontend/.env.local to enable email sign-in.
        </p>
      )}
      {isAuthDevBypass() ? (
        <button
          type="button"
          onClick={useLocalBypass}
          className="rounded-full border border-white/15 py-3 text-sm"
        >
          Local staff session (dev bypass)
        </button>
      ) : null}
      <Link href="/staff/signup" className="text-sm text-amber-200 underline">
        Create a staff account
      </Link>
    </main>
  );
}
