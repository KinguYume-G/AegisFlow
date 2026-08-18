import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunTimeline } from "./run-timeline";

describe("RunTimeline", () => {
  it("renders the canonical ten steps and preserves waiting truth", () => {
    render(
      <RunTimeline
        steps={[
          {
            step_id: "11111111-1111-4111-8111-111111111111",
            name: "intake",
            sequence: 1,
            status: "completed",
            started_at: "2026-08-17T00:00:00Z",
            completed_at: "2026-08-17T00:00:01Z",
          },
          {
            step_id: "22222222-2222-4222-8222-222222222222",
            name: "human_approval",
            sequence: 8,
            status: "waiting",
            started_at: "2026-08-17T00:00:02Z",
            completed_at: null,
          },
        ]}
        runStatus="waiting_approval"
      />,
    );

    expect(screen.getAllByRole("listitem")).toHaveLength(10);
    expect(screen.getByText("Human approval")).toBeInTheDocument();
    expect(screen.getByText("Waiting", { selector: ".step-status" })).toBeInTheDocument();
  });
});
