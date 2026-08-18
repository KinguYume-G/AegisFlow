import {
  createCipheriv,
  createDecipheriv,
  createHmac,
  randomBytes,
  timingSafeEqual,
} from "node:crypto";

export interface LoginTransaction {
  state: string;
  nonce: string;
  codeVerifier: string;
  returnPath: string;
  expiresAt: number;
}

const OPAQUE_SESSION = /^afs_cs_[A-Za-z0-9_-]{43}$/;
const CSRF = /^[A-Za-z0-9_-]{43}$/;

function encryptionKey(encoded: string): Buffer {
  const key = Buffer.from(encoded, "base64url");
  if (key.length !== 32) throw new Error("session_encryption_key_invalid");
  return key;
}

function validateTransaction(value: LoginTransaction): LoginTransaction {
  const invalidReturnPath =
    !value.returnPath.startsWith("/") || value.returnPath.startsWith("//");
  if (invalidReturnPath) throw new Error("return_path_invalid");
  if (
    !value.state ||
    value.state.length > 512 ||
    !value.nonce ||
    value.nonce.length > 512 ||
    !value.codeVerifier ||
    value.codeVerifier.length > 512 ||
    !Number.isSafeInteger(value.expiresAt) ||
    value.returnPath.length > 2048
  ) {
    throw new Error("login_transaction_invalid");
  }
  return value;
}

export function sealLoginTransaction(
  transaction: LoginTransaction,
  encodedKey: string,
): string {
  const validated = validateTransaction(transaction);
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", encryptionKey(encodedKey), iv);
  const plaintext = Buffer.from(JSON.stringify(validated), "utf8");
  const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const tag = cipher.getAuthTag();
  return `v1.${iv.toString("base64url")}.${encrypted.toString("base64url")}.${tag.toString("base64url")}`;
}

export function openLoginTransaction(
  sealed: string,
  encodedKey: string,
  nowEpochSeconds = Math.floor(Date.now() / 1000),
): LoginTransaction {
  try {
    const [version, ivPart, payloadPart, tagPart, extra] = sealed.split(".");
    if (version !== "v1" || !ivPart || !payloadPart || !tagPart || extra) {
      throw new Error("invalid");
    }
    const iv = Buffer.from(ivPart, "base64url");
    const payload = Buffer.from(payloadPart, "base64url");
    const tag = Buffer.from(tagPart, "base64url");
    if (iv.length !== 12 || tag.length !== 16 || payload.length > 4096) {
      throw new Error("invalid");
    }
    const decipher = createDecipheriv("aes-256-gcm", encryptionKey(encodedKey), iv);
    decipher.setAuthTag(tag);
    const plaintext = Buffer.concat([decipher.update(payload), decipher.final()]);
    const parsed = validateTransaction(
      JSON.parse(plaintext.toString("utf8")) as LoginTransaction,
    );
    if (parsed.expiresAt < nowEpochSeconds) {
      throw new Error("login_transaction_expired");
    }
    return parsed;
  } catch (error) {
    if (error instanceof Error && error.message === "login_transaction_expired") {
      throw error;
    }
    throw new Error("login_transaction_invalid");
  }
}

export function createCsrfToken(sessionToken: string, encodedKey: string): string {
  if (!OPAQUE_SESSION.test(sessionToken)) throw new Error("authentication_required");
  return createHmac("sha256", encryptionKey(encodedKey))
    .update("aegisflow-csrf-v1\0", "utf8")
    .update(sessionToken, "ascii")
    .digest("base64url");
}

export function verifyCsrfToken(
  candidate: string,
  sessionToken: string,
  encodedKey: string,
): boolean {
  if (!CSRF.test(candidate)) return false;
  try {
    const expected = Buffer.from(createCsrfToken(sessionToken, encodedKey), "ascii");
    const provided = Buffer.from(candidate, "ascii");
    return expected.length === provided.length && timingSafeEqual(expected, provided);
  } catch {
    return false;
  }
}
