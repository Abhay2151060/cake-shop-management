"""
In-process login throttling.

The app runs as a single Uvicorn process against a local database, so an
in-memory sliding window is sufficient and adds no infrastructure. It is
deliberately keyed on (client IP, username) so one attacker cannot lock out
every account, and one targeted account cannot be brute forced from one host.
"""

import threading
import time

MAX_ATTEMPTS = 8
WINDOW_SECONDS = 300      # attempts are counted over a rolling 5 minutes
LOCKOUT_SECONDS = 300     # how long a key stays blocked once it trips

_lock = threading.Lock()
_attempts: dict[tuple[str, str], list[float]] = {}
_blocked_until: dict[tuple[str, str], float] = {}


def _key(ip: str, username: str) -> tuple[str, str]:
    return (ip or "unknown", (username or "").strip().lower())


def _prune(now: float) -> None:
    """Drop expired windows so the dicts cannot grow without bound."""
    for key in [k for k, until in _blocked_until.items() if until <= now]:
        _blocked_until.pop(key, None)
    for key in [k for k, stamps in _attempts.items()
                if not stamps or stamps[-1] <= now - WINDOW_SECONDS]:
        _attempts.pop(key, None)


def seconds_until_unblocked(ip: str, username: str) -> int:
    """Remaining lockout in whole seconds; 0 when the caller may proceed."""
    now = time.time()
    with _lock:
        _prune(now)
        until = _blocked_until.get(_key(ip, username))
        return int(until - now) + 1 if until and until > now else 0


def register_failure(ip: str, username: str) -> int:
    """Record a failed login. Returns the number of attempts remaining."""
    now = time.time()
    key = _key(ip, username)
    with _lock:
        _prune(now)
        stamps = [t for t in _attempts.get(key, []) if t > now - WINDOW_SECONDS]
        stamps.append(now)
        _attempts[key] = stamps
        if len(stamps) >= MAX_ATTEMPTS:
            _blocked_until[key] = now + LOCKOUT_SECONDS
            _attempts.pop(key, None)
            return 0
        return MAX_ATTEMPTS - len(stamps)


def reset(ip: str, username: str) -> None:
    """Clear counters after a successful login."""
    key = _key(ip, username)
    with _lock:
        _attempts.pop(key, None)
        _blocked_until.pop(key, None)


def client_ip(request) -> str:
    return request.client.host if request.client else "unknown"
