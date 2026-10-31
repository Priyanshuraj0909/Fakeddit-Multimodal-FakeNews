"""Bound paid research calls per worker; distributed deployments also need platform limits."""
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic
import hashlib
import logging
import os

logger = logging.getLogger(__name__)


class ResearchLimit:
    def __init__(self, maximum=5, window=60, capacity=2000):
        self.maximum, self.window, self.capacity = maximum, window, capacity
        self.entries = OrderedDict()
        self.lock = Lock()
        self.redis_url = os.environ.get('FAKEDDIT_REDIS_URL', '').strip()
        self.failure_reason = 'shared_quota_denied' if self.redis_url else 'rate_limited'
        self.redis = None

    def allow(self, identity):
        if self.redis_url:
            return self._shared_allow(identity)
        now = monotonic()
        with self.lock:
            bucket = self.entries.pop(identity, deque())
            while bucket and bucket[0] <= now-self.window:
                bucket.popleft()
            self.entries[identity] = bucket
            if len(self.entries) > self.capacity:
                self.entries.popitem(last=False)
            if len(bucket) >= self.maximum:
                return False
            bucket.append(now)
            return True

    def _shared_allow(self, identity):
        # Atomic increment/expiry across workers. Never fall back to an unbounded paid call.
        try:
            if self.redis is None:
                from redis import Redis
                self.redis = Redis.from_url(self.redis_url, socket_timeout=2, socket_connect_timeout=2)
            key = 'fakeddit:research:' + hashlib.sha256(identity.encode()).hexdigest()
            count = self.redis.eval("local n = redis.call('INCR', KEYS[1]); if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end; return n", 1, key, self.window)
            return int(count) <= self.maximum
        except Exception:
            # Do not log an exception that might include the Redis credential URL.
            logger.warning('Shared research quota unavailable; research request denied')
            return False
