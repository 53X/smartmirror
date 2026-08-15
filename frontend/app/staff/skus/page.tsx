"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useStaffAuth, useStaffTokenOrBypass } from "@/components/StaffAuthProvider";
import { createStaffSku, listStaffSkus, type SkuRecord } from "@/lib/api";

export default function StaffSkuListPage() {
  const router = useRouter();
  const token = useStaffTokenOrBypass();
  const { setAccessToken } = useStaffAuth();
  const [skus, setSkus] = useState<SkuRecord[]>([]);
  const [barcode, setBarcode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      router.replace("/staff/login");
      return;
    }
    void listStaffSkus(token)
      .then(setSkus)
      .catch((loadError: Error) => setError(loadError.message));
  }, [token, router]);

  async function onCreate(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    setError(null);
    try {
      const created = await createStaffSku(token, { barcode, name });
      setSkus((current) => [created, ...current]);
      setBarcode("");
      setName("");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create SKU");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-4xl">Catalog</h1>
        <button
          type="button"
          className="text-sm text-zinc-400 underline"
          onClick={() => {
            setAccessToken(null);
            router.push("/staff/login");
          }}
        >
          Sign out
        </button>
      </div>
      <p className="text-sm text-zinc-400">
        Follow the part-shot SOP, reconstruct, then approve. Unapproved SKUs never appear on the kiosk.
      </p>
      <form onSubmit={(event) => void onCreate(event)} className="flex flex-wrap gap-3">
        <input
          required
          placeholder="Barcode"
          value={barcode}
          onChange={(event) => setBarcode(event.target.value)}
          className="flex-1 rounded-xl border border-white/10 bg-zinc-900 px-4 py-3"
        />
        <input
          required
          placeholder="Sari name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="flex-[2] rounded-xl border border-white/10 bg-zinc-900 px-4 py-3"
        />
        <button type="submit" className="rounded-full bg-amber-200 px-5 py-3 text-sm font-semibold text-zinc-950">
          Add SKU
        </button>
      </form>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      <ul className="space-y-3">
        {skus.map((sku) => (
          <li key={sku.id} className="rounded-2xl border border-white/10 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-widest text-amber-200/80">{sku.barcode}</p>
                <h2 className="font-display text-2xl">{sku.name}</h2>
                <p className="text-sm text-zinc-400">
                  {sku.parts.length} parts · {sku.approved_for_kiosk ? "on kiosk" : "hidden from kiosk"}
                </p>
              </div>
              <Link href={`/staff/capture/${sku.id}`} className="rounded-full border border-white/15 px-4 py-2 text-sm">
                Capture / approve
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
