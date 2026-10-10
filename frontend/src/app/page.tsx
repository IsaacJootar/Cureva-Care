import Link from "next/link";

// Placeholder landing — replaced by role-aware routing once auth lands.
// Kept minimal and token-driven so the design system is visible from the start.
export default function Home() {
  return (
    <main
      style={{
        minHeight: "100dvh",
        display: "grid",
        placeItems: "center",
        padding: 24,
      }}
    >
      <div
        style={{
          background: "var(--cv-card-bg)",
          border: "1px solid var(--cv-card-border)",
          boxShadow: "var(--cv-card-shadow)",
          borderRadius: "var(--cv-radius-card)",
          padding: "40px 44px",
          maxWidth: 440,
          textAlign: "center",
        }}
      >
        <div
          className="cv-brand"
          style={{ fontSize: 24, color: "var(--cv-text-primary)" }}
        >
          Cureva Care
        </div>
        <p
          style={{
            color: "var(--cv-text-secondary)",
            marginTop: 10,
            fontSize: 13,
          }}
        >
          Maternal-care intelligence for ANC, Delivery, and PNC registers.
        </p>
        <Link
          href="/login"
          style={{
            display: "inline-block",
            marginTop: 22,
            background: "var(--cv-button-primary-bg)",
            color: "var(--cv-button-primary-text)",
            fontWeight: 600,
            padding: "10px 20px",
            borderRadius: "var(--cv-radius-control)",
            textDecoration: "none",
          }}
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}
