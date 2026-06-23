"""Production entry point serving the Vite app and contract-analysis API."""

from __future__ import annotations

from pathlib import Path

from flask import send_from_directory

from api.analyze import app


DIST_DIRECTORY = Path(__file__).parent / "dist"


@app.get("/")
@app.get("/<path:path>")
def frontend(path: str = ""):
    """Serve built frontend assets and fall back to the Vite entry page."""
    target = DIST_DIRECTORY / path
    if path and target.is_file():
        return send_from_directory(DIST_DIRECTORY, path)
    return send_from_directory(DIST_DIRECTORY, "index.html")
