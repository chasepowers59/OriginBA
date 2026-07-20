"""Simple in-memory login rate limiting (per email + client IP key)."""

from __future__ import annotations

from collections import defaultdict
from time import time

from fastapi import HTTPException

_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300


def _prune(key: str, now: float) -> list[float]:
    recent = [ts for ts in _ATTEMPTS[key] if now - ts < _WINDOW_SECONDS]
    _ATTEMPTS[key] = recent
    return recent


def check_login_rate_limit(key: str) -> None:
    now = time()
    if len(_prune(key, now)) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again in a few minutes.",
        )


def record_login_failure(key: str) -> None:
    now = time()
    recent = _prune(key, now)
    recent.append(now)
    _ATTEMPTS[key] = recent


def clear_login_attempts(key: str) -> None:
    _ATTEMPTS.pop(key, None)
