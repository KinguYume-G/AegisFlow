import { z } from "zod";

const uuid = z.string().uuid();
const dateTime = z.string().datetime({ offset: true });
const digest = z.string().regex(/^[0-9a-f]{64}$/);
const nonnegativeDecimal = z
  .union([
    z.number().finite().nonnegative(),
    z.string().regex(/^\d+(?:\.\d+)?$/),
  ])
  .transform((value) => Number(value));
const githubName = z.string().min(1).max(100).regex(/^[A-Za-z0-9_.-]+$/);
const baseRef = z
  .string()
  .min(1)
  .max(255)
  .regex(/^[A-Za-z0-9][A-Za-z0-9._/-]*$/)
  .refine((value) => !value.split("/").includes(".."), "base_ref_traversal");

export const repositoryInputSchema = z
  .object({
    owner: githubName,
    name: githubName,
    base_ref: baseRef,
    base_sha: z.string().regex(/^[0-9a-f]{40}$/),
  })
  .strict();

export const createRunInputSchema = z
  .object({
    source_type: z.enum(["prd", "issue", "bug"]),
    source_ref: z.string().max(2048).nullable(),
    title: z.string().trim().min(1).max(200),
    body: z.string().trim().min(20).max(50_000),
    repository: repositoryInputSchema,
  })
  .strict();

export const runSummarySchema = z
  .object({
    run_id: uuid,
    tenant_id: uuid,
    status: z.string().min(1).max(64),
    source_type: z.string().min(1).max(32),
    title: z.string().min(1).max(200),
    requested_by: z.string().min(1).max(512),
    created_at: dateTime,
    updated_at: dateTime,
  })
  .strict();

const actionPreviewSchema = z
  .object({
    effect: z.string().min(1).max(128),
    effect_mode: z.enum(["dry_run", "github"]),
    repository: z.string().min(3).max(201),
    base_ref: z.string().min(1).max(255),
    base_sha: z.string().regex(/^[0-9a-f]{40}$/),
    branch_name: z.string().min(1).max(255),
    changed_files: z.array(z.string().min(1).max(4096)).max(1000),
    content_digest: digest,
    risk: z.string().min(1).max(64),
  })
  .passthrough();

export const pendingActionSchema = z.discriminatedUnion("kind", [
  z
    .object({
      kind: z.literal("clarification"),
      request_id: uuid,
      questions: z
        .array(
          z
            .object({
              field: z.string().min(1).max(64),
              question: z.string().min(1).max(1000),
              schema_version: z.number().int().positive(),
            })
            .strict(),
        )
        .min(1)
        .max(50),
    })
    .strict(),
  z
    .object({
      kind: z.literal("approval"),
      request_id: uuid,
      action_preview: actionPreviewSchema,
      action_digest: digest,
      reason: z.string().max(4096).nullable(),
    })
    .strict(),
]);

const stepSchema = z
  .object({
    step_id: uuid,
    name: z.string().min(1).max(128),
    sequence: z.number().int().positive(),
    status: z.string().min(1).max(64),
    started_at: dateTime,
    completed_at: dateTime.nullable(),
  })
  .strict();

const approvalSchema = z
  .object({
    approval_id: uuid,
    decision: z.string().min(1).max(32),
    decided_by: z.string().max(512).nullable(),
    decided_at: dateTime.nullable(),
    reason: z.string().max(4096).nullable(),
    action_preview: actionPreviewSchema.nullable(),
    action_digest: digest.nullable(),
  })
  .strict();

const artifactSchema = z
  .object({
    kind: z.string().min(1).max(128),
    content_digest: digest,
    payload: z.record(z.string(), z.unknown()),
    created_at: dateTime,
  })
  .strict();

const availabilityValue = z.object({ value: z.number().nullable(), status: z.string() }).strict();
const traceSchema = z
  .object({
    event_id: uuid,
    agent: z.string().min(1).max(128),
    model: z.string().min(1).max(255),
    token_usage: z
      .object({
        input_tokens: availabilityValue,
        output_tokens: availabilityValue,
        total_tokens: availabilityValue,
      })
      .passthrough(),
    cost_usage: z
      .object({
        amount: nonnegativeDecimal.nullable(),
        source: z.string(),
        currency: z.string().nullable(),
      })
      .passthrough(),
    latency_ms: z.number().nonnegative(),
    created_at: dateTime,
  })
  .strict();

const evaluationSchema = z
  .object({
    outcome: z.string().min(1).max(64),
    task_success: z.boolean(),
    tool_success_rate: nonnegativeDecimal.refine((value) => value <= 1),
    total_steps: z.number().int().nonnegative(),
    completed_steps: z.number().int().nonnegative(),
    input_tokens: z.number().int().nonnegative().nullable(),
    output_tokens: z.number().int().nonnegative().nullable(),
    cost_usd: nonnegativeDecimal.nullable(),
    detail: z.record(z.string(), z.unknown()),
    created_at: dateTime,
  })
  .strict();

const auditSchema = z
  .object({
    event_id: uuid,
    actor: z.string().min(1).max(512),
    action: z.string().min(1).max(128),
    decision: z.string().min(1).max(64),
    reason: z.string().max(4096).nullable(),
    trace_id: z.string().max(512).nullable(),
    created_at: dateTime,
  })
  .strict();

export const runDetailSchema = z
  .object({
    summary: runSummarySchema,
    request: createRunInputSchema,
    steps: z.array(stepSchema).max(1000),
    pending_action: pendingActionSchema.nullable(),
    approvals: z.array(approvalSchema).max(100),
    artifacts: z.array(artifactSchema).max(1000),
    traces: z.array(traceSchema).max(5000),
    evaluation: evaluationSchema.nullable(),
    audit: z.array(auditSchema).max(5000),
  })
  .strict();

export const runListSchema = z
  .object({ items: z.array(runSummarySchema).max(100), next_cursor: z.string().nullable() })
  .strict();

export const sessionSchema = z
  .object({
    actor_reference: z.string().min(1).max(512),
    profile: z.enum(["oidc", "local_mvp"]),
    tenants: z
      .array(
        z
          .object({
            tenant_id: uuid,
            slug: z.string().min(1).max(100),
            roles: z.array(z.string().min(1).max(64)).max(32),
            capabilities: z.array(z.string().min(1).max(128)).max(128),
          })
          .strict(),
      )
      .max(100),
  })
  .strict();

export const clarificationInputSchema = z
  .object({ answers: z.record(z.string().min(1).max(128), z.string().trim().min(1).max(8192)) })
  .strict()
  .refine((value) => Object.keys(value.answers).length > 0, "answers_required");

export const approvalInputSchema = z
  .object({ decision: z.enum(["approved", "rejected"]), reason: z.string().max(4096).optional() })
  .strict();

export type CreateRunInput = z.infer<typeof createRunInputSchema>;
export type RunSummary = z.infer<typeof runSummarySchema>;
export type RunDetail = z.infer<typeof runDetailSchema>;
export type PendingApproval = Extract<z.infer<typeof pendingActionSchema>, { kind: "approval" }>;
export type Session = z.infer<typeof sessionSchema>;
