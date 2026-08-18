import { NextResponse } from "next/server";
import { ZodError } from "zod";

import { CoreApiError } from "./core-client";
import { MutationGuardError } from "./mutation-guard";

export function problem(status: number, code: string) {
  return NextResponse.json({ error: { code } }, { status });
}

export function routeError(error: unknown) {
  if (error instanceof MutationGuardError) return problem(403, error.code);
  if (error instanceof ZodError || error instanceof SyntaxError) return problem(400, "input_invalid");
  if (error instanceof CoreApiError) return problem(error.status, error.code);
  return problem(500, "console_request_failed");
}

export function idempotencyKey(scope: string): string {
  return `console:${scope}:${crypto.randomUUID()}`;
}
