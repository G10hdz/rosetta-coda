/* ══════════════════════════════════════════════════════════════════
   Rosetta Coda — research console
   Renders the frozen release artifacts. No frameworks, no CDNs.
   Every section loads independently: a failed fetch degrades only its
   own panel to a .state-missing state. No number is invented — cells
   carry their artifact source in a data-src attribute / tooltip.
   ════════════════════════════════════════════════════════════════════ */
"use strict";

const BASE = "../artifacts/release/";
const FILES = {
  manifest: "manifest.json",
  gate: "spec-004-duration-gate.json",
  features: "spec-007-featureset.json",
  hypotheses: "spec-009-ranked-hypotheses.json",
  calibration: "spec-012-calibration.json",
  reportMd: "spec-010-report.md",
};

const $ = (id) => document.getElementById(id);

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const fmt = {
  int: (n) => Number(n).toLocaleString("en-US"),
  fixed: (n, d) => Number(n).toFixed(d),
  sci: (n) => {
    const x = Number(n);
    if (x === 0) return "0";
    const exp = Math.floor(Math.log10(Math.abs(x)));
    return `${(x / 10 ** exp).toFixed(2)}×10${sup(exp)}`;
  },
};

function sup(n) {
  const map = { "-": "⁻", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
  return String(n).split("").map((c) => map[c] ?? c).join("");
}

const NO_OBS = '<span class="null-val">not_observable</span>';

/* Number cell: finite value formatted, null/undefined → not_observable. */
function num(v, d = 3, src) {
  const a = src ? ` data-src="${esc(src)}" title="source: ${esc(src)}"` : "";
  return Number.isFinite(v) ? `<span class="mono"${a}>${fmt.fixed(v, d)}</span>` : `<span${a}>${NO_OBS}</span>`;
}

function badge(state, label) {
  const s = state == null ? "unknown" : String(state);
  return `<span class="badge" data-state="${esc(s)}" aria-label="state: ${esc(s)}">${esc(label ?? s)}</span>`;
}

/* ── Fetching ────────────────────────────────────────────────────── */
async function fetchJSON(name) {
  const res = await fetch(BASE + FILES[name], { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} — ${FILES[name]}`);
  return res.json();
}
async function fetchText(name) {
  const res = await fetch(BASE + FILES[name], { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} — ${FILES[name]}`);
  return res.text();
}

function body(secId) {
  const el = $(secId).querySelector(".section-body");
  el.setAttribute("aria-busy", "false");
  return el;
}

function markMissing(secId) {
  const sec = $(secId);
  sec.classList.add("state-missing");
  body(secId).innerHTML = '<p class="state-missing__msg" role="status">artifact not available</p>';
}

/* ── Boot: every section independent ─────────────────────────────── */
async function boot() {
  const [manifest, gate, features, hypos, calibration, reportMd] = await Promise.allSettled([
    fetchJSON("manifest"),
    fetchJSON("gate"),
    fetchJSON("features"),
    fetchJSON("hypotheses"),
    fetchJSON("calibration"),
    fetchText("reportMd"),
  ]);
  renderHeader(manifest);
  renderGate(gate);
  renderContrasts(features);
  renderHypotheses(hypos);
  renderCalibration(calibration);
  renderReport(reportMd);
  renderManifest(manifest);
}

/* ── a) Header ───────────────────────────────────────────────────── */
function renderHeader(r) {
  const vb = $("verdict-badge");
  if (r.status !== "fulfilled") {
    vb.dataset.state = "unknown";
    vb.textContent = "unknown";
    vb.setAttribute("aria-label", "gate verdict: unknown — manifest artifact not available");
    $("run-id").textContent = "—";
    return;
  }
  const m = r.value;
  const verdict = m.gate_state ?? null;
  const state = verdict === "pass" ? "pass" : verdict === "indeterminate" ? "indeterminate" : verdict ? "fail" : "unknown";
  vb.dataset.state = state;
  vb.textContent = verdict ?? "unknown";
  vb.setAttribute("aria-label", `gate verdict: ${verdict ?? "unknown"}`);
  $("run-id").textContent = m.run_id ?? "—";
  const sha = m.manifest_sha256 || "";
  $("manifest-sha").textContent = sha ? `${sha.slice(0, 10)}…${sha.slice(-6)}` : "—";
  $("manifest-sha").title = sha ? `Manifest SHA-256: ${sha}` : "Manifest SHA-256 unavailable";
}

/* ── b) Gate card ────────────────────────────────────────────────── */
function renderGate(r) {
  if (r.status !== "fulfilled") return markMissing("sec-gate");
  const g = r.value;
  const F = FILES.gate;
  const mm = g.mixed_model || {};
  const pv = Number.isFinite(mm.p_value);

  const stats = `
    <div class="stat-row">${badge(g.state, g.state == null ? null : `gate · ${g.state}`)}</div>
    <dl class="stats">
      <div><dt>n_obs</dt><dd class="mono" data-src="${F}#/mixed_model/n_obs">${Number.isFinite(mm.n_obs) ? fmt.int(mm.n_obs) : NO_OBS}</dd></div>
      <div><dt>n_groups</dt><dd class="mono" data-src="${F}#/mixed_model/n_groups">${Number.isFinite(mm.n_groups) ? fmt.int(mm.n_groups) : NO_OBS}</dd></div>
      <div><dt>coefficient</dt><dd>${num(mm.coefficient_value, 4, `${F}#/mixed_model/coefficient_value`)}</dd></div>
      <div><dt>p-value</dt><dd class="mono${pv && mm.p_value < 0.05 ? " sig" : ""}" data-src="${F}#/mixed_model/p_value">${pv ? fmt.sci(mm.p_value) : NO_OBS}</dd></div>
    </dl>
    ${mm.coefficient_label ? `<p class="footnote">Coefficient label: <span class="mono">${esc(mm.coefficient_label)}</span>. Raw seconds difference for i vs a — not a standardized effect.</p>` : ""}
    ${(g.details?.model_warnings || []).length ? `<p class="warn">Model note: ${esc(g.details.model_warnings.join(" "))}</p>` : ""}`;

  const effects = g.per_whale_effects || [];
  const rows = effects
    .map((e, i) => {
      const raw = e.raw_diff_a_minus_i;
      const dir = Number.isFinite(raw) ? (raw > 0 ? "a &gt; i" : raw < 0 ? "a &lt; i" : "0") : NO_OBS;
      const dirCls = Number.isFinite(raw) ? (raw > 0 ? "dir--a" : "dir--i") : "";
      return `<tr>
        <td class="mono">${esc(e.whale_id ?? "?")}</td>
        <td class="num">${Number.isFinite(e.n_a) ? fmt.int(e.n_a) : NO_OBS}</td>
        <td class="num">${Number.isFinite(e.n_i) ? fmt.int(e.n_i) : NO_OBS}</td>
        <td class="num" data-src="${F}#/per_whale_effects/${i}/raw_diff_a_minus_i">${Number.isFinite(raw) ? fmt.fixed(raw, 4) : NO_OBS}</td>
        <td class="num" data-src="${F}#/per_whale_effects/${i}/z_diff_a_minus_i">${Number.isFinite(e.z_diff_a_minus_i) ? fmt.fixed(e.z_diff_a_minus_i, 3) : NO_OBS}</td>
        <td class="dir ${dirCls}">${dir}</td>
      </tr>`;
    })
    .join("");

  body("sec-gate").innerHTML = `
    ${stats}
    <div class="table-wrap">
      <table class="data">
        <caption>Per-whale a − i duration effects (raw seconds and per-individual z-score)</caption>
        <thead><tr>
          <th>whale</th><th class="num">n_a</th><th class="num">n_i</th>
          <th class="num">raw_diff</th><th class="num">z_diff</th><th>direction</th>
        </tr></thead>
        <tbody>${rows || `<tr><td colspan="6">${NO_OBS}</td></tr>`}</tbody>
      </table>
    </div>`;
}

/* ── c) Feature contrasts ────────────────────────────────────────── */
function renderContrasts(r) {
  if (r.status !== "fulfilled") return markMissing("sec-contrasts");
  const f = r.value;
  const F = FILES.features;
  const contrasts = f.partition_contrasts || [];

  // Pooled per-vowel means are not stored in the artifact; they are derived
  // in-browser as n-weighted means of /whale_feature_means. Labelled as such.
  const pooled = {};
  for (const row of f.whale_feature_means || []) {
    if (row.vowel !== "a" && row.vowel !== "i") continue;
    for (const [feat, val] of Object.entries(row.means || {})) {
      if (!Number.isFinite(val) || !Number.isFinite(row.n)) continue;
      const slot = (pooled[feat] ??= { a: { s: 0, n: 0 }, i: { s: 0, n: 0 } })[row.vowel];
      slot.s += val * row.n;
      slot.n += row.n;
    }
  }
  const mean = (feat, v) => {
    const slot = pooled[feat]?.[v];
    return slot && slot.n > 0 ? slot.s / slot.n : null;
  };

  const rows = contrasts
    .map((c, i) => {
      const sig = Number.isFinite(c.ci95_low) && Number.isFinite(c.ci95_high) && (c.ci95_low > 0 || c.ci95_high < 0);
      const d = c.a_minus_i;
      const dir = Number.isFinite(d) ? (d > 0 ? "a &gt; i" : d < 0 ? "a &lt; i" : "0") : NO_OBS;
      const dirCls = Number.isFinite(d) ? (d > 0 ? "dir--a" : "dir--i") : "";
      const ci =
        Number.isFinite(c.ci95_low) && Number.isFinite(c.ci95_high)
          ? `[${fmt.fixed(c.ci95_low, 4)}, ${fmt.fixed(c.ci95_high, 4)}]`
          : NO_OBS;
      return `<tr${sig ? ' class="is-sig"' : ""}>
        <td class="mono">${esc(c.feature ?? "?")}</td>
        <td class="num" data-src="${F}#/whale_feature_means (derived, n-weighted)" title="derived: n-weighted mean of /whale_feature_means">${mean(c.feature, "a") == null ? NO_OBS : fmt.fixed(mean(c.feature, "a"), 4)}</td>
        <td class="num" data-src="${F}#/whale_feature_means (derived, n-weighted)" title="derived: n-weighted mean of /whale_feature_means">${mean(c.feature, "i") == null ? NO_OBS : fmt.fixed(mean(c.feature, "i"), 4)}</td>
        <td class="num" data-src="${F}#/partition_contrasts/${i}/a_minus_i">${Number.isFinite(d) ? fmt.fixed(d, 4) : NO_OBS}</td>
        <td class="num" data-src="${F}#/partition_contrasts/${i}">${ci}</td>
        <td class="dir ${dirCls}">${dir}</td>
      </tr>`;
    })
    .join("");

  body("sec-contrasts").innerHTML = `
    <div class="table-wrap">
      <table class="data">
        <caption>${fmt.int(f.n_gate_partition ?? 0)} gate-partition codas · ${esc(f.code_version ?? "")}</caption>
        <thead><tr>
          <th>feature</th><th class="num">a_mean</th><th class="num">i_mean</th>
          <th class="num">a − i</th><th class="num">CI95</th><th>direction</th>
        </tr></thead>
        <tbody>${rows || `<tr><td colspan="6">${NO_OBS}</td></tr>`}</tbody>
      </table>
    </div>
    <p class="footnote">a_mean / i_mean are derived in-browser as n-weighted means of the per-whale vowel means
    (<span class="mono">/whale_feature_means</span>); the artifact stores contrasts, not pooled means.
    Rows with a CI that excludes zero are marked with a thin foam edge — descriptive, not an inferential claim.</p>`;
}

/* ── d) Ranked hypotheses ────────────────────────────────────────── */
function renderHypotheses(r) {
  const el = body("sec-hypotheses");
  if (r.status !== "fulfilled") {
    $("sec-hypotheses").classList.add("state-missing");
    el.innerHTML = `
      <div class="stat-row">${badge("not_generated")}</div>
      <p class="state-missing__msg" role="status">artifact not available</p>`;
    return;
  }
  const doc = r.value;
  const ranked = (doc.ranked || []).slice().sort((x, y) => (x.rank ?? 0) - (y.rank ?? 0));

  if (!ranked.length || doc.state === "not_generated") {
    el.innerHTML = `<div class="stat-row">${badge("not_generated")}</div>
      <p class="loading">No hypotheses in this artifact.</p>`;
    return;
  }

  const list = (items, cls) =>
    items && items.length
      ? `<ul class="hlist ${cls}">${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`
      : `<p class="loading">none recorded</p>`;

  el.innerHTML = `
    <div class="stat-row">
      ${badge(doc.state)}
      <span class="chip">selection rule <strong class="mono">${esc(doc.selection_rule_version ?? "—")}</strong></span>
    </div>
    <p class="footnote">Ranked by a deterministic heuristic score. These are model-generated hypotheses —
    candidates for future tests, not established results.</p>
    <ol class="hypo-list">
      ${ranked
        .map((rh) => {
          const h = rh.hypothesis || {};
          const u = rh.uncertainty || {};
          const uLabel = [u.kind, u.label].filter(Boolean).join(" · ") || h.uncertainty_kind || "unknown";
          return `<li class="hypo-card">
            <div class="hypo-card__head">
              <span class="hypo-card__rank">#${esc(rh.rank ?? "?")}</span>
              <h3 class="hypo-card__title">${esc(h.title ?? "untitled")}</h3>
              <span class="hypo-card__score">score <strong>${Number.isFinite(rh.score) ? fmt.fixed(rh.score, 3) : "—"}</strong></span>
              <span class="badge badge--uncertainty" data-state="indeterminate" aria-label="uncertainty: ${esc(uLabel)}">${esc(uLabel)}</span>
            </div>
            <p class="hypo-card__claim">${esc(h.claim ?? "")}</p>
            <details>
              <summary>Evidence, alternatives, falsifiers, limitations</summary>
              <div class="hblock">
                <p class="hblock__label">Evidence refs · JSON Pointers into the frozen evidence bundle</p>
                ${(h.evidence_refs || []).length
                  ? `<ul class="refs">${h.evidence_refs.map((r2) => `<li><code>${esc(r2)}</code></li>`).join("")}</ul>`
                  : `<p class="loading">none recorded</p>`}
              </div>
              <div class="hblock">
                <p class="hblock__label">Alternatives</p>
                ${list(h.alternatives, "hlist--alt")}
              </div>
              <div class="hblock">
                <p class="hblock__label">Falsifiers</p>
                ${list(h.falsifiers, "hlist--fals")}
              </div>
              <div class="hblock">
                <p class="hblock__label">Limitations</p>
                ${list(h.limitations, "hlist--limit")}
              </div>
              ${(rh.reasons || []).length ? `<div class="hblock">
                <p class="hblock__label">Ranking reasons</p>
                ${list(rh.reasons, "hlist--limit")}
              </div>` : ""}
            </details>
          </li>`;
        })
        .join("")}
    </ol>`;
}

/* ── e) Calibration ──────────────────────────────────────────────── */
function renderCalibration(r) {
  if (r.status !== "fulfilled") return markMissing("sec-calibration");
  const c = r.value;
  const F = FILES.calibration;
  const rate = c.corpus_replication_rate;
  const caveats = c.caveats || [];

  body("sec-calibration").innerHTML = `
    <div class="stat-row">${badge(c.state, c.state == null ? null : `calibration · ${c.state}`)}</div>
    <dl class="stats">
      <div><dt>corpus_replication_rate</dt>
        <dd class="mono" data-src="${F}#/corpus_replication_rate">${rate == null ? "—" : fmt.fixed(rate, 3)}</dd></div>
      <div><dt>split_rule</dt><dd class="mono">${esc(c.split_rule ?? "—")}</dd></div>
      <div><dt>fit group</dt><dd class="mono">${(c.groups?.fit || []).length ? esc(c.groups.fit.join(", ")) : "—"}</dd></div>
      <div><dt>holdout group</dt><dd class="mono">${(c.groups?.holdout || []).length ? esc(c.groups.holdout.join(", ")) : "—"}</dd></div>
    </dl>
    ${caveats.length ? `<div class="hblock">
      <p class="hblock__label">Caveats</p>
      <ul class="hlist hlist--limit">${caveats.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
    </div>` : ""}`;
}

/* ── f) Report ───────────────────────────────────────────────────── */
function renderReport(r) {
  if (r.status !== "fulfilled") return markMissing("sec-report");
  body("sec-report").innerHTML = `<pre class="report-pre" tabindex="0" aria-label="spec-010 report, preformatted markdown">${esc(r.value)}</pre>`;
}

/* ── g) Footer manifest ──────────────────────────────────────────── */
function renderManifest(r) {
  if (r.status !== "fulfilled") return markMissing("sec-manifest");
  const m = r.value;
  const rows = Object.entries(m.artifacts || {})
    .map(
      ([name, a]) => `<tr>
        <td class="mono">${esc(name)}</td>
        <td class="mono" title="${esc(a.sha256 ?? "")}">${esc((a.sha256 ?? "").slice(0, 12)) || NO_OBS}</td>
      </tr>`
    )
    .join("");
  body("sec-manifest").innerHTML = `
    <div class="table-wrap">
      <table class="data">
        <caption>run <span class="mono">${esc(m.run_id ?? "—")}</span> · schema <span class="mono">${esc(m.schema_version ?? "—")}</span></caption>
        <thead><tr><th>artifact</th><th>sha256 (12)</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="2">${NO_OBS}</td></tr>`}</tbody>
      </table>
    </div>`;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
