"""Plain data records read from the CSV files."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class Taxpayer:
    taxpayer_id: str
    full_name: str
    date_of_birth: date
    city: str = ""


@dataclass(frozen=True)
class SalaryLine:
    line_id: str
    taxpayer_id: str
    months: int  # number of months in the period (from_month..to_month inclusive)
    basic_pm: Decimal
    hra_pm: Decimal
    special_pm: Decimal
    lta_pm: Decimal
    employer_nps_pm: Decimal
    professional_tax_pm: Decimal
    rent_paid_pm: Decimal
    rent_city: str
    metro_city: bool


@dataclass(frozen=True)
class HouseProperty:
    hp_id: str
    taxpayer_id: str
    property_type: str  # SELF_OCCUPIED | LET_OUT
    annual_rent_received: Decimal
    municipal_tax_paid: Decimal
    home_loan_interest: Decimal


@dataclass(frozen=True)
class CapitalGain:
    cg_id: str
    taxpayer_id: str
    asset_class: str
    purchase_date: date
    sale_date: date
    cost: Decimal
    sale_value: Decimal
    transfer_expenses: Decimal


@dataclass(frozen=True)
class OtherIncome:
    line_id: str
    taxpayer_id: str
    income_type: str
    amount: Decimal


@dataclass(frozen=True)
class Investment:
    inv_id: str
    taxpayer_id: str
    section: str
    item: str
    amount: Decimal
    payment_date: date
    insured: str = ""  # SELF | PARENTS (80D only)
    parents_age_60_plus: bool = False


@dataclass(frozen=True)
class Tds:
    tds_id: str
    taxpayer_id: str
    amount: Decimal


@dataclass(frozen=True)
class AdvanceTax:
    payment_id: str
    taxpayer_id: str
    payment_date: date
    amount: Decimal


@dataclass
class Dataset:
    taxpayers: dict = field(default_factory=dict)
    salary: dict = field(default_factory=dict)       # taxpayer_id -> [SalaryLine]
    house: dict = field(default_factory=dict)
    gains: dict = field(default_factory=dict)
    other: dict = field(default_factory=dict)
    investments: dict = field(default_factory=dict)
    tds: dict = field(default_factory=dict)
    advance: dict = field(default_factory=dict)
    rejections: list = field(default_factory=list)   # (source_file, record_id, reason)
