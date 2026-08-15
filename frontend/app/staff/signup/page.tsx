"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useStaffAuth } from "@/components/StaffAuthProvider";
import { getSupabaseBrowserClient, isSupabaseConfigured } from "@/lib/supabase/browser";

export default function StaffSignupPage() {
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
      const { data, error: authError } = await supabase.auth.signUp({ email, password });
      if (authError) {
        throw new Error(authError.message);
      }
      if (data.session) {
        setAccessToken(data.session.access_token);
        router.push("/staff/skus");
        return;
      }
      setError("Check your email to confirm the staff account, then sign in.");
    } catch (signUpError) {
      setError(signUpError instanceof Error ? signUpError.message : "Sign-up failed");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6">
      <h1 className="font-display text-4xl">Staff sign up</h1>
      <p className="text-sm text-zinc-400">For store associates. Customers never register here.</p>
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
            minLength={8}
            placeholder="Password (8+ characters)"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded-xl border border-white/10 bg-zinc-900 px-4 py-3"
          />
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          <button type="submit" className="rounded-full bg-amber-200 py-3 text-sm font-semibold text-zinc-950">
            Create staff account
          </button>
        </form>
      ) : (
        <p className="text-sm text-zinc-400">Supabase env is not set. Use local bypass from the sign-in page when enabled.</p>
      )}
      <Link href="/staff/login" className="text-sm text-amber-200 underline">
        Already have an account
      </Link>
    </main>
  );
}
