"""Turning messy free text into keys we can match on."""

import re


def pos_key(value):
    """Reduce a POS name to lowercase letters only.

    Dropping case and punctuation collapses them: "Salt Box", "SALTBOX" and "saltbox" all
    become "saltbox".
    """
    return "".join(c for c in str(value).lower() if c.isalpha())


def phone_key(value):
    """Reduce a phone number to its 10 digits, or None if it isn't one.

    One restaurant shows up as "(555) 173-3531", "555.173.3531" and
    "+1-555-173-3531". The digits are what let the three systems join.
    """
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else None


FILLER = (r"\bthe\b", r"\band\b", r"\brestaurant\b", r"\bverano bay\b")
# FILLER = (r"\bthe\b", r"\band\b", r"\brestaurant\b")


def name_key(value):
    """Reduce a restaurant name to a comparable slug.

    Platforms decorate the same name: "Basil & Bone Grill - Palisade Park",
    "Basil and Bone Grill", "The Basil & Bone Grill". Drop the branch suffix
    after the dash, the filler words, then the punctuation.
    """
    text = str(value).lower().split(" - ")[0]
    for filler in FILLER:
        text = re.sub(filler, " ", text)
    return re.sub(r"[^a-z0-9]", "", text)
