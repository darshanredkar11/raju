from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from time import monotonic

@dataclass
class _Entry:
    value: object
    expires_at: float

class TTLCache:
    """Small thread-safe LRU+TTL cache; MongoDB remains authoritative."""
    def __init__(self, max_items: int = 512, ttl_seconds: float = 60.0):
        if max_items < 1 or ttl_seconds <= 0: raise ValueError("cache limits must be positive")
        self.max_items, self.ttl_seconds = max_items, ttl_seconds
        self._items = OrderedDict(); self._lock = RLock()
    def get(self, key, default=None):
        with self._lock:
            entry = self._items.get(key)
            if entry is None: return default
            if entry.expires_at <= monotonic(): del self._items[key]; return default
            self._items.move_to_end(key); return entry.value
    def set(self, key, value, ttl_seconds=None):
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        with self._lock:
            if ttl <= 0: self._items.pop(key, None); return
            self._items[key] = _Entry(value, monotonic()+ttl); self._items.move_to_end(key)
            while len(self._items) > self.max_items: self._items.popitem(last=False)
    def delete(self, key):
        with self._lock: self._items.pop(key, None)
    def clear(self):
        with self._lock: self._items.clear()
