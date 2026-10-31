"""Exercise real Redis atomic budgets on an isolated local Unix socket; no paid calls."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import os
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.core.rate_limit import ResearchLimit


def check():
    executable = shutil.which('redis-server')
    if not executable:
        raise RuntimeError('Install redis-server to run this optional integration check')
    import redis
    with tempfile.TemporaryDirectory(prefix='fakeddit-redis-', dir='/private/tmp' if Path('/private/tmp').is_dir() else None) as directory:
        socket = str(Path(directory)/'redis.sock')
        process = subprocess.Popen([executable, '--port', '0', '--unixsocket', socket, '--save', '', '--appendonly', 'no'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            client = redis.Redis(unix_socket_path=socket)
            for _ in range(100):
                try:
                    if client.ping():
                        break
                except redis.RedisError:
                    time.sleep(.05)
            else:
                raise RuntimeError('Isolated Redis did not start')
            limits = [ResearchLimit(maximum=2, total_maximum=5, total_window=1) for _ in range(2)]
            for limit in limits:
                limit.redis_url = 'isolated-local-test'
                limit.redis = client
            assert limits[0].allow('same-client')
            assert limits[1].allow('same-client')
            assert not limits[0].allow('same-client')
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda i: limits[i % 2].allow(str(i)), range(20)))
            assert sum(results) == 3, 'Combined total budget must allow exactly three remaining calls'
            time.sleep(1.1)
            assert limits[1].allow('new-client'), 'Expired total quota must replenish'
            process.terminate()
            process.wait(timeout=5)
            assert not limits[0].allow('unavailable'), 'Redis outage must deny research'
            return {'status': 'passed', 'checks': ['cross-instance per-client limit', 'atomic total budget under concurrency', 'expiry', 'outage fails closed'], 'provider_calls': 0}
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


if __name__ == '__main__':
    print(json.dumps(check()))
