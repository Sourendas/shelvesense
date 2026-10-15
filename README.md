# ShelfSense

**AMD Developer Hackathon ACT III · Reinvent Commerce**

Offline catalogue + review assistant: enrich product listings from titles/descriptions/reviews, then answer shopper questions with evidence citations.

This repo ships a **zero-spend local MVP** (Python stdlib only — no GPU, no paid APIs, no `.env`). A meaningful AMD Developer Cloud / ROCm embedding (or open-LLM) step is documented as the production swap for the local TF-IDF stub.

## One-liner demo story

Merchant loads 25 sample SKUs + reviews → ShelfSense fills missing `skin_type` / `concerns` / ingredients → shopper asks *“which SKU for dry skin?”* → ranked recommendations with review citations.

## Requirements

- Python **3.9+** (stdlib only: `http.server`, `csv`, `json`, `re`, …)
- No pip packages required for the MVP
- No network required after you have the files

## Exact run commands

From this directory (`amd-act-iii/`):

```bash
# 1) CLI end-to-end (offline)
python3 run_demo.py
python3 run_demo.py "which SKU for dry skin?"
python3 run_demo.py "best mineral SPF for all skin types"

# 2) Local web UI (stdlib server)
python3 app/server.py
# open http://127.0.0.1:8765/
# optional custom port:
python3 app/server.py 8766
```

CLI writes `demo_last_answer.json` with the last Q&A payload.

## Project layout

```
amd-act-iii/
  README.md          ← you are here
  LICENSE            ← MIT, Copyright (c) 2026 Souren Das
  IDEA.md            ← challenge pitch
  NOTES.md           ← event status / enroll notes
  DEMO_SHOTS.md      ← ≤3 min video shot list
  run_demo.py        ← CLI demo
  data/
    products.csv     ← 25 synthetic SKUs
    reviews.csv      ← 35 short reviews
  app/
    catalog.py       ← CSV loaders
    enrich.py        ← deterministic rule/keyword enrichment
    similarity.py    ← LOCAL TF-IDF stub + AMD plug-in comments
    qa.py            ← shopper Q&A + citations
    server.py        ← stdlib HTTP API + static UI
    static/          ← index.html, app.js, style.css
```

## How enrichment works

`app/enrich.py` scans title + description + review text with keyword rules and fills **only empty** catalogue fields (`skin_type`, `concerns`), while merging inferred ingredients. Fully deterministic — same input → same output. Sources are tagged `catalogue` vs `inferred` in the UI.

## How Q&A works (local stub)

`app/similarity.py` builds a sparse **TF-IDF / bag-of-words** index over products and reviews, scores the query with cosine similarity, and `app/qa.py` aggregates scores per SKU and returns:

- a short natural-language answer
- ranked recommendations
- citations (product blurbs + review snippets)

The API labels the retriever as `local-tfidf-stub`.

## How AMD GPU replaces the local embedder

| Today (offline MVP) | On AMD Developer Cloud / ROCm |
| --- | --- |
| `LocalTfidfIndex` in `app/similarity.py` | Open embedding model (e.g. BGE / Nomic / sentence-transformers) on ROCm PyTorch |
| Sparse cosine on CPU | Dense embeddings + GPU cosine / matmul |
| Optional later: keyword enrich only | Optional: open LLM on AMD (vLLM / ROCm) for attribute fill + answer phrasing |

**Plug-in point:** replace `LocalTfidfIndex.encode` / `score` in `app/similarity.py` (see the header comment block). Keep the same `ask()` return shape so the UI does not change. Do **not** use paid embedding APIs — event-free AMD Cloud / ADP only.

## API (local server)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Web UI |
| GET | `/api/health` | product/review counts |
| GET | `/api/catalogue` | enriched catalogue JSON |
| GET | `/api/ask?q=...` | Q&A |
| POST | `/api/ask` | JSON body `{"question":"...","top_k":5}` |

## License

MIT — Copyright (c) 2026 Souren Das. See [LICENSE](LICENSE).

## Contest notes

- Challenge: **Reinvent Commerce**
- Online build window: 12–18 Oct 2026 (skip Italy on-site)
- Registration / lablab enroll is handled separately (browser agent) — not part of this scaffold
