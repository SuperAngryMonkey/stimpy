"""
Payment handling for Stimpy (ADR 0004).

Three payment types:

  Cash        — pay at pickup / pay the driver. The default, and the only
                type that needs no secrets (ADR 0002 behaviour).
  CreditCard  — card held ONLY in payment_local.py (gitignored, mode 0600,
                written by set_payment.py). Never accepted from a request,
                never logged, never returned.
  GiftCard    — Domino's gift card number + PIN, same file, same rules.
                Recommended over a real card: loss is capped at the balance.

The card is read at order time, attached to the order's Payments block,
and the Domino's response has that block scrubbed before anything is
logged or returned. The number itself only ever exists in payment_local.py
and in the single HTTPS POST to Domino's.
"""
import re

CASH, CARD, GIFTCARD = "Cash", "CreditCard", "GiftCard"
TYPES = {"cash": CASH, "card": CARD, "creditcard": CARD, "giftcard": GIFTCARD, "gift": GIFTCARD}

_CARD_PATTERNS = {
    "VISA": r"^4[0-9]{12}(?:[0-9]{3})?$",
    "MASTERCARD": r"^(?:5[1-5][0-9]{14}|2(?:2[2-9][0-9]|[3-6][0-9]{2}|7[01][0-9]|720)[0-9]{12})$",
    "AMEX": r"^3[47][0-9]{13}$",
    "DISCOVER": r"^6(?:011|5[0-9]{2})[0-9]{12}$",
}


class PaymentError(Exception):
    """Raised when a payment type is requested but not usable."""


def normalize(name):
    """Map a user-facing pay mode ('cash', 'card', 'giftcard') to a type."""
    t = TYPES.get(str(name or "cash").strip().lower())
    if not t:
        raise PaymentError(f"unknown pay mode '{name}' (use cash, card or giftcard)")
    return t


def luhn_ok(number):
    digits = [int(c) for c in number]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def card_type(number):
    return next((t for t, p in _CARD_PATTERNS.items() if re.match(p, number)), "")


def validate_card(number, expiration, cvv, zip_code):
    """Return (ok, problems) for a credit card. Never includes the number."""
    problems = []
    if not re.match(r"^[0-9]{13,19}$", number or ""):
        problems.append("card number must be 13-19 digits")
    elif not luhn_ok(number):
        problems.append("card number fails checksum (typo?)")
    elif not card_type(number):
        problems.append("card type not recognised (Visa/MC/Amex/Discover)")
    if not re.match(r"^(0[1-9]|1[0-2])[0-9]{2}$", expiration or ""):
        problems.append("expiration must be MMYY")
    if not re.match(r"^[0-9]{3,4}$", cvv or ""):
        problems.append("CVV must be 3 or 4 digits")
    if not re.match(r"^[0-9]{5}(?:-[0-9]{4})?$", zip_code or ""):
        problems.append("billing ZIP must be 5 digits")
    return (not problems), problems


def _secrets():
    """Load payment_local.py lazily. Absent file == cash only."""
    try:
        import payment_local as p  # noqa: WPS433
    except ImportError:
        return None
    return p


def configured_type():
    """The default payment type from payment_local.py, or Cash."""
    p = _secrets()
    return normalize(getattr(p, "PAYMENT_TYPE", "cash")) if p else CASH


def tip_amount():
    p = _secrets()
    try:
        return round(float(getattr(p, "DELIVERY_TIP", 0) or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def describe(ptype):
    """Human label that is safe to log/return. Last 4 only."""
    p = _secrets()
    if ptype == CASH:
        return "cash"
    if ptype == CARD:
        n = getattr(p, "CARD_NUMBER", "") if p else ""
        return f"{card_type(n).title() or 'card'} ending {n[-4:]}" if n else "card (not configured)"
    n = getattr(p, "GIFTCARD_NUMBER", "") if p else ""
    return f"gift card ending {n[-4:]}" if n else "gift card (not configured)"


def build_payment(ptype, amount, delivery=False):
    """Return the Domino's Payments[] entry for the given type.

    `amount` is the priced Order.Amounts.Customer value. The tip is added
    on top for delivery only.
    """
    ptype = normalize(ptype)
    if ptype == CASH:
        return {"Type": CASH}

    p = _secrets()
    if p is None:
        raise PaymentError(
            f"{ptype} requested but payment_local.py does not exist. "
            "Run set_payment.py on the stimpy host first."
        )
    tip = tip_amount() if delivery else 0.0
    base = {"Amount": float(amount), "TipAmount": tip}

    if ptype == CARD:
        number = str(getattr(p, "CARD_NUMBER", "")).replace(" ", "")
        exp = str(getattr(p, "CARD_EXPIRATION", ""))
        cvv = str(getattr(p, "CARD_CVV", ""))
        zip_code = str(getattr(p, "CARD_ZIP", ""))
        ok, problems = validate_card(number, exp, cvv, zip_code)
        if not ok:
            raise PaymentError("card in payment_local.py is invalid: " + "; ".join(problems))
        return {
            "Type": CARD,
            "CardType": card_type(number),
            "Number": number,
            "Expiration": exp,
            "SecurityCode": cvv,
            "PostalCode": zip_code,
            **base,
        }

    number = str(getattr(p, "GIFTCARD_NUMBER", "")).replace(" ", "")
    pin = str(getattr(p, "GIFTCARD_PIN", ""))
    if not (number.isdigit() and pin.isdigit()):
        raise PaymentError("gift card number/PIN missing or non-numeric in payment_local.py")
    return {"Type": GIFTCARD, "Number": number, "Pin": pin, **base}


_SCRUB_KEYS = {"Number", "SecurityCode", "Pin", "Expiration", "PostalCode", "CardType"}


def scrub(obj):
    """Recursively strip card fields from any Domino's response/order dict
    before it is logged, stored or returned."""
    if isinstance(obj, dict):
        return {
            k: ("***" if k in _SCRUB_KEYS else scrub(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj
