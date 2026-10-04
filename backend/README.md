# Backend

FastAPI entrypoint: backend.app.main:app. Run from repository root with `python -m uvicorn backend.app.main:app --reload`. Install `pip install -r backend/requirements.txt`. API contracts: [docs/API.md](../docs/API.md). Tests: backend/tests; ML integration tests: tests/test_multimodal.py. Heavy model dependencies remain optional.
