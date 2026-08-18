import { NextResponse } from "next/server";
import { z } from "zod";

import { getRun } from "@/lib/core-client";
import { routeError } from "@/lib/bff-response";

export const dynamic = "force-dynamic";
const runIdSchema = z.string().uuid();

export async function GET(
  _request: Request,
  context: { params: Promise<{ runId: string }> },
) {
  try {
    const { runId } = await context.params;
    const run = await getRun(runIdSchema.parse(runId));
    return NextResponse.json(run, { headers: { "cache-control": "no-store" } });
  } catch (error) {
    return routeError(error);
  }
}
