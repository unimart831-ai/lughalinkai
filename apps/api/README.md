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

FastAPI service for English → Kiswahili / Kikuyu PSA translation using fine-tuned NLLB models hosted on the Hugging Face Hub.

## Space secrets / variables

| Name | Example |
|------|---------|
| `LUGHALINK_MODEL_KIK` | `YOUR_USER/lughalink-nllb-psa-en-kik` |
| `LUGHALINK_MODEL_SW` | `YOUR_USER/lughalink-nllb-psa-en-sw` |
| `HF_TOKEN` | (only if model repos are private) |
| `LUGHALINK_CORS_ORIGINS` | `*` or `https://your-frontend.example` |

## Endpoints

- `GET /health`
- `POST /translate` — JSON `{"text":"...","target":"kik"|"sw"}`
- Interactive docs: `/docs`

Full deploy guide: see repo `DOCS/DEPLOY_HF.md`.
