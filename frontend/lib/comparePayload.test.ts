import { describe, expect, it } from "vitest";
import {
  compareCopy,
  comparePanelSources,
  isSariSku,
  parseComparePayload,
  tryOnGarmentCategory,
} from "./comparePayload";

describe("comparePayload", () => {
  it("yields three image sources when product and result are present", () => {
    const payload = parseComparePayload(
      JSON.stringify({
        skuId: "sku-1",
        skuName: "Bandhani",
        resultUrl: "http://gateway/results/look.png",
        productImageUrl: "http://gateway/kiosk/media/sku-1/reconstructed.png",
        drapeStyle: "straight",
      }),
    );
    expect(payload).not.toBeNull();
    const sources = comparePanelSources(payload!, "data:image/jpeg;base64,abc", (url) =>
      url.replace("http://gateway/results/", "https://kiosk/results/"),
    );
    expect(sources.photoSrc).toBe("data:image/jpeg;base64,abc");
    expect(sources.productSrc).toContain("reconstructed.png");
    expect(sources.generatedSrc).toBe("https://kiosk/results/look.png");
    expect([sources.photoSrc, sources.productSrc, sources.generatedSrc]).toHaveLength(3);
  });

  it("keeps the product column empty-string when productImageUrl is missing", () => {
    const payload = parseComparePayload(
      JSON.stringify({ skuId: "a", skuName: "Look", resultUrl: "/r.png" }),
    );
    expect(payload?.productImageUrl).toBe("");
  });

  it("isSari is false unless category is saree or drape is nivi", () => {
    expect(isSariSku({ garmentCategory: "lehenga", drapeStyle: "straight" })).toBe(false);
    expect(isSariSku({ garmentCategory: "saree" })).toBe(true);
    expect(isSariSku({ drapeStyle: "nivi" })).toBe(true);
  });

  it("omits the word sari from copy when isSari is false", () => {
    const copy = compareCopy({
      skuId: "1",
      skuName: "Silk blouse set",
      resultUrl: "/r.png",
      productImageUrl: "/p.png",
      garmentCategory: "blouse",
    });
    const blob = `${copy.title} ${copy.subtitle} ${copy.photoLabel} ${copy.productLabel} ${copy.generatedLabel} ${copy.tryAnother} ${copy.productPlaceholder}`;
    expect(blob.toLowerCase()).not.toContain("sari");
    expect(blob.toLowerCase()).not.toContain("saree");
  });

  it("may mention sari when isSari is true", () => {
    const copy = compareCopy({
      skuId: "1",
      skuName: "Banarasi",
      resultUrl: "/r.png",
      productImageUrl: "/p.png",
      garmentCategory: "saree",
      drapeStyle: "nivi",
    });
    expect(copy.subtitle.toLowerCase()).toContain("sari");
  });

  it("maps nivi drape to saree category for try-on when category is unset", () => {
    expect(tryOnGarmentCategory({ drape_style: "nivi" })).toBe("saree");
    expect(tryOnGarmentCategory({ garment_category: "lehenga", drape_style: "nivi" })).toBe(
      "lehenga",
    );
  });
});
