"""Content-free OpenTelemetry spans with console or optional OTLP export."""
from contextlib import contextmanager
from functools import lru_cache
import os

ALLOWED_ATTRIBUTES = {'request.id', 'http.request.method', 'http.route', 'http.response.status_code',
                      'operation.status', 'operation.reason', 'provider', 'source.count', 'claim.count'}


@lru_cache(maxsize=1)
def runtime():
    exporter = os.environ.get('FAKEDDIT_TRACE_EXPORTER', 'console').strip()
    if exporter == 'none':
        return None, {'enabled': False, 'status': 'disabled', 'exporter': 'none'}
    if exporter not in {'console', 'otlp'}:
        return None, {'enabled': False, 'status': 'invalid_exporter', 'exporter': 'unavailable'}
    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor, BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
        ratio = float(os.environ.get('FAKEDDIT_TRACE_SAMPLE_RATIO', '0.1'))
        if not 0 <= ratio <= 1:
            raise ValueError('Invalid trace sampling ratio')
        provider = TracerProvider(resource=Resource.create({'service.name': 'fakeddit-api'}),
                                  sampler=ParentBased(TraceIdRatioBased(ratio)))
        if exporter == 'otlp':
            if not os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT', '').strip():
                provider.shutdown()
                return None, {'enabled': False, 'status': 'missing_otlp_endpoint', 'exporter': exporter}
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(timeout=2), max_queue_size=512,
                                                           max_export_batch_size=64, schedule_delay_millis=1000))
        else:
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        return provider, {'enabled': True, 'status': 'configured', 'exporter': exporter, 'sample_ratio': ratio,
                          'note': 'Manual spans exclude submitted content, URLs, credentials and exception messages.'}
    except ImportError:
        return None, {'enabled': False, 'status': 'missing_dependencies', 'exporter': exporter}
    except ValueError:
        return None, {'enabled': False, 'status': 'invalid_configuration', 'exporter': exporter}


def configuration():
    return runtime()[1]


def current_trace_id():
    try:
        from opentelemetry import trace
        context = trace.get_current_span().get_span_context()
        return format(context.trace_id, '032x') if context.is_valid else None
    except ImportError:
        return None


def attributes(span, **values):
    if span is not None:
        for key, value in values.items():
            if key in ALLOWED_ATTRIBUTES and isinstance(value, (str, int, bool)):
                span.set_attribute(key, value)


@contextmanager
def stage(name, **values):
    provider, _ = runtime()
    if provider is None:
        yield None
        return
    tracer = provider.get_tracer('fakeddit.manual')
    with tracer.start_as_current_span(name, record_exception=False, set_status_on_exception=False) as span:
        attributes(span, **values)
        try:
            yield span
        except BaseException:
            from opentelemetry.trace import Status, StatusCode
            span.set_status(Status(StatusCode.ERROR, 'Operation failed'))
            raise
