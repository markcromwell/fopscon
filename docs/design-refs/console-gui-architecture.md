# Console GUI Architecture — the SKELETON
### Foundation Operator Console · reusable GUI-architecture framework v1.0
**Derived from:** `council-of-elrond-v2/foundation-operator-gui/index-v2.html` (the polished demo).
**Paired with:** `console-design-language.md` (the SKIN). Skeleton = shell, navigation, composition, state, and who-sees-what. Skin = tokens, component visuals, voice, motion. **A theme change must never force a restructure; a restructure must never force a re-theme.** If a rule here mentions a color or copy tone, it is a cross-reference to the skin doc, not a definition.
**Scope:** FOPSCON and every future console-type program. Together the two docs are the "console TYPE bundle": new console = this skeleton + this (or a swapped) skin + program-specific screens.

---

## 1. Architectural stance (read this before building anything)

1. **The nav IS the story.** Primary information architecture is not a feature list — it is the human's idea's journey through the Foundation. Screens are stages of that journey.
2. **One primary object per screen.** Every screen is built around exactly one thing the human came to see (the idea box · the build in motion · the running program · the ask · the care feed). Everything else is a secondary region.
3. **Two lenses, one truth.** The PO (narrative) surface and the Operator (evidence) surface render the *same* underlying data. The PO surface warms it; the drawer proves it. Neither may contradict the other, and the PO surface may fold truth away but never omit or upgrade it.
4. **Honest states are first-class.** Every screen ships its empty / not-live / unknown / blocked states as designed states, not afterthoughts. "No data" is a rendered fact with an explanation, never a blank or a fake.
5. **Render from data shapes, not prose.** Screens are pure functions of typed seed shapes (Program, Increment, AssuranceManifest, Friction, PendingDecision/Guidance). No screen invents fields the data layer doesn't carry.

---

## 2. The app shell

```
┌──────────────┬──────────────────────────────────────────────┐
│  RAIL (252px)│  MAIN (fluid, min-width:0)                   │
│  ┌ brand     │  ┌ view header (title · subtitle · live pill)│
│  ├ journey   │  ├ [screen content — §5 composition]         │
│  │  steps    │  │                                           │
│  ├ divider   │  │                                           │
│  └ foot:     │  │                                           │
│    heartbeat │  └ (bottom padding 70px)                     │
└──────────────┴──────────────────────────────────────────────┘
   overlays (outside the grid): scrim · right drawer · toasts
```

- Grid: `.app{display:grid;grid-template-columns:252px 1fr;min-height:100vh}`.
- Rail: `position:sticky;top:0;height:100vh;display:flex;flex-direction:column` — brand at top, journey steps, then `margin-top:auto` foot. The rail is chrome: it never scrolls with content and never hosts screen content.
- Main: `min-width:0` (grid overflow guard), padding `26px 32px 70px`. Wide inner content (tables/charts) scrolls inside its own container; the page never scrolls horizontally.
- Overlay layer (fixed, above the grid): scrim `z-index:80`, drawer `90`, toasts `100`; rail sits at `40`.

### Responsive contract (structure only; visuals in skin doc)
- **≤1140px:** two-column content grids collapse to one; 4-tile bands → 2; decorative flow columns drop.
- **≤880px:** the shell itself reflows — rail becomes a sticky top bar (`grid-template-columns:1fr`; rail flex-row, horizontally scrollable steps; sublabels, rail label and foot hidden). The heartbeat may move into the view header's live pill at this size — it must remain visible somewhere.
- **≤560px:** tile bands → 1–2 columns.

## 3. The journey rail (primary navigation)

The five stages, fixed order and IDs — this is the IA of every Foundation console:

| # | id | Label | Sublabel | Role |
|---|----|-------|----------|------|
| 1 | `idea` | **Idea → Vision** | where it begins | Front door: capture + shape + grade the wish |
| 2 | `build` | **Vision → Program** | watch it take shape | The loop working: skeleton, lanes, feed |
| 3 | `living` | **The Living Program** | your idea, running | The payoff: the deployed, breathing program |
| 4 | `guide` | **Guide** | your hand on the wheel | **The human seat** — asks awaiting the PO |
| 5 | `maintain` | **Maintain** | never done, by design | Forever-care across all living programs |

Structural rules:
- Steps 1–3 + 5 are *places*; step 4 is a *seat* — structurally distinct (`seat` flag → dashed glyph until active, and it alone carries a badge = count of unresolved guidance items, recomputed on every render).
- The rail renders from a `STEPS` array (id, label, sub, icon, seat?, badge?). Adding a stage = adding a row here — screens never hand-roll nav.
- A vertical thread connects the glyphs top-to-bottom (the journey line). Current stage is highlighted; there is no notion of "locked" stages — the human may look anywhere.
- Cross-links between stages are part of the architecture: gallery card → that program's `build`/`living`; recap → `maintain`; "waiting in Guide" feed items → `guide`. Navigation verbs go *forward along the journey*.

## 4. The two-lens model (who sees what)

One audience, two postures — the same person is PO (owns WHAT/taste/blessing) and Operator (verifies HOW/evidence). The architecture serves both without duplicating screens:

| | **PO lens (default surface)** | **Operator lens (one click deeper)** |
|---|---|---|
| Question | "How is my idea doing? What needs me?" | "Why should I believe that? What did it cost?" |
| Where | The screen itself | The **trust drawer** (right panel) + `<details>` fold-downs |
| Content | Narrative cards, journey recaps, quoted wish, stage labels, honest summary pills (two-key/one-key shorthand) | Assurance manifests (full layer detail), friction telemetry, trust weights, blocked-on reasons, mono identifiers |
| Tone | Warm, §7-voice | Rigorous, plain, mono-accented |

Binding rules:
1. **Every trust summary on a PO surface must open its Operator detail** — pill → drawer, "see the honest paperwork" links, `<details class="confdrop">` on guidance cards. No dead-end claims.
2. **The Operator lens is never more optimistic than the PO lens** (and vice versa): both render from the same manifest object; the shorthand pill's state must equal the manifest's `effective`.
3. **Degraded truth surfaces at PO level too** — a one-key or blocked item shows its honest label on the card, not only in the drawer.
4. Operator content is *composed into* the drawer, not built as separate routes: `openDrawer(title, html)` receives manifest/friction renderers from the shared kit.

## 5. Screen-region composition (how ANY screen is assembled)

Every screen is: **rail + view header + primary object + secondary regions (+ drawer/toast reach)**.

```
view = vhead(title, subtitle)          ← 1 line of purpose, + live pill
     + [context switcher]              ← optional: fchip pickrow (which program)
     + PRIMARY OBJECT                  ← the one thing; may use the gradient-frame hero
     + [vitals band]                   ← optional: 4-tile stat row about the primary
     + secondary grid                  ← 1.45–1.55fr : 1fr; narrative left, aside right
     + [tertiary band]                 ← optional full-width chart/feed below
```

Canonical assignments (the five stages as proofs of the pattern):

| Screen | Primary object | Secondary regions |
|---|---|---|
| Idea → Vision | Idea input (hero box) → shaping result (raw ↔ vision cards) | Sample chips · proof gallery of narrative cards |
| Vision → Program | Build hero (program + ring + meta) | Skeleton viz + story lanes + growth chart ‖ live feed |
| Living Program | The app window (running program) | Vitals band · feature constellation ‖ journey recap |
| Guide | The pending asks (guidance cards, newest-first) | Lede card (count + reassurance); per-card confdrop |
| Maintain | Care feed | Forever lede · entropy meters ‖ health chart · watch tiles |

Composition rules:
- Region order is fixed top-to-bottom as listed; a screen may omit optional regions but not reorder them.
- The journey recap region ("From a sentence to this") appears on any screen that shows a single program's now — it is the architectural echo of the rail.
- Feeds render newest-first, capped (~9 rows), with a bottom fade; lanes render left→right in journey direction (`to dream up next → taking shape → alive`).
- **Every region declares its empty/unknown state** in the same cell it would render data (e.g. the not-deployed program renders a "Not live yet" panel *in place of* the app window — never a fake window).

## 6. Routing & state conventions

The demo is a static SPA; the real console keeps the same conventions over live data.

- **Views:** one `<section class="view" id="view-{stage}">` per stage; exactly one `.on`. `show(id, param?)` = set current, re-render target view, re-render rail (badge/active), scroll to top. Entrance animation via the skin's `rise`.
- **Registry:** `RENDER = {idea, build, living, guide, maintain}` — one render function per view, each a pure read of state → innerHTML → wire handlers. No cross-view DOM reads.
- **State atoms:** `CUR` (current stage) + per-view selection (`SEL_BUILD`, `SEL_LIVE`) set via pickrow chips; selection survives navigation. Real console: mirror to `location.hash` (`#/living/prg-0007`) so views are linkable; hash is the only router.
- **Data in, render out:** views consume the typed shapes (§1.5) from a single data module; polling/SSE updates mutate state then call the current view's render (or targeted row-append for feeds). Timers/intervals are owned per-view and must no-op when their view is not current (`if(CUR!=="build")return`) and be cleared on re-render.
- **Overlay protocol:** `openDrawer(title, html)` / `closeDrawer()`; scrim click and Escape close; drawer manages `aria-hidden`. `toast(msg, kind)` for transient facts — toasts announce *events that happened*, never fabricate progress.
- **Honesty in state:** absence of data is represented in state as absence (`null`), and renderers must branch on it (`url:null → "Not live yet"` panel). No renderer defaults a missing value to a healthy-looking one (**this is the fail-closed rule of the UI layer**).

## 7. Loop-alive heartbeat (placement & contract)

- **Home:** the rail foot — persistent across all views, above a hairline, pinned by `margin-top:auto`. On ≤880px it must survive relocation (view-header live pill).
- **Content contract:** ring state + `Loop alive` + `last increment Nm ago`, where N is computed from the newest increment timestamp on every render tick. Stale loop → the same component renders its honest quiet state (`loop quiet · 3h since last increment`, idle ring); dead loop → no pulse, plain statement. The heartbeat is the console's own Trust Strip: it may never animate "alive" without a fresh signal.
- The per-screen `.live` pill in the view header is the same signal, echoed; both bind to the same liveness datum.

## 8. How a NEW screen slots in (the recipe cheaper models follow)

1. **Name its journey stage.** It belongs to one of the five stages (or is a drawer, not a screen). If it genuinely is a new stage, add a `STEPS` row — a rare, human-approved event.
2. **Declare its primary object** (one), its secondary regions, and its honest states (empty / unknown / degraded / blocked) — in that order, before any markup. **"Degraded" includes the console's OWN data-plane read failure** (a source/read the console couldn't reach) — a *distinct* state from a program's weak assurance: the former is "the console can't see," rendered via skin §5.11 (amber `unknown`, sources named); the latter is a §5.4 trust state. Never collapse a read failure into an honest-empty or a program's trust weakness.
3. **Add `view-{id}` section + render function** in the registry; render from the typed shapes only.
4. **Compose from the skin's component library** (design-language §5). A needed-but-missing component is a *framework change request*, not an inline invention.
5. **Wire the lenses:** every trust claim gets its drawer path; every summary pill equals its manifest.
6. **Wire the journey:** entry cross-links from adjacent stages; recap region if it shows one program's now.
7. **Pass both gates:** the skin's compliance checklist (design-language §9) + this doc's review checklist (§9), then mockup↔real fidelity review against the exemplar caliber (`mockups-v2/`).

## 9. Architecture review checklist

- [ ] Screen maps to a journey stage; rail generated from `STEPS`, not hand-rolled.
- [ ] Exactly one primary object; regions in canonical order; secondary grid ratios per §5.
- [ ] Every region has designed empty/unknown/degraded states; no renderer defaults missing → healthy (**hard gate**).
- [ ] PO surface ↔ Operator drawer both present for every trust claim; shorthand state === manifest state.
- [ ] Render functions are pure state→DOM; timers scoped and view-guarded; selection + stage in hash.
- [ ] Heartbeat present and bound to real liveness; survives responsive reflow.
- [ ] Cross-links follow the journey; drawer/toast protocol used (no ad-hoc modals).
- [ ] No skin values defined here-abouts: all visuals via design-language tokens/components.
