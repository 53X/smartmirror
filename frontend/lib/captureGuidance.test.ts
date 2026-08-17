import { describe, expect, it } from "vitest";
import { CAMERA_INSTRUCTION, CAPTURE_HEADLINE, CAPTURE_RULES } from "./captureGuidance";

describe("captureGuidance", () => {
  it("lists the checks that cause preprocess rejects", () => {
    const joined = CAPTURE_RULES.join(" ").toLowerCase();
    expect(CAPTURE_RULES.length).toBeGreaterThanOrEqual(4);
    expect(joined).toContain("one person");
    expect(joined).toContain("face");
    expect(joined).toMatch(/hand|phone/);
    expect(joined).toContain("light");
    expect(CAPTURE_HEADLINE.toLowerCase()).toContain("rejected");
    expect(CAMERA_INSTRUCTION.toLowerCase()).toContain("oval");
  });
});
