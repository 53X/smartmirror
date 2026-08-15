/**
 * Build WhatsApp click-to-chat links and captions for a generated kiosk look.
 */

export function normalizeWhatsAppPhone(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (!digits) {
    return "";
  }
  if (digits.length === 10) {
    return `91${digits}`;
  }
  if (digits.length === 11 && digits.startsWith("0")) {
    return `91${digits.slice(1)}`;
  }
  return digits;
}

export function whatsAppClickToChatUrl(phone: string, text: string): string {
  const encoded = encodeURIComponent(text);
  const normalized = normalizeWhatsAppPhone(phone);
  if (!normalized) {
    return `https://wa.me/?text=${encoded}`;
  }
  return `https://wa.me/${normalized}?text=${encoded}`;
}

export function shareLookCaption(skuName: string): string {
  return `How ${skuName} would look. The physical sari is the source of truth for fabric and fall.`;
}

export async function shareOrOpenWhatsApp(options: {
  imageBlob: Blob;
  skuName: string;
  phone: string;
}): Promise<"shared" | "opened"> {
  const caption = shareLookCaption(options.skuName);
  const file = new File([options.imageBlob], "sari-look.png", {
    type: options.imageBlob.type || "image/png",
  });
  const canShareFiles =
    typeof navigator !== "undefined" &&
    typeof navigator.share === "function" &&
    typeof navigator.canShare === "function" &&
    navigator.canShare({ files: [file] });
  if (canShareFiles) {
    await navigator.share({ files: [file], title: options.skuName, text: caption });
    return "shared";
  }
  const objectUrl = URL.createObjectURL(options.imageBlob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = "sari-look.png";
  anchor.click();
  URL.revokeObjectURL(objectUrl);
  window.open(whatsAppClickToChatUrl(options.phone, caption), "_blank", "noopener,noreferrer");
  return "opened";
}
