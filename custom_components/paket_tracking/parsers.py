from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .const import STATUS_HEUTE, STATUS_OFFEN, STATUS_UNTERWEGS, STATUS_ZUGESTELLT

_QUOTE_RE = re.compile(r"„([^“]+)“")
_WEITERE_RE = re.compile(r"und\s+(\d+)\s+weitere[rn]?\s+Artikel", re.IGNORECASE)
_BESTELLNR_RE = re.compile(r"Bestellnr\.[^\d]*([\d][\d\-]{8,})")
_ZUSTELLUNG_RE = re.compile(r"Zustellung:\s*([A-Za-zÄÖÜäöüß.,0-9 ]+?)(?:\n|\r|$)")

_DHL_TRACKING_RE = re.compile(r"\b\d{10,20}\b")
_UPS_TRACKING_RE = re.compile(r"\b1Z[0-9A-Z]{16}\b")
_HERMES_TRACKING_RE = re.compile(r"\b\d{14,20}\b")


@dataclass
class ParsedEmail:
    carrier: str
    status: str
    key: str
    description: str | None = None
    expected: str | None = None


def _hash_key(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8", "ignore")).hexdigest()[:16]


def _amazon_description(subject: str) -> str | None:
    m = _QUOTE_RE.search(subject)
    if not m:
        return None
    desc = m.group(1).strip()
    extra = _WEITERE_RE.search(subject)
    if extra:
        desc += f" (+{extra.group(1)} weitere)"
    return desc


def parse_amazon(sender: str, subject: str, text: str) -> ParsedEmail | None:
    sender = sender.lower()
    if "amazon.de" not in sender and "amazon.com" not in sender:
        return None

    if "bestellbestaetigung@amazon" in sender:
        status = STATUS_OFFEN
    elif "versandbestaetigung@amazon" in sender:
        status = STATUS_UNTERWEGS
    elif "shipment-tracking@amazon" in sender or "order-update@amazon" in sender:
        if subject.startswith("Zugestellt"):
            status = STATUS_ZUGESTELLT
        elif subject.startswith("In Zustellung") or subject.startswith("Heute"):
            status = STATUS_HEUTE
        elif subject.startswith("Unterwegs") or subject.startswith("Versandt") or "Versendet" in subject:
            status = STATUS_UNTERWEGS
        else:
            return None
    else:
        return None

    order_match = _BESTELLNR_RE.search(text or "")
    order_number = order_match.group(1) if order_match else None
    description = _amazon_description(subject)

    if order_number:
        # Order number is stable across all emails for the same order (confirmation,
        # shipped, out-for-delivery, delivered), so it alone is the dedup key. This
        # means a multi-shipment order collapses into one tracked entry - accepted
        # trade-off, flagged to Simon rather than hidden.
        key = f"amazon:{order_number}"
    else:
        key_desc = (description or subject).strip().lower()
        key = f"amazon:unbekannt:{_hash_key(key_desc)}"

    expected_match = _ZUSTELLUNG_RE.search(text or "")
    expected = expected_match.group(1).strip() if expected_match else None

    return ParsedEmail(
        carrier="Amazon",
        status=status,
        key=key,
        description=description,
        expected=expected,
    )


def parse_dhl(sender: str, subject: str, text: str) -> ParsedEmail | None:
    sender = sender.lower()
    if "dhl.de" not in sender and "deutschepost.de" not in sender:
        return None

    subject_l = subject.lower()
    if "zugestellt" in subject_l:
        status = STATUS_ZUGESTELLT
    elif "heute zugestellt" in subject_l or "wird heute" in subject_l:
        status = STATUS_HEUTE
    elif "unterwegs" in subject_l or "versandt" in subject_l or "versendet" in subject_l:
        status = STATUS_UNTERWEGS
    else:
        return None

    tracking_match = _DHL_TRACKING_RE.search(subject) or _DHL_TRACKING_RE.search(text or "")
    key = f"dhl:{tracking_match.group(0)}" if tracking_match else f"dhl:{_hash_key(sender, subject)}"

    return ParsedEmail(carrier="DHL", status=status, key=key)


def parse_ups(sender: str, subject: str, text: str) -> ParsedEmail | None:
    sender = sender.lower()
    if "ups.com" not in sender:
        return None

    subject_l = subject.lower()
    if "delivery notification" in subject_l or "wurde zugestellt" in subject_l or subject_l.strip().startswith("zugestellt"):
        status = STATUS_ZUGESTELLT
    elif "delivered today" in subject_l or "wird heute" in subject_l or "heute zugestellt" in subject_l:
        status = STATUS_HEUTE
    elif "ship notification" in subject_l or "unterwegs" in subject_l or "versandt" in subject_l:
        status = STATUS_UNTERWEGS
    else:
        return None

    tracking_match = _UPS_TRACKING_RE.search(subject) or _UPS_TRACKING_RE.search(text or "")
    key = f"ups:{tracking_match.group(0)}" if tracking_match else f"ups:{_hash_key(sender, subject)}"

    return ParsedEmail(carrier="UPS", status=status, key=key)


def parse_hermes(sender: str, subject: str, text: str) -> ParsedEmail | None:
    sender = sender.lower()
    if not any(d in sender for d in ("hermesworld.com", "myhermes.de", "evri.com")):
        return None

    subject_l = subject.lower()
    if "wurde zugestellt" in subject_l or subject_l.strip().startswith("zugestellt"):
        status = STATUS_ZUGESTELLT
    elif "wird heute" in subject_l or "heute zugestellt" in subject_l:
        status = STATUS_HEUTE
    elif "unterwegs" in subject_l or "eingeliefert" in subject_l or "auf dem weg" in subject_l:
        status = STATUS_UNTERWEGS
    else:
        return None

    tracking_match = _HERMES_TRACKING_RE.search(subject) or _HERMES_TRACKING_RE.search(text or "")
    key = f"hermes:{tracking_match.group(0)}" if tracking_match else f"hermes:{_hash_key(sender, subject)}"

    return ParsedEmail(carrier="Hermes", status=status, key=key)


PARSERS = (parse_amazon, parse_dhl, parse_ups, parse_hermes)


def parse_email(sender: str, subject: str, text: str) -> ParsedEmail | None:
    for parser in PARSERS:
        result = parser(sender or "", subject or "", text or "")
        if result is not None:
            return result
    return None
