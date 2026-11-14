"""Capital gains: classification, holding-period test, and loss set-off ordering."""
from dataclasses import dataclass

from .constants import (EQUITY_CLASSES, EQUITY_LT_MONTHS, LTCG_EQUITY_EXEMPTION, OTHER_LT_MONTHS)
from .util import ZERO, add_months


@dataclass
class CapitalGainsResult:
    stcg_equity: object = ZERO      # taxed 20%
    stcg_slab: object = ZERO        # added to slab income
    ltcg_equity: object = ZERO      # after loss set-off, BEFORE the 1.25 lakh exemption
    ltcg_equity_taxable: object = ZERO
    ltcg_other: object = ZERO       # taxed 12.5%, no indexation
    cf_stcl: object = ZERO
    cf_ltcl: object = ZERO
    had_loss: bool = False


def is_long_term(g) -> bool:
    """BR-20: 'more than' N months. Exactly N months is still short term."""
    months = EQUITY_LT_MONTHS if g.asset_class in EQUITY_CLASSES else OTHER_LT_MONTHS
    return g.sale_date > add_months(g.purchase_date, months)


def compute_capital_gains(gains) -> CapitalGainsResult:
    bucket = {"stcg_eq": ZERO, "stcg_slab": ZERO, "ltcg_eq": ZERO, "ltcg_oth": ZERO}
    stcl = ltcl = ZERO
    had_loss = False
    for g in gains:
        equity = g.asset_class in EQUITY_CLASSES
        long_term = is_long_term(g)
        gain = g.sale_value - g.cost - g.transfer_expenses
        key = ("ltcg_eq" if equity else "ltcg_oth") if long_term else ("stcg_eq" if equity else "stcg_slab")
        if gain < 0:
            had_loss = True
        if gain >= 0:
            bucket[key] += gain
        elif long_term:
            ltcl += -gain
        else:
            stcl += -gain

    # BR-21 step 1: short-term loss against short-term gains first, then long-term gains
    for key in ("stcg_eq", "stcg_slab", "ltcg_eq", "ltcg_oth"):
        used = min(stcl, bucket[key])
        bucket[key] -= used
        stcl -= used
    # BR-21 step 2: long-term loss ONLY against long-term gains
    for key in ("ltcg_eq", "ltcg_oth"):
        used = min(ltcl, bucket[key])
        bucket[key] -= used
        ltcl -= used

    r = CapitalGainsResult(bucket["stcg_eq"], bucket["stcg_slab"], bucket["ltcg_eq"],
                           ZERO, bucket["ltcg_oth"], stcl, ltcl, had_loss)
    r.ltcg_equity_taxable = max(ZERO, r.ltcg_equity - LTCG_EQUITY_EXEMPTION)   # BR-16
    return r
