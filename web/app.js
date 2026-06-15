/* app.js — dashboard orchestration + rendering for the in-browser ranker. */
import { rankAll, makeReasoning } from "./ranker.js";
import { getEmbedder, embedTexts } from "./embeddings.js";

const LIME = "#C5F24E", PURPLE = "#A78BFA", RED = "#FF6B5B", MUTED = "#8A93A5", TEXT = "#E7EAF0";
let lastRows = null;                 // cache so the slider re-renders without re-embedding

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const status = (msg) => { $("status").innerHTML = msg ? `<div class="card status">${msg}</div>` : ""; };

function parseText(text) {
  return text.trim().startsWith("[") ? JSON.parse(text)
    : text.split(/\r?\n/).filter((l) => l.trim()).map((l) => JSON.parse(l));
}

async function run(raw) {
  try {
    status("Loading AI model… (first run downloads ~30 MB, then it's cached)");
    await getEmbedder(status);
    status(`Embedding ${raw.length} profiles in your browser…`);
    const rows = await rankAll(raw, embedTexts, (d, t) => status(`Embedding profiles… ${d}/${t}`));
    lastRows = rows;
    status("");
    render();
  } catch (e) {
    status(`<span style="color:${RED}">Error: ${esc(e.message || e)}</span>`);
    console.error(e);
  }
}

function statCard(label, value, sub, accent = TEXT, tag = "", tagc = PURPLE) {
  const t = tag ? `<span class="pill" style="background:${tagc}22;color:${tagc}">${tag}</span>` : "";
  return `<div class="stat"><div class="lbl"><span>${label}</span>${t}</div>
    <div class="big" style="color:${accent}">${value}</div><div class="sub">${sub}</div></div>`;
}

function render() {
  if (!lastRows) return;
  const topk = +$("topk").value;
  $("topkval").textContent = topk;
  const rows = lastRows, short = rows.slice(0, topk);
  const maxf = Math.max(...rows.map((r) => r.blend.final), 1e-9);
  const nHp = rows.filter((r) => r.comp.hp_flags.length).length;
  const nSt = rows.filter((r) => r.comp.is_stuffer).length;
  const inBand = short.filter((r) => r.cand.yoe >= 5 && r.cand.yoe <= 9).length;

  $("stats").innerHTML =
    statCard("Candidates scanned", rows.length.toLocaleString(), "embedded in-browser", TEXT, "LIVE", LIME) +
    statCard("Shortlisted", String(short.length).padStart(2, "0"), `${inBand}/${short.length} in 5–9 yr band`, LIME) +
    statCard("Honeypots filtered", String(nHp).padStart(2, "0"), "impossible profiles caught", nHp ? RED : TEXT, "", RED) +
    statCard("Stuffers filtered", String(nSt).padStart(2, "0"), "keyword-only profiles caught", PURPLE, "", PURPLE);

  // ranked cards
  let html = "";
  short.forEach((r, i) => {
    const { cand: c, comp, blend } = r;
    const pct = Math.round(100 * blend.final / maxf);
    const why = esc(makeReasoning(c, blend, blend.final / maxf));
    const title = esc(c.profile.current_title || ""), loc = esc((c.profile.location || "").split(",")[0]);
    let flags = "";
    if (comp.hp_flags.length) flags += `<span class="chip" style="background:${RED}22;color:${RED}">honeypot</span> `;
    if (comp.is_stuffer) flags += `<span class="chip" style="background:${PURPLE}22;color:${PURPLE}">stuffer</span> `;
    html += `<div class="crow"><div style="display:flex;gap:13px;align-items:center">
      <div class="rankbadge">${i + 1}</div><div style="flex:1;min-width:0">
      <div style="display:flex;justify-content:space-between;gap:10px">
        <div style="font-weight:700">${title} · ${c.yoe.toFixed(0)} yrs <span class="muted" style="font-weight:400">· ${loc}</span></div>
        <div style="font-weight:800;color:${LIME}">${pct}</div></div>
      <div class="bar" style="margin:7px 0"><i style="width:${pct}%"></i></div>
      <div class="muted" style="font-size:.8rem;line-height:1.45">${why} ${flags}</div></div></div></div>`;
  });
  $("shortlist").innerHTML = html;

  // role distribution
  const titles = {};
  short.forEach((r) => { const t = esc(r.cand.profile.current_title || ""); titles[t] = (titles[t] || 0) + 1; });
  const ents = Object.entries(titles).sort((a, b) => b[1] - a[1]).slice(0, 6);
  const tmax = Math.max(...ents.map((e) => e[1]), 1);
  let rolesHtml = '<div class="card">';
  for (const [t, n] of ents)
    rolesHtml += `<div class="mbar"><div class="t">${t.slice(0, 18)}</div>
      <div class="b"><i style="width:${Math.round(100 * n / tmax)}%"></i></div><div class="v">${n}</div></div>`;
  rolesHtml += "</div>";

  // experience mix
  const jr = short.filter((r) => r.cand.yoe < 5).length, sr = short.filter((r) => r.cand.yoe > 9).length;
  const tot = Math.max(short.length, 1);
  const segs = [["&lt;5 yrs", jr, MUTED], ["5–9 yrs (ideal)", inBand, LIME], ["&gt;9 yrs", sr, PURPLE]];
  let exp = '<div class="card"><div style="display:flex;height:14px;border-radius:8px;overflow:hidden;margin-bottom:12px">';
  for (const [, n, col] of segs) exp += `<div style="width:${100 * n / tot}%;background:${col}"></div>`;
  exp += "</div>";
  for (const [l, n, col] of segs)
    exp += `<div style="display:flex;justify-content:space-between;font-size:.8rem;margin:5px 0">
      <span class="muted">● ${l}</span><span style="font-weight:700;color:${col}">${n}</span></div>`;
  exp += "</div>";

  $("panels").innerHTML =
    '<div style="font-weight:700;margin-bottom:10px">Shortlist by role</div>' + rolesHtml +
    '<div style="font-weight:700;margin:16px 0 10px">Experience mix</div>' + exp;

  $("downloadWrap").style.display = "block";
}

function downloadCsv() {
  if (!lastRows) return;
  const topk = +$("topk").value, short = lastRows.slice(0, topk);
  const maxf = Math.max(...lastRows.map((r) => r.blend.final), 1e-9);
  let out = "candidate_id,rank,score,reasoning\n";
  short.forEach((r, i) => {
    const sc = (0.45 + 0.54 * (r.blend.final / maxf)).toFixed(4);
    const why = makeReasoning(r.cand, r.blend, r.blend.final / maxf).replace(/"/g, '""');
    out += `${r.cand.id},${i + 1},${sc},"${why}"\n`;
  });
  const blob = new Blob([out], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "ranked_sample.csv"; a.click();
}

// ---- wiring ----
$("topk").addEventListener("input", () => { if (lastRows) render(); else $("topkval").textContent = $("topk").value; });
$("file").addEventListener("change", (e) => {
  const f = e.target.files[0]; if (!f) return;
  const rd = new FileReader();
  rd.onload = () => run(parseText(rd.result));
  rd.readAsText(f);
});
$("loadSample").addEventListener("click", loadSample);

async function loadSample() {
  try {
    status("Loading bundled sample…");
    const raw = await (await fetch("sample_candidates.json")).json();
    run(raw);
  } catch (e) { status(`<span style="color:${RED}">Couldn't load sample: ${esc(e.message)}</span>`); }
}

window.__dl = downloadCsv;   // wire the download button

// auto-load the sample so the page opens populated
loadSample();
