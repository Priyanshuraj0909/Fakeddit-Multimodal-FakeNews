"""Bound paid research calls per worker; distributed deployments also need platform limits."""
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic


class ResearchLimit:
    def __init__(self, maximum=5, window=60, capacity=2000):
        self.maximum, self.window, self.capacity = maximum, window, capacity
        self.entries = OrderedDict()
        self.lock = Lock()

    def allow(self, identity):
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
