/**
 * Compare-screen payload, sari detection, and garment-agnostic kiosk copy.
 */

export interface ComparePayload {
  skuId: string;
  skuName: string;
  resultUrl: string;
  productImageUrl: string;
  drapeStyle?: string;
  garmentCategory?: string;
}

export interface CompareCopy {
  title: string;
  subtitle: string;
  photoLabel: string;
  productLabel: string;
  generatedLabel: string;
  tryAnother: string;
  productPlaceholder: string;
}

export interface ComparePanelSources {
  photoSrc: string;
  productSrc: string;
  generatedSrc: string;
}

/**
 * True when the SKU is a saree (category) or Nivi drape.
 */
export function isSariSku(input: {
  garmentCategory?: string | null;
  drapeStyle?: string | null;
}): boolean {
  return input.garmentCategory === "saree" || input.drapeStyle === "nivi";
}

/**
 * Read a filename from a storage or media URL.
 */
export function filenameFromUrl(url: string | null | undefined): string | null {
  if (!url) {
    return null;
  }
  const segment = url.split("/").pop();
  return segment && segment.length > 0 ? segment : null;
}

/**
 * Parse sessionStorage JSON for the compare screen. Missing product URL becomes "".
 */
export function parseComparePayload(raw: string): ComparePayload | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    const record = parsed as Record<string, unknown>;
    if (
      typeof record.skuId !== "string" ||
      typeof record.skuName !== "string" ||
      typeof record.resultUrl !== "string"
    ) {
      return null;
    }
    return {
      skuId: record.skuId,
      skuName: record.skuName,
      resultUrl: record.resultUrl,
      productImageUrl: typeof record.productImageUrl === "string" ? record.productImageUrl : "",
      drapeStyle: typeof record.drapeStyle === "string" ? record.drapeStyle : undefined,
      garmentCategory: typeof record.garmentCategory === "string" ? record.garmentCategory : undefined,
    };
  } catch {
    return null;
  }
}

/**
 * Kiosk-visible copy. Mentions "sari" only when isSariSku is true.
 */
export function compareCopy(payload: ComparePayload): CompareCopy {
  const sari = isSariSku({
    garmentCategory: payload.garmentCategory,
    drapeStyle: payload.drapeStyle,
  });
  return {
    title: payload.skuName,
    subtitle: sari
      ? `Your still, the sari, and how it would look on you. Ask staff to unfold the real piece before you decide.`
      : `Your still, the piece, and how it would look on you. The garment in hand stays the source of truth.`,
    photoLabel: "You",
    productLabel: "The piece",
    generatedLabel: "On you",
    tryAnother: "Browse another look",
    productPlaceholder: sari ? "Sari image unavailable" : "Product image unavailable",
  };
}

/**
 * The three image sources the compare triptych must render.
 */
export function comparePanelSources(
  payload: ComparePayload,
  stillDataUrl: string,
  resolveResultUrl: (resultUrl: string) => string,
): ComparePanelSources {
  return {
    photoSrc: stillDataUrl,
    productSrc: payload.productImageUrl,
    generatedSrc: resolveResultUrl(payload.resultUrl),
  };
}

/**
 * Category sent to try-on: explicit category, else saree when Nivi.
 */
export function tryOnGarmentCategory(sku: {
  garment_category?: string | null;
  drape_style?: string | null;
}): string | undefined {
  if (sku.garment_category) {
    return sku.garment_category;
  }
  if (sku.drape_style === "nivi") {
    return "saree";
  }
  return undefined;
}
