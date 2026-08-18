import { describe, expect, it } from "vitest";

import { formatCost, formatDuration, formatTokenCount, statusLabel } from "./format";

describe("display formatters", () => {
  it("preserves unavailable measurement instead of displaying zero", () => {
    expect(formatCost(null)).toBe("Not measured");
    expect(formatTokenCount(null)).toBe("Not measured");
  });

  it("formats measured values and stable status labels", () => {
    expect(formatCost(0)).toBe("$0.0000");
    expect(formatTokenCount(2915)).toBe("2,915");
    expect(formatDuration(1532)).toBe("1.53 s");
    expect(statusLabel("waiting_approval")).toBe("Waiting for approval");
  });
});
