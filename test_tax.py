"""BR-22 .. BR-31, BR-36, BR-37: taxable income, rebate, surcharge, cess, rounding, recommendation."""
from decimal import Decimal as D

from taxengine.engine import compute, recommend
from taxengine.tax import band_for, surcharge_amount
from taxengine.util import round_rupee, round_ten
from helpers import FILING, cg, inv, make, sal


def salary_for_taxable(taxable, regime):
    """One-month salary that gives exactly `taxable` after the standard deduction (no other items)."""
    sd = 75000 if regime == "NEW" else 50000
    return make(salary=[sal(months=1, basic=taxable + sd)])


def test_BR22_deductions_never_reduce_special_rate_gains():
    ds = make(gains=[cg("LISTED_EQUITY", "2025-05-01", "2025-12-01", 100000, 600000)],
              invs=[inv("80C", "PPF", 150000)])
    s = compute(ds, "T", "OLD", FILING)
    assert s.total_deductions == 0 and s.taxable_income == 500000 and s.stcg_equity_20 == 500000


def test_BR23_rounding_to_nearest_ten():
    assert round_ten(D("700014")) == 700010
    assert round_ten(D("700015")) == 700020
    assert round_ten(D("700005")) == 700010
    ds = make(salary=[sal(months=1, basic=700014 + 75000)])
    assert compute(ds, "T", "NEW", FILING).taxable_income == 700010


def test_BR24_old_rebate_boundary():
    s = compute(salary_for_taxable(500000, "OLD"), "T", "OLD", FILING)
    assert s.rebate_87a == 12500 and s.total_tax == 0
    s = compute(salary_for_taxable(500010, "OLD"), "T", "OLD", FILING)
    assert s.rebate_87a == 0 and s.total_tax == 13002        # (12500 + 2) * 1.04


def test_BR25_new_rebate_up_to_7_lakh():
    s = compute(salary_for_taxable(700000, "NEW"), "T", "NEW", FILING)
    assert s.tax_slab == 20000 and s.rebate_87a == 20000 and s.total_tax == 0
    s = compute(salary_for_taxable(400000, "NEW"), "T", "NEW", FILING)
    assert s.rebate_87a == 5000 and s.total_tax == 0


def test_BR26_new_marginal_relief_at_7_lakh_10():
    s = compute(salary_for_taxable(700010, "NEW"), "T", "NEW", FILING)     # EC-01
    assert s.tax_slab == 20001 and s.rebate_87a == 0
    assert s.marginal_relief_87a == 19991 and s.total_tax == 10            # (20001 - 19991) = 10, + cess 0.40
    s = compute(salary_for_taxable(775010, "NEW"), "T", "NEW", FILING)     # relief fades out
    assert s.marginal_relief_87a == 0


def test_BR27_no_rebate_on_equity_ltcg():
    ds = make(gains=[cg("LISTED_EQUITY", "2022-01-01", "2025-12-01", 100000, 425000)])  # LTCG 3,25,000 -> 2,00,000 taxable
    s = compute(ds, "T", "NEW", FILING)
    assert s.tax_special_rate == 25000 and s.rebate_87a == 0 and s.total_tax == 26000
    ds = make(salary=[sal(months=1, basic=400000 + 75000)],
              gains=[cg("LISTED_EQUITY", "2022-01-01", "2025-12-01", 100000, 425000)])
    s = compute(ds, "T", "NEW", FILING)       # rebate only covers the slab tax, not the LTCG tax
    assert s.rebate_87a == s.tax_slab and s.total_tax == round_rupee((s.tax_special_rate) * D("1.04"))


def test_BR28_surcharge_thresholds_are_strictly_greater_and_new_is_capped():
    assert band_for(D(5000000), "NEW")[0] == 0 and band_for(D(5000001), "NEW")[0] == 10
    assert band_for(D(10000001), "OLD")[0] == 15 and band_for(D(20000001), "OLD")[0] == 25
    assert band_for(D(60000000), "OLD")[0] == 37 and band_for(D(60000000), "NEW")[0] == 25
    s = compute(salary_for_taxable(5000000, "NEW"), "T", "NEW", FILING)    # EC-02: exactly 50 lakh
    assert s.surcharge == 0 and s.total_tax == 1237600


def test_BR29_surcharge_on_capital_gains_capped_at_15():
    assert surcharge_amount(D(0), D(1000), D(25)) == 150
    assert surcharge_amount(D(1000), D(0), D(25)) == 250
    assert surcharge_amount(D(1000), D(1000), D(37)) == D(370) + D(150)


def test_BR30_surcharge_marginal_relief_at_50_lakh():
    s = compute(salary_for_taxable(5000100, "NEW"), "T", "NEW", FILING)    # EC-02: Rs 100 over
    assert s.surcharge == 119003 and s.marginal_relief_surcharge == 118933
    # tax + surcharge after relief rises by exactly the Rs 100 of extra income
    assert s.tax_slab + s.surcharge - s.marginal_relief_surcharge == 1190000 + 100
    assert s.total_tax == 1237704


def test_BR31_cess_is_4_percent_of_tax_plus_surcharge():
    s = compute(salary_for_taxable(1000000, "NEW"), "T", "NEW", FILING)
    assert s.tax_slab == 50000 and s.cess == 2000 and s.total_tax == 52000


def test_BR36_final_tax_rounded_to_nearest_rupee():
    assert round_rupee(D("10.4")) == 10 and round_rupee(D("10.5")) == 11 and round_rupee(D("-10.5")) == -11
    s = compute(salary_for_taxable(700010, "NEW"), "T", "NEW", FILING)
    assert s.cess == D("0.4") and s.total_tax == 10


def test_BR37_recommendation_lower_net_wins_new_on_tie():
    class S:   # only net_payable matters
        def __init__(self, n): self.net_payable = D(n)
    assert recommend(S(100), S(80)) == ("NEW", 20)
    assert recommend(S(80), S(100)) == ("OLD", 20)
    assert recommend(S(100), S(100)) == ("NEW", 0)
