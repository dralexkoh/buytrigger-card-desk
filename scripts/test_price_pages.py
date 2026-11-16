"""Price pages follow data/prices/<slug>.json, including a rewritten copy."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import raw_price_page
import tcg_modern_prices
import thirtieth_prices

ROOT = Path(__file__).resolve().parents[1]


class SnapshotFollowsEdits(unittest.TestCase):
    def test_published_page_follows_a_temporary_price_and_date(self):
        modules = (thirtieth_prices, tcg_modern_prices)
        originals = {module: (ROOT / module.SNAPSHOT).read_text() for module in modules}
        try:
            for module in modules:
                data = json.loads(originals[module])
                data['source_date'] = '2026-08-09'
                data['cards'] = data['cards'][:-1]
                chosen = data['cards'][0]
                chosen['raw_price_usd'] = 9876.54
                dropped = json.loads(originals[module])['cards'][-1]['tcgplayer_product_id']
                (ROOT / module.SNAPSHOT).write_text(json.dumps(data))
                with tempfile.TemporaryDirectory() as tmp:
                    module.publish_price_page(ROOT, Path(tmp))
                    html = (Path(tmp) / module.PAGE_REL).read_text()
                page = BeautifulSoup(html, 'html.parser')
                text = page.get_text(' ')
                rows = page.select('#price-table tbody tr')
                self.assertEqual(len(rows), len(data['cards']))
                self.assertIn(f'All {len(data["cards"])} cards', text)
                self.assertIn('as of 9 Aug 2026', text)
                self.assertNotIn('13 Nov 2026', text)
                self.assertNotIn(str(dropped), {row['data-id'] for row in rows})
                row = page.select_one(f'#price-table tr[data-id="{chosen["tcgplayer_product_id"]}"]')
                self.assertEqual(row.select_one('.price-usd').get_text(), '$9,876.54')
                self.assertEqual(row['data-price'], '9876.54')
                self.assertEqual(module.source_date(ROOT), '2026-08-09')
        finally:
            for module, original in originals.items():
                (ROOT / module.SNAPSHOT).write_text(original)

    def test_fragment_links_become_root_absolute_without_touching_external_urls(self):
        self.assertEqual(raw_price_page.root_absolute_href('#journal'), '/index.html#journal')
        self.assertEqual(raw_price_page.root_absolute_href('drops.html'), '/drops.html')
        self.assertEqual(raw_price_page.root_absolute_href('index.html#method'), '/index.html#method')
        self.assertEqual(raw_price_page.root_absolute_href('prices/tcg-modern/'), '/prices/tcg-modern/')
        self.assertEqual(raw_price_page.root_absolute_href('/rss.xml'), '/rss.xml')
        self.assertEqual(
            raw_price_page.root_absolute_href('https://cards.alexkoh.me/'),
            'https://cards.alexkoh.me/',
        )


if __name__ == '__main__':
    unittest.main()
