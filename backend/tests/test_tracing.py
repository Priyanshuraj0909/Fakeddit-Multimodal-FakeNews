"""Real SDK spans with an in-memory exporter; synthetic requests, not benchmark evidence."""
import json
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from backend.app import main
from backend.app.core import tracing


def test_nested_trace_context_survives_threadpool_without_news_or_urls(monkeypatch):
    exporter=InMemorySpanExporter()
    provider=TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing,'runtime',lambda:(provider,{'enabled':True,'exporter':'memory','status':'test'}))
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    try:
        with TestClient(main.app) as client:
            response=client.post('/api/detect?private=PRIVATE_QUERY',json={'text':'PRIVATE_NEWS scientists discover a species', 'source_url':'https://example.com/PRIVATE_SOURCE'})
        assert response.status_code==200
        spans=exporter.get_finished_spans()
        root=next(span for span in spans if span.name=='http.request')
        assert response.headers['x-trace-id']==format(root.context.trace_id,'032x')
        assert {'model.classify','research.quota','verification'} <= {span.name for span in spans}
        assert all(span.context.trace_id==root.context.trace_id for span in spans)
        assert next(span for span in spans if span.name=='model.classify').parent.span_id==root.context.span_id
        serialized=json.dumps([{'attributes':dict(span.attributes),'events':[dict(e.attributes) for e in span.events]} for span in spans])
        assert all(marker not in serialized for marker in ('PRIVATE_NEWS','PRIVATE_QUERY','PRIVATE_SOURCE'))
        assert root.attributes['http.route']=='/api/detect'
    finally:
        provider.shutdown()


def test_exception_messages_and_nonallowlisted_attributes_are_never_recorded(monkeypatch):
    exporter=InMemorySpanExporter();provider=TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing,'runtime',lambda:(provider,{}))
    try:
        try:
            with tracing.stage('provider.search', **{'provider':'Groq','secret':'PRIVATE_KEY'}):
                raise RuntimeError('PRIVATE_CONTENT')
        except RuntimeError:
            pass
        span=exporter.get_finished_spans()[0]
        assert dict(span.attributes)=={'provider':'Groq'}
        assert not span.events
        assert span.status.description=='Operation failed'
    finally:
        provider.shutdown()


def test_github_pages_origin_is_allowed_and_other_origins_are_not():
    with TestClient(main.app) as client:
        allowed=client.options('/api/detect',headers={'Origin':'https://priyanshuraj0909.github.io','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
        rejected=client.options('/api/detect',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'})
        assert allowed.status_code==200
        assert allowed.headers['access-control-allow-origin']=='https://priyanshuraj0909.github.io'
        assert 'access-control-allow-origin' not in rejected.headers
