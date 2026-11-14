# Decision log (T066 - PS-023)

One line per choice: what we decided, and why. Items marked (?) are guesses where the brief is silent; they are queried on the support thread.

1. Python 3.10+ with `decimal.Decimal` everywhere - tax must match to the rupee, and floats drift.
2. All numbers from the brief live in `constants.py` - a rule change is a one-line edit and easy to demo in the viva.
3. One `Sheet` dataclass whose field order equals the CSV column order - the output format cannot drift from the code.
4. Rounding is "half up" (Rs 10 for taxable income, Rs 1 for tax) - matches how section 288A/288B round.
5. Gross salary includes employer NPS and LTA (as the README says); LTA gets no exemption because the brief gives no rule.
6. HRA is computed per salary line (month by month) with that line's own rent, city flag and basic - handles EC-04 and city changes.
7. Standard deduction and professional tax are capped so they can never push salary income below zero.
8. House-property loss set-off applies to both regimes because the brief does not limit it to OLD (?).
9. HP loss set-off is limited by the Rs 2L cap AND by slab-rate income available (salary + other sources + slab-rate STCG); the rest is carried forward.
10. Capital-loss order: STCL against STCG (equity first, then slab-rate), then LTCG; LTCL only against LTCG; set-off happens before the Rs 1.25L equity exemption (?).
11. The Rs 1.25L equity LTCG exemption is applied to the net LTCG, and the printed `ltcg_equity_12_5` is the taxable part after it.
12. Chapter VI-A deductions are limited to slab-rate income and never reduce special-rate gains (?).
13. The taxable income (rounded to Rs 10) includes special-rate gains; the rounding difference is placed in slab income so slab + special = total.
14. 87A rebate covers slab tax, equity STCG tax and other-LTCG tax but never equity-LTCG tax, as the brief says; marginal relief is NEW only.
15. Surcharge marginal relief compares against the tax at the threshold itself, taking the excess income off slab income first, then special-rate gains.
16. 234B: simple 1% a month on (tax after TDS - advance tax), counting 1 April 2026 to the filing month with a part-month as a full month; nothing if tax after TDS <= Rs 10,000.
17. 234C: 1% of each instalment shortfall ("per quarter" as written in the brief), using challans dated on or before each due date (?).
18. A recommendation tie goes to NEW and `saving` is the absolute difference of net payable, as the evaluation README binds.
19. Invalid lines are rejected, not fixed: outside-FY dates, negatives, unknown IDs, bad enums; a duplicate TDS id is credited once and logged.
20. Commands run strictly in file order and a later COMPUTE replaces the earlier result, so printing always shows the latest numbers.
