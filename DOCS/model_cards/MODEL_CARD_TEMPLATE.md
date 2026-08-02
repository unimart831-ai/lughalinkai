---
language:
  - en
  - sw
  - ki
tags:
  - translation
  - nllb
  - kenya
  - psa
  - lughalink
license: mit
library_name: transformers
pipeline_tag: translation
base_model: facebook/nllb-200-distilled-600M
---

# LughaLink NLLB PSA — {{PAIR}}

Fine-tuned **NLLB-200 distilled 600M** for English → {{TARGET_NAME}} Public Service Announcements (Kenya).

## Intended use

- Translate short English PSA / public advisory text into {{TARGET_NAME}}.
- Research and course demo (DSA 4020); not a certified government translation service.

## Training data (honesty)

- Source: framework-filtered Kenyan PSA English (real + labeled synthetic).
- Targets: **silver** NLLB zero-shot seeds (`verified=false`), auto-QC filtered.
- **Not human gold.** Do not treat outputs as officially verified.

## Languages

| Role | Language | NLLB code |
|------|----------|-----------|
| Source | English | `eng_Latn` |
| Target | {{TARGET_NAME}} | `{{TARGET_NLLB}}` |

## How to use

```python
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

repo = "{{REPO_ID}}"
tok = AutoTokenizer.from_pretrained(repo)
model = AutoModelForSeq2SeqLM.from_pretrained(repo)
tok.src_lang = "eng_Latn"
text = "The public is advised to follow official health guidelines."
inputs = tok(text, return_tensors="pt")
bos = tok.convert_tokens_to_ids("{{TARGET_NLLB}}")
out = model.generate(**inputs, forced_bos_token_id=bos, max_new_tokens=128)
print(tok.decode(out[0], skip_special_tokens=True))
```

Or via the LughaLink FastAPI Space / local API (`POST /translate`).

## Training summary

- Base: `facebook/nllb-200-distilled-600M`
- Epochs: 1 (PSA silver bitext)
- Platform: Navon / Kinesis A100
- Report: https://github.com/unimart831-ai/lughalinkai/blob/main/DOCS/MODELLING_AND_TRAINING_REPORT.md

## Limitations

- Silver-trained; may copy teacher errors.
- Limited domain outside PSA / public-notice style.
- Cultural appropriateness needs human review.
