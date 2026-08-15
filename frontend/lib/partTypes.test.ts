import { describe, expect, it } from "vitest";
import { REQUIRED_PART_TYPES } from "./partTypes";
import { createSessionId } from "./kioskSession";

describe("part types", () => {
  it("requires pallu and both borders", () => {
    expect(REQUIRED_PART_TYPES).toContain("full_hanging");
    expect(REQUIRED_PART_TYPES).toContain("pallu");
    expect(REQUIRED_PART_TYPES).toContain("body_field");
    expect(REQUIRED_PART_TYPES).toContain("border");
    expect(REQUIRED_PART_TYPES).toContain("blouse");
    expect(REQUIRED_PART_TYPES).toHaveLength(5);
  });
});

describe("kiosk session", () => {
  it("creates a session id long enough for the API", () => {
    expect(createSessionId().length).toBeGreaterThanOrEqual(8);
  });
});
