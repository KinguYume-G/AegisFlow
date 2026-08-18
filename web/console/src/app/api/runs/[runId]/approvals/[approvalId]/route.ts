import { NextResponse } from "next/server";
import { z } from "zod";

import { idempotencyKey, routeError } from "@/lib/bff-response";
import { submitApproval } from "@/lib/core-client";
import { assertTrustedMutation } from "@/lib/mutation-guard";

const idSchema = z.string().uuid();

export async function POST(
  request: Request,
  context: { params: Promise<{ runId: string; approvalId: string }> },
) {
  try {
    assertTrustedMutation(request);
    const { runId, approvalId } = await context.params;
    const result = await submitApproval(
      idSchema.parse(runId),
      idSchema.parse(approvalId),
      await request.json(),
      idempotencyKey("approval"),
    );
    return NextResponse.json(result, { status: 202 });
  } catch (error) {
    return routeError(error);
  }
}
