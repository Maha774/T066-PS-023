"""BR-16 .. BR-21: capital gains classification, rates and loss set-off."""
from decimal import Decimal as D

from taxengine.capital_gains import compute_capital_gains, is_long_term
from taxengine.engine import compute
from helpers import FILING, cg, make


def test_BR16_equity_ltcg_exemption_boundary():
    r = compute_capital_gains([cg("LISTED_EQUITY", "2023-05-10", "2025-09-15", 400000, 525000)])
    assert r.ltcg_equity == 125000 and r.ltcg_equity_taxable == 0         # EC-03
    r = compute_capital_gains([cg("LISTED_EQUITY", "2022-01-01", "2025-09-15", 100000, 400000)])
    assert r.ltcg_equity_taxable == 175000
    s = compute(make(gains=[cg("EQUITY_MF", "2022-01-01", "2025-09-15", 100000, 400000)]), "T", "NEW", FILING)
    assert s.tax_special_rate == D("21875")                               # 12.5% of 1,75,000


def test_BR17_equity_stcg_at_20_percent():
    s = compute(make(gains=[cg("LISTED_EQUITY", "2025-06-01", "2025-12-01", 100000, 200000)]), "T", "OLD", FILING)
    assert s.stcg_equity_20 == 100000 and s.tax_special_rate == 20000


def test_BR18_other_assets_ltcg_12_5_no_indexation():
    s = compute(make(gains=[cg("LAND_BUILDING", "2020-01-01", "2025-12-01", 1000000, 1200000)]), "T", "OLD", FILING)
    assert s.ltcg_other_12_5 == 200000 and s.tax_special_rate == 25000


def test_BR19_other_assets_short_term_goes_to_slab():
    r = compute_capital_gains([cg("GOLD", "2025-01-01", "2025-12-01", 300000, 400000)])
    assert r.stcg_slab == 100000 and r.ltcg_other == 0
    s = compute(make(gains=[cg("GOLD", "2025-01-01", "2025-12-01", 300000, 400000)]), "T", "OLD", FILING)
    assert s.stcg_slab == 100000 and s.tax_special_rate == 0 and s.gross_total_income == 100000


def test_BR20_holding_period_boundaries():
    equity = lambda b, s: cg("LISTED_EQUITY", b, s, 1, 2)
    other = lambda b, s: cg("LAND_BUILDING", b, s, 1, 2)
    assert not is_long_term(equity("2024-08-14", "2025-08-14"))   # exactly 12 months -> short
    assert is_long_term(equity("2024-08-14", "2025-08-15"))       # 12 months + 1 day -> long
    assert not is_long_term(other("2023-10-20", "2025-10-20"))    # exactly 24 months -> short
    assert is_long_term(cg("GOLD", "2023-07-01", "2025-07-02", 1, 2))
    assert not is_long_term(equity("2024-02-29", "2025-02-28"))   # leap day clamps to 28 Feb


def test_BR21_stcl_against_stcg_then_ltcg_and_carry_forward():
    # EC-07: STCL 3,00,000 vs STCG 50,000 + LTCG 1,20,000 -> all wiped, 1,30,000 carried forward
    gains = [cg("LISTED_EQUITY", "2025-04-10", "2025-11-20", 900000, 600000),
             cg("EQUITY_MF", "2025-01-06", "2025-10-03", 200000, 250000),
             cg("LISTED_EQUITY", "2022-06-01", "2025-12-12", 380000, 500000)]
    r = compute_capital_gains(gains)
    assert (r.stcg_equity, r.ltcg_equity, r.cf_stcl, r.cf_ltcl) == (0, 0, 130000, 0)


def test_BR21_ltcl_only_against_ltcg():
    gains = [cg("LISTED_EQUITY", "2025-06-01", "2025-12-01", 100000, 200000),     # STCG 1,00,000
             cg("LAND_BUILDING", "2015-01-01", "2025-12-01", 900000, 700000)]     # LTCL 2,00,000
    r = compute_capital_gains(gains)
    assert r.stcg_equity == 100000        # LTCL must NOT touch the short-term gain
    assert r.cf_ltcl == 200000
    gains.append(cg("GOLD", "2020-01-01", "2025-12-01", 100000, 250000))          # LTCG 1,50,000
    r = compute_capital_gains(gains)
    assert r.ltcg_other == 0 and r.cf_ltcl == 50000 and r.stcg_equity == 100000
