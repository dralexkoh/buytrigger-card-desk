"""Chase cards: the story strip, and the set-page block above the price table."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import raw_price_page
import delta_reign_prices
import sv_151_prices
import prismatic_evolutions_prices
import thirtieth_prices
import tcg_modern_prices
import paldean_fates_prices
import crown_zenith_prices
import fusion_strike_prices
from chase_cards import render_chase_cards, validate_chase_cards
from editorial_visuals import validate_editorial_visuals

ROOT = Path(__file__).resolve().parents[1]
KEEPER = {
    'delta-reign': ['728061', '728062', '726574', '726567', '726576', '728060', '727592', '726565', '726575', '726563'],
    'sv-151': ['517045', '517046', '517044', '502556', '502549', '517048', '517018', '517047', '516997', '513721'],
    'prismatic-evolutions': ['610516', '610511', '610499', '610510', '610505', '610504', '610501', '610508', '610522', '610517'],
    'paldean-fates': ['534919', '535090', '535085', '534522', '534683', '535193', '535527', '534483', '535191', '535215'],
    'crown-zenith': ['478100', '477057', '478101', '478099', '478097', '477060', '478027', '478077', '477061', '478067'],
    'fusion-strike': ['253266', '253265', '253177', '253147', '253176', '253138', '253146', '253371', '253155', '253171'],
}
MODULES = {
    'delta-reign': delta_reign_prices,
    'sv-151': sv_151_prices,
    'prismatic-evolutions': prismatic_evolutions_prices,
    'paldean-fates': paldean_fates_prices,
    'crown-zenith': crown_zenith_prices,
    'fusion-strike': fusion_strike_prices,
}


def card(name='Raikou ex', image='assets/card.jpg', **extra):
    base = {'name': name, 'image': image, 'alt': f'{name} catalogue reference'}
    base.update(extra)
    return base


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
            snapshot = module.load_snapshot(ROOT / module.SNAPSHOT)
            self.assertIn('as of ' + module.format_source_date(snapshot['source_date']), text)
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
        for module in (tcg_modern_prices,):
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


class StoryChaseStripTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'assets').mkdir()
        (self.root / 'assets/card.jpg').write_bytes(b'fixture')
        (self.root / 'assets/two.jpg').write_bytes(b'fixture')
        (self.root / 'assets/three.jpg').write_bytes(b'fixture')
        self.story = {
            'slug': 'example',
            'image': 'assets/card.jpg',
            'imageAlt': 'A collecting illustration',
            'imageCredit': 'Original editorial illustration',
            'visualStyle': 'brand-graphic-v1',
        }
        self.editorial = {'articles': [self.story], 'wire': []}

    def tearDown(self):
        self.temp.cleanup()

    def strip(self, count=3, **extra):
        names = ('Raikou ex', 'Golurk ex', 'Zinnia', 'Rayquaza', 'Mew', 'Lugia')
        images = ('assets/card.jpg', 'assets/two.jpg', 'assets/three.jpg') * 2
        cards = [card(names[i], images[i], set='Delta Reign', number=f'{i+1}/103') for i in range(count)]
        self.story['chase_cards'] = cards
        self.story['chase_cards_credit'] = 'Card image: TCGplayer. Card artwork © Pokémon.'
        self.story.update(extra)
        return cards

    def test_absent_strip_is_not_rendered(self):
        self.assertEqual(render_chase_cards(self.story), '')
        self.assertEqual(validate_editorial_visuals(self.editorial, self.root), 1)
        self.assertNotIn('chase-strip', render_chase_cards({}))

    def test_three_to_six_cards_render_after_validation(self):
        for count in (3, 6):
            with self.subTest(count=count):
                self.strip(count)
                validate_chase_cards(self.story, self.root, 'example')
                html = render_chase_cards(self.story)
                self.assertEqual(html.count('<li>'), count)
                self.assertEqual(html.count('loading="lazy"'), count)
                self.assertIn('aria-label="Chase cards"', html)
                self.assertIn('Card image: TCGplayer. Card artwork © Pokémon.', html)
                self.assertIn('alt="Raikou ex catalogue reference"', html)
                self.assertIn('Delta Reign · 1/103', html)
                self.assertNotIn('target="_blank"', html)

    def test_optional_link_is_escaped_and_marked_external(self):
        self.strip(3)
        self.story['chase_cards'][0]['link'] = 'https://www.tcgplayer.com/product/726574'
        self.story['chase_cards'][1]['name'] = 'A & B <script>'
        validate_chase_cards(self.story, self.root, 'example')
        html = render_chase_cards(self.story)
        self.assertIn('href="https://www.tcgplayer.com/product/726574"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        self.assertIn('A &amp; B &lt;script&gt;', html)
        self.assertNotIn('<script>', html)

    def test_wrong_count_missing_credit_and_unsafe_image_are_rejected(self):
        self.strip(3)
        for count in (0, 2, 7):
            with self.subTest(count=count):
                story = copy.deepcopy(self.story)
                story['chase_cards'] = [card(f'Card {i}', 'assets/card.jpg') for i in range(count)]
                with self.assertRaises(ValueError):
                    validate_chase_cards(story, self.root, 'example')
        for broken in (
            {'chase_cards_credit': ''},
            {'chase_cards_credit': None},
        ):
            story = copy.deepcopy(self.story)
            story.update(broken)
            with self.assertRaises(ValueError):
                validate_editorial_visuals({'articles': [story]}, self.root)
        story = copy.deepcopy(self.story)
        story['chase_cards'][0]['image'] = 'assets/../outside.jpg'
        story['chase_cards'][0]['alt'] = ''
        with self.assertRaises(ValueError):
            validate_chase_cards(story, self.root, 'example')
        story = copy.deepcopy(self.story)
        story['chase_cards'][0]['link'] = 'javascript:alert(1)'
        with self.assertRaises(ValueError):
            validate_chase_cards(story, self.root, 'example')

    def test_credit_without_cards_is_rejected(self):
        self.story['chase_cards_credit'] = 'Card image: TCGplayer.'
        with self.assertRaises(ValueError):
            validate_chase_cards(self.story, self.root, 'example')

    def test_live_demo_uses_the_delta_reign_chase_story(self):
        editorial = json.loads((ROOT / 'editorial.json').read_text())
        guide = next(a for a in editorial['articles'] if a['slug'] == 'delta-reign-product-guide-october')
        self.assertNotIn('chase_cards', guide)
        self.assertEqual(render_chase_cards(guide), '')
        article = next(a for a in editorial['articles'] if a['slug'] == 'delta-reign-chase-card-prices-november-2026')
        validate_chase_cards(article, ROOT, article['slug'])
        html = render_chase_cards(article)
        self.assertEqual(len(article['chase_cards']), 5)
        for entry in article['chase_cards']:
            self.assertTrue((ROOT / entry['image']).is_file())
            self.assertIn(entry['image'], html)
            self.assertIn(f'alt="{entry["alt"]}"', html)
        self.assertIn('Card image: TCGplayer.', html)
        index = next(a for a in editorial['articles'] if a['slug'] == 'how-the-index-works')
        index_text = json.dumps(index)
        self.assertIn('PSA 10 last sales are shown where a reviewed figure is available.', index_text)
        self.assertIn('PSA 9 is not shown.', index_text)
        for item in editorial['wire']:
            # Wire briefs may carry a strip; any that do must validate.
            if render_chase_cards(item):
                validate_chase_cards(item, ROOT, item['id'])
        self.assertTrue(all('chase_cards' not in item or item['slug'] == article['slug'] for item in editorial['articles']))
        browser = (ROOT / 'editorial.js').read_text()
        self.assertTrue(browser.startswith('window.BT_EDITORIAL='))
        payload = browser[len('window.BT_EDITORIAL='):].strip()
        if payload.endswith(';'):
            payload = payload[:-1]
        self.assertEqual(json.loads(payload), editorial)


if __name__ == '__main__':
    unittest.main()
