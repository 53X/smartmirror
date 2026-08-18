/**
 * Gateway client for kiosk (device token) and staff (Supabase JWT or local bypass).
 */

export interface PartImage {
  part_type: string;
  media_url: string;
  content_type: string;
}

export interface SkuRecord {
  id: string;
  barcode: string;
  name: string;
  fabric: string | null;
  length_yards: number | null;
  pallu_shoulder: string;
  drape_style: string;
  garment_category?: string | null;
  price_minor: number | null;
  stock_count: number;
  keep_customer_blouse: boolean;
  parts: PartImage[];
  reconstructed_asset_url: string | null;
  approved_for_kiosk: boolean;
}

export interface JobRecord {
  id: string;
  kind: string;
  status: "queued" | "running" | "succeeded" | "failed";
  sku_id: string | null;
  result_url: string | null;
  error_message: string | null;
  vendor: string;
}

function gatewayUrl(): string {
  return process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://127.0.0.1:8001";
}

function kioskHeaders(): HeadersInit {
  return {
    "X-Kiosk-Token": process.env.NEXT_PUBLIC_KIOSK_DEVICE_TOKEN ?? "",
  };
}

function staffHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export async function listKioskSkus(): Promise<SkuRecord[]> {
  const response = await fetch(`${gatewayUrl()}/kiosk/skus`, { headers: kioskHeaders() });
  return parseJson<SkuRecord[]>(response);
}

export async function createTryOnJob(
  sku: SkuRecord,
  sessionId: string,
  stillBlob: Blob,
): Promise<JobRecord> {
  if (!sku.reconstructed_asset_url) {
    throw new Error("This garment has no product image yet");
  }
  const body = new FormData();
  body.set("sku_id", sku.id);
  body.set("session_id", sessionId);
  body.set("reconstructed_asset_url", sku.reconstructed_asset_url);
  body.set("customer_still", stillBlob, "customer.jpg");
  body.set("drape_style", sku.drape_style);
  const category = sku.garment_category ?? (sku.drape_style === "nivi" ? "saree" : undefined);
  if (category) {
    body.set("garment_category", category);
  }
  const response = await fetch(`${gatewayUrl()}/kiosk/try-on`, {
    method: "POST",
    headers: kioskHeaders(),
    body,
  });
  return parseJson<JobRecord>(response);
}

export async function pollKioskJob(jobId: string): Promise<JobRecord> {
  const response = await fetch(`${gatewayUrl()}/kiosk/jobs/${jobId}`, {
    headers: kioskHeaders(),
  });
  return parseJson<JobRecord>(response);
}

export function kioskMediaUrl(skuId: string, filename: string): string {
  return `${gatewayUrl()}/kiosk/media/${skuId}/${filename}`;
}

export function kioskResultUrl(resultUrl: string): string {
  const filename = resultUrl.split("/").pop() ?? "";
  return `${gatewayUrl()}/kiosk/results/${filename}`;
}

/**
 * Download a generated try-on PNG using the kiosk device token.
 */
export async function fetchKioskResultBlob(resultUrl: string): Promise<Blob> {
  const response = await fetch(kioskResultUrl(resultUrl), { headers: kioskHeaders() });
  if (!response.ok) {
    throw new Error("Could not load the generated look");
  }
  return response.blob();
}

export async function listStaffSkus(accessToken: string): Promise<SkuRecord[]> {
  const response = await fetch(`${gatewayUrl()}/staff/skus`, {
    headers: staffHeaders(accessToken),
  });
  return parseJson<SkuRecord[]>(response);
}

export async function createStaffSku(
  accessToken: string,
  payload: { barcode: string; name: string; fabric?: string },
): Promise<SkuRecord> {
  const response = await fetch(`${gatewayUrl()}/staff/skus`, {
    method: "POST",
    headers: {
      ...staffHeaders(accessToken),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJson<SkuRecord>(response);
}

export async function uploadStaffPart(
  accessToken: string,
  skuId: string,
  partType: string,
  file: Blob,
): Promise<SkuRecord> {
  const body = new FormData();
  body.set("part_type", partType);
  body.set("file", file, `${partType}.jpg`);
  const response = await fetch(`${gatewayUrl()}/staff/skus/${skuId}/parts`, {
    method: "POST",
    headers: staffHeaders(accessToken),
    body,
  });
  return parseJson<SkuRecord>(response);
}

export async function startReconstructJob(
  accessToken: string,
  skuId: string,
): Promise<JobRecord> {
  const response = await fetch(`${gatewayUrl()}/staff/skus/${skuId}/reconstruct`, {
    method: "POST",
    headers: staffHeaders(accessToken),
  });
  return parseJson<JobRecord>(response);
}

export async function pollStaffJob(accessToken: string, jobId: string): Promise<JobRecord> {
  const response = await fetch(`${gatewayUrl()}/staff/jobs/${jobId}`, {
    headers: staffHeaders(accessToken),
  });
  return parseJson<JobRecord>(response);
}

export async function saveReconstructedAsset(
  accessToken: string,
  skuId: string,
  imageBlob: Blob,
): Promise<SkuRecord> {
  const body = new FormData();
  body.set("file", imageBlob, "reconstructed.png");
  const response = await fetch(`${gatewayUrl()}/staff/skus/${skuId}/reconstructed`, {
    method: "POST",
    headers: staffHeaders(accessToken),
    body,
  });
  return parseJson<SkuRecord>(response);
}

export async function approveSku(
  accessToken: string,
  skuId: string,
  approved: boolean,
): Promise<SkuRecord> {
  const response = await fetch(
    `${gatewayUrl()}/staff/skus/${skuId}/approve?approved=${approved}`,
    { method: "POST", headers: staffHeaders(accessToken) },
  );
  return parseJson<SkuRecord>(response);
}

export function staffResultUrl(resultUrl: string): string {
  const filename = resultUrl.split("/").pop() ?? "";
  return `${gatewayUrl()}/staff/results/${filename}`;
}

export function staffMediaUrl(skuId: string, filename: string): string {
  return `${gatewayUrl()}/staff/media/${skuId}/${filename}`;
}
