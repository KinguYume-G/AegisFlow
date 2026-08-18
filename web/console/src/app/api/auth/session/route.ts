import { NextResponse } from "next/server";

import { getSession } from "@/lib/core-client";
import { loadConsoleEnvironment } from "@/lib/environment";
import { csrfForCurrentSession } from "@/lib/server-session";

export const dynamic = "force-dynamic";

export async function GET() {
  const config = loadConsoleEnvironment();
  try {
    const session = await getSession();
    const csrf =
      config.authMode === "oidc" ? await csrfForCurrentSession(config) : null;
    return NextResponse.json(
      { session, csrf },
      { headers: { "cache-control": "no-store" } },
    );
  } catch {
    return NextResponse.json(
      { error: { code: "authentication_required" } },
      { status: 401, headers: { "cache-control": "no-store" } },
    );
  }
}
