"""Salary head: gross, HRA exemption (month by month), standard deduction, professional tax."""
from dataclasses import dataclass

from .constants import (HRA_PCT_OF_BASIC, HRA_RENT_BASIC_PCT, PT_CAP, STD_DEDUCTION)
from .util import ZERO


@dataclass
class SalaryResult:
    gross: object = ZERO
    basic_total: object = ZERO
    employer_nps: object = ZERO
    hra_exemption: object = ZERO
    standard_deduction: object = ZERO
    professional_tax: object = ZERO
    income: object = ZERO


def monthly_hra_exemption(line) -> object:
    """BR-07/BR-08: min(HRA, rent - 10% basic, 50%/40% basic); never below 0; 0 if no rent."""
    if line.rent_paid_pm <= 0:
        return ZERO
    limit = min(line.hra_pm,
                line.rent_paid_pm - HRA_RENT_BASIC_PCT * line.basic_pm,
                HRA_PCT_OF_BASIC[line.metro_city] * line.basic_pm)
    return max(ZERO, limit)


def compute_salary(lines, regime) -> SalaryResult:
    r = SalaryResult()
    pt_total = ZERO
    for ln in lines:
        r.gross += ln.months * (ln.basic_pm + ln.hra_pm + ln.special_pm + ln.lta_pm
                                + ln.employer_nps_pm)
        r.basic_total += ln.months * ln.basic_pm
        r.employer_nps += ln.months * ln.employer_nps_pm
        pt_total += ln.months * ln.professional_tax_pm
        if regime == "OLD":
            r.hra_exemption += ln.months * monthly_hra_exemption(ln)
    if not lines:
        return r
    after_hra = r.gross - r.hra_exemption
    r.standard_deduction = min(STD_DEDUCTION[regime], max(ZERO, after_hra))  # BR-05
    if regime == "OLD":
        r.professional_tax = min(pt_total, PT_CAP, max(ZERO, after_hra - r.standard_deduction))  # BR-06
    r.income = max(ZERO, after_hra - r.standard_deduction - r.professional_tax)
    return r
