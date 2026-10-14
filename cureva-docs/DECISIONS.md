# Cureva Care — build decisions log

A running record of the notable decisions taken while building Cureva Care:
**what** changed, **why**, and **how it's used**. This feeds the eventual usage
document (what we built, the reasoning, and how it's operated). Newest sections
are appended at the bottom.

---

## Platform & environment

- **Database:** PostgreSQL 16 in a Docker container (`cureva-postgres`, host
  port 5434), isolated from the machine's other projects. *Why:* the stack
  locks PostgreSQL and the native EDB installer was CDN-blocked on this network;
  Docker gives real Postgres without touching the existing XAMPP/MySQL. *Used
  by:* the Django backend via `DATABASE_URL`.
- **Object storage:** MinIO (S3-compatible) container for immutable register-
  photo retention. *Used by:* the intake pipeline (`register_intake/storage.py`).
- **Ports:** backend API on **8001**, frontend on **3100** (3000/5432 were
  taken by other local projects).

## Authentication

- **No passwords anywhere** — sign-in is magic-link or SSO only (a locked
  package decision). *Why:* avoids credential storage/rotation; invite-only.
  *Used by:* every user; the magic link (dev) prints to the backend console.
- **Google SSO** built but **deferred** pending real Google client credentials
  (product-owner decision). Magic-link is fully working.

## Vision / OCR provider (open decision #8, resolved)

- **OpenAI (gpt-4o) is the active extraction provider**, swappable behind
  `extraction_engine`; Claude vision is also implemented. *Why:* the pilot's
  available API key is an OpenAI one; the architecture always allowed a swap.
  *Used by:* the intake extraction step; verified live end to end.

## Templates (open decision #1, resolved)

- **Delivery and PNC templates reconciled against the real NHMIS registers** in
  Cureva's existing platform (`app.cureva.care`): Delivery expanded to 25
  columns, PNC to 24, ANC kept at 22. *Why:* the package's Delivery/PNC lists
  were abbreviated placeholders. *Used by:* extraction field-matching.

## Clinical governance (open decision #2, pending)

- Risk/referral rules carry owner `UNASSIGNED (pending clinical sign-off)`
  until a clinical owner is named. The "clinical review of reports" launch gate
  stays open until then.
