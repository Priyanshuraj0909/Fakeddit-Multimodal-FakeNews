"""Request metadata only: submitted news, URLs, credentials and IPs are never logged."""
import json
import logging
from time import perf_counter
from uuid import uuid4
from backend.app.core.tracing import stage, attributes, current_trace_id

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
                trace_id = current_trace_id()
                if trace_id:
                    message['headers'].append((b'x-trace-id', trace_id.encode()))
            await send(message)

        method = scope['method'] if scope['method'] in {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'} else 'OTHER'
        with stage('http.request', **{'request.id': request_id, 'http.request.method': method}) as span:
            try:
                await self.app(scope, receive, response)
            finally:
                route = scope.get('route')
                route_path = getattr(route, 'path', 'unmatched')
                attributes(span, **{'http.route': route_path, 'http.response.status_code': status})
                if span is not None and status >= 500:
                    from opentelemetry.trace import Status, StatusCode
                    span.set_status(Status(StatusCode.ERROR, 'Server response error'))
                logger.info(json.dumps({'request_id': request_id, 'trace_id': current_trace_id(), 'method': method,
                                        'route': route_path, 'status': status,
                                        'duration_ms': round((perf_counter()-start)*1000, 2)}))
