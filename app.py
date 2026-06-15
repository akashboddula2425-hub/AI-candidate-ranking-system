"""
app.py — Team Phoenix · Candidate Ranking dashboard (sandbox demo).

A dark, modern Streamlit dashboard for the Redrob hybrid ranker. Upload a small
candidate sample (.jsonl / .json) and it runs the SAME pipeline used to produce the
submission — dense semantic understanding + structured fit + integrity guards +
behavioural signals — and renders a ranked shortlist with score bars and reasoning.

Run locally:  streamlit run app.py
"""
import io
import os
import json
import csv as _csv
from collections import Counter

import numpy as np
import streamlit as st

from src.profile import Candidate, semantic_document
from src.behavioral import availability_multiplier
from src import scoring, semantic, reasoning

st.set_page_config(page_title="Phoenix · Candidate Ranker", layout="wide",
                   page_icon="✦", initial_sidebar_state="expanded")

# ---------------------------------------------------------------- palette / CSS
LIME = "#C5F24E"; PURPLE = "#A78BFA"; BG = "#0F1115"; PANEL = "#181B22"
BORDER = "#2A2F3A"; TEXT = "#E7EAF0"; MUTED = "#8A93A5"; RED = "#FF6B5B"; GREEN = "#5BE3A6"

st.markdown(f"""
<style>
  .stApp {{ background:{BG}; color:{TEXT}; }}
  #MainMenu, header, footer {{ visibility:hidden; }}
  .block-container {{ padding:1.2rem 2rem 2rem 2rem; max-width:1500px; }}
  html, body, [class*="css"] {{ font-family:'Inter','Segoe UI',system-ui,sans-serif; }}
  section[data-testid="stSidebar"] {{ background:#0A0B0E; border-right:1px solid {BORDER}; }}
  section[data-testid="stSidebar"] * {{ color:{TEXT}; }}
  /* widgets */
  [data-testid="stFileUploaderDropzone"] {{ background:{PANEL}; border:1px dashed {BORDER}; border-radius:14px; }}
  .stSlider label, .stFileUploader label {{ color:{MUTED}!important; font-size:.8rem; }}
  div[data-baseweb="slider"] [role="slider"] {{ background:{LIME}!important; }}
  /* cards */
  .card {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:18px; padding:18px 20px; }}
  .stat {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:18px; padding:16px 18px; height:120px;
           display:flex; flex-direction:column; justify-content:space-between; }}
  .stat .lbl {{ color:{MUTED}; font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; display:flex; justify-content:space-between; }}
  .stat .big {{ font-size:2.5rem; font-weight:800; line-height:1; }}
  .stat .sub {{ color:{MUTED}; font-size:.74rem; }}
  .pill {{ font-size:.62rem; font-weight:700; padding:3px 9px; border-radius:20px; }}
  .h1 {{ font-size:2rem; font-weight:800; margin:0; letter-spacing:-.02em; }}
  .muted {{ color:{MUTED}; }}
  .navitem {{ display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:11px;
             color:{MUTED}; font-weight:600; font-size:.92rem; margin:3px 0; }}
  .navitem.on {{ background:#FFFFFF; color:#0A0B0E; }}
  .navitem.on2 {{ background:{PANEL}; color:{TEXT}; }}
  .crow {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:16px; padding:13px 16px; margin-bottom:10px; }}
  .rankbadge {{ width:38px; height:38px; border-radius:11px; background:#22262F; color:{LIME};
               font-weight:800; font-size:1rem; display:flex; align-items:center; justify-content:center; }}
  .bar {{ height:7px; border-radius:6px; background:#22262F; overflow:hidden; }}
  .bar > i {{ display:block; height:100%; border-radius:6px; background:linear-gradient(90deg,{PURPLE},{LIME}); }}
  .chip {{ font-size:.62rem; font-weight:700; padding:2px 8px; border-radius:8px; }}
  .scroll {{ max-height:560px; overflow-y:auto; padding-right:6px; }}
  .scroll::-webkit-scrollbar {{ width:8px; }} .scroll::-webkit-scrollbar-thumb {{ background:{BORDER}; border-radius:8px; }}
  .mbar {{ display:flex; align-items:center; gap:8px; margin:7px 0; font-size:.8rem; }}
  .mbar .t {{ flex:0 0 130px; color:{MUTED}; }}
  .mbar .b {{ flex:1; height:9px; border-radius:6px; background:#22262F; overflow:hidden; }}
  .mbar .b > i {{ display:block; height:100%; background:{PURPLE}; border-radius:6px; }}
  .mbar .v {{ flex:0 0 28px; text-align:right; font-weight:700; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- helpers
def parse_upload(raw_bytes):
    text = raw_bytes.decode("utf-8")
    if text.lstrip().startswith("["):
        return list(json.loads(text))
    return [json.loads(l) for l in text.splitlines() if l.strip()]


@st.cache_resource(show_spinner=False)
def get_encoder():
    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(semantic.MODEL_NAME); m.max_seq_length = 128
        return m
    except Exception:
        return None


def embed_sample(raw_cands):
    docs = [semantic_document(c) for c in raw_cands]
    model = get_encoder()
    if model is not None:
        emb = model.encode(docs, normalize_embeddings=True, show_progress_bar=False)
        jd = model.encode(semantic.jd_query_texts(), normalize_embeddings=True, show_progress_bar=False)
        sims = (emb @ jd.T + 1) / 2
        return sims[:, 0], sims[:, 1], sims[:, 2], "dense · all-MiniLM-L6-v2"
    s = semantic.tfidf_fallback_scores(docs, list(range(len(docs))))
    return s["main"], s["core"], s["anti"], "TF-IDF fallback"


def rank_sample(raw, topk):
    sm, sc, sa, mode = embed_sample(raw)
    cands = [Candidate(c) for c in raw]
    rows = []
    for i, c in enumerate(cands):
        comp = scoring.structured_components(c)
        behav, _ = availability_multiplier(c)
        blend = scoring.combine(comp, float(sm[i]), float(sc[i]), float(sa[i]), behav)
        rows.append((c, comp, blend))
    rows.sort(key=lambda r: (-r[2]["final"], r[0].id))
    return rows, mode


def stat(col, label, value, sub, accent=TEXT, tag=None, tagcol=PURPLE):
    tag_html = f'<span class="pill" style="background:{tagcol}22;color:{tagcol}">{tag}</span>' if tag else ""
    col.markdown(f"""<div class="stat">
      <div class="lbl"><span>{label}</span>{tag_html}</div>
      <div class="big" style="color:{accent}">{value}</div>
      <div class="sub">{sub}</div></div>""", unsafe_allow_html=True)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin:.2rem 0 1.1rem 0">
        <div style="width:34px;height:34px;border-radius:10px;background:{LIME};color:#0A0B0E;
             font-weight:900;font-size:1.2rem;display:flex;align-items:center;justify-content:center">✦</div>
        <div><div style="font-weight:800;font-size:1.05rem">Phoenix</div>
        <div style="color:{MUTED};font-size:.7rem">Candidate Ranker</div></div></div>""", unsafe_allow_html=True)
    st.markdown(f"""
        <div class="navitem on">▦&nbsp; Dashboard</div>
        <div class="navitem">◍&nbsp; Candidates</div>
        <div class="navitem">▤&nbsp; Reports</div>
        <div class="navitem">⚙&nbsp; About</div>""", unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Candidate sample (.jsonl / .json)", type=["jsonl", "json", "txt"])
    topk = st.slider("Shortlist size", 5, 100, 12)
    st.markdown(f"""<div class="card" style="margin-top:14px;padding:13px 15px">
        <div style="color:{LIME};font-weight:700;font-size:.78rem;margin-bottom:5px">HOW IT WORKS</div>
        <div style="color:{MUTED};font-size:.74rem;line-height:1.5">Dense semantic match + structured
        recruiter-style fit + honeypot/stuffer guards + behavioural availability →
        one explainable score per candidate.</div></div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- header
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown(f'<div class="h1">Candidate Ranking — Overview</div>'
                f'<div class="muted" style="margin-top:2px">Team Phoenix · ranking talent by genuine fit, not keywords</div>',
                unsafe_allow_html=True)
with c2:
    st.markdown(f'<div style="text-align:right;margin-top:8px"><span class="pill" '
                f'style="background:{PANEL};border:1px solid {BORDER};color:{MUTED}">JD · Senior AI Engineer</span></div>',
                unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# Optional preloaded sample (lets the hosted sandbox open already-populated).
_demo = os.environ.get("REDROB_DEMO_FILE")
if _demo and not os.path.exists(_demo):
    _demo = None

# ---------------------------------------------------------------- empty state
if uploaded is None and not _demo:
    s1, s2, s3, s4 = st.columns(4)
    stat(s1, "Candidates", "—", "upload a sample to begin", MUTED)
    stat(s2, "Shortlisted", "—", f"top {topk} by fit", MUTED)
    stat(s3, "Honeypots filtered", "—", "impossible profiles", MUTED)
    stat(s4, "Stuffers filtered", "—", "keyword-only profiles", MUTED)
    st.markdown(f"""<div class="card" style="margin-top:16px;text-align:center;padding:48px 20px">
        <div style="font-size:2.4rem">✦</div>
        <div style="font-weight:800;font-size:1.25rem;margin-top:6px">Upload a candidate sample to rank</div>
        <div class="muted" style="margin-top:6px">Use the bundled <b style="color:{TEXT}">sample_candidates.json</b>,
        or any slice of <b style="color:{TEXT}">candidates.jsonl</b>. The dashboard ranks them live and
        shows a shortlist with scores and reasoning.</div></div>""", unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------------- run pipeline
if uploaded is not None:
    raw = parse_upload(uploaded.read())
else:
    with open(_demo, "rb") as _f:
        raw = parse_upload(_f.read())
with st.spinner("Ranking candidates…"):
    rows, mode = rank_sample(raw, topk)
short = rows[:topk]
maxf = max((r[2]["final"] for r in rows), default=1.0) or 1.0
n_hp = sum(1 for _, comp, _ in rows if comp["hp_flags"])
n_st = sum(1 for _, comp, _ in rows if comp["is_stuffer"])
in_band = sum(1 for c, _, _ in short if 5 <= c.yoe <= 9)

# ---- stat row ----
s1, s2, s3, s4 = st.columns(4)
stat(s1, "Candidates scanned", f"{len(raw):,}", f"semantic mode · {mode}", TEXT, tag="LIVE", tagcol=LIME)
stat(s2, "Shortlisted", f"{len(short):02d}", f"{in_band}/{len(short)} in 5–9 yr band", LIME)
stat(s3, "Honeypots filtered", f"{n_hp:02d}", "impossible profiles caught", RED if n_hp else TEXT, tagcol=RED)
stat(s4, "Stuffers filtered", f"{n_st:02d}", "keyword-only profiles caught", PURPLE, tagcol=PURPLE)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

left, right = st.columns([2.1, 1])

# ---- ranked candidate cards ----
with left:
    st.markdown(f'<div style="font-weight:700;margin-bottom:10px">Ranked shortlist '
                f'<span class="muted" style="font-weight:400">· best fit first</span></div>',
                unsafe_allow_html=True)
    html = ['<div class="scroll">']
    for rank_pos, (c, comp, blend) in enumerate(short, 1):
        pct = int(round(100 * blend["final"] / maxf))
        why = esc(reasoning.make_reasoning(c, blend, blend["final"] / maxf))
        title = esc(c.profile.get("current_title", ""))
        loc = esc(c.profile.get("location", "").split(",")[0])
        flags = ""
        if comp["hp_flags"]:
            flags += f'<span class="chip" style="background:{RED}22;color:{RED}">honeypot</span> '
        if comp["is_stuffer"]:
            flags += f'<span class="chip" style="background:{PURPLE}22;color:{PURPLE}">stuffer</span> '
        html.append(f"""<div class="crow">
          <div style="display:flex;align-items:center;gap:13px">
            <div class="rankbadge">{rank_pos}</div>
            <div style="flex:1;min-width:0">
              <div style="display:flex;justify-content:space-between;gap:10px">
                <div style="font-weight:700">{title} · {c.yoe:.0f} yrs <span class="muted" style="font-weight:400">· {loc}</span></div>
                <div style="font-weight:800;color:{LIME}">{pct}</div>
              </div>
              <div class="bar" style="margin:7px 0"><i style="width:{pct}%"></i></div>
              <div class="muted" style="font-size:.8rem;line-height:1.45">{why} {flags}</div>
            </div>
          </div></div>""")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

# ---- insight panels ----
with right:
    titles = Counter(esc(c.profile.get("current_title", "")) for c, _, _ in short)
    st.markdown('<div style="font-weight:700;margin-bottom:10px">Shortlist by role</div>', unsafe_allow_html=True)
    tmax = max(titles.values()) if titles else 1
    bars = ['<div class="card">']
    for t, n in titles.most_common(6):
        bars.append(f'<div class="mbar"><div class="t">{t[:18]}</div>'
                    f'<div class="b"><i style="width:{int(100*n/tmax)}%"></i></div><div class="v">{n}</div></div>')
    bars.append("</div>")
    st.markdown("".join(bars), unsafe_allow_html=True)

    # experience split
    juniors = sum(1 for c, _, _ in short if c.yoe < 5)
    band = in_band
    senior = sum(1 for c, _, _ in short if c.yoe > 9)
    st.markdown('<div style="font-weight:700;margin:16px 0 10px">Experience mix</div>', unsafe_allow_html=True)
    total = max(len(short), 1)
    segs = [("&lt; 5 yrs", juniors, MUTED), ("5–9 yrs (ideal)", band, LIME), ("&gt; 9 yrs", senior, PURPLE)]
    seg_html = ['<div class="card"><div style="display:flex;height:14px;border-radius:8px;overflow:hidden;margin-bottom:12px">']
    for _, n, col in segs:
        seg_html.append(f'<div style="width:{100*n/total}%;background:{col}"></div>')
    seg_html.append("</div>")
    for lbl, n, col in segs:
        seg_html.append(f'<div style="display:flex;justify-content:space-between;font-size:.8rem;margin:5px 0">'
                        f'<span class="muted">● {lbl}</span><span style="font-weight:700;color:{col}">{n}</span></div>')
    seg_html.append("</div>")
    st.markdown("".join(seg_html), unsafe_allow_html=True)

# ---- export ----
buf = io.StringIO(); w = _csv.writer(buf); w.writerow(["candidate_id", "rank", "score", "reasoning"])
for rank_pos, (c, comp, blend) in enumerate(short, 1):
    sc = round(0.45 + 0.54 * (blend["final"] / maxf), 4)
    w.writerow([c.id, rank_pos, f"{sc:.4f}", reasoning.make_reasoning(c, blend, blend["final"] / maxf)])
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.download_button("⬇  Download ranked CSV", buf.getvalue(), file_name="ranked_sample.csv", mime="text/csv")
