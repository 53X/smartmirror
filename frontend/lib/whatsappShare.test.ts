import { describe, expect, it } from "vitest";
import {
  normalizeWhatsAppPhone,
  shareLookCaption,
  whatsAppClickToChatUrl,
} from "./whatsappShare";

describe("WhatsApp share helpers", () => {
  it("prefixes a 10-digit Indian mobile with 91", () => {
    expect(normalizeWhatsAppPhone("98765 43210")).toBe("919876543210");
  });

  it("strips a leading zero from an 11-digit local number", () => {
    expect(normalizeWhatsAppPhone("09876543210")).toBe("919876543210");
  });

  it("builds a click-to-chat URL with the look caption", () => {
    const url = whatsAppClickToChatUrl("9876543210", shareLookCaption("Bandhani"));
    expect(url).toContain("https://wa.me/919876543210?text=");
    expect(url).toContain("Bandhani");
  });

  it("opens a numberless chat when the phone is empty", () => {
    expect(whatsAppClickToChatUrl("", "hello")).toBe("https://wa.me/?text=hello");
  });
});
