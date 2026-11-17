"""Chase cards sit above the full price table and follow roster chase_rank."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import raw_price_page
import delta_reign_prices
import sv_151_prices
import prismatic_evolutions_prices
import thirtieth_prices
import tcg_modern_prices

ROOT = Path(__file__).resolve().parents[1]
KEEPER = {
    'delta-reign': ['728061', '728062', '726574', '726567', '726576', '728060', '727592', '726565', '726575', '726563'],
    'sv-151': ['517045', '517046', '517044', '502556', '502549', '517048', '517018', '517047', '516997', '513721'],
    'prismatic-evolutions': ['610516', '610511', '610499', '610510', '610505', '610504', '610501', '610508', '610522', '610517'],
}
MODULES = {
    'delta-reign': delta_reign_prices,
    'sv-151': sv_151_prices,
    'prismatic-evolutions': prismatic_evolutions_prices,
}


class ChasePricePages(unittest.TestCase):
    def test_each_set_page_leads_with_the_keeper_order(self):
        for slug, ids in KEEPER.items():
            module = MODULES[slug]
            page = BeautifulSoup(module.render_page(ROOT), 'html.parser')
            main = page.select_one('main')
            block = page.select_one('#chase-cards')
            table = page.select_one('#price-table')
            self.assertIsNotNone(block, slug)
            self.assertLess(str(main).find('id="chase-cards"'), str(main).find('id="price-table"'))
            self.assertEqual(block.select_one('h2').get_text(), 'Chase cards')
            tiles = block.select('.chase-tile')
            self.assertEqual([tile['data-chase-card'] for tile in tiles], ids)
            text = block.get_text(' ')
            self.assertIn('TCGCSV market price', text)
            self.assertIn('as of 16 Nov 2026', text)
            self.assertIn('not offers', text)
            for tile, product_id in zip(tiles, ids):
                image = tile.select_one('img')
                self.assertEqual(image['src'], f'assets/{slug}/{product_id}.jpg')
                self.assertTrue((ROOT / image['src']).is_file())
                row = table.select_one(f'tr[id="card-{product_id}"]')
                self.assertEqual(row['data-id'], product_id)
                self.assertTrue(tile.select_one('strong').get_text())
                self.assertEqual(tile.select_one('.chase-number').get_text(), row['data-number'])

    def test_pages_without_a_roster_do_not_invent_a_chase_block(self):
        for module in (thirtieth_prices, tcg_modern_prices):
            page = BeautifulSoup(module.render_page(ROOT), 'html.parser')
            self.assertIsNone(page.select_one('#chase-cards'))

    def test_rank_order_is_the_roster_field_and_a_missing_image_stays_text(self):
        priced = [
            {'product_id': '20', 'name': 'Second - 002/103', 'number': '002/103', 'price': 2, 'image': None, 'label': 'Rare'},
            {'product_id': '10', 'name': 'First', 'number': '001/103', 'price': 9, 'image': 'assets/delta-reign/10.jpg', 'label': 'Rare'},
        ]
        roster = {'chase_source': 'keeper-2026-11-17', 'cards': [
            {'productId': '20', 'chase_rank': 1},
            {'productId': '10', 'chase_rank': 2},
            {'productId': '30'},
        ]}
        chosen = raw_price_page.chase_cards(priced, roster)
        self.assertEqual([card['product_id'] for card in chosen], ['20', '10'])
        html = raw_price_page.chase_block(chosen, {'price_header': 'Raw price'}, '16 Nov 2026', 'Raw (ungraded) market guide prices, source: TCGCSV market price, as of 16 Nov 2026')
        page = BeautifulSoup(html, 'html.parser')
        self.assertIsNone(page.select_one('[data-chase-card="20"] img'))
        self.assertIn('Second', page.select_one('[data-chase-card="20"] .chase-fallback').get_text())
        self.assertNotIn('http', html)


if __name__ == '__main__':
    unittest.main()
