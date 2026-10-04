# Deployment

Local: `python -m uvicorn backend.app.main:app --reload`. Container: `docker compose up --build`; serves port 8000 and mounts models read-only. The container installs lightweight app dependencies, so trained inference requires an image extended with the matching training/multimodal dependency group. Docker execution has not been verified locally.

Vercel: pyproject.toml declares backend.app.main:app and vercel.json targets backend/app/main.py. Static frontend files are served by FastAPI. Datasets, notebooks, results and tests are excluded from the function bundle. Large CLIP inference should use appropriately provisioned compute; the web deployment bundles the evaluated portable text baseline.

GitHub Actions runs Python and native frontend checks. Existing hosting documentation recorded https://fakeddit-multimodal-fakenews.vercel.app as the connected domain; verify its current release after publication using scripts/check_deployment.py. A Git push is not proof of a successful deployment. No deployment settings or access policies are changed by the restructure.

Never commit .env, model weights or datasets. .env.example documents optional paths. Public health means the server is available; inspect /api/capabilities for actual classifier readiness.

## Frontend packaging repair — 2026-10-05

The production restructure exposed FileNotFoundError for frontend/public/index.html and favicon.svg, despite healthy API responses. These files now live directly under frontend, alongside the src directory. The application serves frontend/index.html and /static/favicon.svg. This avoids the deployment's special handling of public directories. Production validation must check homepage, favicon and module assets as well as API health.

Text-v1 is bundled under backend/app/models/releases; heavy dependencies are unnecessary for that classifier. Configure GROQ_API_KEY in Production and redeploy to enable browser-based source research. Do not expose it in frontend code. The combined route allows 60 seconds of Vercel runtime and a 50-second verification deadline. See VERIFICATION_SETUP.md.
