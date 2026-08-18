import "server-only";

import { z, type ZodType } from "zod";

import {
  approvalInputSchema,
  clarificationInputSchema,
  createRunInputSchema,
  runDetailSchema,
  runListSchema,
  sessionSchema,
  type CreateRunInput,
} from "./contracts";
import { loadConsoleEnvironment } from "./environment";

const profileSchema = z
  .object({
    profile: z.enum(["local_mvp", "standard"]),
    github_effect_mode: z.enum(["dry_run", "github"]),
    model_mode: z.enum(["ollama", "disabled"]),
  })
  .strict();
const acceptedSchema = z
  .object({ accepted: z.literal(true), run_id: z.string().uuid(), status: z.string() })
  .strict();

export class CoreApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
  ) {
    super(code);
    this.name = "CoreApiError";
  }
}

function safeErrorCode(payload: unknown, fallback: string): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "error" in payload &&
    typeof payload.error === "object" &&
    payload.error !== null &&
    "code" in payload.error &&
    typeof payload.error.code === "string"
  ) {
    return payload.error.code.slice(0, 128);
  }
  return fallback;
}

async function coreRequest<T>(
  path: string,
  schema: ZodType<T>,
  init: RequestInit = {},
): Promise<T> {
  const config = loadConsoleEnvironment();
  let response: Response;
  try {
    response = await fetch(`${config.coreUrl}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        accept: "application/json",
        "x-aegisflow-local-persona": config.persona,
        "x-aegisflow-local-token": config.token,
        ...init.headers,
      },
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new CoreApiError(503, "core_unavailable");
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new CoreApiError(response.status, safeErrorCode(payload, "core_request_failed"));
  }
  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new CoreApiError(502, "core_contract_invalid");
  }
  return parsed.data;
}

export async function getSession() {
  return coreRequest("/v1/session", sessionSchema);
}

async function getTenantId(): Promise<string> {
  const session = await getSession();
  const tenant = session.tenants[0];
  if (!tenant) throw new CoreApiError(403, "tenant_membership_required");
  return tenant.tenant_id;
}

export async function getDashboardData() {
  const [session, profile] = await Promise.all([
    getSession(),
    coreRequest("/v1/system/profile", profileSchema),
  ]);
  const tenant = session.tenants[0];
  if (!tenant) throw new CoreApiError(403, "tenant_membership_required");
  const runs = await coreRequest(
    `/v1/tenants/${encodeURIComponent(tenant.tenant_id)}/runs?limit=50`,
    runListSchema,
  );
  return { session, tenant, profile, runs };
}

export async function getRun(runId: string) {
  const tenantId = await getTenantId();
  return coreRequest(
    `/v1/tenants/${encodeURIComponent(tenantId)}/runs/${encodeURIComponent(runId)}`,
    runDetailSchema,
  );
}

export async function createRun(input: unknown, idempotencyKey: string) {
  const request = createRunInputSchema.parse(input) satisfies CreateRunInput;
  const tenantId = await getTenantId();
  return coreRequest(
    `/v1/tenants/${encodeURIComponent(tenantId)}/runs`,
    runDetailSchema,
    {
      method: "POST",
      headers: { "content-type": "application/json", "idempotency-key": idempotencyKey },
      body: JSON.stringify(request),
    },
  );
}

export async function submitClarification(
  runId: string,
  requestId: string,
  input: unknown,
  idempotencyKey: string,
) {
  const request = clarificationInputSchema.parse(input);
  const tenantId = await getTenantId();
  return coreRequest(
    `/v1/tenants/${encodeURIComponent(tenantId)}/runs/${encodeURIComponent(runId)}` +
      `/clarifications/${encodeURIComponent(requestId)}`,
    acceptedSchema,
    {
      method: "POST",
      headers: { "content-type": "application/json", "idempotency-key": idempotencyKey },
      body: JSON.stringify(request),
    },
  );
}

export async function submitApproval(
  runId: string,
  approvalId: string,
  input: unknown,
  idempotencyKey: string,
) {
  const config = loadConsoleEnvironment();
  if (config.persona !== "reviewer") {
    throw new CoreApiError(403, "reviewer_persona_required");
  }
  const request = approvalInputSchema.parse(input);
  const tenantId = await getTenantId();
  return coreRequest(
    `/v1/tenants/${encodeURIComponent(tenantId)}/runs/${encodeURIComponent(runId)}` +
      `/approvals/${encodeURIComponent(approvalId)}`,
    acceptedSchema,
    {
      method: "POST",
      headers: { "content-type": "application/json", "idempotency-key": idempotencyKey },
      body: JSON.stringify(request),
    },
  );
}
