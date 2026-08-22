"""
Shared rate limiter instance.

Lives in its own module so both main.py (registers the exception handler)
and routers/redirect.py (decorates the endpoint) can import the same
`limiter` object without a circular import.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP. Good enough for an MVP; swap for a Redis-backed
# storage backend once running multiple API instances, since the default
# in-memory storage is per-process.
limiter = Limiter(key_func=get_remote_address)