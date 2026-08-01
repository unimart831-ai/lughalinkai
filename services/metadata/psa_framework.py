"""PSA Framework decision-tree classifier (DOCS/PSA FRAMEWORK.pdf).

Labels:
  - psa — public told to act / avoid / be alert (direct, instructive)
  - press_release — government activity/event for media coverage
  - other_gov_comm — legal/admin (tenders, gazette, appointments)
  - not_psa — misc / weak / not matching the three buckets
"""

from __future__ import annotations

import re
from typing import Any

# Step 1 / 2 — PSA action & style cues (framework keywords)
PSA_ACTION = re.compile(
    r"\b("
    r"advise|advised|urges?|urged|warns?|warned|reminds?|reminded|"
    r"alert|caution|avoid|do not|don't|must|shall|prohibited|required|"
    r"register (to|for|by)|verify|report (to|any|immediately)|evacuate|"
    r"boil water|wash (your )?hands|vaccinat|immuni|deadline|"
    r"members of the public|general public|all kenyans|"
    r"public is (hereby )?informed|public (is )?advised|"
    r"citizens? are (advised|reminded|requested)|"
    r"the commission (reminds|urges|advises|informs)|"
    r"are requested to|is requested to|take (immediate )?action|"
    r"stay (indoors|away|alert)|keep (off|away)|"
    r"polling stations? will be open|present your (original )?national identity"
    r")\b",
    re.I,
)

# Press release / media narrative cues
PRESS_RELEASE = re.compile(
    r"\b("
    r"launched|inaugurated|announced|announces|"
    r"statement by the (cabinet secretary|cs|principal secretary)|"
    r"official visit|media invited|press (conference|briefing)|"
    r"signed an? (mou|memorandum)|explore (partnership|cooperation)|"
    r"hosts? .{0,40}(for talks|stakeholders|delegation)|"
    r"capacity-?building|breakfast meeting|"
    r"strengthen (collaboration|partnership)|"
    r"was (held|attended|presided)|in a speech|"
    r"the (cabinet secretary|principal secretary) (said|noted|stated)|"
    r"according to|he said|she said"
    r")\b",
    re.I,
)

# Other government / legal-admin cues
OTHER_GOV = re.compile(
    r"\b("
    r"it is notified for the general information|"
    r"pursuant to|in exercise of the powers|"
    r"gazette notice|kenya gazette|"
    r"tender\s*(no\.?|number)|invitation to tender|"
    r"appointment of|appoints? .{0,40}as |"
    r"vacancy|vacancies|job advertisement|"
    r"bill (no\.?|of)|act (no\.?|of)|subsidiary legislation|"
    r"public procurement|expression of interest|"
    r"board of directors|commissioners? (are|is) hereby"
    r")\b",
    re.I,
)

# Soft length band from framework: PSA = short/direct
SHORT_MAX = 180
LONG_NARRATIVE = 280


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def classify_psa_framework(text: str, title: str = "") -> dict[str, Any]:
    """Apply the 4-step PSA Framework decision tree.

    Returns label, confidence, matched cues, and a short reason.
    """
    body = _norm(text)
    head = _norm(title)
    combined = f"{head}. {body}".strip(". ")
    tokens = len(body.split()) if body else 0

    action_hits = len(PSA_ACTION.findall(combined))
    press_hits = len(PRESS_RELEASE.findall(combined))
    other_hits = len(OTHER_GOV.findall(combined))

    has_action = action_hits > 0
    has_press = press_hits > 0
    has_other = other_hits > 0

    # Step 1 decision tree (framework order)
    if has_action and not (has_press and press_hits >= action_hits + 2 and tokens > LONG_NARRATIVE):
        # Prefer PSA when clear public instruction is present.
        # Downgrade long quote-heavy narratives even with a weak "urged".
        quote_heavy = combined.count('"') >= 4 or re.search(
            r"\b(he said|she said|according to)\b", combined, re.I
        )
        if quote_heavy and action_hits <= 1 and tokens > LONG_NARRATIVE:
            label = "press_release"
            reason = "narrative_media_coverage_over_weak_action"
            conf = 0.55
        elif tokens > LONG_NARRATIVE and action_hits <= 1 and press_hits >= 2:
            label = "press_release"
            reason = "long_press_style_with_weak_psa_cue"
            conf = 0.6
        else:
            label = "psa"
            reason = "public_action_advisory_or_alert"
            # Shorter + more action cues → higher confidence
            conf = 0.55 + min(0.35, action_hits * 0.08)
            if tokens <= SHORT_MAX:
                conf += 0.08
            if tokens > LONG_NARRATIVE:
                conf -= 0.12
    elif has_press:
        label = "press_release"
        reason = "government_activity_or_media_narrative"
        conf = 0.5 + min(0.3, press_hits * 0.07)
    elif has_other:
        label = "other_gov_comm"
        reason = "legal_admin_tender_or_gazette_style"
        conf = 0.55 + min(0.25, other_hits * 0.08)
    else:
        label = "not_psa"
        reason = "no_framework_intent_match"
        conf = 0.2

    # Length sanity for PSA label
    if label == "psa" and tokens < 8:
        label = "not_psa"
        reason = "too_short_for_psa"
        conf = 0.15
    if label == "psa" and tokens > 400:
        # Framework: PSAs are short; very long bodies are rarely true PSAs
        label = "not_psa"
        reason = "too_long_for_framework_psa"
        conf = 0.35

    conf = max(0.0, min(1.0, round(conf, 3)))
    return {
        "framework_label": label,
        "framework_confidence": conf,
        "framework_reason": reason,
        "action_hits": action_hits,
        "press_hits": press_hits,
        "other_hits": other_hits,
        "token_count": tokens,
        "is_strict_psa": label == "psa" and conf >= 0.55,
    }
