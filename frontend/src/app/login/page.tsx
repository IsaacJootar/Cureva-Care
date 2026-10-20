"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_BASE } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { roleLanding } from "@/lib/nav";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { CheckIcon, MotherIcon } from "@/components/icons";

function LoginInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, loading, signInWithTicket, signInWithPassword } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState<string>();
  const [loginError, setLoginError] = useState<string>();
  const [signingIn, setSigningIn] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [showLink, setShowLink] = useState(false);
  const [exchanging, setExchanging] = useState(false);
  const [exchangeError, setExchangeError] = useState<string>();
  const exchangedRef = useRef(false);

  const token = params.get("token");

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

  async function doPasswordLogin(e: React.FormEvent) {
    e.preventDefault();
    const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    if (!valid) {
      setEmailError("Enter a valid email address");
      return;
    }
    setEmailError(undefined);
    setLoginError(undefined);
    setSigningIn(true);
    try {
      const u = await signInWithPassword(email.trim().toLowerCase(), password);
      router.replace(roleLanding(u.role));
    } catch {
      setLoginError("Incorrect email or password.");
      setSigningIn(false);
    }
  }

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
        <span
          style={{
            width: 46,
            height: 46,
            borderRadius: 12,
            background: "var(--cv-accent-gradient)",
            boxShadow: "var(--cv-accent-glow)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            margin: "0 auto 12px",
          }}
        >
          <MotherIcon size={26} />
        </span>
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
      {(exchangeError || loginError) && (
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
          {exchangeError ?? loginError}
        </div>
      )}

      <form onSubmit={doPasswordLogin} noValidate>
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
        <div style={{ marginTop: 12 }}>
          <TextField
            id="password"
            label="Password"
            type="password"
            placeholder="Your password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (loginError) setLoginError(undefined);
            }}
          />
        </div>
        <div style={{ marginTop: 16 }}>
          <Button type="submit" fullWidth loading={signingIn} loadingLabel="Signing in…" disabled={!password}>
            Sign in
          </Button>
        </div>
      </form>

      {!showLink ? (
        <p style={{ fontSize: 11, color: "var(--cv-text-muted)", textAlign: "center", marginTop: 18, lineHeight: 1.6 }}>
          Forgot your password? Ask a Cureva Care administrator to reset it.
          <br />
          <button
            onClick={() => setShowLink(true)}
            style={{ background: "none", border: "none", color: "var(--cv-accent-solid)", cursor: "pointer", fontSize: 11, padding: 0, marginTop: 4 }}
          >
            Or email me a sign-in link instead
          </button>
        </p>
      ) : (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "18px 0" }}>
            <span style={{ flex: 1, height: 1, background: "var(--cv-hairline)" }} />
            <span style={{ fontSize: 10.5, color: "var(--cv-text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>or</span>
            <span style={{ flex: 1, height: 1, background: "var(--cv-hairline)" }} />
          </div>
          <Button variant="secondary" fullWidth loading={sending} loadingLabel="Sending…" onClick={(e) => requestLink(e as unknown as React.FormEvent)}>
            Email me a sign-in link
          </Button>
          <p style={{ fontSize: 11, color: "var(--cv-text-muted)", textAlign: "center", marginTop: 14 }}>
            Access is invite-only.
          </p>
        </>
      )}
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
