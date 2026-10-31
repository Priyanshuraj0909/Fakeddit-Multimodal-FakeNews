"""Per-client and total research budgets; Redis makes both atomic across workers."""
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic
import hashlib
import ipaddress
import logging
import os

logger = logging.getLogger(__name__)
SHARED_BUDGET = """
local client = tonumber(redis.call('GET', KEYS[1]) or '0')
local total = tonumber(redis.call('GET', KEYS[2]) or '0')
if client >= tonumber(ARGV[1]) or total >= tonumber(ARGV[3]) then return 0 end
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
local g = redis.call('INCR', KEYS[2])
if g == 1 then redis.call('EXPIRE', KEYS[2], ARGV[4]) end
return 1
"""


def research_identity(request):
    # Trust the platform's overwritten header only inside a Vercel function.
    if os.environ.get('VERCEL') == '1':
        value = request.headers.get('x-vercel-forwarded-for', '').strip()
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            return 'unknown-vercel-client'
    return request.client.host if request.client else 'unknown'


class ResearchLimit:
    def __init__(self, maximum=5, window=60, capacity=2000, total_maximum=None, total_window=3600):
        self.maximum, self.window, self.capacity = maximum, window, capacity
        self.total_maximum = int(os.environ.get('FAKEDDIT_RESEARCH_TOTAL_MAX', '100')) if total_maximum is None else total_maximum
        self.total_window = total_window
        if min(maximum, window, capacity, self.total_maximum, total_window) <= 0:
            raise ValueError('Research quotas must be positive')
        self.entries = OrderedDict()
        self.total = deque()
        self.lock = Lock()
        self.redis_url = os.environ.get('FAKEDDIT_REDIS_URL', '').strip()
        self.failure_reason = 'shared_quota_denied' if self.redis_url else 'rate_limited'
        self.redis = None

    def status(self):
        return {'backend': 'redis' if self.redis_url else 'process_local',
                'shared_across_instances': bool(self.redis_url),
                'client_maximum': self.maximum, 'client_window_seconds': self.window,
                'total_maximum': self.total_maximum, 'total_window_seconds': self.total_window,
                'note': 'Configured quota backend; runtime connection health is not asserted.'}

    def allow(self, identity):
        if self.redis_url:
            return self._shared_allow(identity)
        now = monotonic()
        with self.lock:
            while self.total and self.total[0] <= now-self.total_window:
                self.total.popleft()
            bucket = self.entries.pop(identity, deque())
            while bucket and bucket[0] <= now-self.window:
                bucket.popleft()
            self.entries[identity] = bucket
            if len(self.entries) > self.capacity:
                self.entries.popitem(last=False)
            if len(bucket) >= self.maximum or len(self.total) >= self.total_maximum:
                return False
            bucket.append(now)
            self.total.append(now)
            return True

    def _shared_allow(self, identity):
        try:
            if self.redis is None:
                from redis import Redis
                self.redis = Redis.from_url(self.redis_url, socket_timeout=2, socket_connect_timeout=2)
            # Same hash tag supports atomic execution on Redis Cluster.
            key = 'fakeddit:{research}:client:' + hashlib.sha256(identity.encode()).hexdigest()
            return bool(self.redis.eval(SHARED_BUDGET, 2, key, 'fakeddit:{research}:total',
                                        self.maximum, self.window, self.total_maximum, self.total_window))
        except Exception:
            logger.warning('Shared research quota unavailable; research request denied')
            return False
