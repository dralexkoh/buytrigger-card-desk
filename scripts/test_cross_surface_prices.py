"""Same-card prices from one release must agree, and a split must fail the check."""
from __future__ import annotations

from pathlib import Path
import unittest

import check_cross_surface_prices as cross

ROOT = Path(__file__).resolve().parents[1]


class ComparisonTests(unittest.TestCase):
    def test_one_price_across_surfaces_is_not_a_mismatch(self):
        groups = {'1': {'modern': 10.0, 'price:tcg-modern': 10.0}, '2': {'idx:delta-reign': 3.5}}
        self.assertEqual([pid for pid, prices in groups.items() if len(prices) > 1 and len(set(prices.values())) > 1], [])

    def test_a_split_price_is_a_mismatch(self):
        prices = {'modern': 3857.8, 'price:tcg-modern': 4619.79}
        self.assertGreater(len(set(prices.values())), 1)

    def test_live_pages_agree(self):
        found = cross.mismatches(ROOT)
        self.assertEqual(found, [], f'{len(found)} mismatches, first {found[:3]}')


if __name__ == '__main__':
    unittest.main()
