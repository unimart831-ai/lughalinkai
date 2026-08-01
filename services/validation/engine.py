from __future__ import annotations

from services.models import PSARecord, ValidationResult


def validate_psa(record: PSARecord) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not record.text.strip():
        errors.append("empty_text")
    if record.token_count < 10:
        errors.append("too_short")
    elif record.token_count > 500:
        warnings.append("too_long")
    if not record.is_psa:
        errors.append("not_classified_as_psa")
    if not record.source_url:
        errors.append("missing_source_url")
    if record.trust_score < 50:
        warnings.append("low_trust_source")
    if not record.published_at:
        warnings.append("missing_publish_date")
    if record.language not in {"en", "sw", "kik", "ki", "luo", "guz", "som"}:
        warnings.append(f"unexpected_language:{record.language}")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
