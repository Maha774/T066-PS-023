"""Slab tax, special-rate tax, 87A rebate + marginal relief, surcharge + marginal relief, cess."""
from dataclasses import dataclass, field

from .constants import (CESS_RATE, LTCG_RATE, NEW_SLABS, OLD_SLABS, REBATE_87A,
                        STCG_EQUITY_RATE, SURCHARGE_BANDS, SURCHARGE_CAP_CAPITAL_GAINS,
                        SURCHARGE_CAP_NEW)
from .util import D, ZERO, round_rupee


def slab_tax(income, slabs):
    tax, lower = ZERO, ZERO
    for upper, rate in slabs:
        top = income if upper is None else min(income, D(upper))
        if top > lower:
            tax += (top - lower) * D(rate) / 100
        if upper is None or income <= upper:
            break
        lower = D(upper)
    return tax


def slabs_for(regime, age_category):
    return NEW_SLABS if regime == "NEW" else OLD_SLABS[age_category]


def special_taxes(stcg_eq, ltcg_eq_taxable, ltcg_other):
    """Returns (tax on equity STCG, tax on equity LTCG, tax on other LTCG)."""
    return stcg_eq * STCG_EQUITY_RATE, ltcg_eq_taxable * LTCG_RATE, ltcg_other * LTCG_RATE


def band_for(income, regime):
    """BR-28: surcharge only when income is GREATER than the threshold.
    Returns (rate %, rate % of the band below, threshold)."""
    cap = SURCHARGE_CAP_NEW if regime == "NEW" else 100
    rate, prev, threshold = 0, 0, None
    for limit, r in SURCHARGE_BANDS:
        r = min(r, cap)
        if income > limit:
            prev, rate, threshold = rate, r, limit
    return D(rate), D(prev), threshold


def surcharge_amount(slab_part, special_part, rate):
    """BR-29: the capital-gains part of the tax never bears more than 15% surcharge."""
    return slab_part * rate / 100 + special_part * min(rate, SURCHARGE_CAP_CAPITAL_GAINS) / 100


def _taxes_at(parts, slabs):
    tax_slab = slab_tax(parts["slab"], slabs)
    st, lt_eq, lt_oth = special_taxes(parts["stcg_eq"], parts["ltcg_eq"], parts["ltcg_oth"])
    return tax_slab, st + lt_eq + lt_oth


def _reduce(parts, excess):
    """Income at the surcharge threshold: take the excess off slab income first, then the
    special-rate gains (BR-30)."""
    parts = dict(parts)
    for key in ("slab", "ltcg_oth", "ltcg_eq", "stcg_eq"):
        cut = min(excess, parts[key])
        parts[key] -= cut
        excess -= cut
    return parts


@dataclass
class TaxResult:
    tax_slab: object = ZERO
    tax_special: object = ZERO
    rebate: object = ZERO
    marginal_relief_87a: object = ZERO
    surcharge: object = ZERO
    marginal_relief_surcharge: object = ZERO
    cess: object = ZERO
    total_tax: object = ZERO
    rules: set = field(default_factory=set)


def compute_tax(regime, age_category, slab_taxable, stcg_eq, ltcg_eq_taxable, ltcg_other,
                total_income) -> TaxResult:
    r = TaxResult()
    slabs = slabs_for(regime, age_category)
    r.rules.add("BR-04" if regime == "NEW" else "BR-02")
    if regime == "OLD" and age_category != "BELOW_60":
        r.rules.add("BR-03")

    parts = {"slab": slab_taxable, "stcg_eq": stcg_eq, "ltcg_eq": ltcg_eq_taxable, "ltcg_oth": ltcg_other}
    r.tax_slab, r.tax_special = _taxes_at(parts, slabs)
    t_st, t_lt_eq, t_lt_oth = special_taxes(stcg_eq, ltcg_eq_taxable, ltcg_other)

    # 87A rebate (BR-24 / BR-25); never against tax on equity LTCG (BR-27)
    limit, max_rebate = REBATE_87A[regime]
    if total_income <= limit:
        r.rebate = min(max_rebate, r.tax_slab + t_st + t_lt_oth)
        if r.rebate > 0:
            r.rules.add("BR-25" if regime == "NEW" else "BR-24")
            if t_lt_eq > 0:
                r.rules.add("BR-27")
    elif regime == "NEW":  # BR-26 marginal relief just above 7 lakh
        excess = total_income - limit
        relief = r.tax_slab + r.tax_special - excess
        if relief > 0:
            r.marginal_relief_87a = relief
            r.rules.add("BR-26")

    after_rebate = r.tax_slab + r.tax_special - r.rebate - r.marginal_relief_87a

    # Surcharge (BR-28, BR-29) with marginal relief (BR-30)
    rate, prev_rate, threshold = band_for(total_income, regime)
    if rate > 0:
        slab_part = max(ZERO, after_rebate - r.tax_special)
        r.surcharge = surcharge_amount(slab_part, r.tax_special, rate)
        r.rules.add("BR-28")
        if r.tax_special > 0 and rate > SURCHARGE_CAP_CAPITAL_GAINS:
            r.rules.add("BR-29")
        excess = total_income - threshold
        t_slab_at, t_special_at = _taxes_at(_reduce(parts, excess), slabs)
        sur_at = surcharge_amount(t_slab_at, t_special_at, prev_rate)
        allowed = t_slab_at + t_special_at + sur_at + excess
        relief = after_rebate + r.surcharge - allowed
        if relief > 0:
            r.marginal_relief_surcharge = relief
            r.rules.add("BR-30")

    base = after_rebate + r.surcharge - r.marginal_relief_surcharge
    r.cess = base * CESS_RATE                                   # BR-31
    r.total_tax = round_rupee(base + r.cess)                    # BR-36
    r.rules.add("BR-31")
    return r
