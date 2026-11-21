import json
import unittest
from pathlib import Path

from ebay_citations import CAMPAIGN, add_tracking, cite_custom_id, tag_html, untracked_hrefs

ROOT = Path(__file__).resolve().parents[1]


class EbayCitationTests(unittest.TestCase):
    def test_campaign_matches_the_commerce_config(self):
        config = json.loads((ROOT / 'commerce.json').read_text())
        self.assertEqual(config['ebay']['campaignId'], CAMPAIGN)

    def test_page_ids_follow_the_placement_rule(self):
        self.assertEqual(cite_custom_id('undervalued.html'), 'uv-cite')
        self.assertEqual(cite_custom_id('undervalued-japanese.html'), 'uvjp-cite')
        self.assertEqual(
            cite_custom_id('stories/delta-reign-chase-card-prices-november-2026/index.html'),
            'story-delta-reign-chase-card-prices-november-2026-cite',
        )
        long_id = 'delta-reign-top-10-week-three-2026-11-21-extra'
        self.assertEqual(
            cite_custom_id(f'news/{long_id}/index.html'),
            'story-' + long_id[:45].rstrip('-') + '-cite',
        )
        self.assertLessEqual(len(cite_custom_id(f'news/{long_id}/index.html')), 64)
        self.assertIsNone(cite_custom_id('prices/delta-reign/index.html'))

    def test_untracked_item_keeps_its_words_and_a_tracked_link_is_left_alone(self):
        original = (
            '<p>See <a href="https://www.ebay.co.uk/itm/297721154258?nordt=true" '
            'rel="noopener noreferrer">UK PSA 10 sold listing</a> today.</p>'
            '<p><a href="https://www.ebay.co.uk/itm/123456789012?campid=5339239680&amp;customid=price-raw">'
            'Check price</a></p>'
        )
        tagged = tag_html(original, 'uv-cite')
        self.assertIn('>UK PSA 10 sold listing</a>', tagged)
        self.assertIn('>Check price</a>', tagged)
        self.assertEqual(tagged.count('Affiliate link'), 1)
        self.assertEqual(tagged.count('ebay-cite'), 1)
        self.assertEqual(untracked_hrefs(tagged), [])
        self.assertIn('nordt=true', tagged)
        self.assertIn('customid=uv-cite', tagged)
        self.assertIn('campid=5339239680', tagged)
        self.assertEqual(tag_html(tagged, 'uv-cite'), tagged)
        self.assertEqual(
            add_tracking('https://www.ebay.co.uk/itm/297721154258?campid=5339239680', 'uv-cite'),
            'https://www.ebay.co.uk/itm/297721154258?campid=5339239680',
        )


if __name__ == '__main__':
    unittest.main()
