"""
Vercel serverless entry point.

Vercel's Python runtime looks for a WSGI/ASGI-compatible `app` object in
files under /api. This file just re-exports your existing FastAPI app —
no application code lives here, so app/main.py stays the single source
of truth whether you run it locally with uvicorn or deploy it on Vercel.
"""
from app.main import app  # noqa: F401
