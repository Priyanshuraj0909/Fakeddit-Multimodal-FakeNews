"""Verify the public production URL without Vercel login or bypass credentials."""
import argparse
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def check(base_url):
    base_url = base_url.rstrip('/')
    host = urlparse(base_url).netloc

    def request(path, method='GET', payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        headers = {'User-Agent': 'Fakeddit-Deployment-Check/1.0'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        with urlopen(Request(base_url + path, data=body, headers=headers, method=method), timeout=15) as response:
            if response.status != 200 or urlparse(response.url).netloc != host:
                raise RuntimeError(f'{path}: expected public HTTP 200 without a login redirect')
            return response.read().decode()

    homepage = request('/')
    if '<title>Fakeddit' not in homepage:
        raise RuntimeError('Homepage does not contain the Fakeddit application')
    request('/', method='HEAD')
    health = json.loads(request('/api/health'))
    request('/api/health', method='HEAD')
    if health.get('status') != 'ok':
        raise RuntimeError('API health check failed')
    for path in ('/static/src/components/workspace.css', '/static/src/pages/workspace.js', '/static/src/services/api.js', '/static/src/utils/media.js', '/static/src/hooks/state.js'):
        if not request(path).strip():
            raise RuntimeError(f'{path}: empty asset')
    capabilities = json.loads(request('/api/capabilities'))
    if capabilities.get('text_analysis') is not True or capabilities.get('media_inspection') != 'browser_local':
        raise RuntimeError('Capabilities endpoint did not return supported modes')
    report = json.loads(request('/api/analyze', method='POST', payload={'text': 'A sample headline for deployment verification.'}))
    if report.get('mode') != 'descriptive' or report.get('word_count', 0) < 1:
        raise RuntimeError('Analysis endpoint did not return a valid report')
    return {'url': base_url, 'status': 'passed', 'version': health.get('version'), 'checks': ['public homepage', 'GET/HEAD availability', 'frontend assets', 'API health', 'capabilities', 'text analysis']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?', default='https://fakeddit-multimodal-fakenews.vercel.app')
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.url), indent=2))
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f'Deployment check failed: {error}\n')
