"""BR-32 .. BR-35: TDS, advance tax, 234B, 234C."""
from datetime import date
from decimal import Decimal as D

from taxengine.engine import compute
from taxengine.interest import compute_interest, months_for_234b
from helpers import FILING, adv, make, sal, tds


def test_BR32_tds_credit_is_summed():
    ds = make(salary=[sal(months=1, basic=775010)], tds_=[tds(2000, "A"), tds(500, "B")])
    s = compute(ds, "T", "NEW", FILING)
    assert s.tds_credit == 2500 and s.net_payable == 10 - 2500


def test_BR33_advance_tax_is_credited():
    ds = make(salary=[sal(months=1, basic=1275000)], advance=[adv(20000, "2025-06-10")])
    s = compute(ds, "T", "NEW", FILING)
    assert s.advance_tax_paid == 20000
    assert s.net_payable == round(s.total_tax - 20000 + s.interest_234b + s.interest_234c)


def test_BR34_interest_234b_months_and_threshold():
    assert months_for_234b(date(2026, 7, 24)) == 4          # Apr, May, Jun, Jul
    assert months_for_234b(date(2026, 10, 30)) == 7
    assert months_for_234b(date(2026, 4, 1)) == 1
    i234b, _, rules = compute_interest(D(100000), [], date(2026, 7, 24))
    assert i234b == D(100000) * D("0.01") * 4 and "BR-34" in rules
    assert compute_interest(D(10000), [], FILING)[0] == 0   # must be ABOVE 10,000
    i234b, _, _ = compute_interest(D(100000), [adv(40000, "2026-03-10")], FILING)
    assert i234b == D(60000) * D("0.01") * 4                # only the shortfall bears interest


def test_BR34_later_filing_date_means_more_months():
    early, _, _ = compute_interest(D(100000), [], date(2026, 7, 15))
    late, _, _ = compute_interest(D(100000), [], date(2026, 9, 15))
    assert late > early and late == D(100000) * D("0.01") * 6


def test_BR35_interest_234c_late_first_instalment():
    # EC-08: 15% of 1,00,000 = 15,000 due by 15 June. Paid on 16 June -> first instalment is short.
    on_time = compute_interest(D(100000), [adv(100000, "2025-06-15")], FILING)[1]
    late = compute_interest(D(100000), [adv(100000, "2025-06-16")], FILING)[1]
    assert on_time == 0
    assert late == D(15000) * D("0.01")                     # only the 15 June instalment is short
    assert "BR-35" in compute_interest(D(100000), [adv(100000, "2025-06-16")], FILING)[2]


def test_BR35_cumulative_instalments():
    payments = [adv(30000, "2025-06-14"), adv(20000, "2025-09-14")]   # 50,000 by Sep, nothing after
    _, i234c, _ = compute_interest(D(100000), payments, FILING)
    # Jun: need 15,000 have 30,000 -> 0 | Sep: need 45,000 have 50,000 -> 0
    # Dec: need 75,000 have 50,000 -> 25,000 | Mar: need 100,000 have 50,000 -> 50,000
    assert i234c == D(25000) * D("0.01") + D(50000) * D("0.01")
