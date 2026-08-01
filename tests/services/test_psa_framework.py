from services.metadata.psa_framework import classify_psa_framework


def test_framework_labels_true_psa():
    text = (
        "IEBC reminds all voters that photographing marked ballot papers inside "
        "the polling booth is strictly prohibited. The public is advised to comply."
    )
    r = classify_psa_framework(text, title="PUBLIC NOTICE")
    assert r["framework_label"] == "psa"
    assert r["is_strict_psa"] is True


def test_framework_labels_press_release():
    text = (
        "The Cabinet Secretary launched a new digital platform during an official visit. "
        "In a speech he said the ministry signed an MoU to strengthen collaboration "
        "and media invited stakeholders attended the breakfast meeting."
    )
    r = classify_psa_framework(text)
    assert r["framework_label"] == "press_release"


def test_framework_labels_other_gov():
    text = (
        "It is notified for the general information that pursuant to the Act, "
        "Tender No. KRA/001/2026 for supply of goods is hereby advertised. "
        "Gazette Notice applies."
    )
    r = classify_psa_framework(text)
    assert r["framework_label"] == "other_gov_comm"
