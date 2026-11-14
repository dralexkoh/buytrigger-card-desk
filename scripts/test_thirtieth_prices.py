"""Public 30th Anniversary raw-price page."""
from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digest_signup
import thirtieth_prices as prices

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIBE = 'https://buytriggercards.substack.com/subscribe?utm_source=site&utm_medium=signup&utm_campaign=thirtieth-anniversary-prices'
SOURCE = 'Raw (ungraded) prices, source: TCGCSV market price, as of 13 Nov 2026'


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = prices.load_snapshot(ROOT / prices.SNAPSHOT)
        self.cards = prices.prepare_cards(self.snapshot, ROOT)

    def test_snapshot_is_the_full_english_set(self):
        counts = {}
        for card in self.cards:
            counts[card['subset']] = counts.get(card['subset'], 0) + 1
        self.assertEqual(len(self.cards), 195)
        self.assertEqual(counts, {
            'ME: 30th Celebration': 161,
            'ME: 30th Celebration Classic Collection': 30,
            'ME: Mega Evolution Promo': 4,
        })
        self.assertEqual(self.snapshot['source_date'], '2026-11-13')
        self.assertTrue(all(card['image'] and (ROOT / card['image']).is_file() for card in self.cards))
        self.assertTrue(all(card['price'] and card['price'] > 0 for card in self.cards))

    def test_default_order_is_raw_price_high_to_low(self):
        ordered = [card['price'] for card in self.cards]
        self.assertEqual(ordered, sorted(ordered, reverse=True))
        self.assertEqual([card['name'] for card in self.cards[:3]], ['Mew - B/RGB', 'Mew - R/RGB', 'Mew - G/RGB'])


class PageTests(unittest.TestCase):
    def setUp(self):
        self.html = prices.render_page(ROOT)
        self.page = BeautifulSoup(self.html, 'html.parser')

    def test_page_lists_every_card_without_graded_or_trading_language(self):
        rows = self.page.select('#price-table tbody tr')
        self.assertEqual(len(rows), 195)
        self.assertNotIn('PSA', self.html)
        self.assertIsNone(re.search(r'(?<!un)graded', self.html, re.I))
        text = self.page.get_text(' ')
        self.assertIn(SOURCE, text)
        self.assertIn('Prices are US-market references in USD, not offers.', text)
        self.assertIsNone(re.search(r'\b(buy|sell|accumulate|invest)\b', text, re.I))
        self.assertIsNone(re.search(r'index level|index change|since launch|performance', text, re.I))
        bare = re.sub(r'BuyTrigger\.Cards', '', text, flags=re.I)
        bare = re.sub(r'BUYTRIGGER\.CARDS', '', bare)
        self.assertNotIn('BuyTrigger', bare)
        self.assertNotIn('BUYTRIGGER', bare)

    def test_metadata_canonical_and_footer(self):
        self.assertEqual(self.page.title.get_text(), 'Pokémon 30th Anniversary raw prices · BuyTrigger.Cards')
        self.assertIn('all 195 English', self.page.select_one('meta[name=description]')['content'])
        self.assertEqual(self.page.select_one('link[rel=canonical]')['href'], prices.PRICE_PAGE_URL)
        self.assertEqual(self.page.select_one('meta[property="og:url"]')['content'], prices.PRICE_PAGE_URL)
        self.assertIn('index, follow', self.page.select_one('meta[name=robots]')['content'])
        self.assertEqual(self.page.select_one('base')['href'], '../../')
        footer = self.page.select_one('footer a[href="prices/thirtieth-anniversary/"]')
        self.assertEqual(footer.get_text(), '30th Anniversary prices')
        self.assertEqual(footer.get('aria-current'), 'page')
        self.assertIsNone(self.page.select_one('script[src="site.js"]'))

    def test_rows_use_local_images_and_plain_tcgplayer_links(self):
        images = self.page.select('#price-table img')
        self.assertEqual(len(images), 195)
        self.assertTrue(all(img['src'].startswith('assets/thirtieth/') and img['src'].endswith('.jpg') for img in images))
        links = self.page.select('#price-table a')
        self.assertEqual(len(links), 195)
        ids = set()
        for link in links:
            self.assertTrue(link['href'].startswith('https://www.tcgplayer.com/product/'))
            self.assertNotIn('?', link['href'])
            self.assertNotIn('utm_', link['href'])
            rel = link['rel'] if isinstance(link.get('rel'), list) else str(link.get('rel')).split()
            self.assertIn('nofollow', rel)
            self.assertIn('noopener', rel)
            self.assertNotIn('sponsored', rel)
            ids.add(link['href'].rsplit('/', 1)[-1])
        self.assertEqual(len(ids), 195)
        self.assertEqual(self.page.select_one('#price-table tbody tr .price-number').get_text(), self.page.select_one('#price-table tbody tr')['data-number'])

    def test_reuses_the_digest_with_the_price_page_campaign(self):
        block = self.page.select_one('.digest-signup')
        self.assertIsNotNone(block)
        self.assertEqual(block.select_one('iframe')['src'], 'https://buytriggercards.substack.com/embed')
        self.assertEqual(block.select_one('.digest-fallback a')['href'], SUBSCRIBE)
        plain = digest_signup.digest_signup_html('story-slug')
        self.assertIn('utm_source=site&amp;utm_medium=signup"', plain)
        self.assertNotIn('utm_campaign', plain)

    def test_sort_and_filter_controls_are_present(self):
        self.assertEqual(self.page.select_one('#price-sort option[selected]')['value'], 'price-desc')
        self.assertEqual(self.page.select_one('th[aria-sort="descending"] button')['data-sort'], 'price')
        self.assertIsNotNone(self.page.select_one('#price-filter'))
        self.assertEqual(len(self.page.select('button[data-sort]')), 3)

    def test_missing_image_stays_text_and_is_not_hotlinked(self):
        snapshot = {
            'source_date': '2026-11-13',
            'cards': [{
                'name': 'Example',
                'number': '001/128',
                'set_name': 'ME: 30th Celebration',
                'raw_price_usd': 1.25,
                'tcgplayer_product_id': '999999',
                'image_path': 'assets/thirtieth/999999.jpg',
            }],
        }
        page = BeautifulSoup(prices.render_page(ROOT, snapshot), 'html.parser')
        self.assertIsNone(page.select_one('#price-table img'))
        self.assertIn('Example', page.select_one('.price-card-fallback').get_text())
        self.assertNotIn('http', page.select_one('.price-card').decode())


if __name__ == '__main__':
    unittest.main()
