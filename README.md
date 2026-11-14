# T066-PS-023 - Individual Income Tax Computation (OLD vs NEW regime), FY 2025-26

Command-file driven engine: reads taxpayer, salary, house-property, capital-gain, other-income,
investment, TDS and advance-tax CSVs, computes tax under both regimes, prints computation sheets and
recommends a regime. Team T066: Jaya Shree R, K Mahalakshmi.

## Requirements
Python 3.10+ . Only the tests need an extra package: `pip install -r requirements.txt` (pytest).

## Run the program
```bash
python -m taxengine sample_data --out output
```
* `sample_data/` holds the input CSVs and `commands.txt` (use `--commands path` for another command file).
* Console shows readable computation sheets and comparisons; add `--quiet` to only write files.
* Output files in `output/`: `computation_sheet.csv`, `regime_comparison.csv`, `rejections.csv`
  (exact column order from the evaluation brief).

## Run the tests (one command)
```bash
python -m pytest
```
47 tests; one or more per business rule, named `test_BRnn_...`; `test_rule_coverage.py` fails if any
rule id in `taxengine/rules.py` has no test.

## Command file
`COMPUTE|taxpayer_id|filing_date`, `PRINT_SHEET|taxpayer_id|OLD or NEW`, `PRINT_COMPARISON|taxpayer_id`.
Commands run in file order; a later COMPUTE replaces the earlier result.

## Layout
| File | Job |
|---|---|
| `taxengine/constants.py` | every number from the brief (slabs, caps, rates, dates) |
| `taxengine/rules.py` | business-rule register BR-01 ... BR-42 |
| `taxengine/loaders.py` | CSV reading + validation, builds `rejections.csv` |
| `taxengine/salary.py` | gross, HRA (monthly), standard deduction, professional tax |
| `taxengine/house_property.py` | self-occupied / let-out income, loss set-off |
| `taxengine/capital_gains.py` | holding period, rates, loss set-off ordering |
| `taxengine/deductions.py` | 80C, 80CCD(1B), 80CCD(2), 80D |
| `taxengine/tax.py` | slabs, 87A rebate + marginal relief, surcharge + marginal relief, cess |
| `taxengine/interest.py` | 234B and 234C |
| `taxengine/engine.py` | one computation in the legal order (BR-38) |
| `taxengine/commands.py`, `report.py` | command runner, CSV + console output |

See `docs/` for the design document and `DECISIONS.md` for the decision log.
