/* embeddings.js — in-browser semantic embeddings via transformers.js.
   Runs sentence-transformers/all-MiniLM-L6-v2 entirely client-side (WASM/ONNX),
   so the ranker needs no server. Returns L2-normalised 384-d vectors. */
import { pipeline, env } from "https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2";

env.allowLocalModels = false;          // pull the model from the HF hub
env.useBrowserCache = true;            // cache it after first load

let extractor = null;

export async function getEmbedder(statusCb) {
  if (extractor) return extractor;
  extractor = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2", {
    progress_callback: (p) => {
      if (statusCb && p.status === "progress" && p.file && p.file.endsWith(".onnx")) {
        statusCb(`Downloading AI model… ${Math.round(p.progress || 0)}%`);
      }
    },
  });
  return extractor;
}

export async function embedTexts(texts, progressCb) {
  const ex = await getEmbedder();
  const out = [];
  const B = 16;
  for (let i = 0; i < texts.length; i += B) {
    const chunk = texts.slice(i, i + B);
    const r = await ex(chunk, { pooling: "mean", normalize: true });
    const d = r.data, dim = d.length / chunk.length;
    for (let j = 0; j < chunk.length; j++) out.push(d.subarray(j * dim, (j + 1) * dim));
    if (progressCb) progressCb(Math.min(i + B, texts.length), texts.length);
  }
  return out;
}
