# Phoenix Candidate Ranker — in-browser demo

A 100% client-side version of the ranker, built for **GitHub Pages**. It runs the
hybrid pipeline **entirely in your browser** — no server, no API, no data leaves your
machine:

- **Dense semantic** match via [`transformers.js`](https://github.com/xenova/transformers.js)
  running `all-MiniLM-L6-v2` (WASM/ONNX) locally.
- **Structured fit + integrity guards + behavioural** scoring ported 1:1 from the Python
  pipeline in [`../src`](../src) (verified byte-identical on the sample).

## Files
| File | Role |
|---|---|
| `index.html` | dashboard shell + styles |
| `app.js` | orchestration + rendering |
| `ranker.js` | the scoring pipeline (JS port of `src/`) |
| `embeddings.js` | in-browser embeddings (transformers.js) |
| `sample_candidates.json` | bundled demo input (auto-loaded) |

## Run locally
```bash
# from the repo root — any static server works (ES modules need http://, not file://)
python -m http.server 8089 --directory web
# open http://localhost:8089
```

## Live
Deployed via GitHub Pages from the `gh-pages` branch (this folder's contents at root).

> The canonical, evaluated pipeline is the **Python** code in `../src` + `rank.py`
> (that's what reproduces `submission.csv`). This in-browser app is a faithful,
> self-contained demo of the same logic.
