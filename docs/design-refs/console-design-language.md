# Console Design Language — the SKIN
### Foundation Operator Console · reusable design-language framework v1.1
<!-- v1.1 (2026-07-04): +§5.11 console data-unavailable state, +§5.12 Vision grade — the 2 framework-change-requests surfaced when composing the v2 mockups (the foundation reporting its own gaps, per architecture §8). -->
**Derived from:** `council-of-elrond-v2/foundation-operator-gui/index-v2.html` (the polished demo — the quality bar)
**Paired with:** `console-gui-architecture.md` (the SKELETON). This doc owns *how it looks, moves, and speaks*; that doc owns *how it is structured*. They are deliberately decoupled: re-theming never forces a restructure, restructuring never forces a re-theme.
**Scope:** every FOPSCON screen, and every future console-type program built by the Foundation. Cheaper models build screens by composing these rules — do not improvise outside them.

---

## 0. The one law that outranks everything here: HONESTY

This design language is a re-skin, **not a re-truth**. Every rule below is subordinate to the Trust Strip law:

> **Nothing renders green / done / live / running unless it is computed from real evidence.**

- A green pill exists only because a real probe, gate, or signoff produced it. The component spec below tells you *how* green looks; only real data tells you *whether* it appears.
- Unknown values render as `—` with a plain-words note (e.g. `version — unavailable · the program doesn't report one yet`). Never a placeholder number, never a fabricated trend.
- Missing history renders as *absence with an explanation*, never a synthetic sparkline. No metrics store → no trend line, period.
- The degraded states (`one-key`, `vacuous`, `inadequate`, `blocked`) are first-class citizens of the palette. They are styled as carefully as success — because the design language's job is to make honesty *beautiful*, not to hide it.
- House rule, verbatim from the demo: **"The number can be ugly, but it can't lie."**

---

## 1. Design tokens (copy-paste these — they ARE the theme)

These are real CSS custom properties, lifted from the demo. A screen is on-theme iff it consumes these tokens and introduces no parallel constants. Hardcoded hex outside this block is a defect.

```css
:root{
  /* ---- surfaces: the obsidian stack (darkest→lightest = depth) ---- */
  --bg:#0c0c0e;            /* page floor */
  --surface:#16161a;       /* card */
  --surface-2:#1b1b20;     /* nested panel / input / chip */
  --surface-3:#212127;     /* deepest nesting, tooltip, skeleton block */
  --line:rgba(255,255,255,.065);        /* default hairline */
  --line-strong:rgba(255,255,255,.13);  /* emphasized hairline / control border */
  --grid:#232329;          /* chart gridlines */

  /* ---- ink: warm off-whites, never pure white ---- */
  --ink:#f2f2ee;           /* primary text */
  --ink-2:#c3c2b7;         /* secondary text */
  --ink-3:#8b897f;         /* tertiary / captions / micro-labels */

  /* ---- trust palette (SEMANTIC — only evidence may summon these) ---- */
  --good:#0ca30c;  --good-hi:#2ec02e;   /* honest green (fill / text-on-dark)   */
  --warn:#fab219;                        /* vacuous / one-key / attention        */
  --serious:#ec835a;                     /* inadequate                           */
  --crit:#d03b3b;  --crit-hi:#e25a5a;   /* blocked / failure (fill / text)      */

  /* ---- identity accents (NON-semantic — never encode pass/fail) ---- */
  --accent:#3987e5;        /* the loop's blue — primary actions, active nav */
  --aqua:#199e70;          /* second categorical / care & maintenance      */
  --gold:#c98500;          /* third categorical (charts only)              */
  --violet:#9085e9;        /* the brain / deliberation                     */
  /* light-on-dark text variants: accent-text #7db3f0 · violet-text #b0a7f2 */

  /* ---- geometry ---- */
  --r-lg:16px; --r-md:11px; --r-sm:7px;   /* card / panel / control */

  /* ---- type ---- */
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,"Cascadia Mono","Segoe UI Mono",Consolas,monospace;
}
```

Base body: `background:var(--bg); color:var(--ink); font:14px/1.5 var(--sans); -webkit-font-smoothing:antialiased;`
Selection: `::selection{background:rgba(57,135,229,.35)}`.

### Token usage rules
1. **Trust colors are earned, not decorative.** `--good*`/`--warn`/`--serious`/`--crit*` may only color an element whose state came from evidence (manifest, probe, gate). Decoration uses the identity accents.
2. **Tinted fills, not solid floods.** Semantic backgrounds are the hue at low alpha over surface: e.g. two-key fill `rgba(12,163,12,.10)` + border `rgba(46,192,46,.42)` + text `--good-hi`. Solid semantic fills are reserved for the primary `.btn.primary` (accent) and `.btn.danger` (crit).
3. **Depth = surface step + hairline, not heavy shadow.** One card shadow exists (see §4); nesting is expressed by moving up the surface stack.
4. **Numbers are tabular.** Any changing numeral gets `font-variant-numeric:tabular-nums`.

---

## 2. Type scale

One family (`--sans`), weight and tracking do the work. Mono (`--mono`) is for machine identifiers only: IDs, URLs, SHAs, layer names, costs-in-tables.

| Step | Size / weight / tracking | Use |
|---|---|---|
| **Hero** | 34px / 680 / -0.02em, lh 1.2 | The one emotional headline per front-door screen. May carry the gradient `em` (see §6). |
| **H1** | 22px / 650 / -0.01em | Screen title in the view header |
| **H2** | 18px / 660 | Primary-object title (e.g. program name in a hero card) |
| **H3** | 15.5px / 650 | Section lede titles |
| **H4 / card title** | 13–13.5px / 650 | Card headings, with a 14px leading icon |
| **Body** | 14px / 400–500, lh 1.5 | Default |
| **Body-emph** | 14.5–15px / 600–640, lh 1.45–1.55 | The "ask", vision statements |
| **Secondary** | 12.5–13px / 400–500, `--ink-2/3` | Supporting prose |
| **Caption** | 11.5–12px, `--ink-3` | Card subtitles, notes, hints |
| **MICRO** | 10.5px / 650 / +0.13em, UPPERCASE, `--ink-3` | The signature label style (`.micro`). Section eyebrows, metric captions |
| **Tag** | 10px / 700 / +0.07em, UPPERCASE | Pills and tags |
| **Big stat** | 25px / 650 / -0.02em | Vitals-tile values |

Rule: **large type is soft-weighted (≤680) with negative tracking; small type earns emphasis through uppercase + wide tracking, not size.** That contrast is most of the demo's sophistication.

---

## 3. Space & layout rhythm

- Card padding: **20–22px** (compact tiles 14–17px). Card-to-card gap: **14–16px**. Section gap: **22–46px** (bigger before a narrative moment).
- Content measure: journey/prose screens cap at **900–1120px**; the front door caps at 1060px with a centered 760px input.
- Grids: primary/secondary split is `minmax(0,1.45–1.55fr) minmax(0,1fr)`; tiles `repeat(4,1fr)`, collapsing 4→2→1 (breakpoints in the architecture doc).
- Hairlines (`--line`) separate regions *inside* a card; whitespace separates cards.

---

## 4. Elevation & special surfaces

```css
/* the ONE card recipe */
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 8px 28px -18px rgba(0,0,0,.7);}
```
- The inset top highlight (machined-edge feel) + a soft deep drop. Do not invent other shadows for resting cards.
- **Gradient-frame hero** (reserved for THE object of a screen — max one per screen): a 1.5px gradient border via padding trick — outer div `border-radius:18px;padding:1.5px;background:linear-gradient(150deg, colorA, colorB 45%, rgba(255,255,255,.08))` + colored glow `box-shadow:0 30px 80px -34px <colorA-glow>`; inner div `background:#121217;border-radius:17px`. Demo uses green→blue for a living app window, blue→violet→aqua for the idea box. The green-tinted frame is itself a truth claim → only when the thing inside is verifiably alive.
- Overlays: tooltip/toast on `#232329` + `--line-strong` + `0 10–14px 28–40px` black shadow; drawer = full-height right panel on `--surface`, `-30px 0 80px -30px rgba(0,0,0,.9)`, behind it a scrim `rgba(6,6,8,.6)` + `backdrop-filter:blur(2px)`.

---

## 5. Component library

Skeleton/placement of each lives in the architecture doc; this section is the *visual contract*. Components consume tokens only.

### 5.1 App shell chrome (visual spec)
Sidebar: `linear-gradient(180deg,#101014,#0c0c0e 40%)`, right hairline `--line`. Brand = 30px SVG mark + name (15px/650) + MICRO subtitle. Main column padding `26px 32px 70px`.

### 5.2 Journey-rail step (`.rstep`)
- Row: 28px circular glyph + label (13.5px/500, `--ink-2`) + MICRO-style sublabel + optional badge. Radius `--r-sm`, padding 10px 8px.
- A continuous 1.5px vertical thread runs behind the glyphs: `linear-gradient(180deg, rgba(57,135,229,.5), rgba(57,135,229,.14) 55%, rgba(255,255,255,.08))` — the journey literally fades from "already lit" to "not yet".
- States — hover: `rgba(255,255,255,.045)` fill; **active:** `rgba(57,135,229,.13)` fill, glyph border `--accent`, glyph fill `rgba(57,135,229,.14)`, halo `0 0 0 3px rgba(57,135,229,.12)`, icon `--accent`.
- The human-seat step (Guide) draws its glyph border **dashed** until active — the seat is reserved for a person.
- Badge: amber `--warn` pill, 20px, dark text `#161005`, count of items awaiting the human.

### 5.3 Narrative program card (`.gcard`)
The card that makes the product emotional. Order is fixed:
1. **The wish, quoted** — the human's actual sentence, 12px italic `--ink-3`, wrapped in real curly quotes;
2. **The becoming** — arrow icon (aqua) + program name, 13px/600;
3. **Footer strip** (hairline above): loop-ring state, stage label, vision grade (severity-colored numeral), `N features alive` right-aligned.
Hover: border → `rgba(57,135,229,.42)`, `translateY(-2px)`. Never put trust chrome on this card — its job is warmth; truth detail lives one click away.

### 5.4 Trust Strip / assurance manifest (`.manifest`) — carried over VERBATIM
The honesty law rendered. Visuals may be reskinned; **states, order and wording may not.**
- Container: `linear-gradient(180deg,var(--surface-2),rgba(27,27,32,.55))`, `--line-strong` border, `--r-md`.
- Header: shield icon + MICRO "Assurance manifest" + `honest`/`sound` boolean flags (bordered mini-tags, green when true / red when false — a false flag renders, plainly).
- **Effective banner** (the headline verdict): `TWO-KEY` green-tint · `ONE-KEY` amber-tint · `VACUOUS` orange-tint · `BLOCKED` red-tint (+ mono "via" detail, e.g. `mechanical_lock + graded_review`; blocked adds "human hands only").
- Trust-weight meter: big numeral colored by severity ramp (≥.75 good / ≥.45 warn / ≥.25 serious / else crit), track at 16% alpha, fill animates `width .8s`, notch at 75%, MICRO caption.
- Layer chips, fixed order `mechanical_lock · graded_review · gate_integrity · required_tests · canary`; state iconography **✓ active · ◌ dashed-circle vacuous · △ inadequate · — n/a**; mono layer name + uppercase state.
- Footnotes keep the demo's honest phrasing: *vacuous — "passed by absence, not by force"*; *inadequate — "engaged, but below the bar"*.
- Compact variant (`.compact`) for embedding in drawers/cards.
- **Inline shorthand** (feature rows, lists): a small pill — 9px square pip in the effective color + the word (`two-key` / `one-key` / `blocked`) — that opens the full manifest on demand. Shorthand may summarize, never upgrade.

### 5.5 Buttons (`.btn`)
Base: radius 8px, 8×16px pad, 13px/640, `--line-strong` border, `--ink-2` text; hover brightens border+ink. Variants: **primary** solid `--accent` (hover `#2f76cd`); **approve** green-tint (the blessing action); **reject** red border-only; **danger** solid `--crit` (take-the-wheel — visually loud because it's an honest override); sizes `sm`/`lg`; disabled `opacity:.38`. Optional 13px leading icon.

### 5.6 Inputs
Textarea/answer: `--surface-2` fill, `--line` border, `--r-sm`, focus border `rgba(57,135,229,.5)` (+ the global `:focus-visible` ring). The front-door idea box alone gets the gradient-frame treatment (§4) over `#131318`. Radio option row (`.opt`): bordered row, selected = accent border + `rgba(57,135,229,.09)` fill + filled dot.

### 5.7 Pills, tags, chips
- `.live` pill: bordered 999px pill, MICRO-style text, 7px pulsing green dot — "Loop live". A truth claim: render only from a live signal.
- `.tag`: 10px uppercase bordered tag; semantic variants tint text+border only (never filled).
- `.fchip` filter/picker chip: 999px, selected = accent tint + accent border.
- Status pips: 5–8px dots; green pips carry a soft glow `0 0 6px rgba(46,192,46,.6–.7)` — alive things emit light.

### 5.8 Loop-alive heartbeat (`.loopline` + `.loopring`)
The permanent proof-of-life. Ring: 18px SVG circle, faint track + accent arc `stroke-dasharray:12 32` orbiting (`--spd` 2.3s building · ~4–6s calm/shipped(green arc) · 7s idle-ish; **idle = static dotted gray, no spin**). Beside it: `Loop alive` (12.5px `--ink-2`) + `last increment Nm ago` (11px `--ink-3`) — a *computed* freshness fact, or an honest `loop quiet · Nh since last increment` when stale. Sits in the rail foot (placement: architecture doc). The ECG heartbeat line (animated dash, `--good-hi`) is the larger alive-motif for Living-screen vitals — only above a real health signal.

### 5.9 Charts & data viz
Hand-drawn SVG, no libraries. Categorical: blue `#3987e5` / aqua `#199e70` / gold `#c98500` (CVD-validated on `--surface`). Gridlines `--grid`, axis text 10px `--ink-3`. Lines 2px with end-dot (4.5px, surface-stroked) + end label; areas at 10% alpha. Crosshair + dark tooltip on hover. Sparklines: 1.6px `#5a5850` line, colored end-dot. **No data → no chart** — render `—` + a plain-words note.

### 5.10 Trust drawer & toasts
Drawer (§4 surface): header = shield + title + ✕; body stacks MICRO-labeled sections of manifests, friction telemetry (5-box grid, `hot` amber numerals when >2), and honest prose. Toasts: bottom-right, icon colored by kind, ~4.6s then fade.

### 5.11 Console data-unavailable state (`.datafail`) — "the console can't see" *(added v1.1, framework-change-request)*
The console's OWN read/source failure — **distinct from the §5.4 trust states.** §5.4 says "we can see the program and its assurance is weak"; this says "the console couldn't *read* its data, so we don't know — and we say so." Never render a source-read failure as a green, a calm idle, or an honest-empty: an unanswered source is **not a confirmed zero.**
- Panel: `--warn` border, `--surface-2` fill, `--r-md`; MICRO header e.g. "couldn't read build state" / "showing 2 of 3 sources".
- Names the unreachable source(s) in mono (`accept`, `pipeline`, …); status pip is amber `unknown` (△ / dashed) — **never a green pip, never the calm idle ring.**
- Plain-words note (§7.7 honest-absence): "a source didn't answer — this isn't a confirmed clear/idle, just what we could reach." Offer a retry affordance where one exists.
- Partial degrade (some sources answered): show what was read **plus** the named gap ("showing 2 of 3 sources") — never silently drop the missing one.

### 5.12 Vision grade (`.vgrade`) — the Idea→Vision verdict *(added v1.1, framework-change-request)*
The honest grade of a drafted Vision against the ≥0.60 vision-gate. Reuses the §5.4 trust-weight-meter *mechanics* for a Vision score — the two are **separate components sharing a meter idiom**, not one component doing two jobs.
- Big numeral colored by the **gate**, not the trust ramp: **ready ≥ .60** → `--good` + "Ready to start"; **not-ready < .60** → `--warn`/`--orange` + "Not ready yet". No third "almost" state — it clears the floor or it doesn't.
- Meter: track at 16% alpha, fill colored to match, a **notch at the 0.60 floor**; MICRO caption "computed by the vision-gate · eligible · ≥ 0.60 floor" (or "· below the 0.60 floor").
- NOT-READY renders the gate's findings — severity-tagged rows (HIGH/MED/LOW pills, §5.7) under "What the gate found missing" — graded down, not glossed over. **No praise copy on a not-ready grade.**
- The Start affordance is gated on ready: ready → enabled "Looks right — start building it"; not-ready → a **locked** "Start — locked until it clears." The console won't fake a pass.
- Voice (§7.3): "Vision grade — earned, not granted." / "The number can be ugly, but it can't lie."

---

## 6. Signature moves (what makes it *this* console)

1. **The gradient `em`** — inside a hero H1 only: `background:linear-gradient(92deg,#7db3f0,#3987e5 45%,#9085e9)` text-clipped. One per screen, max.
2. **The quoted wish** — the human's origin sentence, italic, in real `“ ”`, recurs at every stage ("Born from: …"). This is the product's soul; never paraphrase it.
3. **Alive things move; dead things don't.** Motion = evidence of life (orbiting ring, ECG, pulsing dot, shimmer). Never animate a static fact.
4. **Truth folded, never hidden** — warm surface, rigorous drawer, one click apart, e.g. "Every light in this constellation earned its green. *See the honest paperwork*."
5. **Dark warmth** — warm off-white ink on near-black; tinted translucent fills; glow used only on living/green elements.

## 7. Copy voice — emotional but honest

Register: **a trusted craftsman speaking plainly to the person whose idea it is.** Second person, present tense, concrete.

Rules with canonical examples (reuse these cadences):
1. **Lead with the human's stake, not the system's mechanics.** "Every program here began as a sentence like yours." / "You bring the idea and the judgment. The loop brings the hands."
2. **Name the covenant in every CTA area.** "Nothing builds until you say so." / "The loop suggests — you decide."
3. **Honesty is stated proudly, not apologetically.** "Vision grade — earned, not granted." / "graded down, not glossed over" / "The number can be ugly, but it can't lie."
4. **The loop is humble and animate; never grandiose.** It "paused to ask rather than guess", "stopped itself rather than ship something it couldn't vouch for", is "waiting warmly".
5. **Metaphor set (pick from, don't extend):** journey/road · skeleton→flesh · heartbeat/alive · garden/tending ("a garden, not a monument") · light ("features alive", constellation) · keys ("two keys turned", "your blessing is the second key").
6. **Microcopy carries warmth too**: buttons say "Looks right — carry on", "I believe it — set the loop loose", "My hands, my call" — never "Submit"/"OK"/"Confirm".
7. **Absence is phrased as honest absence:** "point-in-time only · no history store yet", "there's nothing to fake", "unavailable — the program doesn't report one yet".
8. Em-dashes for the turn of a sentence; sentence case everywhere except MICRO/tags; no exclamation marks; no jargon on PO surfaces (jargon is allowed inside the drawer, in mono).

## 8. Motion & reduced motion

- Easing signature: `cubic-bezier(.2,.7,.2,1)`. View/card entrance: `rise` — `opacity 0→1, translateY(9px)→0, .34s`.
- Durations: hover 130–180ms · entrances 300–500ms · meters/arcs 800–1400ms · ambient loops 2.2–6s (pulse 2.2s · ECG 3.2s · shimmer 3.6s · ring per §5.8).
- Ambient motion budget: **≤3 concurrently animated elements per viewport**, all meaning "alive".
- Mandatory kill-switch, verbatim:
```css
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.001s !important;transition-duration:.001s !important}}
```
plus JS `REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches` to skip typewriter/cascade sequencing (content appears immediately).
- Accessibility floor: `:focus-visible{outline:3px solid rgba(57,135,229,.4);outline-offset:2px}`; body text ≥ 4.5:1 (all `--ink*` on all surfaces pass); semantic text-on-dark uses the `-hi` variants; charts get `role="img"` + `aria-label`; drawers manage `aria-hidden` + Escape.

## 9. Compliance checklist (the fidelity-gate rubric for any new screen)

- [ ] Consumes §1 tokens only; no novel hex/radius/shadow/font.
- [ ] Type scale honored; MICRO used for eyebrows; numerals tabular; mono only for machine identifiers.
- [ ] Every green/live/done element traceable to real evidence; unknowns render `—` + plain-words note; no fabricated trends (**hard gate**).
- [ ] Trust states use exact §5.4 taxonomy and phrasing.
- [ ] At most one gradient-frame hero; ambient-motion budget respected; reduced-motion clean.
- [ ] Copy passes §7 (register, covenant line present, honest-absence phrasing, no "Submit").
- [ ] The origin wish is quoted where the screen tells any part of the journey.
- [ ] Focus rings visible; contrast floor met.
- [ ] Console data-plane unavailability (a source/read the console itself couldn't reach) renders the §5.11 data-unavailable state — amber `unknown`, sources named — never a fabricated idle/empty/green, and distinct from a program's §5.4 trust state (**hard gate**).
- [ ] A Vision score renders via §5.12 — numeral colored by the 0.60 gate, ready/not-ready honest with the gate's findings shown when not-ready, Start gated on ready.
