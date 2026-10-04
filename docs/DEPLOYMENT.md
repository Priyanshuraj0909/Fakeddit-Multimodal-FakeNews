# Deployment

Local: `python -m uvicorn backend.app.main:app --reload`. Container: `docker compose up --build`; serves port 8000 and mounts models read-only. The container installs lightweight app dependencies, so trained inference requires an image extended with the matching training/multimodal dependency group. Docker execution has not been verified locally.

Vercel: pyproject.toml declares backend.app.main:app and vercel.json targets backend/app/main.py. Static frontend files are served by FastAPI. Datasets, notebooks, results and tests are excluded from the function bundle. Large CLIP inference should use appropriately provisioned compute; the lightweight web deployment has no bundled model.

GitHub Actions runs Python and native frontend checks. Existing hosting documentation recorded https://fakeddit-multimodal-fakenews.vercel.app as the connected domain; verify its current release after publication using scripts/check_deployment.py. A Git push is not proof of a successful deployment. No deployment settings or access policies are changed by the restructure.

Never commit .env, model weights or datasets. .env.example documents optional paths. Public health means the server is available; inspect /api/capabilities for actual classifier readiness.
