"""CSV writers (exact evaluation format) and a readable console printout."""
import csv
from dataclasses import fields
from pathlib import Path

from .engine import Sheet
from .util import fmt

SHEET_COLUMNS = [f.name for f in fields(Sheet)]
COMPARISON_COLUMNS = ["taxpayer_id", "filing_date", "old_total_tax", "new_total_tax",
                      "old_net_payable", "new_net_payable", "recommended_regime", "saving"]
REJECTION_COLUMNS = ["source_file", "record_id", "reason"]
TEXT_COLUMNS = {"taxpayer_id", "regime", "age_category", "rule_ids", "filing_date",
                "recommended_regime"}


def _cell(column, value):
    if column == "rule_ids":
        return ";".join(value)
    return value if column in TEXT_COLUMNS else fmt(value)


def write_outputs(result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "computation_sheet.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(SHEET_COLUMNS)
        for s in result.sheets:
            w.writerow([_cell(c, getattr(s, c)) for c in SHEET_COLUMNS])
    with open(out_dir / "regime_comparison.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COMPARISON_COLUMNS)
        for row in result.comparisons:
            w.writerow([_cell(c, row[c]) for c in COMPARISON_COLUMNS])
    with open(out_dir / "rejections.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(REJECTION_COLUMNS)
        w.writerows(result.rejections)


_LAYOUT = [
    ("INCOME HEADS", ["gross_salary", "hra_exemption", "standard_deduction", "professional_tax",
                      "income_salary", "income_house_property", "income_other_sources",
                      "stcg_equity_20", "stcg_slab", "ltcg_equity_12_5", "ltcg_other_12_5",
                      "hp_loss_set_off", "gross_total_income"]),
    ("DEDUCTIONS (Chapter VI-A)", ["ded_80c", "ded_80ccd_1b", "ded_80ccd_2", "ded_80d",
                                   "total_deductions", "taxable_income"]),
    ("TAX", ["tax_slab", "tax_special_rate", "rebate_87a", "marginal_relief_87a", "surcharge",
             "marginal_relief_surcharge", "cess", "total_tax"]),
    ("PAYMENTS AND INTEREST", ["tds_credit", "advance_tax_paid", "interest_234b",
                               "interest_234c", "net_payable"]),
    ("CARRY FORWARD", ["cf_hp_loss", "cf_stcl", "cf_ltcl"]),
]


def render_sheet(s) -> str:
    lines = [f"=== {s.taxpayer_id}  |  {s.regime} regime  |  age category {s.age_category} ==="]
    for title, cols in _LAYOUT:
        lines.append(f"-- {title}")
        lines += [f"   {c:<28}{fmt(getattr(s, c)):>16}" for c in cols]
    lines.append(f"-- Rules applied: {', '.join(s.rule_ids)}")
    return "\n".join(lines)


def render_comparison(c) -> str:
    return (f"=== {c['taxpayer_id']}  comparison (filed {c['filing_date']}) ===\n"
            f"   OLD: tax {fmt(c['old_total_tax'])}   net payable {fmt(c['old_net_payable'])}\n"
            f"   NEW: tax {fmt(c['new_total_tax'])}   net payable {fmt(c['new_net_payable'])}\n"
            f"   Recommended: {c['recommended_regime']}   (saves {fmt(c['saving'])})")
