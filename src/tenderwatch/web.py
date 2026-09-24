from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


STATIC_DIR = Path(__file__).with_name("web_static")


class Catalog:
    def __init__(self, root: Path) -> None:
        current = root / "data" / "ProcessingRuns" / "current"
        run_root = current.resolve() if current.is_symlink() else current
        path = run_root / "CanonicalObservations" / "canonical.jsonl"
        if not path.is_file():
            path = root / "data" / "CanonicalObservations" / "canonical.jsonl"
        self.items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.by_id = {item["canonical_id"]: item for item in self.items}


def make_handler(catalog: Catalog):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/canonicals":
                self._json(list(catalog.by_id.values()))
                return
            if parsed.path.startswith("/api/canonicals/"):
                item = catalog.by_id.get(parsed.path.rsplit("/", 1)[-1])
                self._json(item, 200 if item else 404)
                return
            # Client-side detail rendering handles canonical routes.
            if parsed.path.startswith("/tender/"):
                parsed = parsed._replace(path="/index.html")
            relative = parsed.path.removeprefix("/") or "index.html"
            file_path = (STATIC_DIR / relative).resolve()
            if STATIC_DIR not in file_path.parents or not file_path.is_file():
                self.send_error(404)
                return
            content_type = "text/html; charset=utf-8" if file_path.suffix == ".html" else "text/plain; charset=utf-8"
            if file_path.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif file_path.suffix == ".js":
                content_type = "text/javascript; charset=utf-8"
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, value, status: int = 200) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the TenderWatch canonical explorer.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    catalog = Catalog(args.root)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(catalog))
    print(f"TenderWatch explorer: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
