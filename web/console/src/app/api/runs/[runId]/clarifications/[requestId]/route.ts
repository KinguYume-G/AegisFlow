import { NextResponse } from "next/server";
import { z } from "zod";

import { idempotencyKey, routeError } from "@/lib/bff-response";
import { submitClarification } from "@/lib/core-client";
import { assertTrustedMutation } from "@/lib/mutation-guard";

const idSchema = z.string().uuid();

export async function POST(
  request: Request,
  context: { params: Promise<{ runId: string; requestId: string }> },
) {
  try {
    assertTrustedMutation(request);
    const { runId, requestId } = await context.params;
    const result = await submitClarification(
      idSchema.parse(runId),
      idSchema.parse(requestId),
      await request.json(),
      idempotencyKey("clarification"),
    );
    return NextResponse.json(result, { status: 202 });
  } catch (error) {
    return routeError(error);
  }
}
