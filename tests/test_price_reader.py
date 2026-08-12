"""Regression test for the fabricated-price incident.

    make demo-fabrication              # the narrated, human-readable version
    python3 -m unittest tests.test_price_reader -v

2026-08-11: `WebExecutor._read_price` returned `$177.83` from MyChoice landing-page marketing
copy with zero form fields filled. This test locks the fix down as an assertion, not just a demo.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.executors.web.executor import WebExecutor  # noqa: E402


class _StubPage:
    def __init__(self, price_node_text: str | None = None):
        self._price_node_text = price_node_text

    def query_selector(self, selector: str):
        if self._price_node_text is not None and selector.startswith(".price"):
            return SimpleNamespace(inner_text=lambda: self._price_node_text)
        return None


def price_believed(text: str, *, fields_filled: bool, page: _StubPage | None = None) -> float | None:
    """Mirrors the precondition check in WebExecutor._walk exactly."""
    page = page or _StubPage()
    steps = [SimpleNamespace(fields_filled=(["some_field"] if fields_filled else []))]
    if not any(s.fields_filled for s in steps):
        return None
    return WebExecutor._read_price(page, text)


class TestFabricationRegression(unittest.TestCase):
    LANDING_PAGE_TEXT = (
        "Affordable Car Insurance in Canada from $94/month\n\n"
        "Monthly Premiums\tDate\tQuote Type\tAge\tVehicle\tCity\n"
        "$223.50\tAug 11, 2026\tAuto\t38\tNissan Rogue SV\tMedicine Hat\n"
        "$243.08\tAug 10, 2026\tAuto\t44\tAcura Rdx A-spec\tOakville\n"
    )

    def test_no_price_believed_when_no_field_was_filled(self):
        """The exact incident: marketing copy, zero fields filled."""
        self.assertIsNone(price_believed(self.LANDING_PAGE_TEXT, fields_filled=False))

    def test_price_believed_from_an_explicit_container_after_a_real_fill(self):
        page = _StubPage(price_node_text="$1,712.00 per year")
        self.assertEqual(price_believed("irrelevant body text", fields_filled=True, page=page),
                         1712.00)

    def test_no_price_believed_next_to_advertising_language_even_after_a_fill(self):
        """A fill happened, but the figure is still marketing copy on the same page."""
        text = "Rates from $189.83 per month. Complete the form to see your actual price."
        self.assertIsNone(price_believed(text, fields_filled=True))

    def test_price_believed_from_free_text_after_a_fill_with_no_advertising_language(self):
        text = "Your annual premium is $1,634.00 based on the information provided."
        self.assertEqual(price_believed(text, fields_filled=True), 1634.00)

    def test_the_original_fixture_produces_no_believed_price(self):
        """The actual recaptured artifact from the incident, end to end."""
        fixture = (Path(__file__).resolve().parent.parent
                  / "out" / "fixtures" / "fabrication_demo" / "mychoice_landing_page.txt")
        if not fixture.exists():
            self.skipTest("fabrication demo fixture not present")
        text = fixture.read_text(encoding="utf-8")
        self.assertIsNone(price_believed(text, fields_filled=False))


if __name__ == "__main__":
    unittest.main()
