"""BR-38 .. BR-41 and a full run on the sample pack."""
import csv
from pathlib import Path

from taxengine.commands import run_commands
from taxengine.engine import compute
from taxengine.loaders import load_dataset
from taxengine.report import COMPARISON_COLUMNS, SHEET_COLUMNS, write_outputs
from helpers import FILING, cg, house, inv, make, other, sal

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"

HEADERS = {
    "taxpayers.csv": "taxpayer_id,full_name,gender,date_of_birth,pan,city,residential_status",
    "salary.csv": "line_id,taxpayer_id,from_month,to_month,basic_pm,hra_pm,special_pm,lta_pm,employer_nps_pm,professional_tax_pm,rent_paid_pm,rent_city,metro_city",
    "capital_gains.csv": "cg_id,taxpayer_id,asset_class,purchase_date,sale_date,cost,sale_value,transfer_expenses",
    "investments.csv": "inv_id,taxpayer_id,section,item,amount,payment_date,insured,parents_age_60_plus",
    "tds.csv": "tds_id,taxpayer_id,deductor_type,deductor_tan,section,amount",
}


def write(tmp_path, name, *rows):
    (tmp_path / name).write_text("\n".join([HEADERS[name], *rows]) + "\n")


def base(tmp_path):
    write(tmp_path, "taxpayers.csv", "TP-1,A B,F,1990-01-01,AAAPA9999A,Pune,RESIDENT")


def test_BR38_order_set_off_then_deductions_then_tax():
    ds = make(salary=[sal(months=12, basic=100000)], houses=[house("SELF_OCCUPIED", interest=300000)],
              invs=[inv("80C", "PPF", 150000)])
    s = compute(ds, "T", "OLD", FILING)
    assert s.income_salary == 1200000 - 50000
    assert s.hp_loss_set_off == 200000                                   # set-off first ...
    assert s.gross_total_income == 950000                                 # ... gives GTI ...
    assert s.taxable_income == 800000                                     # ... then Chapter VI-A
    assert s.rule_ids.index("BR-15") < s.rule_ids.index("BR-31")


def test_BR39_invalid_lines_are_rejected_with_reason(tmp_path):
    base(tmp_path)
    write(tmp_path, "investments.csv",
          "I-1,TP-1,80C,PPF,50000,2025-09-01,,",             # fine
          "I-2,TP-1,80C,LIC,24000,2026-04-02,,",             # after the FY
          "I-3,TP-1,80C,PPF,-5,2025-09-01,,",                # negative
          "I-4,TP-9,80C,PPF,100,2025-09-01,,",               # unknown taxpayer
          "I-5,TP-1,80D,HEALTH_SELF,100,2025-09-01,,",       # insured missing
          "I-6,TP-1,80C,PPF,100,not-a-date,,")               # bad date
    write(tmp_path, "capital_gains.csv",
          "C-1,TP-1,GOLD,2025-09-01,2025-08-01,100,200,0",   # sold before bought
          "C-2,TP-1,CRYPTO,2024-01-01,2025-08-01,100,200,0", # unknown asset
          "C-3,TP-1,GOLD,2024-01-01,2026-05-01,100,200,0")   # sale outside FY
    ds = load_dataset(tmp_path)
    rejected = {rid: reason for _, rid, reason in ds.rejections}
    assert set(rejected) == {"I-2", "I-3", "I-4", "I-5", "I-6", "C-1", "C-2", "C-3"}
    assert "outside FY" in rejected["I-2"] and "negative" in rejected["I-3"]
    assert len(ds.investments["TP-1"]) == 1 and not ds.gains["TP-1"]


def test_BR40_duplicate_tds_certificate_credited_once(tmp_path):
    base(tmp_path)
    write(tmp_path, "tds.csv", "TDS-7,TP-1,BANK,IVRE14162D,194A,1825.00",
          "TDS-7,TP-1,BANK,IVRE14162D,194A,1825.00", "TDS-8,TP-1,EMPLOYER,AAAA11111A,192,1000.00")
    ds = load_dataset(tmp_path)
    assert sum(t.amount for t in ds.tds["TP-1"]) == 2825
    assert [r[1] for r in ds.rejections] == ["TDS-7"]


def test_BR41_commands_run_in_order_and_later_compute_replaces(tmp_path):
    base(tmp_path)
    write(tmp_path, "salary.csv", "S-1,TP-1,2025-04,2026-03,100000,0,0,0,0,0,0,,false")
    (tmp_path / "commands.txt").write_text(
        "# comment\n\nPRINT_SHEET|TP-1|OLD\n"                      # before COMPUTE -> rejected
        "COMPUTE|TP-1|2026-07-24\nPRINT_COMPARISON|TP-1\n"
        "COMPUTE|TP-1|2026-10-30\nPRINT_COMPARISON|TP-1\n"
        "COMPUTE|TP-9|2026-07-24\nFOO|TP-1\n")
    result = run_commands(load_dataset(tmp_path), tmp_path / "commands.txt")
    assert [c["filing_date"] for c in result.comparisons] == ["2026-07-24", "2026-10-30"]
    reasons = [r[2] for r in result.rejections]
    assert any("not been computed" in x for x in reasons) and any("unknown taxpayer" in x for x in reasons)
    assert any("unknown command" in x for x in reasons)


def test_sample_pack_end_to_end(tmp_path):
    ds = load_dataset(SAMPLE)
    result = run_commands(ds, SAMPLE / "commands.txt")
    write_outputs(result, tmp_path)
    sheets = list(csv.reader(open(tmp_path / "computation_sheet.csv")))
    assert sheets[0] == SHEET_COLUMNS and len(SHEET_COLUMNS) == 40 and len(sheets) == 31
    assert list(csv.reader(open(tmp_path / "regime_comparison.csv")))[0] == COMPARISON_COLUMNS
    assert [(r[0], r[1]) for r in list(csv.reader(open(tmp_path / "rejections.csv")))[1:]] == \
        [("investments.csv", "INV-016"), ("tds.csv", "TDS-007")]
    by = {(s.taxpayer_id, s.regime): s for s in result.sheets}
    assert by[("TP-001", "NEW")].total_tax == 10                           # EC-01
    assert by[("TP-003", "NEW")].marginal_relief_surcharge == 118933       # EC-02
    assert by[("TP-015", "NEW")].surcharge == 0                            # EC-02
    assert by[("TP-009", "OLD")].ltcg_equity_12_5 == 0                     # EC-03
    assert by[("TP-006", "OLD")].hra_exemption == 180000                   # EC-04
    assert (by[("TP-014", "OLD")].hp_loss_set_off, by[("TP-014", "OLD")].cf_hp_loss) == (100000, 150000)  # EC-05
    assert by[("TP-008", "OLD")].age_category == "60_79"                   # EC-06
    assert by[("TP-007", "OLD")].cf_stcl == 130000                         # EC-07
    assert by[("TP-010", "OLD")].taxable_income == 500000 and by[("TP-010", "OLD")].total_tax == 0
