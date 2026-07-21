from __future__ import annotations

import re

PSA_POSITIVE_PATTERNS = [
    r"\b(advises|advised|urges|encourages|reminds|warns|alert|caution)\b",
    r"\b(avoid|register|report|vaccinate|boil|evacuate|verify|apply by|file|filing)\b",
    r"\b(deadline|before|by \d|within \d+\s*(hours|days)|due date)\b",
    r"\b(ministry of|iebc|ndma|nps|helb|kuccps|who|unicef|huduma|eacc|kra|treasury|knec|nema|ntsa|meteo)\b",
    r"\b(public (is )?advised|members of the public|public notice|press release)\b",
    r"\b(voter|voting|polling|ballot|by-?election|voter registration)\b",
    r"\b(the commission (reminds|urges|advises|informs))\b",
    r"\b(clarification|accreditation|service delivery|huduma (centre|center))\b",
    r"\b(anti-?corruption|report corruption|integrity|accountability|good governance)\b",
    r"\b(fight against corruption|safeguarding|public resources|transparency)\b",
    r"\b(taxpayer|tax returns|excise|vat|customs|compliance|communications authority)\b",
    r"\b(government|president|cabinet|national assembly|senate|public service)\b",
    # health / education / security / agriculture
    r"\b(outbreak|immunization|vaccine|mpox|cholera|malaria|hiv|tb|maternal|nutrition|hospital|clinic|sha|nhif)\b",
    r"\b(school|learner|student|exam|kcse|kcpe|scholarship|bursary|enrollment|capitation|tvet)\b",
    r"\b(flood|drought|disaster|evacuation|road safety|police|crime|cyber|scam|phishing)\b",
    r"\b(farmer|crop|livestock|fertilizer|harvest|irrigation|pest|agriculture)\b",
    r"\b(weather forecast|advisory|early warning|bulletin|red cross|relief)\b",
]

PSA_NEGATIVE_PATTERNS = [
    r"\b(match report|celebrity|premier league|gossip|rumour)\b",
]

AUTHORITY_PREFIX = re.compile(
    r"^(ministry of|iebc|ndma|nps|helb|kuccps|who|unicef|huduma|eacc|kra|public notice|"
    r"clarification|aaaca|press release|president|ca\b|knec|nema|kenya red cross|fao)",
    re.I,
)


def classify_psa(title: str, text: str) -> tuple[bool, float]:
    combined = f"{title}\n{text}".lower()
    score = 0.0

    for pattern in PSA_POSITIVE_PATTERNS:
        if re.search(pattern, combined, re.I):
            score += 0.12

    for pattern in PSA_NEGATIVE_PATTERNS:
        if re.search(pattern, combined, re.I):
            score -= 0.25

    if AUTHORITY_PREFIX.match(title.strip()):
        score += 0.2

    if re.search(
        r"\b(kenya revenue authority|communications authority|ethics and anti-corruption|"
        r"independent electoral|ministry of health|ministry of education|kenya meteorological|"
        r"national drought|kenya red cross|world health organization|unicef|knec|nema)\b",
        combined,
    ):
        score += 0.15

    imperative_count = len(
        re.findall(r"\b(avoid|must|shall|do not|don't|ensure|prohibited|required|deadline)\b", combined)
    )
    score += min(imperative_count * 0.05, 0.2)

    token_len = len(text.split())
    if token_len > 1000:
        score -= 0.15
    elif token_len < 12:
        score -= 0.2
    elif 15 <= token_len <= 400:
        score += 0.1

    score = max(0.0, min(1.0, score))
    is_psa = score >= 0.28
    return is_psa, round(score, 3)
