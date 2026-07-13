# Rosetta Coda — design system

## Identity

Rosetta Coda is a **duration-gate instrument**: a deterministic scientific dashboard
for bioacoustics researchers studying sperm whale codas. It does not translate
whale language. It surfaces reproducible evidence — cohort funnel, mixed-effects
model, per-whale effects — in a single viewport.

### Design ethos

- **Unity & empathy.** Every pixel serves the researcher's question. The interface
  is an instrument, not a dashboard. Calm, patient, oceanic — like a hydrophone
  array waiting for the next click train.
- **Wow factor of technology.** The tech is real: frozen SHA-256 gates, schema-
  validated Sol hypotheses, mixed-effects models. The UI surfaces this with
  precision — cyan data ink, tabular numerics, ambient sonar pulses — not with
  decorative gradients or animation.
- **Ridiculously simple.** One viewport. Two columns. No tabs, no settings, no
  onboarding. At 1440×810 every number is visible without scrolling.
- **Researcher-ready.** Every figure is a real JSON Pointer into a frozen artifact.
  No invented metrics. Every mock is clearly labelled.

### Inspiration

[Project CETI — listen](https://listen.projectceti.org/): deep ocean dark,
hydrophone-as-interface, minimal chrome, oceanic calm. The user is underwater
with the data.

## Colour palette

All tokens in OKLch for perceptual uniformity.

### Water column (surfaces)

| Token | Value | Usage |
|-------|-------|-------|
| `--abyss` | `oklch(0.12 0.022 240)` | Body background |
| `--deep` | `oklch(0.18 0.028 236)` | Panel inset, hover surface |
| `--panel` | `oklch(0.21 0.03 234)` | Panel background |
| `--panel-2` | `oklch(0.24 0.032 232)` | Hypothesis panel surface |
| `--line` | `oklch(0.30 0.025 230 / 0.5)` | Borders, dividers, hr |

### Data ink (text)

| Token | Value | Usage |
|-------|-------|-------|
| `--bone` | `oklch(0.94 0.012 215)` | Primary text |
| `--muted` | `oklch(0.72 0.022 218)` | Secondary text, labels |
| `--faint` | `oklch(0.58 0.020 220)` | Meta, captions, empty states |

### Signals (accent)

| Token | Value | Usage |
|-------|-------|-------|
| `--teal` | `oklch(0.76 0.08 200)` | Primary data ink, active elements |
| `--foam` | `oklch(0.82 0.09 175)` | Positive / code `a` |
| `--deepsea` | `oklch(0.65 0.075 235)` | Code `i` |
| `--amber` | `oklch(0.84 0.11 85)` | Live status lamp, gate pass |
| `--coral` | `oklch(0.74 0.13 48)` | Preview warning, caution |

### Semantic

| Token | Value | Usage |
|-------|-------|-------|
| `--pass` | `var(--amber)` | Gate passed |
| `--fail` | `var(--coral)` | Gate failed |

### Accent discipline

- `--teal` is the primary data accent: used for the logo glow, funnel terminal
  step, inline code refs, focus rings. At most 2–3 visible uses per panel.
- `--foam` / `--deepsea` are split-bar and per-whale chart colours — data only,
  never chrome.
- `--amber` is the signal lamp: exactly one instance, with sonar pulse rings.
- `--coral` is caution: the preview badge only.
- No accent is ever used as a background fill or gradient besides the panel
  top-edge line.

## Typography

| Role | Font stack | Weight | Size |
|------|-----------|--------|------|
| Display / panel titles | `Inter`, `SF Pro Display`, -apple-system, system-ui, sans-serif | 500 | `clamp(0.82rem, 1.1vw, 0.98rem)` (panel) / `clamp(1.25rem, 2.1vw, 1.9rem)` (masthead) |
| Body | `Spectral`, `Iowan Old Style`, Palatino, Georgia, serif | 400 | `clamp(0.85rem, 1.1vw, 0.96rem)` |
| Numerics / code | `SF Mono`, `Cascadia Code`, `Roboto Mono`, ui-monospace | 400 | 0.72–0.92rem |
| Labels & small | `Inter`, system-ui, sans-serif | 450 | 0.68–0.78rem |

### Letter-spacing rules

- ALL CAPS labels: `0.14em–0.16em`
- Body text: `0` (default)
- Numerics: `-0.01em` (tight)
- Display text ≥ 32px: `-0.01em`

### Pairing discipline

Sans-serif display + serif body creates a clear hierarchy: the instrument
chrome speaks in clean technical tones (Inter), while the data reads with
editorial patience (Spectral). Mono provides the technical contrast for
numerics and code refs.

## Layout

### Grid

```
┌──────────────────────────────────┐
│           Masthead               │
├────────────────┬─────────────────┤
│                │                 │
│  Evidence      │  Hypo panel     │
│  (cohort,      │  (claim pinned, │
│   model,       │   details       │
│   whales)      │   scroll)       │
│                │                 │
│                │  creed pinned   │
└────────────────┴─────────────────┘
```

- Single 16:9 viewport — no scrolling on the outer page.
- Evidence column (1.08fr) wider than hypothesis (0.92fr).
- Max width 1680px, centered.

### Hypothesis panel structure

```
.hypo (flex column)
  .hypo__head       — pinned: panel title + origin badge
  .hypo__pinned     — pinned: compact preview note + claim title + claim text
  .hypo__detail     — scrollable: evidence refs, uncertainty, alternatives,
                      falsifiers, limitations, meta chips
  .creed            — pinned: instrument principles
```

### Spacing

| Token | Value |
|-------|-------|
| `--pad` | `clamp(0.7rem, 1.1vw, 1.15rem)` |
| `--gap` | `clamp(0.6rem, 1vw, 1rem)` |
| `--r` (radius) | 10px |

- Panel body padding: `var(--pad)`
- Grid gap: `var(--gap)`
- Semi-transparent hairline borders
- Top-edge gradient line (2–3px) on each panel

## Component rules

### Ambient background
- Very deep oceanic gradient with subtle radial glows
- CSS-animated bioluminescent particles (15–20 tiny dots drifting upward)
- No external images, pure CSS

### Sonar status lamp
- Larger lamp (14px) with CSS concentric pulse rings
- Loading state: slow expanding rings
- Pass state: steady amber with shimmer
- Fail state: coral steady

### Animated click-train logo
- SVG lines pulse sequentially left-to-right, like a whale click train arriving
- Each line fades in with a staggered delay
- Teal glow on active line

### Panels
- Background: `linear-gradient(160deg, var(--panel), var(--deep))`
- Subtle glass edge: 1px line at `oklch(0.30 0.025 230 / 0.5)`
- Top-edge line: gradient from transparent → accent → transparent
- No shadows, no rounded insets

### Data display
- Tabular numerics with `font-variant-numeric: tabular-nums`
- Big coefficient values (clamp 1.9–3rem)
- Small stats in grid layout (`1fr 1fr`) with dotted bottom borders
- Funnel steps with left-border color coding (terminal = teal)

### Per-whale bars
- 4-column grid, bars grow up from bottom with spring-like cubic-bezier animation
- Max 0.9s stagger by index
- Reduced-motion: instant reveal

### Preview note (hypothesis panel, mock mode)
- One compact line
- Coral text + coral left border
- Sits inside `.hypo__pinned` between head and claim title

## States

| State | Visual |
|-------|--------|
| Loading | Skeleton funnel (opacity 0.4), sonar pulse lamp, "Awaiting evidence…" |
| Gate pass | Amber lamp pulse, data rendered, particles drift |
| Gate fail | Coral lamp, error box with instructions, toast |
| Mock hypothesis | Coral badge + compact preview note |
| Live hypothesis | Amber badge + meta row with model/effort/sha |
| Reduced motion | All animations zeroed, bars appear instantly |
| Narrow / short | Single column stack, auto overflow, whales wrap to 2 cols |

## What this system does NOT do

- No semantic claims about whale language
- No external image dependencies (all CSS/SVG)
- No emoji icons
- No gradients except panel top-edge line
- No shadows except the sonar lamp glow
- No tabs, drawers, or multi-page navigation
- No settings or configuration panels
- No "demo only" labels on real data — only on the preview mock
