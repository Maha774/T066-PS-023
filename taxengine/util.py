"""Small helpers: money rounding, month and date arithmetic."""
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

D = Decimal
ZERO = D("0")


def d(x) -> Decimal:
    return x if isinstance(x, Decimal) else D(str(x))


def round_rupee(x) -> Decimal:
    """Nearest rupee, halves round up (BR-36)."""
    return d(x).quantize(D("1"), rounding=ROUND_HALF_UP)


def round_ten(x) -> Decimal:
    """Nearest Rs 10, halves round up (BR-23)."""
    return (d(x) / 10).quantize(D("1"), rounding=ROUND_HALF_UP) * 10


def fmt(x) -> str:
    """Money printed with exactly 2 decimals."""
    return f"{d(x).quantize(D('0.01'), rounding=ROUND_HALF_UP):.2f}"


def add_months(start: date, n: int) -> date:
    """start + n calendar months; day is clamped to the month's length."""
    m = start.month - 1 + n
    year, month = start.year + m // 12, m % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def parse_month(s: str):
    year, month = s.strip().split("-")
    year, month = int(year), int(month)
    if not 1 <= month <= 12:
        raise ValueError(f"invalid month '{s}'")
    return year, month


def month_index(ym) -> int:
    return ym[0] * 12 + ym[1] - 1
