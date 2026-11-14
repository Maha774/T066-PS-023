"""Every rule in the register must be exercised by a test whose name carries its ID."""
import re
from pathlib import Path

from taxengine.rules import REGISTER


def test_every_rule_id_has_a_test():
    text = " ".join(p.read_text() for p in Path(__file__).parent.glob("test_*.py") if p.name != Path(__file__).name)
    named = set(re.findall(r"def test_(BR\d\d)", text))
    missing = [rid for rid in REGISTER if rid.replace("-", "") not in named]
    assert not missing, f"no test named for: {missing}"
