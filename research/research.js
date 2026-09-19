/* ══════════════════════════════════════════════════════════════════
   Rosetta Coda — research console
   Renders the frozen release artifacts. No frameworks, no CDNs.
   Every section loads independently: a failed fetch degrades only its
   own panel to a .state-missing state. No number is invented — cells
   carry their artifact source in a data-src attribute / tooltip.
   ════════════════════════════════════════════════════════════════════ */
"use strict";

const BASE = "/artifacts/release/";
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
  renderTimeTime(features);
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
        <caption>${Number.isFinite(f.n_gate_partition) ? fmt.int(f.n_gate_partition) : "—"} gate-partition codas · ${esc(f.code_version ?? "")}</caption>
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

/* ── d) Time-time plot ───────────────────────────────────────────── */
function renderTimeTime(r) {
  if (r.status !== "fulfilled") return markMissing("sec-timetime");
  const f = r.value;
  const F = FILES.features;
  const recs = f.partition_features || [];

  const points = [];
  const whaleSet = new Set();
  recs.forEach((coda, i) => {
    const pat = coda.ici_pattern;
    if (!Array.isArray(pat) || pat.length < 2) return;
    const whale = coda.whale_id_raw == null || coda.whale_id_raw === "" ? "" : String(coda.whale_id_raw);
    if (whale) whaleSet.add(whale);
    for (let k = 0; k < pat.length - 1; k++) {
      const x = pat[k];
      const y = pat[k + 1];
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      points.push({
        x,
        y,
        vowel: coda.vowel == null ? "" : String(coda.vowel),
        whale,
        coda_id: coda.coda_id == null ? "" : String(coda.coda_id),
        coda_type: coda.coda_type == null ? "" : String(coda.coda_type),
        src: `${F}#/partition_features/${i}/ici_pattern/${k}`,
      });
    }
  });

  if (!points.length) {
    body("sec-timetime").innerHTML = `<p class="loading">${NO_OBS}</p>
      <p class="footnote">No successive ICI pairs in <span class="mono" data-src="${esc(F)}#/partition_features">/partition_features</span>.</p>`;
    return;
  }

  const whales = Array.from(whaleSet).sort();
  let rawMax = 0;
  for (const p of points) rawMax = Math.max(rawMax, p.x, p.y);
  const domain = niceCeilIci(rawMax);

  const L = 56;
  const R = 14;
  const T = 14;
  const B = 44;
  const INNER = 360;
  const VB_W = L + INNER + R;
  const VB_H = T + INNER + B;
  const xOf = (v) => L + (v / domain) * INNER;
  const yOf = (v) => T + INNER - (v / domain) * INNER;

  const step = domain <= 1 ? 0.25 : domain <= 2.5 ? 0.5 : 1;
  const ticks = [];
  for (let t = 0; t <= domain + 1e-9; t += step) ticks.push(Number(t.toFixed(4)));
  const tickDec = step < 0.5 ? 2 : 1;

  const tickMarks = ticks
    .map((t) => {
      const x = xOf(t);
      const y = yOf(t);
      return `
        <line class="tt-tick" x1="${x}" y1="${T + INNER}" x2="${x}" y2="${T + INNER + 5}" />
        <text class="tt-tick-label" x="${x}" y="${T + INNER + 16}" text-anchor="middle">${fmt.fixed(t, tickDec)}</text>
        <line class="tt-tick" x1="${L}" y1="${y}" x2="${L - 5}" y2="${y}" />
        <text class="tt-tick-label" x="${L - 8}" y="${y + 3}" text-anchor="end">${fmt.fixed(t, tickDec)}</text>`;
    })
    .join("");

  const whaleBoxes = whales
    .map(
      (w) => `<label class="tt-whale">
        <input type="checkbox" name="tt-whale" value="${esc(w)}" checked />
        <span class="mono">${esc(w)}</span>
      </label>`
    )
    .join("");

  function meanPair(vowel) {
    let sx = 0, sy = 0, n = 0;
    for (const p of points) {
      if (p.vowel !== vowel) continue;
      sx += p.x; sy += p.y; n += 1;
    }
    return n ? { x: sx / n, y: sy / n, n } : null;
  }
  const meanA = meanPair("a");
  const meanI = meanPair("i");
  const meanMarks = [meanA && { m: meanA, cls: "a", label: "mean a" }, meanI && { m: meanI, cls: "i", label: "mean i" }]
    .filter(Boolean)
    .map(({ m, cls, label }) => {
      const cx = xOf(m.x);
      const cy = yOf(m.y);
      const lx = L + INNER - 8;
      return `
        <g class="tt-mean-g" aria-hidden="true">
          <line class="tt-leader" x1="${lx - 2}" y1="${cy}" x2="${cx + 6}" y2="${cy}" />
          <line class="tt-mean tt-mean--${cls}" x1="${cx - 5}" y1="${cy}" x2="${cx + 5}" y2="${cy}" />
          <line class="tt-mean tt-mean--${cls}" x1="${cx}" y1="${cy - 5}" x2="${cx}" y2="${cy + 5}" />
          <text class="tt-anno" x="${lx}" y="${cy - 6}" text-anchor="end">${label}</text>
        </g>`;
    })
    .join("");
  const isoLabelX = xOf(domain * 0.72);
  const isoLabelY = yOf(domain * 0.72);

  const el = body("sec-timetime");
  el.innerHTML = `
    <div class="tt-toolbar">
      <ul class="tt-legend" aria-label="Vowel color key">
        <li><span class="tt-legend__swatch tt-legend__swatch--a" aria-hidden="true"></span> vowel a</li>
        <li><span class="tt-legend__swatch tt-legend__swatch--i" aria-hidden="true"></span> vowel i</li>
      </ul>
      <fieldset class="tt-whales">
        <legend>Whales</legend>
        <div class="tt-whales__opts">${whaleBoxes || NO_OBS}</div>
      </fieldset>
    </div>
    <div class="tt-shell">
      <span class="tt-shell__mark tt-shell__mark--tl" aria-hidden="true"></span>
      <span class="tt-shell__mark tt-shell__mark--tr" aria-hidden="true"></span>
      <span class="tt-shell__mark tt-shell__mark--bl" aria-hidden="true"></span>
      <span class="tt-shell__mark tt-shell__mark--br" aria-hidden="true"></span>
      <ul class="tt-callouts" aria-hidden="true">
        <li><span class="tt-callouts__pin tt-callouts__pin--a"></span> vowel a</li>
        <li><span class="tt-callouts__pin tt-callouts__pin--i"></span> vowel i</li>
        <li><span class="tt-callouts__pin tt-callouts__pin--iso"></span> isochrony y = x</li>
      </ul>
      <figure class="tt-figure">
        <svg class="tt-svg" viewBox="0 0 ${VB_W} ${VB_H}" role="img"
          aria-label="Time-time scatter of successive normalized inter-click intervals, colored by vowel. Dashed line is the isochronous y equals x reference. Crosses mark per-vowel means.">
          <defs>
            <clipPath id="tt-clip"><rect x="${L}" y="${T}" width="${INNER}" height="${INNER}" /></clipPath>
          </defs>
          <g class="tt-chrome" aria-hidden="true">
            <rect class="tt-plot-bg" x="${L}" y="${T}" width="${INNER}" height="${INNER}" />
            <line class="tt-diag" x1="${xOf(0)}" y1="${yOf(0)}" x2="${xOf(domain)}" y2="${yOf(domain)}" stroke-dasharray="4 3" />
            <text class="tt-anno" x="${isoLabelX + 8}" y="${isoLabelY - 6}">y = x</text>
            ${tickMarks}
            ${meanMarks}
            <text class="tt-axis-label" x="${L + INNER / 2}" y="${VB_H - 4}" text-anchor="middle">ICI_k / mean</text>
            <text class="tt-axis-label" text-anchor="middle" transform="translate(12, ${T + INNER / 2}) rotate(-90)">ICI_k+1 / mean</text>
          </g>
          <g class="tt-points" clip-path="url(#tt-clip)"></g>
        </svg>
        <figcaption>
          <span class="mono" data-src="${esc(F)}#/partition_features">${fmt.int(points.length)}</span> successive pairs
          from <span class="mono" data-src="${esc(F)}#/partition_features">${fmt.int(recs.length)}</span> gate-partition codas.
          Axes are ICI divided by coda mean.
        </figcaption>
      </figure>
      <dl class="tt-readout">
        <div><dt>pairs</dt><dd class="mono">${fmt.int(points.length)}</dd></div>
        <div><dt>whales</dt><dd class="mono">${fmt.int(whales.length)}</dd></div>
        <div><dt>domain</dt><dd class="mono">0–${fmt.fixed(domain, domain < 2 ? 2 : 1)}</dd></div>
        <div><dt>mean a n</dt><dd class="mono">${meanA ? fmt.int(meanA.n) : NO_OBS}</dd></div>
        <div><dt>mean i n</dt><dd class="mono">${meanI ? fmt.int(meanI.n) : NO_OBS}</dd></div>
      </dl>
    </div>
    <p class="tt-detail-wrap"><output class="tt-detail" aria-live="polite">Hover or click a point for coda details.</output></p>
    <p class="footnote">Each point is one successive pair from <span class="mono">ici_pattern</span> (normalized ICI / mean).
    The dashed line is y = x, the isochronous-rhythm reference. Crosses are per-vowel means of those pairs.
    Density and any clusters are descriptive structure only — not meaning, intent, or words.</p>`;

  const g = el.querySelector(".tt-points");
  const NS = "http://www.w3.org/2000/svg";
  const frag = document.createDocumentFragment();
  for (const p of points) {
    const c = document.createElementNS(NS, "circle");
    const vClass = p.vowel === "a" ? "tt-pt tt-pt--a" : p.vowel === "i" ? "tt-pt tt-pt--i" : "tt-pt";
    c.setAttribute("class", vClass);
    c.setAttribute("cx", String(xOf(p.x)));
    c.setAttribute("cy", String(yOf(p.y)));
    c.setAttribute("r", "2.5");
    c.dataset.codaId = p.coda_id;
    c.dataset.codaType = p.coda_type;
    c.dataset.whale = p.whale;
    c.dataset.vowel = p.vowel;
    c.dataset.x = String(p.x);
    c.dataset.y = String(p.y);
    c.dataset.src = p.src;
    frag.appendChild(c);
  }
  g.appendChild(frag);

  const out = el.querySelector(".tt-detail");
  const svg = el.querySelector(".tt-svg");
  let active = null;

  function show(pt) {
    if (active) active.classList.remove("is-active");
    active = pt;
    pt.classList.add("is-active");
    const id = pt.dataset.codaId;
    const typ = pt.dataset.codaType;
    const whale = pt.dataset.whale;
    const vowel = pt.dataset.vowel;
    const src = pt.dataset.src;
    const x = Number(pt.dataset.x);
    const y = Number(pt.dataset.y);
    out.innerHTML = [
      id ? `<span class="mono" data-src="${esc(src)}">${esc(id)}</span>` : NO_OBS,
      typ ? `<span class="mono">${esc(typ)}</span>` : NO_OBS,
      whale ? `<span class="mono">${esc(whale)}</span>` : NO_OBS,
      vowel ? `vowel <span class="mono">${esc(vowel)}</span>` : `vowel ${NO_OBS}`,
      `(${num(x, 3, src)}, ${num(y, 3, src)})`,
    ].join(" · ");
  }

  function fromEvent(ev) {
    const t = ev.target;
    if (t && t.classList && t.classList.contains("tt-pt")) show(t);
  }
  svg.addEventListener("pointerover", fromEvent);
  svg.addEventListener("click", fromEvent);

  const boxes = el.querySelectorAll('input[name="tt-whale"]');
  function applyWhaleFilter() {
    const on = new Set();
    boxes.forEach((b) => {
      if (b.checked) on.add(b.value);
    });
    g.querySelectorAll(".tt-pt").forEach((c) => {
      const w = c.dataset.whale;
      c.setAttribute("visibility", !w || on.has(w) ? "visible" : "hidden");
    });
    if (active && active.getAttribute("visibility") === "hidden") {
      active.classList.remove("is-active");
      active = null;
    }
  }
  boxes.forEach((b) => b.addEventListener("change", applyWhaleFilter));
}

/* Nice upper bound so both axes share a round, equal domain. */
function niceCeilIci(x) {
  if (!Number.isFinite(x) || x <= 0) return 1;
  const pow = 10 ** Math.floor(Math.log10(x));
  const n = x / pow;
  const nice = n <= 1 ? 1 : n <= 1.5 ? 1.5 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 3 ? 3 : n <= 5 ? 5 : 10;
  return nice * pow;
}

/* ── e) Ranked hypotheses ────────────────────────────────────────── */
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

/* ── f) Calibration ──────────────────────────────────────────────── */
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

/* ── g) Report ───────────────────────────────────────────────────── */
function renderReport(r) {
  if (r.status !== "fulfilled") return markMissing("sec-report");
  body("sec-report").innerHTML = `<pre class="report-pre" tabindex="0" aria-label="spec-010 report, preformatted markdown">${esc(r.value)}</pre>`;
}

/* ── h) Footer manifest ──────────────────────────────────────────── */
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
