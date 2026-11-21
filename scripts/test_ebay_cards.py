"""Buy on eBay card blocks in news briefs and Features (README data-ebay-card format)."""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ebay_cards import (render_ebay_cards, validate_ebay_cards, validate_section_blocks,
                        news_placement_for, check_rendered_news_placements)

ROOT = Path(__file__).resolve().parents[1]
BRIEF = {'id': 'delta-reign-raikou-ex-sir-spike-cools-2026-11-19',
         'ebay_cards': [{'name': 'Raikou ex', 'number': '136/103', 'set': 'Delta Reign'}]}


def blocks_in_editorial():
    """Every block on the site, as (placement, card) pairs, read from editorial.json."""
    editorial = json.loads((ROOT / 'editorial.json').read_text())
    found = []
    for wire in editorial['wire']:
        for card in wire.get('ebay_cards') or []:
            found.append((news_placement_for(wire['id']), card))
    for article in editorial['articles']:
        for section in article['sections']:
            for div in BeautifulSoup(section['html'], 'html.parser').select('div[data-ebay-card]'):
                found.append((div['data-ebay-placement'], {
                    'name': div['data-ebay-name'], 'number': div['data-ebay-number'], 'set': div['data-ebay-set']}))
    return found


class EbayCardBlocks(unittest.TestCase):
    def test_brief_renders_readme_block(self):
        out = render_ebay_cards(BRIEF, BRIEF['id'])
        div = BeautifulSoup(out, 'html.parser').select_one('div[data-ebay-card]')
        self.assertEqual(div['data-ebay-name'], 'Raikou ex')
        self.assertEqual(div['data-ebay-number'], '136/103')
        self.assertEqual(div['data-ebay-set'], 'Delta Reign')
        self.assertEqual(div['data-ebay-placement'], 'story-delta-reign-raikou-ex-sir-spike-cools-2026-11')
        self.assertEqual(div.decode_contents(), '')
        self.assertNotIn('http', out)

    def test_absent_is_unchanged(self):
        self.assertEqual(render_ebay_cards({'id': 'x'}, 'x'), '')
        validate_ebay_cards({'id': 'x'}, 'x', 'x')

    def test_news_placement_truncates_to_45_and_trims_hyphen(self):
        long_id = 'delta-reign-kecleon-illustration-rare-more-than-doubled-since-launch-2026-11-18'
        self.assertEqual(news_placement_for(long_id), 'story-delta-reign-kecleon-illustration-rare-more-th')
        # character 45 is a hyphen here, so it is trimmed
        self.assertEqual(news_placement_for('a' * 44 + '-bcd-2026-11-20'), 'story-' + 'a' * 44)
        self.assertEqual(news_placement_for('short-id-2026-11-17'), 'story-short-id-2026-11-17')
        validate_ebay_cards({'ebay_cards': BRIEF['ebay_cards']}, long_id, long_id)
        self.assertLessEqual(len(news_placement_for(long_id) + '-psa10'), 64)

    def test_built_page_check_rejects_wrong_placement(self):
        good = render_ebay_cards(BRIEF, BRIEF['id'])
        check_rendered_news_placements(good, BRIEF['id'], 'ok')
        with self.assertRaises(ValueError):
            check_rendered_news_placements(good.replace('2026-11"', '2026-11-19"'), BRIEF['id'], 'bad')

    def test_site_js_uses_the_same_placement(self):
        src = (ROOT / 'site.js').read_text()
        fn = re.search(r'function ebayBlock\(w,c\)\{.*?\}\nfunction ebayCards\(w,skip\)\{.*?\}\n', src, re.S).group(0)
        esc = re.search(r'const esc=.*?;\n', src).group(0)
        ids = [w['id'] for w in json.loads((ROOT / 'editorial.json').read_text())['wire'] if w.get('ebay_cards')]
        script = esc + fn + "const ids=JSON.parse(require('fs').readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(ids.map(id=>ebayCards({id,ebay_cards:[{name:'Raikou ex',number:'136/103',set:'Delta Reign'}]}))));"
        out = json.loads(subprocess.check_output(['node', '-e', script], input=json.dumps(ids).encode()))
        for news_id, markup in zip(ids, out):
            with self.subTest(news_id=news_id):
                check_rendered_news_placements(markup, news_id, news_id)

    def test_rejects_long_feature_slug_urls_prices_and_extra_fields(self):
        long_slug = 'a' * 53
        block = f'<div data-ebay-card data-ebay-name="Kecleon" data-ebay-number="117/103" data-ebay-set="Delta Reign" data-ebay-placement="story-{long_slug}"></div>'
        with self.assertRaises(ValueError):
            validate_section_blocks({'slug': long_slug, 'sections': [{'html': block}]}, long_slug)
        for bad in ({'name': 'Raikou ex', 'number': '136/103', 'set': 'https://www.ebay.co.uk/'},
                    {'name': 'Raikou ex $100', 'number': '136/103', 'set': 'Delta Reign'},
                    {'name': 'Raikou ex', 'number': '136/103', 'set': 'Delta Reign', 'url': 'x'},
                    {'name': 'Raikou ex', 'number': '', 'set': 'Delta Reign'}):
            with self.assertRaises(ValueError):
                validate_ebay_cards({'ebay_cards': [bad]}, BRIEF['id'], 'bad')

    def test_feature_block_needs_its_own_placement(self):
        good = '<div data-ebay-card data-ebay-name="Kecleon" data-ebay-number="117/103" data-ebay-set="Delta Reign" data-ebay-placement="story-my-feature"></div>'
        validate_section_blocks({'slug': 'my-feature', 'sections': [{'html': good}]}, 'my-feature')
        with self.assertRaises(ValueError):
            validate_section_blocks({'slug': 'other', 'sections': [{'html': good}]}, 'other')
        with self.assertRaises(ValueError):
            validate_section_blocks({'slug': 'my-feature', 'sections': [{'html': good + good}]}, 'my-feature')

    def test_every_live_block_renders_a_shop_box(self):
        found = blocks_in_editorial()
        self.assertTrue(found)
        script = ("const {ebayCardBlock}=require('./commerce.js');const fs=require('fs');"
                  "const config=JSON.parse(fs.readFileSync('commerce.json','utf8'));"
                  "const rows=JSON.parse(fs.readFileSync(0,'utf8'));"
                  "process.stdout.write(JSON.stringify(rows.map(r=>ebayCardBlock(r.card,config,{placement:r.placement,variant:'shop'}))));")
        payload = [{'placement': p, 'card': {k: html.unescape(v) for k, v in c.items()}} for p, c in found]
        out = json.loads(subprocess.check_output(['node', '-e', script], cwd=ROOT, input=json.dumps(payload).encode()))
        for (placement, card), rendered in zip(found, out):
            with self.subTest(placement=placement, card=card['name'] + ' ' + card['number']):
                self.assertIn('shop-strip', rendered)
                self.assertIn('Affiliate link', rendered)
                self.assertEqual(len(re.findall(r'href="https://www\.ebay\.co\.uk/sch/i\.html\?', rendered)), 3)


if __name__ == '__main__':
    unittest.main()
