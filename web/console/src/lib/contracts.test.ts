import { describe, expect, it } from "vitest";

import { createRunInputSchema, runDetailSchema } from "./contracts";

describe("console contracts", () => {
  it("accepts a bounded Run request and rejects traversal or unknown fields", () => {
    const valid = {
      source_type: "prd",
      source_ref: null,
      title: "Add deterministic delivery status",
      body: "Return a small deterministic status function with one unit test.",
      repository: {
        owner: "KinguYume-G",
        name: "AegisFlow",
        base_ref: "main",
        base_sha: "a".repeat(40),
      },
    };

    expect(createRunInputSchema.parse(valid)).toEqual(valid);
    expect(() =>
      createRunInputSchema.parse({
        ...valid,
        repository: { ...valid.repository, base_ref: "feature/../main" },
      }),
    ).toThrow();
    expect(() => createRunInputSchema.parse({ ...valid, persona: "reviewer" })).toThrow();
  });

  it("rejects a malformed Run detail instead of inventing missing state", () => {
    expect(() => runDetailSchema.parse({ summary: { status: "completed" } })).toThrow();
  });

  it("accepts stable clarification fields and rejects lossy string questions", () => {
    const validAction = {
      kind: "clarification",
      request_id: "20000000-0000-4000-8000-000000000002",
      questions: [
        {
          field: "acceptance_criteria",
          question: "What exact command proves completion?",
          schema_version: 1,
        },
      ],
    };
    const detail = {
      summary: {
        run_id: "20000000-0000-4000-8000-000000000002",
        tenant_id: "10000000-0000-4000-8000-000000000001",
        status: "waiting_clarification",
        source_type: "prd",
        title: "Fixture",
        requested_by: "developer",
        created_at: "2026-08-18T00:00:00Z",
        updated_at: "2026-08-18T00:00:00Z",
      },
      request: {
        source_type: "prd",
        source_ref: null,
        title: "Fixture",
        body: "A bounded request body long enough for validation.",
        repository: {
          owner: "owner",
          name: "repo",
          base_ref: "main",
          base_sha: "a".repeat(40),
        },
      },
      steps: [],
      pending_action: validAction,
      approvals: [],
      artifacts: [],
      traces: [
        {
          event_id: "30000000-0000-4000-8000-000000000003",
          agent: "planner",
          model: "ollama_chat/qwen3:8b",
          token_usage: {
            input_tokens: { value: 10, status: "measured" },
            output_tokens: { value: 5, status: "measured" },
            total_tokens: { value: 15, status: "measured" },
          },
          cost_usage: { amount: "0.0", source: "provider_reported", currency: "USD" },
          latency_ms: 10,
          created_at: "2026-08-18T00:00:00Z",
        },
      ],
      evaluation: {
        outcome: "completed",
        task_success: true,
        tool_success_rate: "1.0000",
        total_steps: 10,
        completed_steps: 10,
        input_tokens: 10,
        output_tokens: 5,
        cost_usd: "0.000000",
        detail: {},
        created_at: "2026-08-18T00:00:00Z",
      },
      audit: [],
    };

    const parsed = runDetailSchema.parse(detail);
    expect(parsed.pending_action).toEqual(validAction);
    expect(parsed.traces[0]?.cost_usage.amount).toBe(0);
    expect(parsed.evaluation?.tool_success_rate).toBe(1);
    expect(parsed.evaluation?.cost_usd).toBe(0);
    const unavailableUsage = runDetailSchema.parse({
      ...detail,
      summary: { ...detail.summary, status: "failed" },
      evaluation: {
        ...detail.evaluation,
        outcome: "failed",
        task_success: false,
        input_tokens: null,
        output_tokens: null,
        cost_usd: null,
      },
    });
    expect(unavailableUsage.evaluation?.input_tokens).toBeNull();
    expect(unavailableUsage.evaluation?.output_tokens).toBeNull();
    expect(() =>
      runDetailSchema.parse({
        ...detail,
        pending_action: { ...validAction, questions: ["What is missing?"] },
      }),
    ).toThrow();
  });
});
