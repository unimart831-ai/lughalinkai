# Deploy LughaLink MT on Hugging Face

**Goal:** Store fine-tuned NLLB checkpoints on the Hub, serve them with a FastAPI API (HF Space), and call that API from a custom browser UI later.

No mT5 in this path. Streamlit is not the product UI.

```text
Navon checkpoint  →  HF Hub model repos
                         ↓
              FastAPI Space (GPU preferred)
                         ↓
              Custom web UI (later)
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

Replace `YOUR_USER` with your HF username or org.

```bash
cd ~/lughalinkai

# dry-run first
python scripts/push_to_hub.py --hf-user YOUR_USER --all --dry-run

# public upload (recommended for course digital public good)
python scripts/push_to_hub.py --hf-user YOUR_USER --pair en-kik
python scripts/push_to_hub.py --hf-user YOUR_USER --pair en-sw

# or both:
# python scripts/push_to_hub.py --hf-user YOUR_USER --all
```

Expected repos:

- `https://huggingface.co/YOUR_USER/lughalink-nllb-psa-en-kik`
- `https://huggingface.co/YOUR_USER/lughalink-nllb-psa-en-sw`

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

export LUGHALINK_MODEL_KIK=YOUR_USER/lughalink-nllb-psa-en-kik
export LUGHALINK_MODEL_SW=YOUR_USER/lughalink-nllb-psa-en-sw
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

## 3. Deploy API as a Hugging Face Space (Docker)

### 3.1 Create the Space

1. https://huggingface.co/new-space  
2. **SDK:** Docker  
3. Name e.g. `lughalink-mt-api`  
4. Link this GitHub repo **or** push the repo contents so the **root `Dockerfile`** is used  
5. Hardware: **GPU** if available (T4/A10). Free CPU works but is slow/cold for 600M.

### 3.2 Space variables

In Space → Settings → Variables / Secrets:

| Variable | Value |
|----------|--------|
| `LUGHALINK_MODEL_KIK` | `YOUR_USER/lughalink-nllb-psa-en-kik` |
| `LUGHALINK_MODEL_SW` | `YOUR_USER/lughalink-nllb-psa-en-sw` |
| `LUGHALINK_CORS_ORIGINS` | `*` (tighten later to your frontend origin) |
| `HF_TOKEN` (secret) | only if models are private |

### 3.3 Verify Space URL

After build:

```bash
export SPACE=https://YOUR_USER-lughalink-mt-api.hf.space

curl -s "$SPACE/health"
curl -s -X POST "$SPACE/translate" \
  -H "Content-Type: application/json" \
  -d '{"text":"Wash hands regularly.","target":"sw"}'
```

Browser: open `$SPACE/docs`.

### 3.4 GPU vs CPU

| Hardware | Expectation |
|----------|-------------|
| GPU Space | Reasonable latency for demos |
| Free CPU | Long cold start; may OOM or timeout on 2.3G loads |
| Navon A100 running uvicorn | Best for live class demo if Space GPU unavailable |

Same API code either way — only where it runs changes.

---

## 4. Frontend contract (custom UI later)

Your web app should **not** load model weights. It only calls the API.

### Request

`POST /translate`

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
  "model": "YOUR_USER/lughalink-nllb-psa-en-kik",
  "source_lang": "en"
}
```

### Browser `fetch` example

```javascript
const res = await fetch("https://YOUR_USER-lughalink-mt-api.hf.space/translate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: "IEBC reminds voters to verify their details on the official portal.",
    target: "sw",
  }),
});
const data = await res.json();
console.log(data.translation);
```

Host the UI on Vercel / Netlify / GitHub Pages. Set `LUGHALINK_CORS_ORIGINS` to that origin when you leave prototype mode.

---

## 5. Repo files involved

| Path | Role |
|------|------|
| `scripts/push_to_hub.py` | Upload checkpoints + model card |
| `DOCS/model_cards/MODEL_CARD_TEMPLATE.md` | Hub README template |
| `services/translation/nllb_infer.py` | Shared NLLB generate logic |
| `apps/api/main.py` | FastAPI app |
| `apps/api/requirements.txt` | API deps |
| `Dockerfile` | HF Space / container entry |
| `DOCS/DEPLOY_HF.md` | This guide |

---

## 6. Honesty for demos / reports

State clearly:

- Models are fine-tuned on **PSA silver** translations (`verified=false`).
- Automatic BLEU/chrF used silver refs (see `DOCS/MODELLING_AND_TRAINING_REPORT.md`).
- Outputs are assistive, not official government translations, until human review.
