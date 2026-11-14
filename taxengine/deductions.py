"""Chapter VI-A deductions."""
from .constants import (CAP_80C, CAP_80CCD_1B, CAP_80D_PARENTS, CAP_80D_SELF, CHECKUP_CAP,
                        NPS_EMPLOYER_PCT)
from .util import ZERO


def deduction_80c(investments):
    return min(CAP_80C, sum((i.amount for i in investments if i.section == "80C"), ZERO))


def deduction_80ccd_1b(investments):
    return min(CAP_80CCD_1B, sum((i.amount for i in investments if i.section == "80CCD1B"), ZERO))


def deduction_80d(investments, age_category):
    """BR-11: self and parents caps; the check-up (max 5,000) sits INSIDE each cap."""
    self_prem = parents_prem = self_chk = parents_chk = ZERO
    parents_senior = False
    for i in investments:
        if i.section != "80D":
            continue
        if i.insured == "SELF":
            if i.item == "CHECKUP":
                self_chk += i.amount
            else:
                self_prem += i.amount
        else:
            if i.item == "CHECKUP":
                parents_chk += i.amount
            else:
                parents_prem += i.amount
            parents_senior = parents_senior or i.parents_age_60_plus
    self_ded = min(CAP_80D_SELF[age_category], self_prem + min(self_chk, CHECKUP_CAP))
    parents_ded = min(CAP_80D_PARENTS[parents_senior], parents_prem + min(parents_chk, CHECKUP_CAP))
    return self_ded + parents_ded


def deduction_80ccd_2(employer_nps, basic_total, regime):
    """BR-12: employer NPS up to 10% of basic (OLD) or 14% (NEW) - allowed in both regimes."""
    return min(employer_nps, basic_total * NPS_EMPLOYER_PCT[regime])
