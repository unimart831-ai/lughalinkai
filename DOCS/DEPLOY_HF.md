# Deploy LughaLink MT on Hugging Face

**Goal:** Store fine-tuned NLLB checkpoints on the Hub, serve them with FastAPI + a clean browser UI (HF Space). The **browser never downloads** the 2.3 GB weights — it only sends JSON to `/translate`; the Space loads models from the Hub once on the server.

No mT5 in this path. Streamlit is not the product UI.

```text
Navon checkpoint  →  HF Hub model repos (iranzi/...)
                         ↓
         FastAPI Space (UI at / + API at /translate)
                         ↓
              User browser (text in / out only)
```

---

## 0. Prerequisites

1. Hugging Face account: https://huggingface.co/join  
2. Access token (write): https://huggingface.co/settings/tokens  
3. On Navon (where `artifacts/mt_baseline/*/final` exist):

```bash
cd ~/lughalinkai
git pull
pip install huggingface_hub
huggingface-cli login
# paste token
```

---

## 1. Upload models to the Hub

HF account for this project: **`iranzi`**.

```bash
cd ~/lughalinkai

# dry-run first
python scripts/push_to_hub.py --hf-user iranzi --all --dry-run

# public upload (recommended for course digital public good)
python scripts/push_to_hub.py --hf-user iranzi --pair en-kik
python scripts/push_to_hub.py --hf-user iranzi --pair en-sw

# or both:
# python scripts/push_to_hub.py --hf-user iranzi --all
```

Expected repos:

- `https://huggingface.co/iranzi/lughalink-nllb-psa-en-kik`
- `https://huggingface.co/iranzi/lughalink-nllb-psa-en-sw`

Each upload includes `model.safetensors`, tokenizer files, and a model card from `DOCS/model_cards/MODEL_CARD_TEMPLATE.md`.

Private repos:

```bash
python scripts/push_to_hub.py --hf-user YOUR_USER --all --private
```

Then set `HF_TOKEN` on the Space.

---

## 2. Run the API locally (smoke)

```bash
cd ~/lughalinkai
pip install -r apps/api/requirements.txt

export LUGHALINK_MODEL_KIK=iranzi/lughalink-nllb-psa-en-kik
export LUGHALINK_MODEL_SW=iranzi/lughalink-nllb-psa-en-sw
# export HF_TOKEN=...   # if private

# On Navon with local disks instead of Hub:
# export LUGHALINK_MODEL_KIK=$PWD/artifacts/mt_baseline/en-kik/final
# export LUGHALINK_MODEL_SW=$PWD/artifacts/mt_baseline/en-sw/final

uvicorn apps.api.main:app --host 0.0.0.0 --port 7860
```

Test:

```bash
curl -s http://127.0.0.1:7860/health | python -m json.tool

curl -s -X POST http://127.0.0.1:7860/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"The public is advised to follow official health guidelines.","target":"kik"}' \
  | python -m json.tool

curl -s -X POST http://127.0.0.1:7860/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"IEBC reminds voters to verify their details on the official portal.","target":"sw"}' \
  | python -m json.tool
```

Interactive docs: `http://127.0.0.1:7860/docs`

---

## 3. Deploy UI + API as a Hugging Face Space (Docker)

### 3.1 Create the Space

**Option A — script (after `hf auth login` as `iranzi`):**

```bash
python scripts/create_hf_space.py
```

Then in Space Settings → connect GitHub `unimart831-ai/lughalinkai` (root `Dockerfile`) and pick GPU if available.

**Option B — manual checklist:**

1. Open https://huggingface.co/new-space  
2. **Owner:** `iranzi`  
3. **Space name:** `lughalink-mt-api`  
4. **SDK:** **Docker**  
5. Connect GitHub repo `unimart831-ai/lughalinkai` (root `Dockerfile`; root `README.md` has Space YAML)  
6. Hardware: **GPU** if available (T4/A10). Free CPU is slow/cold for 600M.

### 3.2 Space variables

Settings → Variables and secrets:

| Variable | Value |
|----------|--------|
| `LUGHALINK_MODEL_KIK` | `iranzi/lughalink-nllb-psa-en-kik` |
| `LUGHALINK_MODEL_SW` | `iranzi/lughalink-nllb-psa-en-sw` |
| `LUGHALINK_CORS_ORIGINS` | `*` |
| `HF_TOKEN` (secret) | only if models are private |

Defaults in code already point at the `iranzi/...` repos if env vars are omitted, but setting them explicitly is clearer.

### 3.3 What users open

| URL | Purpose |
|-----|---------|
| `https://iranzi-lughalink-mt-api.hf.space/` | **Clean translator UI** |
| `.../docs` | API playground |
| `.../health` | Model config check |
| `.../translate` | JSON API used by the UI |

### 3.4 Verify

```bash
export SPACE=https://iranzi-lughalink-mt-api.hf.space

curl -s "$SPACE/health"
curl -s -X POST "$SPACE/translate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Wash hands regularly.","target":"sw"}'
```

Open `$SPACE/` in a browser and translate a sample PSA.

### 3.5 GPU vs CPU

| Hardware | Expectation |
|----------|-------------|
| GPU Space | Reasonable latency for demos |
| Free CPU | Long cold start; may OOM or timeout on 2.3G loads |
| Navon A100 + uvicorn | Fast fallback demo if Space GPU unavailable |

**Calling without downloading (your machine):** correct — only the Space server pulls Hub weights once. Browsers send/receive short JSON.

---

### Request

`POST /translate` — used by the built-in UI at `/` (`apps/api/static`).

```json
{
  "text": "The public is advised to follow official health guidelines.",
  "target": "kik"
}
```

`target`: `"kik"` | `"sw"`

### Response

```json
{
  "translation": "...",
  "target": "kik",
  "model": "iranzi/lughalink-nllb-psa-en-kik",
  "source_lang": "en"
}
```

Host a separate frontend on Vercel / Netlify / GitHub Pages if needed. Set `LUGHALINK_CORS_ORIGINS` to that origin when you leave prototype mode.

---

## 5. Repo files involved

| Path | Role |
|------|------|
| `scripts/push_to_hub.py` | Upload checkpoints + model card |
| `scripts/create_hf_space.py` | Create Space + set Hub model env vars |
| `DOCS/model_cards/MODEL_CARD_TEMPLATE.md` | Hub README template |
| `services/translation/nllb_infer.py` | Shared NLLB generate logic |
| `apps/api/main.py` | FastAPI app |
| `apps/api/requirements.txt` | API deps |
| `Dockerfile` | HF Space / container entry |
| `README.md` | Space YAML frontmatter + project docs |
| `DOCS/DEPLOY_HF.md` | This guide |

---

## 6. Honesty for demos / reports

State clearly:

- Models are fine-tuned on **PSA silver** translations (`verified=false`).
- Automatic BLEU/chrF used silver refs (see `DOCS/MODELLING_AND_TRAINING_REPORT.md`).
- Outputs are assistive, not official government translations, until human review.
