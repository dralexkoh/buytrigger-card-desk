import copy
import json
import tempfile
import unittest
from pathlib import Path

from chase_cards import render_chase_cards, validate_chase_cards
from editorial_visuals import validate_editorial_visuals

ROOT = Path(__file__).resolve().parents[1]


def card(name='Raikou ex', image='assets/card.jpg', **extra):
    base = {'name': name, 'image': image, 'alt': f'{name} catalogue reference'}
    base.update(extra)
    return base


class ChaseCardTests(unittest.TestCase):
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
        self.assertTrue(all(render_chase_cards(item) == '' for item in editorial['wire']))
        self.assertTrue(all('chase_cards' not in item or item['slug'] == article['slug'] for item in editorial['articles']))
        browser = (ROOT / 'editorial.js').read_text()
        self.assertTrue(browser.startswith('window.BT_EDITORIAL='))
        self.assertEqual(json.loads(browser[len('window.BT_EDITORIAL='):-1]), editorial)


if __name__ == '__main__':
    unittest.main()
