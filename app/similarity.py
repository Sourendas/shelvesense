"""LOCAL STUB: TF-IDF / bag-of-words similarity (CPU, stdlib-only).

This is a stand-in for AMD GPU embeddings. It is intentionally simple so the
MVP runs offline with zero spend and no model downloads.

---------------------------------------------------------------------------
AMD / ROCm plug-in point (replace this module's encode + score path):

  1. On AMD Developer Cloud with ROCm PyTorch, load an open embedding model
     (e.g. sentence-transformers / bge / nomic) as torch.nn.Module on device
     "cuda" (ROCm) or Instinct/Radeon as provided by the event.
  2. Replace `LocalTfidfIndex.encode` with model.encode(texts) → float tensors.
  3. Replace `score` cosine over sparse TF-IDF with dense cosine / dot product
     on GPU; batch product+review corpus once at catalogue load.
  4. Optional: run open LLM summarization for the final answer sentence on
     the same AMD GPU (vLLM / ROCm) while keeping citation retrieval here.

Do NOT call paid embedding APIs. Event-free AMD Cloud / ADP only.
---------------------------------------------------------------------------
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset(
    """
    a an the and or of to for in on with without that this is are was were be
    been being it its from by as at into over under about after before than
    then so if but not no yes my me i you your we our they their he she his her
    use used using very just also more most can will would should could
    """.split()
)


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


class LocalTfidfIndex:
    """Sparse TF-IDF index — LOCAL STUB for AMD embeddings."""

    def __init__(self, documents: list[str]):
        self.documents = documents
        self.doc_tokens: list[list[str]] = [tokenize(d) for d in documents]
        self.df: Counter[str] = Counter()
        for toks in self.doc_tokens:
            for term in set(toks):
                self.df[term] += 1
        self.n = max(len(documents), 1)
        self.doc_vecs: list[dict[str, float]] = [self._tfidf(toks) for toks in self.doc_tokens]

    def _tfidf(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        tf = Counter(tokens)
        length = len(tokens)
        vec: dict[str, float] = {}
        for term, count in tf.items():
            idf = math.log((1 + self.n) / (1 + self.df.get(term, 0))) + 1.0
            vec[term] = (count / length) * idf
        return self._l2_normalize(vec)

    @staticmethod
    def _l2_normalize(vec: dict[str, float]) -> dict[str, float]:
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {k: v / norm for k, v in vec.items()}

    def encode(self, text: str) -> dict[str, float]:
        """Encode a query. AMD swap: return dense GPU embedding instead."""
        return self._tfidf(tokenize(text))

    @staticmethod
    def cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        # iterate smaller
        if len(a) > len(b):
            a, b = b, a
        return sum(v * b.get(k, 0.0) for k, v in a.items())

    def score(self, query: str) -> list[tuple[int, float]]:
        """Return (doc_index, score) sorted descending.

        AMD swap: encode query on GPU, matmul against cached corpus matrix.
        """
        q = self.encode(query)
        scored = [(i, self.cosine(q, dv)) for i, dv in enumerate(self.doc_vecs)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


def build_corpus_texts(
    products: Iterable[dict], reviews: Iterable[dict]
) -> tuple[list[str], list[dict]]:
    """Build searchable docs: one per product (with review snippets) + one per review."""
    texts: list[str] = []
    meta: list[dict] = []
    reviews_by_sku: dict[str, list[dict]] = {}
    for r in reviews:
        reviews_by_sku.setdefault(r["sku"], []).append(r)

    for p in products:
        rev_bits = []
        for r in reviews_by_sku.get(p["sku"], [])[:5]:
            rev_bits.append(f"{r.get('title', '')} {r.get('body', '')}")
        blob = " ".join(
            [
                p.get("sku", ""),
                p.get("title", ""),
                p.get("description", ""),
                p.get("category", ""),
                p.get("brand", ""),
                " ".join(p.get("skin_type") or []),
                " ".join(p.get("concerns") or []),
                " ".join(p.get("key_ingredients") or []),
                " ".join(rev_bits),
            ]
        )
        texts.append(blob)
        meta.append({"kind": "product", "sku": p["sku"], "ref": p})

    for r in reviews:
        blob = f"{r.get('sku', '')} {r.get('title', '')} {r.get('body', '')}"
        texts.append(blob)
        meta.append({"kind": "review", "sku": r["sku"], "ref": r})

    return texts, meta
