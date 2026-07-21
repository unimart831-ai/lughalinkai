from services.metadata.classifier import classify_psa


def test_psa_positive():
    is_psa, score = classify_psa(
        "Ministry of Health advises public",
        "Avoid unnecessary travel to Ebola hotspots. Report symptoms immediately.",
    )
    assert is_psa is True
    assert score >= 0.55


def test_psa_iebc_public_notice():
    is_psa, score = classify_psa(
        "PUBLIC NOTICE",
        "The Commission reminds all voters that taking photographs of marked ballot papers "
        "inside the polling booth is strictly prohibited. The Commission urges all voters to comply.",
    )
    assert is_psa is True
    assert score >= 0.55


def test_psa_negative():
    is_psa, score = classify_psa(
        "Match Report: Gor Mahia wins",
        "The team scored two goals in the second half according to experts.",
    )
    assert is_psa is False


def test_cleaning_pipeline():
    from services.preprocessing.cleaning import clean_raw_content

    result = clean_raw_content("Ministry urges public to register by Friday.")
    assert result["token_count"] >= 5
    assert "register" in result["text"].lower()
