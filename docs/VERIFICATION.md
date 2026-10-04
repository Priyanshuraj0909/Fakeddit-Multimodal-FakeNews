# FakeEdit v2 verification — 2026-10-04

## Automated checks

- Python 3.12: `python -m pytest -q` — 9 tests passed, with one upstream Starlette/AnyIO deprecation warning.
- Node.js: `npm test` — 8 tests passed.
- `npm run check`, Python module compilation, and Git whitespace checks passed.
- Backend tests cover homepage/static assets, input validation, missing/corrupt models, trained-artifact inference, post-ID preservation, split overlap, embedding alignment, and phrase boundaries.
- Frontend tests cover file formats/limits, empty files, UTF-8 decoding, report metadata, incomplete API schemas, timeouts, and cancellation.

## Browser checks

`tests/browser/workspace-smoke.js` verifies the running app in Chromium:

- Text input → API → rendered report.
- Keyboard tab navigation and theme switching.
- Undecodable PNG/MOV attachment fallback, oversized-video rejection, and image drag/drop.
- Valid PNG dimensions and a generated WebM preview with playback controls.
- Combined report attachment metadata, removal, reset, and UTF-8 file import.
- API errors, malformed responses, retry availability, and cancelled-response suppression.

Desktop dark/light and mobile screenshots were visually inspected. The mobile layout was checked for horizontal overflow. No browser JavaScript errors were reported during the verified flows.

## Deployment and limits

The connected production URL is https://fakeddit-multimodal-fakenews.vercel.app. GitHub Actions runs Python and frontend checks on every push; Vercel automatically redeploys `main`. The final remote build is checked after publication.

Real Fakeddit training and the historical 93.9% claim have not been reproduced because the original data/embeddings/model are absent. Synthetic fixtures verify software behavior only. Media previews do not perform image/video inference. Original Colab notebooks retain historical environment assumptions documented in PROJECT_REVIEW.md.

## Public-access repair

The Vercel project now uses Standard Protection: the stable production domain is public, while preview/generated deployment URLs remain protected. A fresh browser opened the production app without authentication and passed the multimodal smoke flow. GET/HEAD availability support and an unauthenticated deployment-check script were added; see DEPLOYMENT.md.
