# Synthetic PSA augmentation

**Why:** Strict framework filtering left **1,615** real PSAs. Scraping more sites was slow and low-yield. To reach the course volume target (~5,000) we generated additional **framework-valid** PSA texts from the same action/advisory patterns.

**How:** `python scripts/generate_synthetic_psas.py --target-total 5000`

**Honesty rules**
- Metadata includes `"synthetic": true`, `"method": "synthetic_template"`
- Never mark synthetic rows `verified=true`
- Report real vs synthetic counts separately in Week 2 / final reports
- Prefer real rows for human evaluation samples when reviewers exist

**Current mix**
| Origin | Rows |
|--------|-----:|
| Real (scraped + framework-strict) | 1,615 |
| Synthetic (template, framework-filtered) | 3,385 |
| **Total** | **5,000** |
