"""Deterministic rule/keyword attribute enrichment from title, description, reviews.

No network, no paid APIs. Pure Python heuristics — good enough for offline demo.
When AMD Developer Cloud / ROCm is available, swap the keyword pass for an
open LLM or embedding+classifier running on AMD GPU (see similarity.py).
"""

from __future__ import annotations

from typing import Any

# keyword → attribute value maps (lowercase match against combined text)
SKIN_TYPE_RULES: list[tuple[list[str], str]] = [
    (["dry skin", "for dry", "dry patches", "cracked", "flaky", "dehydrated", "dry winter", "dry cheeks", "dry face", "dry lips", "dry scalp", "dry legs", "dry cracked"], "dry"),
    (["oily skin", "for oily", "oil-control", "oil control", "shine", "mattifying", "matte"], "oily"),
    (["combination skin", "combination"], "combination"),
    (["sensitive skin", "for sensitive", "hypoallergenic", "calming", "soothe", "redness"], "sensitive"),
    (["mature skin", "fine lines", "aging"], "mature"),
    (["all skin", "all skin types"], "all"),
]

CONCERN_RULES: list[tuple[list[str], str]] = [
    (["hydrat", "moistur", "dry", "dehydrat", "flak"], "hydration"),
    (["barrier", "ceramides", "repair"], "barrier repair"),
    (["acne", "blemish", "breakout", "pore", "blackhead"], "acne / pores"),
    (["bright", "dull", "dark spot", "uneven tone", "vitamin c"], "brightening"),
    (["spf", "sunscreen", "sun protection", "uv"], "sun protection"),
    (["fine line", "wrinkle", "retinol", "anti-aging", "age"], "anti-aging"),
    (["oil", "shine", "matte", "sebum"], "oil control"),
    (["redness", "calm", "soothe", "irritat", "sensitive"], "calming"),
    (["pollution", "antioxidant", "urban"], "pollution protection"),
    (["frizz", "hair", "scalp"], "hair / scalp care"),
    (["puff", "eye", "bag"], "eye care"),
]

INGREDIENT_RULES: list[tuple[list[str], str]] = [
    (["hyaluronic"], "hyaluronic acid"),
    (["glycerin"], "glycerin"),
    (["ceramide"], "ceramides"),
    (["niacinamide"], "niacinamide"),
    (["retinol"], "retinol"),
    (["salicylic"], "salicylic acid"),
    (["zinc oxide"], "zinc oxide"),
    (["titanium"], "titanium dioxide"),
    (["vitamin c", "ascorbic"], "vitamin c"),
    (["centella", "cica"], "centella"),
    (["panthenol"], "panthenol"),
    (["shea"], "shea butter"),
    (["aloe"], "aloe"),
    (["tea tree"], "tea tree"),
    (["benzoyl"], "benzoyl peroxide"),
    (["peptide"], "peptides"),
    (["caffeine"], "caffeine"),
    (["squalane"], "squalane"),
    (["argan"], "argan oil"),
    (["kaolin", "charcoal", "clay"], "clay / charcoal"),
    (["green tea"], "green tea"),
    (["lavender"], "lavender"),
    (["oatmeal"], "oatmeal"),
    (["urea"], "urea"),
    (["ferulic"], "ferulic acid"),
    (["witch hazel"], "witch hazel"),
    (["micelle"], "micelles"),
]


def _text_blob(product: dict[str, Any], reviews: list[dict[str, Any]]) -> str:
    parts = [
        product.get("title", ""),
        product.get("description", ""),
        product.get("category", ""),
        " ".join(product.get("key_ingredients") or []),
        " ".join(product.get("skin_type") or []),
        " ".join(product.get("concerns") or []),
    ]
    for r in reviews:
        parts.append(r.get("title", ""))
        parts.append(r.get("body", ""))
    return " ".join(parts).lower()


def _match_rules(text: str, rules: list[tuple[list[str], str]], limit: int = 5) -> list[str]:
    found: list[str] = []
    for keywords, label in rules:
        if any(k in text for k in keywords):
            if label not in found:
                found.append(label)
            if len(found) >= limit:
                break
    return found


def enrich_product(product: dict[str, Any], reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Fill missing attributes; never overwrite non-empty catalogue fields."""
    text = _text_blob(product, reviews)
    existing_skin = list(product.get("skin_type") or [])
    existing_concerns = list(product.get("concerns") or [])
    existing_ings = list(product.get("key_ingredients") or [])

    inferred_skin = _match_rules(text, SKIN_TYPE_RULES)
    inferred_concerns = _match_rules(text, CONCERN_RULES)
    inferred_ings = _match_rules(text, INGREDIENT_RULES)

    filled_skin = existing_skin or inferred_skin
    filled_concerns = existing_concerns or inferred_concerns
    # merge ingredients: keep catalogue + add inferred not already present
    merged_ings = list(existing_ings)
    for ing in inferred_ings:
        if ing not in merged_ings:
            merged_ings.append(ing)

    avg_rating = None
    if reviews:
        avg_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 2)

    enriched = {
        "skin_type": filled_skin,
        "concerns": filled_concerns,
        "key_ingredients": merged_ings,
        "review_count": len(reviews),
        "avg_rating": avg_rating,
        "source": {
            "skin_type": "catalogue" if existing_skin else ("inferred" if inferred_skin else "missing"),
            "concerns": "catalogue" if existing_concerns else ("inferred" if inferred_concerns else "missing"),
            "key_ingredients": "catalogue+inferred" if existing_ings else ("inferred" if inferred_ings else "missing"),
        },
    }
    out = dict(product)
    out["skin_type"] = filled_skin
    out["concerns"] = filled_concerns
    out["key_ingredients"] = merged_ings
    out["enriched"] = enriched
    return out


def enrich_catalogue(
    products: list[dict[str, Any]], reviews: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_sku: dict[str, list[dict[str, Any]]] = {}
    for r in reviews:
        by_sku.setdefault(r["sku"], []).append(r)
    return [enrich_product(p, by_sku.get(p["sku"], [])) for p in products]
