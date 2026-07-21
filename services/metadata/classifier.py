from __future__ import annotations

import re

PSA_POSITIVE_PATTERNS = [
    r"\b(advises|advised|urges|encourages|reminds|warns|alert|caution)\b",
    r"\b(avoid|register|report|vaccinate|boil|evacuate|verify|apply by)\b",
    r"\b(deadline|before|by \d|within \d+\s*(hours|days))\b",
    r"\b(ministry of|iebc|ndma|nps|helb|kuccps|who|unicef|huduma|eacc)\b",
    r"\b(public (is )?advised|members of the public|public notice)\b",
    r"\b(voter|voting|polling|ballot|by-?election|voter registration)\b",
    r"\b(the commission (reminds|urges|advises|informs))\b",
    r"\b(clarification|accreditation|service delivery|huduma (centre|center))\b",
    r"\b(anti-?corruption|report corruption|integrity|accountability|good governance)\b",
    r"\b(fight against corruption|safeguarding|public resources|transparency)\b",
]

PSA_NEGATIVE_PATTERNS = [
    r"\b(opinion|commentary|analysis|experts say|match report|celebrity)\b",
    r"\b(score|goal|premier league|entertainment|gossip)\b",
]

AUTHORITY_PREFIX = re.compile(
    r"^(ministry of|iebc|ndma|nps|helb|kuccps|who|unicef|huduma|eacc|public notice|clarification|aaaca)",
    re.I,
)


def classify_psa(title: str, text: str) -> tuple[bool, float]:
    combined = f"{title}\n{text}".lower()
    score = 0.0

    for pattern in PSA_POSITIVE_PATTERNS:
        if re.search(pattern, combined, re.I):
            score += 0.15

    for pattern in PSA_NEGATIVE_PATTERNS:
        if re.search(pattern, combined, re.I):
            score -= 0.2

    if AUTHORITY_PREFIX.match(title.strip()):
        score += 0.2

    imperative_count = len(
        re.findall(r"\b(avoid|must|shall|do not|don't|ensure|prohibited)\b", combined)
    )
    score += min(imperative_count * 0.05, 0.2)

    token_len = len(text.split())
    if token_len > 800:
        score -= 0.25
    elif token_len > 500:
        score -= 0.1
    elif 15 <= token_len <= 300:
        score += 0.1

    score = max(0.0, min(1.0, score))
    is_psa = score >= 0.5
    return is_psa, round(score, 3)
