"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function LogoutButton({ csrf }: { csrf: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function logout() {
    setBusy(true);
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-aegisflow-csrf": csrf,
        },
        body: "{}",
      });
    } finally {
      router.replace("/login?reason=signed_out");
      router.refresh();
    }
  }

  return (
    <button className="button button--secondary" disabled={busy} onClick={logout} type="button">
      {busy ? "Signing out…" : "Sign out"}
    </button>
  );
}
