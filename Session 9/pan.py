"""Day 9: PAN (card number) redaction: keep the agent stack out of PCI DSS scope.

No API key needed:  python pan.py
"""
import re

_PAN = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for c in reversed(digits):
        n = int(c)
        if alt:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total, alt = total + n, not alt
    return total % 10 == 0


def redact_pan(text: str) -> str:
    """Mask card numbers (13-19 digits passing Luhn), keeping the last 4."""
    def mask(m):
        digits = re.sub(r"\D", "", m.group())
        return f"[PAN ****{digits[-4:]}]" if 13 <= len(digits) <= 19 and luhn_ok(digits) else m.group()
    return _PAN.sub(mask, text)


if __name__ == "__main__":
    sample = "Card 4111 1111 1111 1111 was charged; order 1234567890123 (not a card); amex 378282246310005."
    print(redact_pan(sample))
    assert "4111 1111" not in redact_pan(sample) and "1234567890123" in redact_pan(sample)
    print("ok")