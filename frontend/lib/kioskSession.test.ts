import { describe, expect, it } from "vitest";
import { idleTimeoutMs, sessionTimeoutMinutes } from "./kioskSession";

describe("kioskSession idle helpers", () => {
  it("returns at least 30 seconds for idle timeout", () => {
    expect(idleTimeoutMs()).toBeGreaterThanOrEqual(30_000);
  });

  it("exposes session timeout minutes as a positive integer", () => {
    expect(sessionTimeoutMinutes()).toBeGreaterThanOrEqual(1);
  });
});
