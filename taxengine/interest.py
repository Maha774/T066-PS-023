"""Interest for late / short payment of advance tax: sections 234B and 234C."""
from .constants import (ADVANCE_SCHEDULE, AY_START, INTEREST_MIN_NET_TAX, INTEREST_RATE)
from .util import ZERO


def months_for_234b(filing_date) -> int:
    """1 April 2026 up to the filing month; a part of a month counts as a full month."""
    if filing_date < AY_START:
        return 0
    return (filing_date.year - AY_START.year) * 12 + filing_date.month - AY_START.month + 1


def compute_interest(net_tax_after_tds, advance_payments, filing_date):
    """BR-34 / BR-35. Returns (interest_234b, interest_234c, rule_ids).
    Nothing is charged unless the tax left after TDS is above Rs 10,000."""
    if net_tax_after_tds <= INTEREST_MIN_NET_TAX:
        return ZERO, ZERO, set()
    rules = set()
    paid_total = sum((p.amount for p in advance_payments), ZERO)

    shortfall = net_tax_after_tds - paid_total
    i234b = ZERO
    if shortfall > 0:
        i234b = shortfall * INTEREST_RATE * months_for_234b(filing_date)
        if i234b > 0:
            rules.add("BR-34")

    i234c = ZERO
    for due, pct in ADVANCE_SCHEDULE:
        paid_by_due = sum((p.amount for p in advance_payments if p.payment_date <= due), ZERO)
        short = max(ZERO, net_tax_after_tds * pct - paid_by_due)
        i234c += short * INTEREST_RATE          # 1% per quarter / instalment (as the brief says)
    if i234c > 0:
        rules.add("BR-35")
    return i234b, i234c, rules
