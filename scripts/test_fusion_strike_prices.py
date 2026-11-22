"""Public Fusion Strike raw-price page."""
from __future__ import annotations

from pathlib import Path
import json
import re
import sys
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digest_signup
import fusion_strike_prices as prices
import raw_price_page

ROOT = Path(__file__).resolve().parents[1]


def release_date():
    return json.loads((ROOT / 'refresh-status.json').read_text())['sourceDate']


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = prices.load_snapshot(ROOT / prices.SNAPSHOT)
        self.cards = prices.prepare_cards(self.snapshot, ROOT)
        self.html = prices.render_page(ROOT)

    def test_snapshot_is_the_full_english_set(self):
        self.assertEqual(len(self.cards), 284)
        self.assertEqual(self.snapshot['source_date'], release_date())
        self.assertEqual(self.snapshot['set_slug'], 'fusion-strike')
        self.assertTrue(all(card['image'] and (ROOT / card['image']).is_file() for card in self.cards))
        self.assertTrue(all(card['price'] and card['price'] > 0 for card in self.cards))
        self.assertTrue(all(card['image'].startswith('assets/fusion-strike/') for card in self.cards))

    def test_default_order_is_raw_price_high_to_low(self):
        ordered = [card['price'] for card in self.cards]
        self.assertEqual(ordered, sorted(ordered, reverse=True))

    def test_gengar_vmax_alternate_art_is_271(self):
        card = next(card for card in self.cards if card['product_id'] == '253266')
        self.assertEqual(card['number'], '271/264')
        self.assertIn('Gengar VMAX', card['name'])
        secrets = [card for card in self.cards if int(card['number'].split('/', 1)[0]) > 264]
        self.assertEqual(len(secrets), 20)


class PageTests(unittest.TestCase):
    def setUp(self):
        self.html = prices.render_page(ROOT)
        self.page = BeautifulSoup(self.html, 'html.parser')

    def test_page_lists_every_card_without_graded_or_trading_language(self):
        rows = self.page.select('#price-table tbody tr')
        self.assertEqual(len(rows), 284)
        editorial = raw_price_page.without_ebay_buttons(self.html)
        self.assertNotIn('PSA', editorial)
        self.assertIsNone(re.search(r'(?<!un)graded', self.html, re.I))
        text = BeautifulSoup(editorial, 'html.parser').get_text(' ')
        date = prices.format_source_date(prices.load_snapshot(ROOT / prices.SNAPSHOT)['source_date'])
        self.assertIn(f'Raw (ungraded) market guide prices, source: TCGCSV market price, as of {date}', text)
        self.assertIn('US-market references in USD, not offers.', text)
        self.assertIn('These figures follow the daily market-guide release.', text)
        self.assertIn('Card image: The Pokémon Company / pokemon.com', text)
        self.assertIsNone(re.search(r'\b(buy|sell|accumulate|invest)\b', text, re.I))
        self.assertIsNone(re.search(r'index level|index change|since launch|performance', text, re.I))
        bare = re.sub(r'BuyTrigger\.Cards', '', text, flags=re.I)
        bare = re.sub(r'BUYTRIGGER\.CARDS', '', bare)
        self.assertNotIn('BuyTrigger', bare)
        self.assertNotIn('BUYTRIGGER', bare)

    def test_metadata_canonical_and_footer(self):
        self.assertEqual(self.page.title.get_text(), 'Pokémon Fusion Strike raw prices · BuyTrigger.Cards')
        self.assertIn('all 284 English', self.page.select_one('meta[name=description]')['content'])
        self.assertEqual(self.page.select_one('link[rel=canonical]')['href'], prices.PRICE_PAGE_URL)
        self.assertEqual(self.page.select_one('footer a[href="/prices/fusion-strike/"]').get('aria-current'), 'page')
        self.assertEqual(self.page.select_one('footer a[href="/prices/fusion-strike/"]').get_text(), 'Fusion Strike prices')

    def test_rows_use_local_images_and_plain_tcgplayer_links(self):
        images = self.page.select('#price-table .price-card img')
        self.assertEqual(len(images), 284)
        self.assertTrue(all(img['src'].startswith('assets/fusion-strike/') and img['src'].endswith('.jpg') for img in images))
        links = self.page.select('#price-table a.price-check')
        self.assertEqual(len(links), 284)

    def test_reuses_the_shared_digest_band(self):
        block = self.page.select_one('.digest-signup')
        self.assertIsNotNone(block)
        self.assertEqual(block.select_one('form.digest-form')['action'], 'https://buytriggercards.substack.com/subscribe')

    def test_sort_controls_are_present(self):
        self.assertEqual(self.page.select_one('#price-sort option[selected]')['value'], 'price-desc')
        self.assertIsNotNone(self.page.select_one('#price-filter'))


if __name__ == '__main__':
    unittest.main()
