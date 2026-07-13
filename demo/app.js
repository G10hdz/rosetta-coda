/* ══════════════════════════════════════════════════════════════════
   Rosetta Coda — duration-gate instrument
   Loads real evidence from the frozen SPEC-004 gate artifact and renders
   it. The GPT-5.6 Sol panel shows a LIVE hypothesis only if the instrument
   actually produced one; otherwise a clearly-labelled Preview mock. The
   mock is never presented as coming from Sol.
   ════════════════════════════════════════════════════════════════════ */
"use strict";

const GATE_URL = "/artifacts/gates/spec-004-duration-gate.json";
const SOL_URL = "/artifacts/demo/sol-hypothesis.json";
// A tiny manifest declares whether a live Sol artifact exists. Consulting it
// first means the demo never issues a request that 404s in the console when
// running offline in Preview mode; the live artifact is only fetched when the
// manifest says it is there.
const MANIFEST_URL = "/artifacts/demo/manifest.json";

const $ = (id) => document.getElementById(id);

const fmt = {
  int: (n) => Number(n).toLocaleString("en-US"),
  fixed: (n, d) => Number(n).toFixed(d),
  sci: (n) => {
    const x = Number(n);
    if (x === 0) return "0";
    const exp = Math.floor(Math.log10(Math.abs(x)));
    const mant = x / 10 ** exp;
    return `${mant.toFixed(2)}×10${sup(exp)}`;
  },
};

function sup(n) {
  const map = { "-": "⁻", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
  return String(n).split("").map((c) => map[c] ?? c).join("");
}

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ── Boot ──────────────────────────────────────────────────────────── */
async function boot() {
  let gate;
  try {
    gate = await fetchJSON(GATE_URL);
  } catch (err) {
    return renderGateError(err);
  }
  renderGate(gate);

  // Sol panel: live artifact only if the manifest declares one. Otherwise a
  // clearly-labelled Preview mock. We never request a URL that would 404 in
  // the console during the offline Preview path.
  let sol = null;
  try {
    const manifest = await fetchJSON(MANIFEST_URL);
    if (manifest && manifest.sol_hypothesis_available) {
      sol = await fetchJSON(SOL_URL);
    }
  } catch {
    sol = null; // no manifest / no live artifact — expected Preview path
  }
  renderHypothesis(sol, gate);
}

async function fetchJSON(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`);
  return res.json();
}

/* ── Gate rendering ────────────────────────────────────────────────── */
function renderGate(g) {
  // Status lamp + frozen hash
  const pass = g.state === "pass";
  const state = pass ? "pass" : "fail";
  const lamp = document.querySelector(".status__lamp");
  const wrap = document.getElementById("lamp-wrap");
  lamp.dataset.state = state;
  if (wrap) wrap.dataset.state = state;
  $("gate-state-label").textContent = pass ? "Gate · pass" : `Gate · ${g.state}`;
  const hash = g.codamd_hash || "";
  $("gate-hash").textContent = hash ? `${hash.slice(0, 10)}…${hash.slice(-6)}` : "—";
  $("gate-hash").title = `Frozen coda.md SHA-256: ${hash}`;

  // Cohort funnel
  const cf = g.cohort_flow || {};
  const steps = [
    ["input", cf.total_input],
    ["hand-verified", cf.after_handv_filter],
    ["coda-typed", cf.after_codatype_filter],
    ["whale-resolved", cf.after_whale_filter],
  ].filter(([, n]) => Number.isFinite(n));
  const funnel = $("funnel");
  funnel.innerHTML = steps
    .map(
      ([k, n], i) =>
        `<li class="funnel__step"${i === steps.length - 1 ? " data-terminal" : ""}>
           <span class="funnel__n mono">${fmt.int(n)}</span>
           <span class="funnel__k">${esc(k)}</span>
         </li>`
    )
    .join("");
  $("cohort-total").textContent = Number.isFinite(cf.after_whale_filter)
    ? `${fmt.int(cf.after_whale_filter)} obs`
    : "—";

  // Vowel split
  const nA = cf.n_a ?? 0;
  const nI = cf.n_i ?? 0;
  $("n-a").textContent = fmt.int(nA);
  $("n-i").textContent = fmt.int(nI);
  $("n-groups").textContent = fmt.int(g.mixed_model?.n_groups ?? (g.per_whale_effects || []).length);
  const total = nA + nI || 1;
  $("seg-a").style.flex = String(nA / total);
  $("seg-i").style.flex = String(nI / total);
  $("split-bar").setAttribute(
    "aria-label",
    `Vowel split: ${fmt.int(nA)} code a, ${fmt.int(nI)} code i`
  );

  // Mixed model
  const mm = g.mixed_model || {};
  $("coef-value").textContent = Number.isFinite(mm.coefficient_value)
    ? fmt.fixed(mm.coefficient_value, 3)
    : "—";
  if (mm.coefficient_label) $("coef-label").textContent = mm.coefficient_label;
  const pv = $("p-value");
  pv.textContent = Number.isFinite(mm.p_value) ? fmt.sci(mm.p_value) : "—";
  if (Number.isFinite(mm.p_value) && mm.p_value < 0.05) pv.classList.add("sig");
  $("t-value").textContent = Number.isFinite(mm.t_value) ? fmt.fixed(mm.t_value, 2) : "—";
  $("m-groups").textContent = fmt.int(mm.n_groups ?? "—");
  $("m-obs").textContent = fmt.int(mm.n_obs ?? "—");

  const warnings = g.details?.model_warnings || [];
  if (warnings.length) {
    const w = $("model-warn");
    w.hidden = false;
    w.textContent = `Model note: ${warnings.join(" ")}`;
  }

  // Per-whale effects
  renderWhales(g.per_whale_effects || []);
}

function renderWhales(effects) {
  const host = $("whales");
  if (!effects.length) {
    host.innerHTML = `<p class="empty">No per-whale effects in artifact.</p>`;
    return;
  }
  const maxZ = Math.max(...effects.map((e) => Math.abs(e.z_diff_a_minus_i ?? 0)), 0.001);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  host.innerHTML = effects
    .map((e, i) => {
      const z = e.z_diff_a_minus_i ?? 0;
      const raw = e.raw_diff_a_minus_i;
      const pct = Math.max(6, (Math.abs(z) / maxZ) * 100);
      const delay = reduce ? 0 : 0.12 * i + 0.15;
      const id = esc(e.whale_id ?? "?");
      const n = (e.n_a ?? 0) + (e.n_i ?? 0);
      const rawTxt = Number.isFinite(raw) ? `+${fmt.fixed(raw, 3)} s raw` : "raw n/a";
      const tip = `${id}: +${fmt.fixed(z, 2)} z-score (a − i), ${rawTxt}, n=${fmt.int(n)}`;
      return `
        <div class="whale" title="${esc(tip)}">
          <span class="whale__val mono">+${fmt.fixed(z, 2)}<span class="whale__z">z</span></span>
          <div class="whale__track" role="img" aria-label="${esc(tip)}">
            <div class="whale__fill" style="height:${pct.toFixed(1)}%;animation-delay:${delay}s"></div>
          </div>
          <span class="whale__id">${id}</span>
          <span class="whale__n">n=${fmt.int(n)}</span>
        </div>`;
    })
    .join("");
}

/* ── Hypothesis panel ──────────────────────────────────────────────── */
function renderHypothesis(sol, gate) {
  const pinned = $("hypo-pinned");
  const detail = $("hypo-detail");
  const origin = $("hypo-origin");
  detail.setAttribute("aria-busy", "false");

  const isLive = sol && sol.hypothesis && typeof sol.hypothesis === "object";
  const h = isLive ? sol.hypothesis : mockHypothesis();

  if (isLive) {
    origin.dataset.origin = "live";
    origin.textContent = `Live · ${esc(sol.model || "gpt-5.6-sol")}`;
    origin.title = "Schema-validated live GPT-5.6 Sol output";
  } else {
    origin.dataset.origin = "mock";
    origin.textContent = "Preview · illustrative";
    origin.title = "Illustrative preview — not produced by any model";
  }

  const alts = h.alternatives || [];
  const fals = h.falsifiers || [];
  const allRefs = h.evidence_refs || [];
  const keyRefs = allRefs.slice(0, 3);
  const restRefs = allRefs.slice(3);

  const list = (items, cls) =>
    `<ul class="hlist ${cls}">${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;

  const refList = (items) =>
    `<ul class="refs">${items.map((r) => `<li><code>${esc(r)}</code></li>`).join("")}</ul>`;

  const meta = isLive
    ? `<div class="meta-row">
         <span class="chip">model <strong>${esc(sol.model || "—")}</strong></span>
         <span class="chip">effort <strong>${esc(sol.reasoning_effort || "—")}</strong></span>
         <span class="chip">source sha <strong class="mono">${esc((sol.source_artifact_sha256 || "").slice(0, 10))}…</strong></span>
       </div>`
    : `<div class="meta-row">
         <span class="chip">status <strong>illustrative preview</strong></span>
         <span class="chip">not produced by any model</span>
         <span class="chip">refs verified against the real gate</span>
       </div>`;

  // Compact one-line preview note (pinned, mock only).
  const previewNote = isLive
    ? ""
    : `<p class="preview-note"><strong>Preview.</strong> Illustrative structure — <strong>not</strong> a Sol output. Run <code>uv&nbsp;run&nbsp;python&nbsp;-m&nbsp;scripts.run_sol_demo</code> for a live, schema-validated GPT-5.6&nbsp;Sol hypothesis.</p>`;

  // Pinned (never scrolls): preview note, claim, top evidence, the single
  // strongest alternative and the single decisive falsifier.
  pinned.innerHTML = `
    ${previewNote}
    <div class="claim">
      <h3 class="claim__title">${esc(h.title)}</h3>
      <p class="claim__text">${esc(h.claim)}</p>
    </div>
    ${keyRefs.length ? `<div class="keyrefs">
      <p class="hblock__label">Key evidence <span class="hblock__hint">JSON Pointer → frozen gate</span></p>
      ${refList(keyRefs)}
    </div>` : ""}
    <div class="keypoints">
      ${alts.length ? `<div class="keypoint keypoint--alt">
        <span class="keypoint__tag">Strongest alternative</span>
        <p>${esc(alts[0])}</p>
      </div>` : ""}
      ${fals.length ? `<div class="keypoint keypoint--fals">
        <span class="keypoint__tag">Decisive falsifier</span>
        <p>${esc(fals[0])}</p>
      </div>` : ""}
    </div>
  `;

  // Scrollable detail: everything secondary.
  const restAlts = alts.slice(1);
  const restFals = fals.slice(1);
  detail.innerHTML = `
    ${restRefs.length ? `<div class="hblock">
      <p class="hblock__label">Further evidence</p>
      ${refList(restRefs)}
    </div>` : ""}

    ${restAlts.length ? `<div class="hblock">
      <p class="hblock__label">Other alternatives</p>
      ${list(restAlts, "hlist--alt")}
    </div>` : ""}

    ${restFals.length ? `<div class="hblock">
      <p class="hblock__label">Other falsifiers</p>
      ${list(restFals, "hlist--fals")}
    </div>` : ""}

    <div class="hblock">
      <p class="hblock__label">Uncertainty &amp; limitations</p>
      <div class="meta-row"><span class="chip">kind <strong>${esc(h.uncertainty_kind)}</strong></span></div>
      ${list(h.limitations || [], "hlist--limit")}
    </div>

    ${meta}
  `;
}

/* Illustrative mock. Every evidence ref below is a real JSON Pointer into
   the frozen gate artifact. No semantic claims. Clearly labelled as preview. */
function mockHypothesis() {
  return {
    title: "A stable within-whale a–i coda-duration contrast",
    claim:
      "Within coda type 1+1+3, codas hand-labelled a have a longer total coda duration than those labelled i. The pooled mixed-effects model estimates a raw −0.132 s difference for i; the same direction holds within every resolved whale after per-individual standardization (z-scoring).",
    evidence_refs: [
      "/mixed_model/coefficient_value",
      "/mixed_model/p_value",
      "/per_whale_effects/0/z_diff_a_minus_i",
      "/mixed_model/n_obs",
      "/cohort_flow/n_a",
      "/cohort_flow/n_i",
      "/per_whale_effects/3/z_diff_a_minus_i",
    ],
    uncertainty_kind: "sampling",
    alternatives: [
      "The pooled coefficient is carried by the two best-sampled whales (ATWOOD, FORK); the two smaller whales (PINCHY, TBB) may not replicate the effect independently.",
      "A recording- or session-level effect correlated with the a/i label, rather than the label itself, lengthens code-a codas.",
      "The contrast is sensitive to the analyst's a/i hand-labels; a stricter or independent re-labelling could attenuate it.",
    ],
    falsifiers: [
      "On a whale held out of model fitting, its z-scored a−i duration difference is non-positive.",
      "The sign reverses or the effect loses significance under an independent re-labelling of the a/i categories.",
      "On independent replication the −0.132 s coefficient falls outside the preregistered ±0.02 s tolerance around −0.13 s.",
    ],
    limitations: [
      "Only four resolved whales; the model MLE sits on a variance boundary (boundary-of-parameter-space note).",
      "The a/i labels are analyst-assigned phonological categories, not semantic units.",
      "Duration is one deterministic feature; no acoustic or contextual features are modelled.",
    ],
  };
}

/* ── Error state ───────────────────────────────────────────────────── */
function renderGateError(err) {
  const lamp = document.querySelector(".status__lamp");
  const wrap = document.getElementById("lamp-wrap");
  lamp.dataset.state = "fail";
  if (wrap) wrap.dataset.state = "fail";
  $("gate-state-label").textContent = "Gate · unavailable";

  $("hypo-detail").setAttribute("aria-busy", "false");
  $("hypo-pinned").innerHTML = `<p class="empty">Gate artifact unavailable — see error below.</p>`;
  $("hypo-detail").innerHTML = `
    <div class="error-box">
      <p style="margin:0 0 0.5rem"><strong>Could not load the gate artifact.</strong></p>
      <p style="margin:0 0 0.5rem">Serve the repo root and open the demo path:</p>
      <p style="margin:0"><code>python3 -m http.server 8000</code><br>
      <code>http://localhost:8000/demo/</code></p>
      <p style="margin:0.5rem 0 0;opacity:0.8">${esc(err.message)}</p>
    </div>`;

  const funnel = $("funnel");
  if (funnel) funnel.innerHTML = `<li class="funnel__step"><span class="funnel__k">artifact unavailable</span></li>`;

  const toast = $("toast");
  toast.hidden = false;
  toast.textContent = "Evidence artifact failed to load — see the hypothesis panel.";
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
