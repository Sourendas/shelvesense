# AMD ACT III — IDEA (ShelfSense)

## Project name
**ShelfSense**

## One-liner
**Reinvent Commerce** challenge: a catalogue + review assistant that enriches product listings and answers shopper questions — with a meaningful inference/embedding step intended for **AMD Developer Cloud / ROCm** (free event access). Local MVP runs offline with a TF-IDF stub until GPU access is available.

## Challenge pick
- Primary: **Reinvent Commerce** (shopping assistants, catalogue enrichment, review/sentiment → action)
- Alternate if credits/GPU access is smoother: Evolus Business Agents track (free Evolus workspace with event code at kickoff; bring-your-own open model on AMD via Fireworks or vLLM on AMD Cloud)

## Why solo-feasible
- Clear demo path: sample catalogue CSV → enrich titles/attributes → shopper Q&A with citations from reviews.
- Aligns with existing Price Gap commerce instincts.
- Online-only; **skip Italy on-site** (travel not covered).
- Local MVP already scaffolded (stdlib Python, zero spend).

## Tech stack
| Layer | Choice |
| --- | --- |
| Local MVP | Python 3 stdlib (`http.server`), rule enrichment + TF-IDF stub |
| Compute (event) | AMD Developer Cloud GPU (hackathon ADP access) + ROCm PyTorch |
| App | Stdlib server now; FastAPI optional later if deps available |
| Models (event) | Open embedding / LLM runnable on AMD (event-provided list TBD) |
| Optional partner | Evolus free event workspace (code at kickoff; no card; 50k credits to 31 Oct 2026) |
| Repo | Public GitHub, MIT; containerized if rules require |

## MVP demo story
Merchant uploads 25 products + reviews → ShelfSense fills missing attributes + answers “which SKU for dry skin?” with evidence → README shows where AMD GPU embeddings replace the local stub.

## Status
- Local offline MVP: **done** (see README.md).
- lablab registration: **pending browser enroll**.
- No paid AMD plans. No API keys in repo.
