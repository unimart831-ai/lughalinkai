# Human Evaluation Guide — LughaLink PSA MT

**Audience:** Kiswahili and/or Kikuyu reviewers  
**Sheet:** `datasets/gold/human_eval_100.csv`  
**When:** After automatic metrics; scores can be filled later without blocking the demo.

## What you are scoring

Each row is an **English Public Service Announcement** sentence. Optional machine suggestions (`mt_suggestion_sw` / `mt_suggestion_kik`) may be present — treat them as drafts, not truth.

Score **separately** for Kiswahili (`*_sw`) and Kikuyu (`*_kik`) on a **1–5** scale:

| Score | Fluency | Adequacy | Cultural accuracy |
|------:|---------|----------|-------------------|
| 5 | Natural, native-like | Full meaning preserved | Terms/register fit Kenyan public messaging |
| 4 | Minor awkwardness | Small omission/addition | Mostly appropriate |
| 3 | Understandable but stiff | Partial meaning | Some odd wording |
| 2 | Hard to read | Major meaning loss | Inappropriate or confusing |
| 1 | Broken / wrong language | Meaning wrong or empty | Offensive or misleading |

## How to fill the sheet

1. Open `datasets/gold/human_eval_100.csv` in Excel/Google Sheets.
2. Enter your `reviewer_id` (name or initials) on each row you score.
3. If the machine suggestion is wrong, write a corrected translation in `preferred_sw_edit` / `preferred_kik_edit`.
4. Use `notes` for names, numbers, legal terms, or uncertainty.
5. Prefer scoring rows with `synthetic_source=false` first (real scraped PSAs).

## Rules

- Do **not** mark machine output as gold unless you fully accept or edit it.
- Keep directive PSA tone (advise / warn / instruct), not casual chat.
- Leave blank any language you do not speak; do not guess.

## After review

Return the filled CSV to the team. We will set `verified=true` only for human-accepted/edited pairs in a separate gold file — never silently overwrite silver training data.
