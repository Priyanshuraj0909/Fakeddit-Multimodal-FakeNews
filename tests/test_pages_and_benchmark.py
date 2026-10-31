import json
from pathlib import Path
import httpx
import pytest
from scripts.build_pages import build
from scripts.run_verification_batch import load_cases, capture
from scripts.evaluate_verification import evaluate


def test_pages_package_preserves_relative_modules_and_real_api_configuration(tmp_path):
    output=tmp_path/'site'
    build(output)
    markup=(output/'index.html').read_text()
    assert 'name="fakeddit-api-base" content="https://fakeddit-multimodal-fakenews.vercel.app"' in markup
    assert 'src="./static/src/pages/workspace.js"' in markup
    assert 'href="/static/' not in markup
    assert (output/'static/src/services/ocr.js').is_file()
    assert not list(output.rglob('*.gz'))
    with pytest.raises(ValueError):build(tmp_path/'bad','https://user:secret@example.com')
    with pytest.raises(ValueError):build(output)


def test_case_batch_requires_bounded_real_inputs_and_unique_ids(tmp_path):
    cases=tmp_path/'cases.jsonl'
    cases.write_text(json.dumps({'id':'one','text':'Actual submitted claim'})+'\n')
    assert load_cases(cases)[0]['id']=='one'
    cases.write_text(cases.read_text()*2)
    with pytest.raises(ValueError):load_cases(cases)


def test_unconfigured_verification_writes_unavailable_manifest_without_provider_calls(tmp_path):
    paths=[]
    def transport(request):
        paths.append(request.url.path)
        return httpx.Response(200,json={'verification':{'available':False,'status':'missing_api_key'}})
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        result=capture([{'id':'one','payload':{'text':'Synthetic fixture'}}],tmp_path/'run.jsonl','https://api.example',client=client)
    assert paths==['/api/capabilities']
    assert result['status']=='unavailable' and result['attempted_cases']==0
    assert result['reference_metrics'] is None
    assert not (tmp_path/'run.jsonl').exists()


def test_evaluation_includes_failures_but_requires_provenance_for_independent_scores():
    empty=evaluate([{'id':'outage','report':{'verification':{'status':'unavailable','reason':'timeout','claims':[]}},'reviews':[],'duration_ms':50000}])
    assert empty['status']=='unavailable' and empty['claim_verdict_accuracy'] is None
    assert empty['report_statuses']=={'unavailable':1}
    assert empty['latency_ms']['median']==50000
    record={'id':'reviewed','report':{'verification':{'status':'completed','claims':[{'verdict':'supported','evidence_ids':[1]}],'sources':[{'id':1}]}},
            'reviews':[{'claim_index':0,'expected_verdict':'supported','citations':[{'source_id':1,'supports_assessment':True}]}]}
    with pytest.raises(ValueError):evaluate([record],require_independent=True)
    record['review_metadata']={'reviewer_id':'synthetic-reviewer','independent':True,'reviewed_at':'2026-10-31T00:00:00Z'}
    assert evaluate([record],require_independent=True)['reviews_with_provenance']==1


def test_batch_records_http_failures_without_fabricating_a_verification_report(tmp_path):
    def transport(request):
        return httpx.Response(200,json={'verification':{'available':True}}) if request.url.path.endswith('capabilities') else httpx.Response(503,text='Private provider internals')
    output=tmp_path/'run.jsonl'
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        result=capture([{'id':'one','payload':{'text':'Synthetic contract fixture'}}],output,'https://api.example',client=client)
    row=json.loads(output.read_text())
    assert result['status']=='stopped'
    assert row['report'] is None and row['run_status']=='transport_error' and row['http_status']==503
    assert 'Private provider internals' not in output.read_text()
    scores=evaluate([row])
    assert scores['status']=='unavailable' and scores['report_statuses']=={'transport_error':1}


def test_review_worksheet_retains_failed_runs_and_capture_latency(tmp_path):
    from scripts.create_evidence_review import worksheet
    path=tmp_path/'run.jsonl'
    completed={'id':'one','duration_ms':1000,'report':{'verification':{'status':'completed','claims':[{'verdict':'supported','evidence_ids':[1]}],'sources':[{'id':1}]}},'reviews':[]}
    failed={'id':'two','duration_ms':50000,'report':None,'run_status':'transport_error','reviews':[]}
    path.write_text('\n'.join(json.dumps(row) for row in (completed,failed)))
    rows=worksheet([path])
    assert len(rows)==2 and rows[1]['report'] is None and rows[1]['duration_ms']==50000
    assert rows[0]['reviews'][0]['expected_verdict'] is None
    rows[0]['review_metadata']={'reviewer_id':'synthetic-reviewer','reviewed_at':'2026-10-31T00:00:00Z','independent':True}
    rows[0]['reviews'][0].update(expected_verdict='supported',citations=[{'source_id':1,'supports_assessment':True}])
    result=evaluate(rows,require_independent=True)
    assert result['reviewed_claims']==1 and result['service_unavailable_fraction']==.5


def test_batch_preflight_failure_does_not_invent_a_case_or_metrics(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(503,text='Server unavailable'))) as client:
        result=capture([{'id':'one','payload':{'text':'Synthetic fixture'}}],tmp_path/'run.jsonl','https://api.example',client=client)
    assert result['status']=='unavailable' and result['reason']=='preflight_failed'
    assert result['attempted_cases']==0 and result['reference_metrics'] is None
    assert not (tmp_path/'run.jsonl').exists()
