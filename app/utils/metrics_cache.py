"""Redis-based cache for admin dashboard metrics and research data."""

from app.extensions import cache
from flask import current_app
import json


def get() -> dict | None:
    """Retrieve cached data."""
    cached_data = cache.get("dashboard_metrics")
    if cached_data:
        return json.loads(cached_data)
    return None


def set(data: dict) -> None:
    """Store data in cache with 5 minute TTL."""
    cache.set("dashboard_metrics", json.dumps(data), timeout=300)


def invalidate() -> None:
    """Invalidate the cache."""
    cache.delete("dashboard_metrics")


def get_cached_data(key: str) -> dict | None:
    """Retrieve cached data by key."""
    cached_data = cache.get(key)
    if cached_data:
        return json.loads(cached_data)
    return None


def set_cached_data(key: str, data: dict, timeout: int = 300) -> None:
    """Store data in cache with custom TTL."""
    cache.set(key, json.dumps(data), timeout=timeout)


def invalidate_cached_data(key: str) -> None:
    """Invalidate cached data by key."""
    cache.delete(key)

