"""Unit tests for NLLB helper validation (no GPU / no weights)."""

import pytest

from services.translation.nllb_infer import NLLB_CODES, translate_nllb


def test_nllb_codes():
    assert NLLB_CODES["sw"] == "swh_Latn"
    assert NLLB_CODES["kik"] == "kik_Latn"


def test_translate_rejects_bad_target():
    with pytest.raises(ValueError):
        translate_nllb(None, None, "cpu", "hello", "xx")
