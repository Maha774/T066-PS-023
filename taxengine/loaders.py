"""Read the CSV files, validate every line, and collect rejections (BR-39, BR-40)."""
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from .constants import FY_END, FY_START
from .models import (AdvanceTax, CapitalGain, Dataset, HouseProperty, Investment,
                     OtherIncome, SalaryLine, Taxpayer, Tds)
from .util import D, month_index, parse_month

ASSET_CLASSES = {"LISTED_EQUITY", "EQUITY_MF", "LAND_BUILDING", "GOLD", "UNLISTED_SHARES"}
INCOME_TYPES = {"SAVINGS_INTEREST", "FD_INTEREST", "DIVIDEND"}
HP_TYPES = {"SELF_OCCUPIED", "LET_OUT"}
SECTION_ITEMS = {
    "80C": {"EPF", "PPF", "ELSS", "LIC", "TUITION", "HL_PRINCIPAL"},
    "80CCD1B": {"NPS_SELF"},
    "80D": {"HEALTH_SELF", "HEALTH_PARENTS", "CHECKUP"},
}


def _rows(path: Path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _text(row, col, required=True):
    value = (row.get(col) or "").strip()
    if required and not value:
        raise ValueError(f"missing {col}")
    return value


def _money(row, col):
    raw = _text(row, col)
    try:
        value = D(raw)
    except Exception:
        raise ValueError(f"{col} is not a number: '{raw}'")
    if value < 0:
        raise ValueError(f"{col} is negative")
    return value


def _date(row, col):
    raw = _text(row, col)
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"{col} is not a valid date: '{raw}'")


def _bool(row, col, required=True):
    raw = _text(row, col, required).lower()
    if raw not in ("true", "false", ""):
        raise ValueError(f"{col} must be true or false")
    return raw == "true"


def _in_fy(value: date, col: str):
    if not FY_START <= value <= FY_END:
        raise ValueError(f"{col} {value} is outside FY 2025-26")


def load_dataset(data_dir) -> Dataset:
    data_dir = Path(data_dir)
    ds = Dataset()
    for name in ("taxpayers", "salary", "house_property", "capital_gains",
                 "other_income", "investments", "tds", "advance_tax"):
        _LOADERS[name](ds, _rows(data_dir / f"{name}.csv"))
    return ds


def _each(ds, filename, id_col, rows, build):
    """Run build(row) on every row; a ValueError rejects just that line."""
    for row in rows:
        record_id = (row.get(id_col) or "").strip() or "?"
        try:
            build(row)
        except ValueError as err:
            ds.rejections.append((filename, record_id, str(err)))


def _known(ds, row):
    tid = _text(row, "taxpayer_id")
    if tid not in ds.taxpayers:
        raise ValueError(f"unknown taxpayer_id {tid}")
    return tid


def _load_taxpayers(ds, rows):
    def build(r):
        tid = _text(r, "taxpayer_id")
        if tid in ds.taxpayers:
            raise ValueError("duplicate taxpayer_id")
        if _text(r, "residential_status").upper() != "RESIDENT":
            raise ValueError("only RESIDENT individuals are supported")
        ds.taxpayers[tid] = Taxpayer(tid, _text(r, "full_name"), _date(r, "date_of_birth"),
                                     _text(r, "city", False))
    _each(ds, "taxpayers.csv", "taxpayer_id", rows, build)


def _load_salary(ds, rows):
    ds.salary = defaultdict(list)

    def build(r):
        tid = _known(ds, r)
        try:
            start, end = parse_month(_text(r, "from_month")), parse_month(_text(r, "to_month"))
        except ValueError:
            raise ValueError("from_month/to_month must be YYYY-MM")
        if month_index(start) > month_index(end):
            raise ValueError("from_month is after to_month")
        if month_index(start) < month_index((2025, 4)) or month_index(end) > month_index((2026, 3)):
            raise ValueError("salary period is outside FY 2025-26")
        ds.salary[tid].append(SalaryLine(
            _text(r, "line_id"), tid, month_index(end) - month_index(start) + 1,
            _money(r, "basic_pm"), _money(r, "hra_pm"), _money(r, "special_pm"),
            _money(r, "lta_pm"), _money(r, "employer_nps_pm"), _money(r, "professional_tax_pm"),
            _money(r, "rent_paid_pm"), _text(r, "rent_city", False), _bool(r, "metro_city")))
    _each(ds, "salary.csv", "line_id", rows, build)


def _load_house(ds, rows):
    ds.house = defaultdict(list)

    def build(r):
        tid = _known(ds, r)
        kind = _text(r, "property_type")
        if kind not in HP_TYPES:
            raise ValueError(f"unknown property_type {kind}")
        ds.house[tid].append(HouseProperty(
            _text(r, "hp_id"), tid, kind, _money(r, "annual_rent_received"),
            _money(r, "municipal_tax_paid"), _money(r, "home_loan_interest")))
    _each(ds, "house_property.csv", "hp_id", rows, build)


def _load_gains(ds, rows):
    ds.gains = defaultdict(list)

    def build(r):
        tid = _known(ds, r)
        asset = _text(r, "asset_class")
        if asset not in ASSET_CLASSES:
            raise ValueError(f"unknown asset_class {asset}")
        bought, sold = _date(r, "purchase_date"), _date(r, "sale_date")
        if sold < bought:
            raise ValueError("sale_date is before purchase_date")
        _in_fy(sold, "sale_date")
        ds.gains[tid].append(CapitalGain(
            _text(r, "cg_id"), tid, asset, bought, sold, _money(r, "cost"),
            _money(r, "sale_value"), _money(r, "transfer_expenses")))
    _each(ds, "capital_gains.csv", "cg_id", rows, build)


def _load_other(ds, rows):
    ds.other = defaultdict(list)

    def build(r):
        tid = _known(ds, r)
        kind = _text(r, "income_type")
        if kind not in INCOME_TYPES:
            raise ValueError(f"unknown income_type {kind}")
        ds.other[tid].append(OtherIncome(_text(r, "line_id"), tid, kind, _money(r, "amount")))
    _each(ds, "other_income.csv", "line_id", rows, build)


def _load_investments(ds, rows):
    ds.investments = defaultdict(list)

    def build(r):
        tid = _known(ds, r)
        section, item = _text(r, "section"), _text(r, "item")
        if section not in SECTION_ITEMS or item not in SECTION_ITEMS[section]:
            raise ValueError(f"item {item} is not valid under section {section}")
        paid = _date(r, "payment_date")
        _in_fy(paid, "payment_date")
        insured = _text(r, "insured", False)
        if section == "80D":
            if insured not in ("SELF", "PARENTS"):
                raise ValueError("80D line needs insured = SELF or PARENTS")
            if item == "HEALTH_SELF" and insured != "SELF":
                raise ValueError("HEALTH_SELF must have insured = SELF")
            if item == "HEALTH_PARENTS" and insured != "PARENTS":
                raise ValueError("HEALTH_PARENTS must have insured = PARENTS")
        ds.investments[tid].append(Investment(
            _text(r, "inv_id"), tid, section, item, _money(r, "amount"), paid, insured,
            _bool(r, "parents_age_60_plus", False)))
    _each(ds, "investments.csv", "inv_id", rows, build)


def _load_tds(ds, rows):
    ds.tds = defaultdict(list)
    seen = set()

    def build(r):
        tid = _known(ds, r)
        tds_id = _text(r, "tds_id")
        amount = _money(r, "amount")
        if tds_id in seen:  # BR-40: a re-uploaded certificate is credited once
            raise ValueError("duplicate tds_id - credited once")
        seen.add(tds_id)
        ds.tds[tid].append(Tds(tds_id, tid, amount))
    _each(ds, "tds.csv", "tds_id", rows, build)


def _load_advance(ds, rows):
    ds.advance = defaultdict(list)

    def build(r):
        tid = _known(ds, r)
        paid = _date(r, "payment_date")
        _in_fy(paid, "payment_date")
        ds.advance[tid].append(AdvanceTax(_text(r, "payment_id"), tid, paid, _money(r, "amount")))
    _each(ds, "advance_tax.csv", "payment_id", rows, build)


_LOADERS = {
    "taxpayers": _load_taxpayers, "salary": _load_salary, "house_property": _load_house,
    "capital_gains": _load_gains, "other_income": _load_other,
    "investments": _load_investments, "tds": _load_tds, "advance_tax": _load_advance,
}
