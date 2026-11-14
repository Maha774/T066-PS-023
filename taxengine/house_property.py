"""House property head and the loss set-off against other income."""
from .constants import (HP_LOSS_SETOFF_CAP, LETOUT_STD_PCT, SO_INTEREST_CAP)
from .util import ZERO


def compute_house_property(properties, regime):
    """Return (income_or_loss, rule_ids). A negative number is a loss."""
    total, rules = ZERO, set()
    for hp in properties:
        if hp.property_type == "SELF_OCCUPIED":
            total -= min(hp.home_loan_interest, SO_INTEREST_CAP[regime])   # BR-13
            rules.add("BR-13")
        else:
            nav = hp.annual_rent_received - hp.municipal_tax_paid           # BR-14
            total += nav - nav * LETOUT_STD_PCT - hp.home_loan_interest
            rules.add("BR-14")
    return total, rules


def set_off_loss(hp_income, available_income):
    """BR-15: set-off is limited by BOTH the Rs 2 lakh cap and the income available.
    Returns (amount_set_off, loss_carried_forward)."""
    if hp_income >= 0:
        return ZERO, ZERO
    loss = -hp_income
    set_off = min(loss, HP_LOSS_SETOFF_CAP, max(ZERO, available_income))
    return set_off, loss - set_off
