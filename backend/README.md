# FakeEdit Backend

All server-side application and training code is organized in this folder.

| Location | Purpose |
| --- | --- |
| `main.py` | FastAPI server, input validation, static frontend serving, and optional model inference |
| `fakeddit/signals.py` | Descriptive text analysis |
| `fakeddit/train_text.py` | Reproducible text classifier training |
| `fakeddit/train_multimodal.py` | Offline multimodal training from aligned embeddings |

## Run locally

Run these commands from the **repository root**, using Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-app.txt
python -m uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000 for the app and http://127.0.0.1:8000/docs for interactive API documentation.

## API endpoints

- `GET /api/health`: service health and validated model readiness.
- `GET /api/capabilities`: supported modes, limits, and unavailable inference features.
- `POST /api/analyze`: descriptive analysis of a JSON body such as `{"text": "Your headline"}`.
- `POST /api/predict`: optional trained text classifier; returns 503 until model artifacts and inference dependencies are installed.

The Vercel entrypoint is `backend.main:app`, configured in the root `pyproject.toml`. API URLs stay the same.

Image and video previews are processed in the browser; this backend does not currently perform image/video inference. See the [project README](../README.md) for training instructions, dependency groups, model setup, and deployment details.
