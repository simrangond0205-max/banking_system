"""Production WSGI server (Waitress on Windows; use Gunicorn on Linux/Docker)."""

from __future__ import annotations

import os

from waitress import serve

from webapp import app

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    print(f"Serving on http://{host}:{port}", flush=True)
    serve(app, host=host, port=port)
