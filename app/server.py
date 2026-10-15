#!/usr/bin/env python3
"""Stdlib HTTP server for ShelfSense offline demo. No FastAPI / Flask required."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Allow `python3 app/server.py` from repo root or app/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.catalog import load_products, load_reviews  # noqa: E402
from app.enrich import enrich_catalogue  # noqa: E402
from app.qa import ask  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
PORT = 8765

_products_raw = load_products()
_reviews = load_reviews()
_products = enrich_catalogue(_products_raw, _reviews)


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: object) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _file_response(handler: BaseHTTPRequestHandler, path: Path, content_type: str) -> None:
    data = path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[shelfsense] " + (fmt % args) + "\n")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            return _file_response(self, STATIC / "index.html", "text/html; charset=utf-8")
        if path == "/static/app.js":
            return _file_response(self, STATIC / "app.js", "application/javascript; charset=utf-8")
        if path == "/static/style.css":
            return _file_response(self, STATIC / "style.css", "text/css; charset=utf-8")
        if path == "/api/health":
            return _json_response(
                self,
                200,
                {
                    "ok": True,
                    "products": len(_products),
                    "reviews": len(_reviews),
                    "retriever": "local-tfidf-stub",
                },
            )
        if path == "/api/catalogue":
            slim = []
            for p in _products:
                slim.append(
                    {
                        "sku": p["sku"],
                        "title": p["title"],
                        "brand": p["brand"],
                        "category": p["category"],
                        "price_usd": p["price_usd"],
                        "skin_type": p["skin_type"],
                        "concerns": p["concerns"],
                        "key_ingredients": p["key_ingredients"],
                        "size": p["size"],
                        "enriched": p.get("enriched"),
                    }
                )
            return _json_response(self, 200, {"products": slim, "count": len(slim)})
        if path == "/api/ask":
            qs = parse_qs(parsed.query)
            q = (qs.get("q") or [""])[0]
            return _json_response(self, 200, ask(q, _products, _reviews))

        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/ask":
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return _json_response(self, 400, {"error": "invalid JSON"})
        q = data.get("question") or data.get("q") or ""
        top_k = int(data.get("top_k") or 5)
        return _json_response(self, 200, ask(q, _products, _reviews, top_k=top_k))


def main() -> None:
    port = PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    server = ThreadingHTTPServer((HOST, port), Handler)
    print(f"ShelfSense offline demo → http://{HOST}:{port}/")
    print(f"Catalogue: {len(_products)} products, {len(_reviews)} reviews")
    print("Retriever: local-tfidf-stub (AMD ROCm embeddings: see app/similarity.py)")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
