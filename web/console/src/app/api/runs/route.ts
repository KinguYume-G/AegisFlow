import { NextResponse } from "next/server";

import { createRun, getDashboardData } from "@/lib/core-client";
import { idempotencyKey, routeError } from "@/lib/bff-response";
import { assertTrustedMutation } from "@/lib/mutation-guard";
import { loadConsoleEnvironment } from "@/lib/environment";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const data = await getDashboardData();
    return NextResponse.json(data.runs, { headers: { "cache-control": "no-store" } });
  } catch (error) {
    return routeError(error);
  }
}

export async function POST(request: Request) {
  try {
    assertTrustedMutation(request, loadConsoleEnvironment());
    const body: unknown = await request.json();
    const run = await createRun(body, idempotencyKey("run"));
    return NextResponse.json(run, { status: 202 });
  } catch (error) {
    return routeError(error);
  }
}
