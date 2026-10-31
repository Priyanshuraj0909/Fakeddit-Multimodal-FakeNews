"""Package the existing browser workspace for GitHub Pages, backed by the real API."""
import argparse
import html
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API = 'https://fakeddit-multimodal-fakenews.vercel.app'


def build(output, api_base=DEFAULT_API):
    parsed = urlparse(api_base)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('Use an HTTPS API origin without credentials, path, query or fragment')
    api_base = api_base.rstrip('/')
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new output directory; existing artifacts are preserved')
    output.mkdir(parents=True)
    shutil.copytree(ROOT/'frontend/src', output/'static/src')
    shutil.copyfile(ROOT/'frontend/favicon.svg', output/'static/favicon.svg')
    markup = (ROOT/'frontend/index.html').read_text()
    markup = markup.replace('<title>', f'<meta name="fakeddit-api-base" content="{html.escape(api_base, quote=True)}">\n  <title>', 1)
    markup = markup.replace('href="/static/', 'href="./static/').replace('src="/static/', 'src="./static/')
    markup = markup.replace('href="/docs"', f'href="{html.escape(api_base, quote=True)}/docs"').replace('href="/"', 'href="./"')
    (output/'index.html').write_text(markup)
    (output/'.nojekyll').write_text('')
    return {'output': str(output), 'api_base': api_base, 'hosting': 'static_frontend_with_external_fastapi',
            'note': 'No model weights, credentials or datasets are included.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--api-base', default=DEFAULT_API)
    print(json.dumps(build(**vars(parser.parse_args()))))
