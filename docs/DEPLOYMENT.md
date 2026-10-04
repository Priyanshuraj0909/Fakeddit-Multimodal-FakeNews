# Public Vercel deployment

Public URL: https://fakeddit-multimodal-fakenews.vercel.app/

The Vercel project `fakeddit-multimodal-fakenews` builds this repository's `main` branch as a FastAPI application. The entrypoint is `api.index:app`, configured in `pyproject.toml`.

## Access configuration

Vercel Authentication is set to **Standard Protection** (`prod_deployment_urls_and_all_previews`). The stable production domain above is public; generated deployment URLs and preview URLs retain protection. Password and Trusted IP protection are disabled for this project.

See [Vercel Authentication documentation](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication).

This is a Vercel project setting, not an application login or a `vercel.json` option. If the project is recreated, select Standard Protection so the portfolio URL remains public. Successful protected/bypass fetches alone do not establish anonymous visitor access.

## Verify availability

```bash
python scripts/check_deployment.py
```

The script uses no login credentials or bypass tokens. It checks the homepage, GET/HEAD availability, static assets, API health, and a sample text-analysis request. GitHub Actions runs it on successful production deployment events and supports manual execution from the Actions tab.

The app supports HEAD requests on `/` and `/api/health` for uptime clients. No model artifacts are needed for the text explorer.

## If the page does not open

Check whether the browser shows a Vercel login, an HTTP error, or a connection timeout. A login usually points to protection settings; a timeout may be a network/DNS problem before the request reaches the app. Check deployment status, domain assignment, and request logs before changing application code.

For a timeout, try a private browser window and another network. For an application error, run the check above and inspect Vercel runtime logs. The local app remains available through `python -m uvicorn api.index:app --reload`.
