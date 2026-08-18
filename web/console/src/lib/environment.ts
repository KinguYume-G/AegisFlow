import { z } from "zod";

export type ConsolePersona = "developer" | "reviewer";

export interface ConsoleEnvironment {
  coreUrl: string;
  persona: ConsolePersona;
  token: string;
  developerConsoleUrl: string;
  reviewerConsoleUrl: string;
}

const environmentSchema = z
  .object({
    AEGISFLOW_CORE_URL: z.string().url(),
    AEGISFLOW_CONSOLE_PERSONA: z.enum(["developer", "reviewer"]),
    AEGISFLOW_LOCAL_TOKEN: z.string().min(16).max(256),
    AEGISFLOW_DEVELOPER_CONSOLE_URL: z.string().url().default("http://localhost:3000"),
    AEGISFLOW_REVIEWER_CONSOLE_URL: z.string().url().default("http://localhost:3001"),
  })
  .passthrough();

function validatedHttpUrl(value: string, code: string): string {
  const url = new URL(value);
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error(code);
  }
  return url.toString().replace(/\/$/, "");
}

export function loadConsoleEnvironment(
  source: Record<string, string | undefined> = process.env,
): ConsoleEnvironment {
  const result = environmentSchema.safeParse(source);
  if (!result.success) {
    const personaIssue = result.error.issues.some(
      (issue) => issue.path[0] === "AEGISFLOW_CONSOLE_PERSONA",
    );
    throw new Error(personaIssue ? "console_persona_invalid" : "console_environment_invalid");
  }
  const values = result.data;
  const coreUrl = validatedHttpUrl(values.AEGISFLOW_CORE_URL, "core_url_invalid");
  const developerConsoleUrl = validatedHttpUrl(
    values.AEGISFLOW_DEVELOPER_CONSOLE_URL,
    "developer_console_url_invalid",
  );
  const reviewerConsoleUrl = validatedHttpUrl(
    values.AEGISFLOW_REVIEWER_CONSOLE_URL,
    "reviewer_console_url_invalid",
  );
  return {
    coreUrl,
    persona: values.AEGISFLOW_CONSOLE_PERSONA,
    token: values.AEGISFLOW_LOCAL_TOKEN,
    developerConsoleUrl,
    reviewerConsoleUrl,
  };
}

export function publicConsoleContext(config: ConsoleEnvironment) {
  return {
    persona: config.persona,
    developerConsoleUrl: config.developerConsoleUrl,
    reviewerConsoleUrl: config.reviewerConsoleUrl,
  } as const;
}
