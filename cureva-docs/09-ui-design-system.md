# UI Design System

This is the visual and structural specification for the Next.js frontend
— written so Claude Code can build
the real product's screens to match the approved prototype exactly,
without needing to reverse-engineer them from images alone. Four of the
six original prototype boards are included as reference screenshots
(`ui-reference/`); one more is fully specified below in writing instead,
because it's interactive and a single screenshot would only show one
moment of it — the state logic here is more useful to a coding agent
than a picture would be. Three further screens (Admin · Organisations,
the organisation dashboard, and My organisation's users) were added
after the prototype was built and have no reference image at all — they
are spec-only, following the same token system and component library as
everything else in this file.

**What's actually built vs. specified.** The Overview screen is the only
one visually rebuilt to the full "premium" direction this file describes
— tinted gradient washes, frosted glass top bar, glossy card shadows —
see `ui-reference/01-overview-premium.png`. The other reference images
(Templates, Manage facilities, Facility lead) still show the earlier,
flatter card/background styling and are included only for their
*structure and content* (exact nav items, table columns, card contents)
— every visual token (color, shadow, radius) should come from this file,
not from those three images. **One piece of the premium direction has
since been confirmed and extended everywhere, not just Overview: the
active-nav-link treatment** (gradient wash + left accent border + bold
white label, spec'd under "Sidebar nav item" below) is now the required
active state for every sidebar, on every screen, for every role — it is
no longer an Overview-only accent. The full background-wash/glass-topbar
treatment is still Overview-only in the prototype; when the real
frontend is built, apply the complete token system below to all six
screens from the start rather than reproducing the older/newer mix the
prototype currently shows. A second reference, the shared **"UI
Patterns" page**, was built afterward specifically to pilot every other
reusable interaction (toasts, dialogs, menus, loading states, and more)
before it got written down here — its outcome is folded into the
Component library section below in full; there is no separate image for
it because the components are inherently interactive and the written
spec is the source of truth. The primary-button color and the row-menu
icon treatment documented below both came out of that review and now
apply everywhere a primary button or a row-actions menu appears.

## How to use this file

1. "Navigation map" gives the exact nav structure per role — link names,
   order, and the route each one points to (cross-referenced to
   `05-api-routes.md`).
2. "Design tokens" gives the full color/typography/spacing system, in
   both light and dark mode, plus how the toggle works.
3. "Component library" specs each reusable piece once, so screens
   below just reference it instead of redefining it.
4. "Screens" walks every board, its layout, and (for the two intake
   screens) every interactive state.

## Navigation map

Every role shares the same Next.js app and the same left sidebar
structure — a brand mark, one or more labelled nav groups, a "preview
as" block (prototype only — not part of the real product), and a user
footer. What differs per role is which groups and links exist, per
`01-product-scope.md`'s "Roles" and "Facility-level dashboards"
sections. There are four roles, and their navs don't overlap: a Systems
admin only ever sees ADMIN; a Data officer only ever sees INTAKE; a
Facility lead and an Organisation user both see the same MAIN group,
scoped differently.

**Systems admin** — administrative only, no dashboard access by
default (least privilege — see `01-product-scope.md`'s "Roles"):

| Group | Link (in order) | Route |
|---|---|---|
| ADMIN | Templates | `/admin/templates` |
| ADMIN | Manage facilities | `/admin/facilities` |
| ADMIN | Organisations | `/admin/organisations` |
| ADMIN | Users & roles | `/admin/users` |
| ADMIN | Settings | `/admin/settings` |

**Settings was missing from this table until the Roles & Operations
review caught it** — `/admin/settings` has been a real, fully-specified
route since early in this package (every tunable platform value, see
`08-delivery-plan.md`), but nothing in the sidebar ever linked to it.
Fixed here, permanently a 5th ADMIN item.

**Every role also gets an account menu**, reached by clicking the user
footer at the bottom of any sidebar — see "Account menu" in the
Component library below. It isn't a nav group and doesn't appear in the
tables above because it's role-agnostic; every role gets the identical
three items.

**Facility lead** — the MAIN group, locked to their one facility, in
this exact order:

| Group | Link (in order) | Route |
|---|---|---|
| *(facility name, non-clickable context row)* | — | — |
| MY FACILITY | Overview | `/overview` (locked to assigned facility) |
| MY FACILITY | Care journey | `/care-journey` (locked) |
| MY FACILITY | Needs attention | `/needs-attention` (locked) |
| MY FACILITY | Outcomes | `/outcomes` (locked) |
| MY FACILITY | Records | `/records` (locked) |
| MY FACILITY | Reports | `/reports` (locked) |
| REVIEW | Identity review *(badge: pending count)* | `/identity-review` |

**Organisation user** — the same MAIN group as Facility lead, minus
Needs attention (Facility-lead-only — see below), scoped instead to
their organisation's granted facilities/regions (see "Organisations and
access scoping" in `01-product-scope.md`); no ADMIN group, no REVIEW
group:

| Group | Link (in order) | Route |
|---|---|---|
| MAIN | Overview | `/overview` (scoped to the organisation's granted facilities) |
| MAIN | Care journey | `/care-journey` (scoped) |
| MAIN | Outcomes | `/outcomes` (scoped) |
| MAIN | Facilities | `/facilities` (scoped) |
| MAIN | Records | `/records` (scoped) |
| MAIN | Reports | `/reports` (scoped) |
| ORGANISATION *(only when `can_manage_org_users` is set)* | My organisation's users | `/org/users` |

**Data officer** — the shortest nav of all, since a Data officer never
sees a dashboard (see "Roles" in `01-product-scope.md`). No facility
name in the sidebar at all — they aren't locked to one:

| Group | Link (in order) | Route |
|---|---|---|
| INTAKE | New intake | `/intakes` (starts with choosing a facility) |
| INTAKE | Intake history | `/intakes` (history view — every batch this data officer has ever submitted, across every facility) |

**Mobile (Facility lead)** — a four-item bottom tab bar replaces the
sidebar entirely: **Overview**, **Records**, **Reports** — wait, only
three natural primary tabs remain for Facility lead once Intake is
excluded, so the fourth slot is **Care journey**, with everything else
(Needs attention, Outcomes, Identity review) collapsing into the
**More** sheet (see "Mobile bottom-sheet overflow" in the component
library).

**Mobile (Data officer)** — the two INTAKE links plus a **More** sheet
holding nothing extra (there's nothing else in a Data officer's nav to
overflow) — see screen 6 below for the exact layout, which predates
this role clarification and is described as it was built.

## Design tokens — light mode

Colors are given as the exact values used in the rebuilt Overview
screen. A neutral/info card, success, warning, and danger each have
their own tinted background wash — cards are **never** flat white in
this system; see "Cards are tinted" below.

**Backgrounds**

| Token | Value | Used for |
|---|---|---|
| `--cv-bg` | `#f7f6f2` | Page base, under the gradient washes |
| `--cv-bg-wash-1` | `radial-gradient(1000px 640px at 108% -8%, rgba(91,141,239,0.10), transparent 60%)` | Top-right ambient tint, layered over `--cv-bg` |
| `--cv-bg-wash-2` | `radial-gradient(760px 620px at -8% 112%, rgba(52,201,143,0.08), transparent 55%)` | Bottom-left ambient tint, layered under wash-1 |
| `--cv-sidebar-bg` | `linear-gradient(180deg,#151513,#0c0c0b)` | Sidebar |
| `--cv-topbar-bg` | `rgba(247,246,242,0.78)` + `backdrop-filter: blur(16px)` | Top bar (frosted glass) |

**Text**

| Token | Value | Used for |
|---|---|---|
| `--cv-text-primary` | `#12131c` | Headings, values, primary content |
| `--cv-text-secondary` | `#56554f` | Body copy, table cells |
| `--cv-text-muted` | `#898781` | Labels, captions, placeholder-weight text |
| `--cv-text-on-dark` | `#ffffff` / `#e7e6e1` / `#8b8a84` | Text on the sidebar (primary/secondary/muted) |

**Accent (brand)**

| Token | Value | Used for |
|---|---|---|
| `--cv-accent-gradient` | `linear-gradient(135deg,#5b8def,#2f5fd6)` | Logo mark, active-nav-link wash, progress/funnel fills |
| `--cv-accent-solid` | `#2f5fd6` | Links, icon strokes, focus rings, selection/checked states, chart series 1 |
| `--cv-accent-glow` | `0 6px 16px -4px rgba(47,95,214,0.5)` | Shadow under the logo mark and active-nav elements |

**Buttons — primary/submit action, and destructive**

`--cv-button-primary-bg` is a narrow, deliberate token. It is **not** "the
color of buttons" — most interactive elements in this system are not
this color, and should stay exactly as specified elsewhere in this file.
It is specifically for **the one action-button on a screen or card that
submits, confirms, or commits something** — the thing you'd hit Enter
on. That's it.

| Token | Value | Used for |
|---|---|---|
| `--cv-button-primary-bg` | `#111110` (the sidebar's own dark ink) | The single submit/commit action button on a screen or card: Save facility, Save changes, Add facility, New intake, Extract, Confirm flagged field, Approve new template, Start first intake. This is a deliberate decision, not an oversight — blue was tried first and rejected as "too ordinary"; reusing the product's own dark ink instead is more distinctive and keeps the sidebar's identity present in the content area too. |
| `--cv-button-primary-text` | `#ffffff` | Text/icon on a primary/submit button |
| `--cv-button-danger-bg` | `#b3372f` | Destructive buttons only — Delete, Deactivate, Revoke access, and similar. Never changes, regardless of the primary-button color decision above. |
| `--cv-button-secondary-bg` | `#fcfcfb` with a `1px solid #e1e0d9` border | Secondary/ghost buttons (Cancel, Remove, Switch facility) — neutral card surface, no fill |

**This explicitly does NOT extend to every clickable control that
happens to look like a button.** These all keep the color already
specified for them elsewhere in this file, untouched by this decision:
segmented-control tabs and pills (e.g. the Antenatal/Delivery/Postnatal
tab), filter and date-range chips, the toggle switch, pagination's
numbered page buttons, the row-actions (kebab) menu's icon buttons,
status badges/pills, and the active-nav sidebar link. None of those are
a submit/commit action, so none of them move to `#111110` — they keep
whatever color fits their own context (mostly blue for selection/active
states, neutral surface otherwise, status colors where relevant). Blue
(`--cv-accent-solid` / `--cv-accent-gradient`) keeps meaning exactly what
it always has — a link, a selection/checked state, or the active-nav
highlight — it just never fills a *submit* button any more.

**Status washes** (background gradient + border + text/icon color, as a set)

| Status | Card background | Card border | Text / icon |
|---|---|---|---|
| Neutral/info | `linear-gradient(165deg,#f7faff,#edf2fc)` | `rgba(63,110,214,0.14)` | `#2f5fd6` icon, `#12131c` value, `#6b6f80` label |
| Success | `linear-gradient(165deg,#f2faf6,#e6f5ec)` | `rgba(15,157,99,0.18)` | `#0f6b3f` (deep, on light pills) / `#0f9d63` (bright, icons) |
| Warning | `linear-gradient(165deg,#fefaf1,#fcf3de)` | `rgba(201,133,0,0.18)` | `#a3690a` / `#b4770a` text, `#c98500` icon |
| Danger | `linear-gradient(165deg,#fdf5f4,#fbe8e5)` | `rgba(211,66,53,0.20)` | `#b3372f` text, `#c2483d` / `#d03b3b` icon |

**Cards are tinted, deliberately.** Every card on the canvas — stat
tiles, chart panels, table containers, the intake card — picks up a
faint background wash rather than sitting on flat white. Chart/table
panels that aren't reporting a status use the neutral wash (or a plain
`linear-gradient(180deg,#ffffff,#fbfaf6)` for large content panels where
a colored wash would be too loud); stat tiles pick their wash from the
status they're reporting. This is a deliberate identity choice — see
`ui-reference/01-overview-premium.png`.

## Design tokens — dark mode

Dark mode is a full parallel token set, not an automatic filter/invert.
Same hue families throughout (the accent stays the same blue, status
colors stay the same hue), but surfaces invert and every tinted wash
becomes a dark, saturated-but-dim glow instead of a light pastel.

**Backgrounds**

| Token | Light | Dark |
|---|---|---|
| `--cv-bg` | `#f7f6f2` | `#0b0c10` |
| `--cv-bg-wash-1` | `rgba(91,141,239,0.10)` radial, top-right | `rgba(91,141,239,0.16)` radial, top-right |
| `--cv-bg-wash-2` | `rgba(52,201,143,0.08)` radial, bottom-left | `rgba(52,201,143,0.10)` radial, bottom-left |
| `--cv-sidebar-bg` | `linear-gradient(180deg,#151513,#0c0c0b)` | `linear-gradient(180deg,#0d0d0c,#070707)` (one step darker than the content area, so it still reads as its own plane) |
| `--cv-topbar-bg` | `rgba(247,246,242,0.78)` blur(16px) | `rgba(15,16,19,0.72)` blur(16px) |
| `--cv-card-bg` (neutral panel) | `linear-gradient(180deg,#ffffff,#fbfaf6)` | `linear-gradient(165deg,#171a20,#12141a)` |
| `--cv-card-border` | `rgba(20,20,26,0.07)` | `rgba(255,255,255,0.08)` |
| `--cv-card-shadow` | `0 1px 2px rgba(20,20,10,0.04), 0 14px 30px -18px rgba(30,42,90,0.22)` | `0 1px 2px rgba(0,0,0,0.4), 0 14px 30px -18px rgba(0,0,0,0.6)` |

**Text**

| Token | Light | Dark |
|---|---|---|
| `--cv-text-primary` | `#12131c` | `#f2f1ec` |
| `--cv-text-secondary` | `#56554f` | `#b6b4ac` |
| `--cv-text-muted` | `#898781` | `#86847c` |

**Accent**

| Token | Light | Dark |
|---|---|---|
| `--cv-accent-gradient` | `linear-gradient(135deg,#5b8def,#2f5fd6)` | `linear-gradient(135deg,#6d9bf5,#3a68d8)` (a touch brighter, for contrast against dark surfaces) |
| `--cv-accent-solid` | `#2f5fd6` | `#6d9bf5` |
| `--cv-accent-glow` | `0 6px 16px -4px rgba(47,95,214,0.5)` | `0 6px 18px -4px rgba(58,104,216,0.6)` |

**Buttons — primary and destructive**

| Token | Light | Dark |
|---|---|---|
| `--cv-button-primary-bg` | `#111110` | **Not yet decided — see open decision #9 in `08-delivery-plan.md`.** `#111110` reused as-is would sit almost flush against dark mode's `#0b0c10` page background and fail contrast; this needs its own value (most likely inverted — a light neutral button with dark text) before Module 1's design-token work is signed off. Do not guess at build time. |
| `--cv-button-primary-text` | `#ffffff` | Depends on the resolved background above |
| `--cv-button-danger-bg` | `#b3372f` | `#f0776b` (matches the dark-mode Danger status text color already in this file, for the same reason every other status color gets a dark-mode step) |

**Status washes**

| Status | Light bg | Dark bg | Light text | Dark text |
|---|---|---|---|---|
| Neutral/info | `linear-gradient(165deg,#f7faff,#edf2fc)` | `linear-gradient(165deg,rgba(91,141,239,0.16),rgba(91,141,239,0.05))` | `#2f5fd6` | `#8fb4f5` |
| Success | `linear-gradient(165deg,#f2faf6,#e6f5ec)` | `linear-gradient(165deg,rgba(52,201,143,0.16),rgba(52,201,143,0.05))` | `#0f6b3f` | `#4fd39b` |
| Warning | `linear-gradient(165deg,#fefaf1,#fcf3de)` | `linear-gradient(165deg,rgba(230,163,0,0.18),rgba(230,163,0,0.05))` | `#a3690a` | `#e0ad3f` |
| Danger | `linear-gradient(165deg,#fdf5f4,#fbe8e5)` | `linear-gradient(165deg,rgba(224,71,60,0.18),rgba(224,71,60,0.06))` | `#b3372f` | `#f0776b` |

Borders for status cards in dark mode use the same hue at `0.26–0.28`
alpha (mirroring the light mode's `0.14–0.20` alpha borders, just
brighter to stay visible against a dark surface).

**How the toggle works.** Implement as CSS custom properties defined
under `:root` (light, the default) and overridden under
`:root[data-theme="dark"]`, following Tailwind's class-based dark mode
strategy (`darkMode: 'class'` in `tailwind.config`, with the class/attr
applied to `<html>`) rather than the `prefers-color-scheme` media-query
strategy alone — the person needs to be able to force a choice, not
just follow the OS.

- **Default:** on first visit, follow `prefers-color-scheme` (system).
- **Explicit choice:** a sun/moon toggle button lives in the top bar,
  immediately left of the notification bell (see "Top bar" in the
  component library). Clicking it sets `data-theme="dark"` or
  `data-theme="light"` on `<html>`.
- **Persistence:** written to `localStorage` immediately (so the next
  page load has no flash of the wrong theme — use a small
  render-blocking inline script in `<head>` that reads it before first
  paint, the standard pattern for this) **and** saved to the user's own
  profile (`users.theme_preference`, one of `light` \| `dark` \|
  `system`, default `system` — see `02-data-model.md`) so the choice
  follows them across devices once they're signed in, not just
  remembered per-browser.
- Every token above is read through the CSS variable, never hard-coded
  a second time in component styles — a component that needs
  `--cv-accent-solid` reads the variable, so flipping `data-theme` on
  `<html>` is the only code path that ever changes a color.

## Typography, spacing, radius, shadow, icons

- **Typeface:** "Space Grotesk" (weights 600/700) for the brand
  wordmark and all headings (`h1`, `h2`); system font stack
  (`-apple-system, "Segoe UI", system-ui, sans-serif`) for everything
  else. Numeric values (stat tile numbers, table numbers) use
  `font-variant-numeric: tabular-nums` so columns of numbers align.
- **Scale:** 21px page title (`h1`) · 16px brand wordmark · 13–13.5px
  section/card titles · 12.5–13px body and table cells · 11–11.5px
  meta text and secondary lines · 10–10.5px uppercase micro-labels
  (`letter-spacing: 0.3–0.6px`).
- **Radius:** 7–9px on nav items, buttons, and small controls · 10–14px
  on cards and panels · 20px on pills/chips (full capsule).
- **Shadow:** cards use the two-layer `--cv-card-shadow` above (a tight
  1px definition shadow plus a soft, offset ambient shadow) rather than
  a single hard drop-shadow — this is what gives the "glossy premium"
  read instead of a flat Material-style shadow.
- **Icons:** inline stroke SVGs only (no icon font, no emoji), 1.8–2.4px
  stroke weight, rounded caps and joins, 13–18px box depending on
  context — the same feather/lucide-style icon language used
  throughout the prototype. A stat tile's icon sits inside a small
  (26px) rounded-square badge tinted to the tile's status color, per
  the component spec below.

## Component library

**Sidebar nav item.** Inactive: icon stroke `#8b8a84`, label
`--cv-text-on-dark` secondary (`#b7b6b0`), 13px, no background. Active:
icon stroke lightens to a pale accent tint, label `#ffffff` and 600
weight, background `linear-gradient(90deg, rgba(91,141,239,0.24),
rgba(91,141,239,0.05))`, plus a 2.5px solid accent-color left border.
8px vertical padding, 8–10px radius. **This active state is required on
every role's sidebar, for every link, on every screen** — it started as
an Overview-only accent but is now confirmed as the one universal active
state; there is no "plainer" fallback version elsewhere in the product.
The same treatment (slightly tighter padding) is also correct for any
other active/selected pill outside the main nav — e.g. the "PROTOTYPE ·
PREVIEW AS" role-switcher block in this prototype's own sidebar.

**Stat tile.** Padding 14×16px, radius 14px, background + border from
the relevant status wash. A 26×26px icon badge (8px radius, tinted
background at ~20% of the status color, icon stroke at full status
color) sits above an 11px uppercase muted label, a 26px bold tabular
number (with an optional lighter secondary fragment, e.g. "23 / 25"),
and an 11.5px status line with a small icon.

**Chart card.** Padding 18×20px, radius 14px, neutral card background.
Bar charts use a vertical gradient fill (light-to-accent) with a
`inset 0 1px 0 rgba(255,255,255,0.35)` top highlight for a glossy sheen,
4–6px rounded tops only. Horizontal funnel/progress bars use the same
gradient logic left-to-right, darkening at each successive step to show
progression.

**Data table.** Wrapped in a card (14px radius). Header row: 10.5px
uppercase muted labels, hairline top+bottom border. Body rows: 12.5px,
hairline bottom border only, no zebra striping. Status column uses the
**status pill** component.

**Status pill.** Inline-flex, 3×9px padding, 20px (full capsule)
radius, 11px 600-weight text, background/text from the relevant status
wash's *pill* variant (slightly more saturated than the card wash — see
the exact values already in use: success `linear-gradient(135deg,
#e5f5ea,#d8f0e0)` / `#0f6b3f`; warning `linear-gradient(135deg,
#fbf0dc,#f7e6c4)` / `#a3690a`; danger `linear-gradient(135deg,
#fbe7e2,#f8d9d2)` / `#b3372f`). A small check/warning/clock icon
precedes the label where the state benefits from one.

**Filter chip.** Inline-flex, 6×12px padding, 20px radius, background
`linear-gradient(180deg,#ffffff,#f8f7f2)`, hairline border, 12.5px text,
a small chevron-down icon trailing.

**Primary/submit action button.** `--cv-button-primary-bg` (`#111110`)
background, white text, 600 weight, 8px radius, flat — no gradient, no
glow shadow. This replaced an earlier accent-gradient/blue treatment;
the change is deliberate (see "Buttons — primary/submit action, and
destructive" in Design tokens above) and applies to the one submit/
commit action on a screen or card: New intake, Extract, Confirm flagged
field, Add facility, Save facility, Save changes, Approve new template,
Start first intake. It does **not** apply to every button-shaped control
in the product — tabs, chips, the toggle switch, pagination numbers, and
the row-actions menu icons all keep their own colors, specified where
each of those is defined; this token is reserved for the actual "submit
this" moment, not a general button restyle. Secondary/ghost buttons use
the neutral card background (`#fcfcfb`) and a hairline border instead.
Destructive buttons (`--cv-button-danger-bg`, `#b3372f`) always sit
apart from other actions — on the right in a button row, or reached only
through the confirm dialog below — and never adopt the primary button's
dark fill.

**Top bar.** Frosted glass (`--cv-topbar-bg` + `backdrop-filter:
blur(16px)`), hairline bottom border, page title (h1) + subtitle on the
left, filter chips + notification bell + **theme toggle** + primary
button on the right, in that order (theme toggle sits immediately left
of the notification bell — see "How the toggle works" above).

**Mobile bottom-sheet overflow ("More").** A four-item bottom tab bar
(Overview / Intake / Records / More). Tapping **More** opens a modal
sheet: a semi-transparent scrim (`rgba(11,11,11,0.42)`) covering the
full screen behind it, and a white sheet anchored to the bottom (above
the 64px tab bar), 16px top-corner radius, a small drag-handle bar, a
"More" header with a close (×) button, then every nav link that didn't
fit the four primary tabs, each a simple icon+label row. Tapping any
row, the scrim, or the × closes the sheet. This is the general pattern
for any role whose nav has more than four items on mobile — Facility
lead's mobile nav, for instance, would put Care journey, Needs attention,
Outcomes, Reports, and Identity review in this sheet, keeping Overview,
Intake (if applicable), Records, and More as the four fixed tabs.

**Intake extraction checklist ("labor illusion" effect).** See
`03-templates-and-intake.md` for the design rationale. Each register
field renders as one row: a leading status indicator (empty ring =
pending, spinning ring in accent color = reading, filled check in
success color = matched, warning triangle in warning color = needs
mapping), the field label, and a trailing state label ("reading…" in
accent color, or "needs mapping" in warning color) for the two states
that need one. Rows tick down top-to-bottom in real time as the vision
model actually completes each field — never artificially paced.

### Workspace switcher (Data officer)

The control a Data officer uses to scope their whole session to one
facility, replacing an earlier design where facility choice lived inside
the intake card itself. See "Who submits data, and for which facility"
in `01-product-scope.md` and `03-templates-and-intake.md` for the
product rationale.

- **No facility selected (default on login, and after switching).** The
  sidebar's usual position for a locked facility name instead shows a
  clickable badge: a building icon, "No facility selected", and a
  swap-arrows icon, on the sidebar's input-fill color (`#1c1c1a`). The
  main content area shows a **facility index** instead of the intake
  card: a heading ("Choose a facility to begin"), a search field
  (placeholder "Search facilities by name, LGA, or state"), and a
  scrollable list of every facility — each row a small building icon, the
  facility name (bold), a meta line (region · last-intake label ·
  completeness%), an amber flag-count pill when the facility has open
  template flags, and a trailing chevron. Typing filters the list
  live, client-side, across name and region. An empty result set shows
  the standard empty state ("No facilities match "{query}"").
- **Facility selected.** The sidebar badge now shows the facility's name
  (truncated with ellipsis if long) with a caption below it, "Your
  active workspace — click to switch"; clicking the badge, or a
  **Switch facility** button that appears in the top bar next to the
  date-range chip, clears the selection and returns to the facility
  index. The page title becomes the facility's own name, with "{region}
  · your active workspace" as the subtitle. Every stat tile, the intake
  card, and the intake history table below all re-scope to this
  facility — nothing on the page still reads "across every facility"
  once one is chosen.
- **Mobile.** The sidebar badge becomes a full-width **workspace bar**
  directly under the dark top bar (same input-fill background, same
  tap-to-switch behavior) — always visible, whichever content is showing
  underneath it. The facility index and the workspace content below it
  are otherwise the same pattern as desktop, stacked full-width.
- Switching facilities always resets any in-progress intake back to
  idle — there's no such thing as a half-finished intake that follows
  you from one facility's workspace into another's.

### Toast notification

Top-right, fixed to the viewport (not the scroll position), stacking
downward, max width ~340px, one line where possible. Background/border/
text/icon all come from the matching status wash — the same success/
warning/error/info tint pairing as every status badge, so a toast is
never a contrast question. A thin 2px underline in the icon color drains
from full width to empty over the toast's lifetime, giving a visible
countdown. Auto-dismisses at ~4.5s, or a small × dismisses it early.
Never more than a handful stack at once in practice — if several fire in
quick succession, the newest appears at the top.

### Trend chart — loading and empty states

The chart card itself (padding, radius, background) is the existing
"Chart card" spec above; this adds its two non-happy-path states, since
a chart is data-dependent and will hit both in production.

- **Loading.** The bar area is replaced by a row of skeleton blocks at
  plausible-but-fake heights (the `cv-skel` pulse animation — see
  "Loading / skeleton" below), same footprint as the real chart so
  nothing reflows when data arrives. No shimmer sweep; a slow opacity
  pulse only, so it never reads as "stuck." No legend or axis is shown
  while loading.
- **Empty.** A muted 26px line-chart glyph, a 12.5px semibold heading
  ("No data for this range"), and an 11px muted line suggesting a fix
  ("Try a wider date range or a different facility"). Same footprint as
  the loaded chart's plot area, centered.
- Series colors always follow the validated categorical order (blue →
  orange → aqua → yellow, from `--cv-accent-solid` and onward — see the
  Color theme's "Chart series" row) and are never reused for status.
  Only the most recent period gets a direct value label above its bars;
  earlier periods rely on the legend and axis, not a label on every bar.

### Empty state (general)

The same shape everywhere a list, table, or chart has nothing to show:
a dashed 1px border (`#d8d6cc`) card, muted 22px icon, a 12.5px
semibold heading naming what's missing, an 11px muted line giving a
reason or a way forward, and — only when there's a real next action
(not just "nothing here yet") — a primary button beneath it, e.g. "Start
first intake" on a brand-new facility's empty intake history. Never a
blank white box with no explanation.

### Destructive-action confirm dialog

A real in-app modal, not a browser `confirm()` popup — used for
revoking organisation access, deactivating a user, deleting a facility,
or any other irreversible action. Centered, 380px, `#fcfcfb` surface,
12px radius, a `rgba(11,11,11,0.45)` full-screen scrim behind it
(clicking the scrim cancels). A 38px rounded-square icon badge in the
danger wash sits above a 15px bold heading naming exactly what will
happen ("Revoke access for {name}?"), then a 12.5px secondary-text
sentence spelling out the concrete, irreversible consequence — never a
generic "Are you sure?". Two full-width-split buttons: **Cancel**
(secondary, left) and the destructive action itself (danger red, right)
— destructive is always on the right, always red, never the default
focus.

### Filter & date-range chip menu

Extends the existing "Filter chip" spec with its open-menu behavior,
since every chip in the product is interactive, not just decorative.
Clicking a chip opens a floating panel (10px radius, white, hairline
border, drop shadow `0 10px 26px -10px rgba(11,11,11,0.25)`) anchored
below it. Two menu shapes cover every case in the product:

- **Single-select (e.g. date range).** A plain list of options, each row
  showing a bold accent-blue check beside the current selection; a
  dashed divider above a trailing "Custom range…" row when one applies.
  Selecting a row closes the menu immediately.
- **Multi-select (e.g. region).** Each row is a 15px checkbox (accent
  blue when checked, white/bordered when not) plus the label; the chip's
  own label summarizes the count ("2 selected") once more than one item
  is picked, "All" when none are. The menu stays open across multiple
  picks so a person can select several regions in one pass.

Opening one chip's menu closes any other open chip menu on the same bar.

### Loading / skeleton (stat tiles and beyond)

First paint of any stat tile, card, or table shows skeleton blocks (flat
`#e6e5df` fill, 4px radius, a slow ease-in-out opacity pulse between 55%
and 100%, ~1.1s cycle) sized to roughly match the real content's
proportions — a label-width bar above a shorter, taller number-width
bar, for a stat tile specifically. Never a spinner floating over blank
space. Critically: a **background refresh** (switching the workspace
facility, changing a date-range chip) does not re-trigger the skeleton
and blank the tile — the old value stays visible until the new one is
ready, then swaps directly. Skeletons are for first paint only.

### Tooltip

A 14px circular `#e1e0d9` "i" glyph beside any label that benefits from
a one-line definition — a metric name, an abbreviation, a confidence
score. Clicking it opens a dark (`#111110`) panel below-left, 8px
radius, ~240px wide, `#e7e6e1` text at 11.5px/1.5 line-height, one
explanatory sentence. Stays open until the person clicks elsewhere
(not hover-triggered — this must work identically on touch).

### Form field, validation & submission

A labelled input (11.5px semibold secondary-color label, 5px gap, 1px
`#e1e0d9` border normally) that only shows an error after a submit
attempt — never while the person is still typing, and never on blur
alone. On an invalid submit: the border turns danger red (1.5px), a
small red circle-exclamation icon plus an 11px red message appear below
the field ("Enter a valid email address"), and the field revalidates
live on every keystroke from that point on so the error clears the
moment the input becomes valid. A read-only field (e.g. a facility name
that's contextual, not editable, on this form) uses the page background
color as its fill so it visibly can't be focused. Submitting a valid
form fires a success toast and, where relevant, runs the button-loading
sequence below.

### Button states — loading, disabled, success

Every Save/Extract/Confirm-class button follows the same four-state
sequence, so it never looks committed before the request actually
resolves: **idle** (the normal primary-button spec) → **loading**, on
click — same dark fill at 75% opacity, a small white spinning-ring
icon replaces the leading position, the label changes to a present
participle ("Saving…"), `cursor: default` and effectively disabled so a
second click can't double-submit → a brief **success** flash — fill
changes to `--cv-button-danger-bg`'s success counterpart (`#0f6b3f`), a
check icon, "Saved" — before returning to idle. A **disabled** button
(e.g. Save before required fields are filled) uses a flat light-grey
fill (`#eeede7`) and muted text (`#b7b6b0`), never the primary color at
reduced opacity — reduced-opacity-primary is reserved for the loading
state specifically, so the two are never visually confused. Implementer
note: don't rely on the HTML `disabled` attribute's *value* to gate this
— `disabled="false"` still disables in plain HTML/React; gate on
conditional rendering of two variants (or a controlled `disabled={bool}`
prop in React, which behaves correctly, unlike a literal attribute
string) instead.

### Toggle switch

One component, two uses: the theme toggle in the top bar, and any
admin on/off flag (facility active/inactive, user active/inactive, a
notification channel). 38×22px capsule track, `--cv-accent-solid` blue
when on / `#d8d6cc` when off, 18px white knob that slides with an
18ms-eased transform, `0 1px 3px rgba(11,11,11,0.25)` knob shadow. A
label sits to the right, and — for anything less self-explanatory than
"dark mode" — a short state caption beside that (e.g. "Active" /
"Inactive — hidden from new intakes").

### Row actions menu (kebab)

Every admin table row (facilities, users, organisations, templates)
gets a trailing three-dot (⋮) trigger, 26×26px, no visible background
until hovered/open. Clicking it opens a small horizontal icon-only
button row (not a vertical list) anchored to its top-right: white
surface, 10px radius, hairline border, `0 10px 26px -10px
rgba(11,11,11,0.25)` shadow, 6px internal padding, each icon button
32×32px with a 7px radius hover state. **Icons only — no visible text
labels**, each carrying an `aria-label` for accessibility (e.g. "Edit
facility", "View records", "Deactivate") rather than a name printed
next to it; this was an explicit, considered choice over icon+label
rows. Non-destructive actions (Edit, View) use the default secondary
icon stroke color (`#52514e`); a destructive action (Deactivate,
Delete) sits after a 1px vertical divider, stroke colored
`--cv-button-danger-bg` red, and always opens the confirm dialog above
rather than acting immediately.

### Upload / processing progress bar

For staging a register photo before extraction starts — a determinate
fill (the browser genuinely knows upload progress), never an
indeterminate spinner. A label ("Uploading register photo…") and a
right-aligned percentage share one row above a 6px-tall, 4px-radius
track (`#eeede7`) with an accent-blue fill that transitions width over
~140ms per update rather than jumping. On completion: a green check
icon, "Uploaded — ready to extract," replacing the bar.

### Pagination

For any long table (Records, Facilities, Intake history). A left-
aligned "Showing X–Y of N" count, right-aligned Prev/Next chevrons
flanking numbered page buttons (28×28px, 7px radius). The current page
is filled `--cv-accent-solid` blue with white text; other pages are the
neutral card surface with secondary text. Prev/Next each render as one
of two variants depending on whether they're usable — a real button at
one end of the range, or a non-interactive, `#d8d6cc`-colored look-alike
at the other — for the same reason noted under "Button states" above:
a real `disabled` attribute can't be conditionally toggled by its
string value, so use two gated variants instead of one button with a
computed `disabled`.

### Account menu

Settled in the Roles & Operations review: every sidebar's user footer
(avatar, name, role — previously just static text) becomes clickable.
Clicking it opens a small popover anchored above the footer (230px,
white, 10px radius, hairline border, the same floating-menu shadow used
elsewhere) with exactly three rows, identical for every role:

1. **Profile** — the user's own name (editable — see below) and email
   (read-only always). `PATCH /api/v1/users/me`, name only; email and
   role are never self-service, always Systems-admin-set (see
   "Buttons — primary/submit action, and destructive" for why this isn't
   a bigger settings page: it's one field, so it's a small inline edit
   inside the popover, not its own route).
2. **Notification preferences** — links to `/settings/notifications`,
   which was already fully specified but had no link anywhere in the
   product before this. Same page, same behavior, for every role.
3. **Sign out**, set apart with a dashed divider above it and rendered
   in danger red, consistent with every other destructive-adjacent
   action in this system (it isn't literally destructive — nothing is
   deleted — but ending the session is a deliberate, one-way action, so
   it gets the same visual weight).

**There is no password field, anywhere, on purpose.** Sign-in is
magic-link or SSO only (see `00-START-HERE.md`'s "Final locked
decisions") — nobody has a Cureva Care password to change. An SSO user's
password lives with their identity provider (Google, Microsoft/Azure
AD, Okta), not here.

## Screens

### 1. Overview (`/overview`) — `Main.dc.html`

This is an Organisation user's multi-facility Overview (the version
scoped to their organisation's granted facilities — see screen 8 for how
a Facility lead's single-facility version of this same page differs).
Reference: `ui-reference/01-overview-premium.png` (the only screen
already rebuilt to this system). Layout: sidebar (Organisation user nav,
per the navigation map above) + top bar (title, 2 filter chips —
Facility, date range — bell, theme toggle) + content: a 5-column row of
stat tiles (Reporting facilities, Verified records, Open referrals,
Stale facilities, Template flags — each tinted per its own status), a
2-column row (Contact activity bar chart, Care-journey funnel), and a
facilities status table (5 rows shown, "View all facilities" link to
`/facilities`). No **+ New intake** button here — that action belongs
only to a Data officer's `/intakes` screen (screen 5), since neither a
Facility lead nor an Organisation user submits data.

### 2. Admin · Templates (`/admin/templates`) — `Templates.dc.html`

Reference: `ui-reference/02-admin-templates.png` (structure/content
only — restyle to the token system above, not to this image's flat
styling). Layout: sidebar (Systems admin nav, Templates
active) + top bar (title, subtitle, **+ New template** button) +
content: a 3-way segmented control (Antenatal (ANC) / Delivery /
Postnatal (PNC)), a "Shared default" card showing the active default
template's version, approver, usage count, and its field list as chips,
a "Facility-specific overrides" table (facility, template, version,
approved by, status), and an "Open flags — awaiting admin review" panel
listing each flagged intake with **Review** and **Approve new template**
actions. See "Template-mapping admin screen" in
`03-templates-and-intake.md` for the full behavior this screen exposes.

### 3. Admin · Manage facilities (`/admin/facilities`) — `Facilities.dc.html`

Reference: `ui-reference/03-admin-facilities.png` (structure/content
only). Layout: sidebar (Systems admin nav, Manage facilities
active) + top bar (title, facility count/region count subtitle, **+ Add
facility** button) + content: 3 filter chips (Region, Template, Status)
plus a search box, and a facility table (Facility, Region, Template —
"Default" or "Custom · v#" pill —, Last intake, Completeness, Status).
**+ Add facility** opens the guided State → LGA → Ward picker described
in `02-data-model.md`.

### 4. Facility lead (`/overview`, locked view) — `FacilityLead.dc.html`

Reference: `ui-reference/04-facility-lead.png` (structure/content only).
Layout: sidebar (Facility lead nav, per the navigation map above — note
the facility name shown as a non-clickable context row, not a
switcher) + top bar (facility name as title, "locked to your
assignment" subtitle, one date-range chip) + content: a 4-column stat
row (Open referrals, Identity matches pending, Missed postnatal
follow-up, 4+ ANC completion %), a 2-column row (this facility's
care-journey funnel + a follow-up worklist table naming each woman,
reason, and days-since), and an "Identity matches awaiting your
confirmation" table (new record, candidate match, matched-on fields,
confidence score, Confirm/Reject actions) — this is the identity-review
queue from `02-data-model.md`, surfaced inline for convenience as well
as at `/identity-review`.

### 5. Data officer (`/intakes`) — `DataOfficer.dc.html`

**This screen was rebuilt this round around the workspace switcher** (see
"Workspace switcher (Data officer)" in the Component library above) —
an earlier version of this board put a single-field facility picker
*inside* the intake card as its first step; that's been replaced by a
session-level switcher that scopes the whole screen, not just the
intake card. The prototype board now matches the spec below.

Layout: sidebar (Data officer nav, per the navigation map above — the
workspace-switcher badge sits directly under the brand mark, above the
INTAKE group, showing either "No facility selected" or the active
facility's name) + a top bar and content area that both depend on
whether a facility is currently active:

- **No facility active.** Top bar shows only a title ("Choose a
  facility to begin") and subtitle ("Search the index below, select
  one, and your workspace switches to it") — no stat row, no date chip,
  no New intake button, since none of those mean anything yet. The
  content area is the facility index: a card containing a search field
  ("Search facilities by name, LGA, or state") and the scrollable
  facility list described in the workspace-switcher component spec.
- **Facility active.** Top bar: the facility's name as the page title,
  "{region} · your active workspace" as the subtitle, and on the right
  a **Switch facility** secondary button, a date-range chip ("Last 30
  days"), and the **New intake** primary button. Content: a 3-column
  stat row scoped to *this* facility (Data completeness, Last intake —
  red and flagged with "N days past the 14-day alert window" once
  stale, Open template flags — red-bordered card and amber "awaiting
  admin resolution" line once nonzero) and, below it, **the intake
  card**, which is stateful:

  - **Idle (default).** Two side-by-side dashed-border tiles: **Capture
    Register** (camera icon) and **Upload Register** (upload icon), each
    with a one-line description. Clicking either moves to Staged. (The
    facility is already established by this point — this step no longer
    asks for one.)
  - **Staged.** Header "Review before extracting" with a source line
    ("Captured just now · this device's camera" or "Uploaded photo"), a
    file row (thumbnail icon, "ANC register — page 1", "Ready for
    extraction", a **Remove** link), and a full-width **Extract**
    primary button.
  - **Extracting.** The full field checklist (component spec above)
    ticks down field by field in real time — this is the labor-illusion
    effect from `03-templates-and-intake.md`, not a fake loader.
  - **Done.** Header becomes "Extraction complete" with a match/flag
    summary line. Two actions appear: **Start another intake**
    (secondary, returns to Idle, same facility still active) and
    **Confirm flagged field** (primary, goes to
    `/intakes/[id]/confirm-fields`).
  - **Register-family mismatch (interrupts Extracting → Done).** See
    "Register-family cross-check" in `03-templates-and-intake.md` — a
    distinct banner state with **Confirm &lt;declared&gt; is correct**
    and **Switch to &lt;suspected&gt;** actions, replacing the normal
    Done summary until resolved.

  Below the intake card: "Your intake history at {facility}" table
  (Register, Submitted, Rows, Source, Status) — scoped to the active
  facility, unlike the personal cross-facility history an earlier
  version of this spec described; switching facilities switches this
  table too.

### 6. Data officer — Mobile (`DataOfficerMobile.dc.html`)

Same workspace-switcher model and the same intake-card states as
screen 5, in a 390×844 single-column phone layout: a dark top bar
(brand mark, a desktop-view link, avatar) with a full-width
**workspace bar** directly beneath it (tap anywhere on the bar to open
the facility index, whether switching away from a facility or choosing
the first one) — see the "Mobile" bullet under the workspace-switcher
component spec.

With no facility active, the content area below the workspace bar is
the same searchable facility index as desktop, stacked full-width. Once
one is active: stacked full-width stat tiles, then the intake card
(Capture Register as the primary filled full-width button, Upload
Register as a secondary dashed-outline button below it), then a
stacked-cards intake history (not a table) scoped to that facility. No
bottom tab bar is needed the way `01-product-scope.md`'s general mobile
pattern describes for Facility lead — a Data officer's whole nav is the
two INTAKE links, so mobile keeps those as a simple two-item bottom tab
bar (New intake / Intake history) instead of a four-item bar with a
More sheet.

### 7. Admin · Organisations (`/admin/organisations`)

No prototype board built yet — spec only, following the same visual
system and the same guided-picker pattern already established for
`/admin/facilities`. Layout: sidebar (Systems admin nav,
Organisations active) + top bar (title, organisation-count subtitle,
**+ New organisation** button) + content: an organisation table (Name,
Type, Facilities/regions granted — a short summary chip like "12
facilities · Kano, Lagos" —, Access tier, Active users, Status).
**+ New organisation** opens a short two-step flow: (1) name and type,
(2) a facility/region access step reusing the same State → LGA → Ward
picker component as facility creation, except selecting at any level
grants that whole node (not just one facility) and multiple
facilities/regions can be added to one grant, each row also getting its
own access-tier selector (Aggregate / De-identified / Identifiable,
defaulting to Aggregate per `07-security-privacy-access.md`). Clicking an
existing organisation opens the same picker, pre-filled, to add or
revoke grants.

### 8. Organisation dashboard (`/overview` and the rest of MAIN)

No new visual components — this is screen 1 (Overview) and the rest of
the MAIN group (Care journey/Outcomes/Facilities/Records/Reports),
rendered exactly as already specified, with the facility scope resolved
to the organisation's granted set. Nothing to build twice — see screen 1
above and screen 4 (Facility lead) for how the same pages render for the
other role that sees them, locked to one facility instead of a
configurable set. **Needs attention (screen 12) is not part of this
group for an Organisation user** — see screen 12 below for why; screen
1's "Open referrals" stat tile is the rolled-up signal an organisation
gets instead.

### 9. My organisation's users (`/org/users`)

Only visible to an Organisation user with `can_manage_org_users` set
(see "Roles" in `01-product-scope.md`) — everyone else in that
organisation doesn't see this link at all. No prototype board built yet
— spec only. Layout: sidebar (Organisation user nav, My organisation's
users active) + top bar (title, subtitle, **+ Invite user** button) +
content: a user table (Name, Email, Role, Status) scoped to this
organisation only. **+ Invite user** opens a short form (name, email,
and a toggle for whether the new user should also get
`can_manage_org_users` — every invited user is role `organisation_user`,
there's nothing else to pick). **Each row gets the standard row-actions
menu** (icon-only kebab, see the Component library) with a single
Deactivate action — `DELETE /api/v1/organisations/{id}/users/{userId}`,
soft delete only, behind the destructive-action confirm dialog. Settled
in the Roles & Operations review: this was previously create-only, with
no way to remove someone once invited.

### 10. Admin · Users & roles (`/admin/users`)

No prototype board built yet — spec only, same shape as screen 9 with
admin's wider scope. Layout: sidebar (Systems admin nav, Users & roles
active) + top bar (title, user-count subtitle, **+ Create user**
button) + content: a filterable table (Name, Email, Role, Facility/
Organisation — whichever applies, or "—" for a Systems admin — Status).
**+ Create user** opens a short form: name, email, role (Data officer /
Facility lead / Systems admin — this screen never creates an
Organisation user, that only happens via `/admin/organisations`), and,
only when Facility lead is picked, a facility picker (the guided
State → LGA → Ward → Facility control). **Each row gets the standard
row-actions menu**: Edit (name or role — `PATCH /api/v1/users/{id}`,
opens the same short form pre-filled) and Deactivate (soft delete,
`POST /api/v1/users/{id}/deactivate`, behind the destructive-action
confirm dialog; a deactivated row shows a muted "Inactive" status pill
with a **Reactivate** action in its place). Settled in the Roles &
Operations review: this screen was previously create-only.

### 11. Admin · Settings (`/admin/settings`)

No prototype board built yet — spec only. Layout: sidebar (Systems
admin nav, Settings active) + top bar (title, subtitle "Every tunable
value in the platform, in one place") + content: a single-column list of
setting rows (`GET /api/v1/settings`), each a card showing the setting's
key, its human-readable description, its current value, its default,
and an inline edit control matched to its declared type (a number field
for `stale_facility_alert_days`, a percentage/slider for a confidence
threshold, and so on). Saving one row is its own
`PATCH /api/v1/settings/{key}` call with the standard button-loading
sequence — there's no page-level "Save all," since settings are
independent and saving them independently avoids one bad edit blocking
every other one.

### 12. Needs attention (`/needs-attention`)

Never given its own screen spec until now — it existed only as a nav
link. **Facility-lead-only** — settled in a later Roles & Operations
pass: an Organisation user does not get this route, this nav link, or
the underlying `GET /api/v1/worklists` endpoint at all (see
"Organisations and access scoping" in `01-product-scope.md`). Cureva Care
sells organisations clean intelligence, not an operational to-do list of
other people's unresolved cases — especially once "Mark actioned"
existed only for a Facility lead, a read-only worklist for anyone else
had no real purpose. An organisation still sees this lens, rolled up, as
the "Open referrals" stat tile on their Overview (screen 1) — never the
named-case list. Layout: sidebar + top bar (title, date-range chip) +
content: a worklist table (`GET /api/v1/worklists`) — Woman/record
reference (identifiable, since only an identifiable-access Facility
lead reaches this screen), the triggering
rule's plain-language reason, severity as a status pill, days open, and
a trailing action column. **Mark actioned**, settled in the Roles &
Operations review: a secondary button opens a small inline note field
("What did you do?", optional) and confirms with
`POST /api/v1/worklists/{itemId}/action`. An actioned item stays on the
worklist — it isn't removed — but picks up a muted "Actioned 3 days ago
by {name}" line beneath its reason, so a Facility lead can see at a
glance what's genuinely untouched versus already followed up on. If the
rule still evaluates true after a later intake, the item's severity
treatment is unchanged by having been actioned before — action history
is additive, never a dismissal.
