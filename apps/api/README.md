---
title: LughaLink PSA MT API
emoji: 🇰🇪
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# LughaLink PSA MT API

FastAPI service + clean web UI for English → Kiswahili / Kikuyu PSA translation.
Models load from the Hub on the **server**; the browser only calls `/translate`.

## Space secrets / variables

| Name | Value |
|------|---------|
| `LUGHALINK_MODEL_KIK` | `iranzi/lughalink-nllb-psa-en-kik` |
| `LUGHALINK_MODEL_SW` | `iranzi/lughalink-nllb-psa-en-sw` |
| `HF_TOKEN` | (only if model repos are private) |
| `LUGHALINK_CORS_ORIGINS` | `*` or your frontend origin |

## Endpoints

- `GET /` — translator UI
- `GET /health`
- `POST /translate` — JSON `{"text":"...","target":"kik"|"sw"}`
- Interactive docs: `/docs`

Full deploy guide: see repo `DOCS/DEPLOY_HF.md`.
