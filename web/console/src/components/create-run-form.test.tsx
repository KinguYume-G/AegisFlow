import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CreateRunForm } from "./create-run-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("CreateRunForm", () => {
  it("emits repository patterns that compile under the HTML UnicodeSets mode", () => {
    render(<CreateRunForm />);

    for (const name of ["Owner", "Repository"]) {
      const pattern = screen.getByLabelText(name).getAttribute("pattern");
      expect(pattern).not.toBeNull();
      expect(() => new RegExp(pattern!, "v")).not.toThrow();
      expect(new RegExp(`^(?:${pattern})$`, "v").test("AegisFlow-example.repo")).toBe(true);
    }
  });
});
