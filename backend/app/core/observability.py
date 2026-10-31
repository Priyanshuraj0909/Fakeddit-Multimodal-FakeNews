"""Request metadata only: submitted news, URLs, credentials and IPs are never logged."""
import json
import logging
from time import perf_counter
from uuid import uuid4

logger = logging.getLogger('fakeddit.requests')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class RequestTelemetry:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request_id, start, status = uuid4().hex, perf_counter(), 500
        scope.setdefault('state', {})['request_id'] = request_id

        async def response(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                message.setdefault('headers', []).append((b'x-request-id', request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, response)
        finally:
            route = scope.get('route')
            logger.info(json.dumps({'request_id': request_id, 'method': scope['method'],
                                    'route': getattr(route, 'path', 'unmatched'), 'status': status,
                                    'duration_ms': round((perf_counter()-start)*1000, 2)}))
