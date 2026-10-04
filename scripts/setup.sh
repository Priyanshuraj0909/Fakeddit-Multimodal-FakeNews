#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
printf 'Start: .venv/bin/python -m uvicorn backend.app.main:app --reload
'
