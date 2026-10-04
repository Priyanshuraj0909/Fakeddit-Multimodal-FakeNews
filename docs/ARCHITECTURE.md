# FakeEdit workspace architecture

## Runtime

FastAPI serves `frontend/index.html`, static assets under `/static`, descriptive analysis, optional text-model inference, and OpenAPI documentation. Vercel discovers `backend.main:app` through `pyproject.toml`. App requirements remain separate from research/training requirements; the frontend uses native ES modules and readable CSS without a build-time framework or external font/CDN dependencies.

## Frontend boundaries

- `app.js` coordinates accessible tabs, theme preference, DOM rendering, upload controllers, and report actions.
- `state.js` owns immutable top-level state. Media changes merge by modality so replacing an image preserves video.
- `api.js` bounds request time, forwards cancellation, and validates report schemas before rendering.
- `media.js` validates file MIME/extension/size and decodes media in detached elements. Failed, replaced, removed, or cancelled previews release object URLs. File content is not uploaded to the server.

Text input is sent to `/api/analyze` or `/api/predict`. Edits, attachment changes, and reset clear the report and abort its request, preventing stale responses from representing newer evidence. Reports include local attachment metadata with an explicit preview-only assessment; blob URLs and raw media bytes are excluded.

## Input handling

One image and one video can coexist with text. Drag/drop and native file pickers share validation. Dropping a file elsewhere does not navigate away. Invalid replacement files preserve an already valid preview. Browser-supported MP4/WebM codecs are required; a decode failure is reported without leaving the submit button locked. Some WebM files lack a finite duration; they remain previewable with an explicit unavailable-duration label.

UTF-8 text import rejects invalid bytes, whitespace-only files, and content beyond 10,000 characters. Theme storage is optional: blocked localStorage does not prevent the toggle from working. Tabs support arrow keys, Home, and End; upload controls remain keyboard accessible. Reduced-motion preferences suppress animations.

## Research code

Original Colab notebooks are preserved as historical records and require the original inputs/Drive paths. Runnable local training lives in `backend/fakeddit/`. Post IDs are read as strings to preserve leading zeros. Multimodal embedding checks reject empty/non-numeric/non-finite arrays and require identical ID ordering. New pipelines use independent validation/test splits.

No trained multimodal or video detector is shipped. Model artifacts remain the prerequisite for text-model prediction. A dataset class and a writing signal do not establish factual truth.
