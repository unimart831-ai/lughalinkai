from services.translation.sentences import split_sentences
from services.translation.silver_qc import auto_qc_pair, is_near_copy


def test_split_sentences_basic():
    text = (
        "The Ministry of Health urges the public to wash hands regularly. "
        "Avoid crowded places during the outbreak. Visit your nearest clinic."
    )
    sents = split_sentences(text, min_tokens=4, max_tokens=40)
    assert len(sents) >= 2
    assert all(len(s.split()) >= 4 for s in sents)


def test_auto_qc_rejects_dry_run():
    qc = auto_qc_pair("Register to vote before Friday.", "[DRY_RUN swh_Latn] Register")
    assert qc["auto_qc_pass"] is False
    assert "tgt_missing_or_dry_run" in qc["auto_qc_reasons"]


def test_auto_qc_accepts_plausible_pair():
    qc = auto_qc_pair(
        "Please register to vote before Friday at your local IEBC office.",
        "Tafadhali jisajili kupiga kura kabla ya Ijumaa katika ofisi yako ya IEBC.",
    )
    assert qc["auto_qc_pass"] is True
    assert qc["glossary_preservation"] >= 0.5


def test_near_copy():
    assert is_near_copy("Avoid unnecessary travel now", "Avoid unnecessary travel now")
