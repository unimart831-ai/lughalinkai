# PSA Framework Audit

**Framework:** `DOCS/PSA FRAMEWORK.pdf`  
**Script:** `python scripts/audit_psa_framework.py --also-gate`

## Decision labels

| Label | Meaning (from framework) |
|-------|--------------------------|
| `psa` | Public told to act / avoid / be alert — direct, instructive |
| `press_release` | Government activity/event for media |
| `other_gov_comm` | Legal/admin (tenders, gazette, appointments) |
| `not_psa` | No clear framework intent |

## Latest freeze result

| Metric | Value |
|--------|------:|
| Input rows (`week2_ready` before clean) | 4,152 |
| Framework `psa` labels | 1,822 |
| **Strict kept** (PSA + conf≥0.55 + legacy gate) | **1,615** |
| Quarantined | 2,537 |
| Keep rate | 38.9% |
| Verdict | **poor_needs_clean** → cleaned |

### Strict keep by domain

| Domain | Kept |
|--------|-----:|
| Governance | 953 |
| Health | 252 |
| Security | 233 |
| Education | 135 |
| Agriculture | 42 |

## Canonical files now

| File | Role |
|------|------|
| `datasets/processed/week2_strict_psas.csv` | Framework-strict PSAs |
| `datasets/processed/week2_ready_psas.csv` | **Updated freeze** (= strict, **1,615** rows) |
| `datasets/processed/week2_ready_psas_pre_framework.csv` | Backup of pre-audit freeze (4,152) |
| `datasets/processed/week2_framework_quarantine.csv` | Rejected non-PSAs |
| `datasets/interim/psa_framework_audit.csv` | Full row-level scores |
| `datasets/interim/week2_mt_sentences.csv` | Regenerated PSA sentences (**235**) for MT seed |

## Reproduce

```bash
python scripts/audit_psa_framework.py --also-gate
# optional: raise bar
python scripts/audit_psa_framework.py --also-gate --min-confidence 0.6
```
