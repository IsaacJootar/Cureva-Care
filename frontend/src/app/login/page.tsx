"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_BASE } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { roleLanding } from "@/lib/nav";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { CheckIcon } from "@/components/icons";

const SSO_ERRORS: Record<string, string> = {
  sso_state: "The sign-in request expired or was tampered with. Please try again.",
  sso_failed: "We couldn't complete Google sign-in. Please try again.",
  not_invited: "That account isn't registered for Cureva Care. Ask an administrator to invite you.",
};

function LoginInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, loading, signInWithTicket } = useAuth();

  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string>();
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [exchanging, setExchanging] = useState(false);
  const [exchangeError, setExchangeError] = useState<string>();
  const exchangedRef = useRef(false);

  const token = params.get("token");
  const ssoError = params.get("error");

  // Exchange a sign-in ticket (from a magic link or the SSO callback) once.
  useEffect(() => {
    if (!token || exchangedRef.current) return;
    exchangedRef.current = true;
    setExchanging(true);
    signInWithTicket(token)
      .then((u) => router.replace(roleLanding(u.role)))
      .catch(() => {
        setExchangeError("This sign-in link is invalid, expired, or already used.");
        setExchanging(false);
      });
  }, [token, signInWithTicket, router]);

  // Already signed in → go to the role landing.
  useEffect(() => {
    if (!token && !loading && user) router.replace(roleLanding(user.role));
  }, [token, loading, user, router]);

  async function requestLink(e: React.FormEvent) {
    e.preventDefault();
    const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    if (!valid) {
      setEmailError("Enter a valid email address");
      return;
    }
    setEmailError(undefined);
    setSending(true);
    try {
      await fetch(`${API_BASE}/auth/magic-link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      setSent(true);
    } finally {
      setSending(false);
    }
  }

  const shell = (children: React.ReactNode) => (
    <main style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: 24 }}>
      <div
        style={{
          background: "var(--cv-card-bg)",
          border: "1px solid var(--cv-card-border)",
          boxShadow: "var(--cv-card-shadow)",
          borderRadius: "var(--cv-radius-card)",
          padding: "34px 36px",
          width: 400,
          maxWidth: "100%",
        }}
      >
        <div className="cv-brand" style={{ fontSize: 22, color: "var(--cv-text-primary)", textAlign: "center" }}>
          Cureva Care
        </div>
        <p style={{ color: "var(--cv-text-muted)", fontSize: 11.5, textAlign: "center", marginTop: 4, marginBottom: 24 }}>
          Maternal-care intelligence platform
        </p>
        {children}
      </div>
    </main>
  );

  if (exchanging) {
    return shell(
      <p style={{ textAlign: "center", color: "var(--cv-text-secondary)", fontSize: 12.5 }}>Signing you in…</p>,
    );
  }

  if (sent) {
    return shell(
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            width: 42,
            height: 42,
            borderRadius: 10,
            background: "var(--cv-success-bg)",
            border: "1px solid var(--cv-success-border)",
            color: "var(--cv-success-icon)",
            display: "grid",
            placeItems: "center",
            margin: "0 auto 14px",
          }}
        >
          <CheckIcon size={20} />
        </div>
        <h2 style={{ fontSize: 15, color: "var(--cv-text-primary)", margin: "0 0 6px" }}>Check your email</h2>
        <p style={{ fontSize: 12.5, color: "var(--cv-text-secondary)", lineHeight: 1.5 }}>
          If <strong>{email}</strong> is registered, a single-use sign-in link is on its way. It expires in 15 minutes.
        </p>
      </div>,
    );
  }

  return shell(
    <>
      {(exchangeError || (ssoError && SSO_ERRORS[ssoError])) && (
        <div
          style={{
            background: "var(--cv-danger-bg)",
            border: "1px solid var(--cv-danger-border)",
            color: "var(--cv-danger-text)",
            borderRadius: 8,
            padding: "9px 11px",
            fontSize: 11.5,
            marginBottom: 16,
          }}
        >
          {exchangeError ?? SSO_ERRORS[ssoError!]}
        </div>
      )}

      <form onSubmit={requestLink} noValidate>
        <TextField
          id="email"
          label="Work email"
          type="email"
          placeholder="you@facility.org"
          value={email}
          error={emailError}
          onChange={(e) => {
            setEmail(e.target.value);
            if (emailError) setEmailError(undefined);
          }}
        />
        <div style={{ marginTop: 14 }}>
          <Button type="submit" fullWidth loading={sending} loadingLabel="Sending…">
            Email me a sign-in link
          </Button>
        </div>
      </form>

      <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "18px 0" }}>
        <span style={{ flex: 1, height: 1, background: "var(--cv-hairline)" }} />
        <span style={{ fontSize: 10.5, color: "var(--cv-text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          or
        </span>
        <span style={{ flex: 1, height: 1, background: "var(--cv-hairline)" }} />
      </div>

      <Button
        variant="secondary"
        fullWidth
        onClick={() => {
          window.location.href = `${API_BASE}/auth/google/start`;
        }}
      >
        Continue with Google
      </Button>

      <p style={{ fontSize: 11, color: "var(--cv-text-muted)", textAlign: "center", marginTop: 18, lineHeight: 1.5 }}>
        Access is invite-only. There is no password — sign in with a magic link or your organisation's SSO.
      </p>
    </>,
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginInner />
    </Suspense>
  );
}
