"""BR-01 .. BR-15, BR-42: age, slabs, salary, HRA, deductions, house property."""
from decimal import Decimal as D

from taxengine.deductions import deduction_80c, deduction_80ccd_1b, deduction_80ccd_2, deduction_80d
from taxengine.engine import age_category, compute
from taxengine.house_property import compute_house_property, set_off_loss
from taxengine.salary import compute_salary
from taxengine.tax import slab_tax, slabs_for
from helpers import FILING, adv, house, inv, make, other, sal


def test_BR01_age_category_on_31_march():
    from datetime import date
    assert age_category(date(1966, 3, 31)) == "60_79"     # turns 60 on 31 March -> senior
    assert age_category(date(1966, 4, 1)) == "BELOW_60"   # turns 60 the next day
    assert age_category(date(1946, 3, 31)) == "80_PLUS"
    assert age_category(date(1946, 4, 1)) == "60_79"


def test_BR02_old_slabs():
    assert slab_tax(D(1200000), slabs_for("OLD", "BELOW_60")) == D(172500)
    assert slab_tax(D(250000), slabs_for("OLD", "BELOW_60")) == 0


def test_BR03_old_basic_exemption_by_age():
    assert slab_tax(D(1000000), slabs_for("OLD", "60_79")) == D(110000)
    assert slab_tax(D(1000000), slabs_for("OLD", "80_PLUS")) == D(100000)
    assert slab_tax(D(300000), slabs_for("OLD", "60_79")) == 0
    assert slab_tax(D(500000), slabs_for("OLD", "80_PLUS")) == 0


def test_BR04_new_slabs():
    assert slab_tax(D(1500000), slabs_for("NEW", "BELOW_60")) == D(140000)
    assert slab_tax(D(300000), slabs_for("NEW", "BELOW_60")) == 0
    assert slab_tax(D(1500000), slabs_for("NEW", "80_PLUS")) == D(140000)   # same for all ages


def test_BR05_standard_deduction_and_cap():
    lines = [sal(months=12, basic=50000)]
    assert compute_salary(lines, "OLD").standard_deduction == 50000
    assert compute_salary(lines, "NEW").standard_deduction == 75000
    tiny = [sal(months=1, basic=40000)]
    assert compute_salary(tiny, "NEW").standard_deduction == 40000      # never more than salary
    assert compute_salary(tiny, "NEW").income == 0


def test_BR06_professional_tax_old_only_capped():
    lines = [sal(months=12, basic=50000, pt=300)]    # 3,600 a year
    assert compute_salary(lines, "OLD").professional_tax == 2500
    assert compute_salary(lines, "NEW").professional_tax == 0


def test_BR07_hra_exemption_formula():
    # min(25000, 20000 - 5000, 40% of 50000 = 20000) = 15000 a month
    lines = [sal(months=12, basic=50000, hra=25000, rent=20000)]
    assert compute_salary(lines, "OLD").hra_exemption == 15000 * 12
    assert compute_salary([sal(basic=50000, hra=25000, rent=0)], "OLD").hra_exemption == 0   # no rent
    assert compute_salary(lines, "NEW").hra_exemption == 0                                    # OLD only
    metro = [sal(months=1, basic=50000, hra=40000, rent=60000, metro=True)]
    assert compute_salary(metro, "OLD").hra_exemption == 25000                               # 50% of basic


def test_BR08_hra_month_by_month_and_never_negative():
    # EC-04: 3 months rent 5,000 < 10% of basic -> 0; then Chennai (metro), rent 26,000
    lines = [sal(months=3, basic=60000, hra=30000, rent=5000, city="Mysuru"),
             sal(months=9, basic=60000, hra=30000, rent=26000, metro=True, city="Chennai")]
    assert compute_salary(lines, "OLD").hra_exemption == 20000 * 9


def test_BR09_80c_cap():
    items = [inv("80C", "EPF", 115200), inv("80C", "PPF", 50000), inv("80C", "ELSS", 25000)]
    assert deduction_80c(items) == 150000
    ds = make(salary=[sal(basic=100000)], invs=items)
    assert compute(ds, "T", "NEW", FILING).ded_80c == 0           # OLD only


def test_BR10_80ccd_1b_cap():
    assert deduction_80ccd_1b([inv("80CCD1B", "NPS_SELF", 65000)]) == 50000


def test_BR11_80d_caps_and_checkup_inside_cap():
    self_prem = inv("80D", "HEALTH_SELF", 22000, "SELF")
    checkup = inv("80D", "CHECKUP", 7000, "SELF")
    assert deduction_80d([self_prem, checkup], "BELOW_60") == 25000    # 22000 + 5000 -> capped 25000
    assert deduction_80d([inv("80D", "HEALTH_SELF", 62000, "SELF")], "80_PLUS") == 50000
    assert deduction_80d([inv("80D", "HEALTH_SELF", 62000, "SELF")], "BELOW_60") == 25000
    parents = inv("80D", "HEALTH_PARENTS", 38000, "PARENTS", senior=True)
    assert deduction_80d([parents], "BELOW_60") == 38000               # cap 50,000 for 60+ parents
    assert deduction_80d([inv("80D", "HEALTH_PARENTS", 38000, "PARENTS", senior=False)], "BELOW_60") == 25000
    assert deduction_80d([inv("80D", "CHECKUP", 4000, "SELF")], "BELOW_60") == 4000


def test_BR12_employer_nps_10_and_14_percent():
    assert deduction_80ccd_2(D(134400), D(960000), "OLD") == 96000
    assert deduction_80ccd_2(D(134400), D(960000), "NEW") == 134400


def test_BR13_self_occupied_interest_cap():
    props = [house("SELF_OCCUPIED", interest=240000)]
    assert compute_house_property(props, "OLD")[0] == -200000
    assert compute_house_property(props, "NEW")[0] == 0


def test_BR14_let_out_house_income():
    props = [house("LET_OUT", rent=180000, municipal=0, interest=100000)]
    assert compute_house_property(props, "OLD")[0] == D(180000 - 54000 - 100000)
    props = [house("LET_OUT", rent=200000, municipal=20000, interest=0)]
    assert compute_house_property(props, "NEW")[0] == D(126000)


def test_BR15_loss_set_off_limited_by_cap_and_by_income():
    assert set_off_loss(D(-250000), D(100000)) == (100000, 150000)    # EC-05: income is the limit
    assert set_off_loss(D(-250000), D(500000)) == (200000, 50000)     # cap is the limit
    assert set_off_loss(D(50000), D(500000)) == (0, 0)
    ds = make(houses=[house("LET_OUT", rent=180000, interest=376000)],
              others=[other("FD_INTEREST", 100000)])
    s = compute(ds, "T", "OLD", FILING)
    assert (s.hp_loss_set_off, s.cf_hp_loss, s.gross_total_income) == (100000, 150000, 0)


def test_BR42_interest_and_dividend_are_other_sources():
    ds = make(others=[other("FD_INTEREST", 100000), other("DIVIDEND", 20000), other("SAVINGS_INTEREST", 5000)])
    s = compute(ds, "T", "OLD", FILING)
    assert s.income_other_sources == 125000
    assert s.gross_total_income == 125000
