from services.preprocessing.glossary import apply_glossary_normalization, find_glossary_hits
from services.preprocessing.normalize import normalize_psa_text, preprocess_psa_text
from services.preprocessing.splits import stratified_sample, stratified_split


def test_normalize_inserts_alnum_boundary():
    text = normalize_psa_text("PUBLIC NOTICE15th Jul 2026. Register now.")
    assert "NOTICE 15th" in text
    assert "  " not in text


def test_glossary_hits_and_alias_rewrite():
    text = apply_glossary_normalization("Avoid Mpesa scams and report to IEBC.")
    assert "M-PESA" in text
    hits = find_glossary_hits(text)
    assert "M-PESA" in hits
    assert "IEBC" in hits


def test_preprocess_token_count():
    feats = preprocess_psa_text("Ministry of Health: Avoid travel to Ebola hotspots.")
    assert feats["token_count"] >= 6
    assert feats["text_norm"]
    assert feats["lang_primary"] in ("en", "sw", None) or isinstance(feats["lang_primary"], str)


def test_stratified_split_covers_all_rows():
    rows = [{"PSA_ID": f"p{i}", "Domain": d} for i, d in enumerate(
        ["Governance"] * 40 + ["Health"] * 20 + ["Education"] * 10
    )]
    train, dev, test = stratified_split(rows, ratios=(0.8, 0.1, 0.1), seed=1)
    assert len(train) + len(dev) + len(test) == len(rows)
    assert len(train) > len(dev)
    assert {r["PSA_ID"] for r in train + dev + test} == {r["PSA_ID"] for r in rows}


def test_stratified_sample_size():
    rows = [{"PSA_ID": f"p{i}", "Domain": d} for i, d in enumerate(
        ["Governance"] * 50 + ["Health"] * 30 + ["Agriculture"] * 20
    )]
    sample = stratified_sample(rows, 25, seed=7, min_per_group=3)
    assert len(sample) == 25
    domains = {r["Domain"] for r in sample}
    assert "Agriculture" in domains
