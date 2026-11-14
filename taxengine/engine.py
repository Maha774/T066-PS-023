"""One computation: income heads -> set-offs -> GTI -> Chapter VI-A -> rebate -> surcharge
-> cess -> TDS -> interest (BR-38)."""
from dataclasses import dataclass, field

from .capital_gains import compute_capital_gains
from .constants import FY_END
from .deductions import (deduction_80c, deduction_80ccd_1b, deduction_80ccd_2, deduction_80d)
from .house_property import compute_house_property, set_off_loss
from .interest import compute_interest
from .salary import compute_salary
from .tax import compute_tax
from .util import ZERO, round_rupee, round_ten

Z = ZERO


@dataclass
class Sheet:
    """Field order = column order of computation_sheet.csv."""
    taxpayer_id: str = ""
    regime: str = ""
    age_category: str = ""
    gross_salary: object = Z
    standard_deduction: object = Z
    professional_tax: object = Z
    hra_exemption: object = Z
    employer_nps_in_salary: object = Z
    income_salary: object = Z
    income_house_property: object = Z
    stcg_equity_20: object = Z
    stcg_slab: object = Z
    ltcg_equity_12_5: object = Z
    ltcg_other_12_5: object = Z
    income_other_sources: object = Z
    hp_loss_set_off: object = Z
    gross_total_income: object = Z
    ded_80c: object = Z
    ded_80ccd_1b: object = Z
    ded_80ccd_2: object = Z
    ded_80d: object = Z
    total_deductions: object = Z
    taxable_income: object = Z
    tax_slab: object = Z
    tax_special_rate: object = Z
    rebate_87a: object = Z
    marginal_relief_87a: object = Z
    surcharge: object = Z
    marginal_relief_surcharge: object = Z
    cess: object = Z
    total_tax: object = Z
    tds_credit: object = Z
    advance_tax_paid: object = Z
    interest_234b: object = Z
    interest_234c: object = Z
    net_payable: object = Z
    cf_hp_loss: object = Z
    cf_stcl: object = Z
    cf_ltcl: object = Z
    rule_ids: list = field(default_factory=list)


def age_category(dob) -> str:
    """BR-01: age on 31 March 2026 (a person turning 60 that day is already a senior)."""
    age = FY_END.year - dob.year - ((FY_END.month, FY_END.day) < (dob.month, dob.day))
    if age >= 80:
        return "80_PLUS"
    return "60_79" if age >= 60 else "BELOW_60"


def _sort_rules(rules):
    return sorted(rules, key=lambda r: int(r.split("-")[1]))


def compute(ds, taxpayer_id, regime, filing_date) -> Sheet:
    tp = ds.taxpayers[taxpayer_id]
    s = Sheet(taxpayer_id=taxpayer_id, regime=regime, age_category=age_category(tp.date_of_birth))
    rules = {"BR-01", "BR-38", "BR-36"}

    # ---- income heads -------------------------------------------------
    salary_lines = ds.salary.get(taxpayer_id, [])
    sal = compute_salary(salary_lines, regime)
    s.gross_salary, s.standard_deduction = sal.gross, sal.standard_deduction
    s.professional_tax, s.hra_exemption = sal.professional_tax, sal.hra_exemption
    s.employer_nps_in_salary, s.income_salary = sal.employer_nps, sal.income
    if salary_lines:
        rules.add("BR-05")
    if sal.professional_tax > 0:
        rules.add("BR-06")
    if regime == "OLD" and any(ln.rent_paid_pm > 0 for ln in salary_lines):
        rules.update({"BR-07", "BR-08"})

    hp_income, hp_rules = compute_house_property(ds.house.get(taxpayer_id, []), regime)
    s.income_house_property = hp_income
    rules |= hp_rules

    s.income_other_sources = sum((o.amount for o in ds.other.get(taxpayer_id, [])), Z)
    if s.income_other_sources > 0:
        rules.add("BR-42")

    gains = ds.gains.get(taxpayer_id, [])
    cg = compute_capital_gains(gains)
    s.stcg_equity_20, s.stcg_slab = cg.stcg_equity, cg.stcg_slab
    s.ltcg_equity_12_5, s.ltcg_other_12_5 = cg.ltcg_equity_taxable, cg.ltcg_other
    s.cf_stcl, s.cf_ltcl = cg.cf_stcl, cg.cf_ltcl
    if gains:
        rules.add("BR-20")
    for flag, rid in ((cg.ltcg_equity > 0 or cg.ltcg_equity_taxable > 0, "BR-16"),
                      (cg.stcg_equity > 0, "BR-17"), (cg.ltcg_other > 0, "BR-18"),
                      (cg.stcg_slab > 0, "BR-19"), (cg.had_loss, "BR-21")):
        if flag:
            rules.add(rid)

    # ---- set-offs -> gross total income (BR-15) -----------------------
    available = s.income_salary + s.income_other_sources + s.stcg_slab
    s.hp_loss_set_off, s.cf_hp_loss = set_off_loss(hp_income, available)
    if hp_income < 0:
        rules.add("BR-15")
    hp_positive = max(Z, hp_income)
    slab_base = (s.income_salary + hp_positive + s.income_other_sources + s.stcg_slab
                 - s.hp_loss_set_off)
    special = s.stcg_equity_20 + s.ltcg_equity_12_5 + s.ltcg_other_12_5
    s.gross_total_income = slab_base + special

    # ---- Chapter VI-A -------------------------------------------------
    inv = ds.investments.get(taxpayer_id, [])
    if regime == "OLD":
        s.ded_80c = deduction_80c(inv)
        s.ded_80ccd_1b = deduction_80ccd_1b(inv)
        s.ded_80d = deduction_80d(inv, s.age_category)
        for amt, rid in ((s.ded_80c, "BR-09"), (s.ded_80ccd_1b, "BR-10"), (s.ded_80d, "BR-11")):
            if amt > 0:
                rules.add(rid)
    s.ded_80ccd_2 = deduction_80ccd_2(sal.employer_nps, sal.basic_total, regime)
    if s.ded_80ccd_2 > 0:
        rules.add("BR-12")
    claimed = s.ded_80c + s.ded_80ccd_1b + s.ded_80ccd_2 + s.ded_80d
    s.total_deductions = min(claimed, slab_base)   # BR-22: not against special-rate gains
    rules.add("BR-22")

    # ---- taxable income, rounded to Rs 10 (BR-23) ---------------------
    total_income = round_ten(slab_base - s.total_deductions + special)
    s.taxable_income = total_income
    slab_taxable = max(Z, total_income - special)

    # ---- tax, rebate, surcharge, cess ---------------------------------
    t = compute_tax(regime, s.age_category, slab_taxable, s.stcg_equity_20,
                    s.ltcg_equity_12_5, s.ltcg_other_12_5, total_income)
    s.tax_slab, s.tax_special_rate = t.tax_slab, t.tax_special
    s.rebate_87a, s.marginal_relief_87a = t.rebate, t.marginal_relief_87a
    s.surcharge, s.marginal_relief_surcharge = t.surcharge, t.marginal_relief_surcharge
    s.cess, s.total_tax = t.cess, t.total_tax
    rules |= t.rules

    # ---- TDS, advance tax, interest -----------------------------------
    s.tds_credit = sum((x.amount for x in ds.tds.get(taxpayer_id, [])), Z)
    advance = ds.advance.get(taxpayer_id, [])
    s.advance_tax_paid = sum((a.amount for a in advance), Z)
    if s.tds_credit > 0:
        rules.add("BR-32")
    if advance:
        rules.add("BR-33")
    s.interest_234b, s.interest_234c, int_rules = compute_interest(
        s.total_tax - s.tds_credit, advance, filing_date)
    rules |= int_rules
    s.net_payable = round_rupee(s.total_tax - s.tds_credit - s.advance_tax_paid
                                + s.interest_234b + s.interest_234c)
    s.rule_ids = _sort_rules(rules)
    return s


def recommend(old: Sheet, new: Sheet):
    """BR-37: lower net payable wins; NEW when equal. Returns (regime, saving)."""
    regime = "OLD" if old.net_payable < new.net_payable else "NEW"
    return regime, abs(old.net_payable - new.net_payable)
