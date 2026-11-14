"""Tiny builders so each test shows only the numbers it cares about."""
from datetime import date
from decimal import Decimal as D

from taxengine.models import (AdvanceTax, CapitalGain, Dataset, HouseProperty, Investment,
                              OtherIncome, SalaryLine, Taxpayer, Tds)

FILING = date(2026, 7, 24)


def sal(months=12, basic=0, hra=0, special=0, lta=0, nps=0, pt=0, rent=0, metro=False, city=""):
    return SalaryLine("S", "T", months, D(basic), D(hra), D(special), D(lta), D(nps), D(pt),
                      D(rent), city, metro)


def house(kind="SELF_OCCUPIED", rent=0, municipal=0, interest=0):
    return HouseProperty("H", "T", kind, D(rent), D(municipal), D(interest))


def cg(asset, bought, sold, cost, sale, expenses=0):
    return CapitalGain("C", "T", asset, date.fromisoformat(bought), date.fromisoformat(sold),
                       D(cost), D(sale), D(expenses))


def other(kind, amount):
    return OtherIncome("O", "T", kind, D(amount))


def inv(section, item, amount, insured="", senior=False):
    return Investment("I", "T", section, item, D(amount), date(2025, 9, 1), insured, senior)


def tds(amount, tds_id="TDS-1"):
    return Tds(tds_id, "T", D(amount))


def adv(amount, paid):
    return AdvanceTax("A", "T", date.fromisoformat(paid), D(amount))


def make(dob="1990-01-01", salary=(), houses=(), gains=(), others=(), invs=(), tds_=(), advance=()):
    ds = Dataset()
    ds.taxpayers["T"] = Taxpayer("T", "Test", date.fromisoformat(dob))
    ds.salary["T"], ds.house["T"], ds.gains["T"] = list(salary), list(houses), list(gains)
    ds.other["T"], ds.investments["T"] = list(others), list(invs)
    ds.tds["T"], ds.advance["T"] = list(tds_), list(advance)
    return ds
