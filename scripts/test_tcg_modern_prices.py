"""Public TCG Modern raw market-guide page."""
from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digest_signup
import tcg_modern_prices as prices

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIBE = 'https://buytriggercards.substack.com/subscribe?utm_source=site&utm_medium=signup&utm_campaign=tcg-modern-prices'


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = prices.load_snapshot(ROOT / prices.SNAPSHOT)
        self.cards = prices.prepare_cards(self.snapshot, ROOT)

    def test_snapshot_is_the_english_holofoil_list(self):
        sets = {card['subset'] for card in self.cards}
        self.assertEqual(len(self.cards), 99)
        self.assertEqual(len(sets), 40)
        self.assertEqual(self.snapshot['source_date'], '2026-11-13')
        self.assertEqual(self.snapshot['source'], 'TCGCSV marketPrice')
        self.assertTrue(all(card['price'] and card['price'] > 0 for card in self.cards))
        mews = [card for card in self.cards if str(card['image']).startswith('assets/thirtieth/')]
        self.assertEqual(sorted(card['product_id'] for card in mews), ['717607', '717608', '717609'])
        self.assertTrue(all((ROOT / card['image']).is_file() for card in mews))
        self.assertEqual(sum(1 for card in self.cards if card['image']), 3)

    def test_default_order_is_market_guide_high_to_low(self):
        ordered = [card['price'] for card in self.cards]
        self.assertEqual(ordered, sorted(ordered, reverse=True))


class PageTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = prices.load_snapshot(ROOT / prices.SNAPSHOT)
        self.cards = prices.prepare_cards(self.snapshot, ROOT)
        self.html = prices.render_page(ROOT)
        self.page = BeautifulSoup(self.html, 'html.parser')
        self.text = self.page.get_text(' ')
        self.date = prices.format_source_date(self.snapshot['source_date'])

    def test_page_lists_every_card_from_the_snapshot(self):
        rows = self.page.select('#price-table tbody tr')
        self.assertEqual(len(rows), len(self.cards))
        self.assertEqual(
            [row['data-id'] for row in rows],
            [card['product_id'] for card in self.cards],
        )
        sets = len({card['label'] for card in self.cards})
        self.assertIn(f'All {len(self.cards)} English Holofoil cards across {sets} sets.', self.text)
        self.assertIn(f'All {len(self.cards)} cards', self.text)
        self.assertIn(
            f'Raw (ungraded) market guide prices, source: TCGCSV market price, as of {self.date}.',
            self.text,
        )
        self.assertIn('US-market references in USD, not sales or offers.', self.text)
        self.assertNotIn('PSA', self.html)
        self.assertIsNone(re.search(r'(?<!un)graded', self.html, re.I))
        self.assertIsNone(re.search(r'\b(buy|sell|accumulate|invest)\b', self.text, re.I))
        self.assertIsNone(re.search(r'sale', re.sub(r'not sales or offers', '', self.text, flags=re.I), re.I))
        self.assertIsNone(re.search(
            r'index level|index change|since launch|week-on-week|7-day|7 day|performance|multiplier',
            self.text,
            re.I,
        ))
        bare = re.sub(r'BuyTrigger\.Cards', '', self.text, flags=re.I)
        bare = re.sub(r'BUYTRIGGER\.CARDS', '', bare)
        self.assertNotIn('BuyTrigger', bare)
        self.assertNotIn('BUYTRIGGER', bare)

    def test_metadata_canonical_footer_and_root_absolute_nav(self):
        count = len(self.cards)
        sets = len({card['label'] for card in self.cards})
        self.assertEqual(self.page.title.get_text(), 'TCG Modern raw market guide prices · BuyTrigger.Cards')
        description = self.page.select_one('meta[name=description]')['content']
        self.assertIn(f'all {count} English Holofoil TCG Modern cards across {sets} sets', description)
        self.assertIn(self.date, description)
        self.assertEqual(self.page.select_one('link[rel=canonical]')['href'], prices.PRICE_PAGE_URL)
        self.assertEqual(self.page.select_one('meta[property="og:url"]')['content'], prices.PRICE_PAGE_URL)
        self.assertIn('index, follow', self.page.select_one('meta[name=robots]')['content'])
        self.assertEqual(self.page.select_one('base')['href'], '../../')
        footer = self.page.select_one('footer a[href="/prices/tcg-modern/"]')
        self.assertEqual(footer.get_text(), 'TCG Modern prices')
        self.assertEqual(footer.get('aria-current'), 'page')
        other = self.page.select_one('footer a[href="/prices/thirtieth-anniversary/"]')
        self.assertEqual(other.get_text(), '30th Anniversary prices')
        self.assertIsNone(other.get('aria-current'))
        self.assertEqual(self.page.select_one('#site-nav a[data-nav="journal"]')['href'], '/index.html#journal')
        self.assertEqual(self.page.select_one('#site-nav a[data-nav="drops"]')['href'], '/drops.html')
        self.assertEqual(self.page.select_one('footer a[href="/rss.xml"]').get_text(), 'RSS')
        self.assertEqual(self.page.select_one('a.skip')['href'], '#main')
        for link in self.page.select('header.masthead a[href], footer a[href]'):
            href = link.get('href') or ''
            if href.startswith(('http://', 'https://', 'mailto:')):
                continue
            self.assertTrue(href.startswith('/'), href)
        self.assertIsNone(self.page.select_one('script[src="site.js"]'))

    def test_rows_use_repo_images_and_plain_tcgplayer_links(self):
        images = self.page.select('#price-table img')
        self.assertEqual(
            sorted(img['src'] for img in images),
            ['assets/thirtieth/717607.jpg', 'assets/thirtieth/717608.jpg', 'assets/thirtieth/717609.jpg'],
        )
        self.assertEqual(len(self.page.select('.price-card-fallback')), len(self.cards) - len(images))
        links = self.page.select('#price-table a')
        self.assertEqual(len(links), len(self.cards))
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
        self.assertEqual(ids, {card['product_id'] for card in self.cards})
        self.assertNotIn('tcg-modern-index', self.html)

    def test_reuses_the_digest_with_the_price_page_campaign(self):
        block = self.page.select_one('.digest-signup')
        self.assertIsNotNone(block)
        self.assertEqual(block.select_one('iframe')['src'], 'https://buytriggercards.substack.com/embed')
        self.assertEqual(block.select_one('.digest-fallback a')['href'], SUBSCRIBE)
        plain = digest_signup.digest_signup_html('story-slug')
        self.assertIn('utm_source=site&amp;utm_medium=signup&amp;utm_campaign=story-slug', plain)

    def test_sort_and_filter_controls_are_price_name_and_set(self):
        self.assertEqual(self.page.select_one('#price-sort option[selected]')['value'], 'price-desc')
        self.assertEqual(self.page.select_one('th[aria-sort="descending"] button')['data-sort'], 'price')
        self.assertEqual(
            [button['data-sort'] for button in self.page.select('button[data-sort]')],
            ['name', 'set', 'price'],
        )
        self.assertEqual(self.page.select_one('#price-filter')['placeholder'], 'Name, number or set')
        self.assertIsNone(self.page.select_one('button[data-sort="number"]'))

    def test_missing_image_stays_text_and_is_not_hotlinked(self):
        snapshot = {
            'source_date': '2026-11-13',
            'cards': [{
                'name': 'Example',
                'number': '001/128',
                'set_name': 'Example Set',
                'raw_price_usd': 12.5,
                'tcgplayer_product_id': '83857',
                'image_path': 'assets/tcg-modern/83857.jpg',
            }],
        }
        page = BeautifulSoup(prices.render_page(ROOT, snapshot), 'html.parser')
        self.assertIsNone(page.select_one('#price-table img'))
        self.assertIn('Example', page.select_one('.price-card-fallback').get_text())
        self.assertNotIn('http', page.select_one('.price-card').decode())
        self.assertEqual(page.select_one('.price-usd').get_text(), '$12.50')
        self.assertIn('as of 13 Nov 2026', page.get_text(' '))

    def test_only_the_three_mews_may_reuse_thirtieth_artwork(self):
        snapshot = {
            'source_date': '2026-11-13',
            'cards': [{
                'name': 'Not Mew',
                'number': '1/1',
                'set_name': 'Example Set',
                'raw_price_usd': 10,
                'tcgplayer_product_id': '83857',
                'image_path': 'assets/thirtieth/83857.jpg',
            }],
        }
        with self.assertRaises(ValueError):
            prices.render_page(ROOT, snapshot)


if __name__ == '__main__':
    unittest.main()
