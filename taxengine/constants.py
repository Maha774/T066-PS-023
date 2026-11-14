"""Every number from the brief lives here, so a rule change is a one-line edit."""
from datetime import date
from decimal import Decimal as D

FY_START = date(2025, 4, 1)
FY_END = date(2026, 3, 31)
AY_START = date(2026, 4, 1)  # 234B interest runs from here to the filing date

# (upper limit of band, rate %) - last band has no upper limit
OLD_SLABS = {
    "BELOW_60": [(250000, 0), (500000, 5), (1000000, 20), (None, 30)],
    "60_79": [(300000, 0), (500000, 5), (1000000, 20), (None, 30)],
    "80_PLUS": [(500000, 0), (1000000, 20), (None, 30)],
}
NEW_SLABS = [(300000, 0), (700000, 5), (1000000, 10), (1200000, 15), (1500000, 20), (None, 30)]

STD_DEDUCTION = {"OLD": D(50000), "NEW": D(75000)}
PT_CAP = D(2500)
HRA_RENT_BASIC_PCT = D("0.10")
HRA_PCT_OF_BASIC = {True: D("0.50"), False: D("0.40")}  # metro? -> percentage

CAP_80C = D(150000)
CAP_80CCD_1B = D(50000)
CAP_80D_SELF = {"BELOW_60": D(25000), "60_79": D(50000), "80_PLUS": D(50000)}
CAP_80D_PARENTS = {False: D(25000), True: D(50000)}  # parents 60+? -> cap
CHECKUP_CAP = D(5000)
NPS_EMPLOYER_PCT = {"OLD": D("0.10"), "NEW": D("0.14")}

SO_INTEREST_CAP = {"OLD": D(200000), "NEW": D(0)}
LETOUT_STD_PCT = D("0.30")
HP_LOSS_SETOFF_CAP = D(200000)

EQUITY_CLASSES = {"LISTED_EQUITY", "EQUITY_MF"}
OTHER_CLASSES = {"LAND_BUILDING", "GOLD", "UNLISTED_SHARES"}
EQUITY_LT_MONTHS = 12
OTHER_LT_MONTHS = 24
LTCG_EQUITY_EXEMPTION = D(125000)
STCG_EQUITY_RATE = D("0.20")
LTCG_RATE = D("0.125")

# regime -> (income limit for rebate, maximum rebate)
REBATE_87A = {"OLD": (D(500000), D(12500)), "NEW": (D(700000), D(25000))}

# (income must be GREATER than threshold, surcharge %)
SURCHARGE_BANDS = [(D(5000000), 10), (D(10000000), 15), (D(20000000), 25), (D(50000000), 37)]
SURCHARGE_CAP_NEW = 25
SURCHARGE_CAP_CAPITAL_GAINS = D(15)
CESS_RATE = D("0.04")

INTEREST_MIN_NET_TAX = D(10000)  # 234B/234C only if tax after TDS is above this
INTEREST_RATE = D("0.01")
# 234C: (due date, cumulative % of tax that must be paid by then)
ADVANCE_SCHEDULE = [
    (date(2025, 6, 15), D("0.15")),
    (date(2025, 9, 15), D("0.45")),
    (date(2025, 12, 15), D("0.75")),
    (date(2026, 3, 15), D("1.00")),
]
