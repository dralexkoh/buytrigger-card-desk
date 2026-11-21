"""The daily price snapshots follow the public data release, and the as-of check fails closed."""
from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

import price_release

ROOT = Path(__file__).resolve().parents[1]


class AsOfCheckTests(unittest.TestCase):
    def test_matching_release_passes(self):
        price_release.assert_price_as_of('2026-11-21', '2026-11-21')

    def test_stale_as_of_fails(self):
        with self.assertRaises(AssertionError) as caught:
            price_release.assert_price_as_of('2026-11-16', '2026-11-21')
        message = str(caught.exception)
        self.assertIn('2026-11-16', message)
        self.assertIn('2026-11-21', message)

    def test_visible_as_of_dates_are_read_from_the_page_text(self):
        text = 'Raw guides, as of 21 Nov 2026. Chase tile as of 21 Nov 2026.'
        self.assertEqual(price_release.visible_as_of_dates(text), {'21 Nov 2026'})


class RebuildTests(unittest.TestCase):
    def test_rebuild_keeps_membership_and_takes_the_release_guide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data' / 'prices').mkdir(parents=True)
            (root / 'data' / 'market-cache').mkdir(parents=True)
            (root / 'refresh-status.json').write_text(json.dumps({'sourceDate': '2026-11-21'}))
            snapshot = {
                'set_name': 'Example',
                'set_slug': 'delta-reign',
                'source': 'TCGCSV marketPrice',
                'source_date': '2026-11-16',
                'generated_at': '2026-11-17T00:00:00Z',
                'cards': [{
                    'name': 'Kecleon',
                    'number': '117/103',
                    'raw_price_usd': 32.68,
                    'tcgplayer_product_id': '726567',
                }, {
                    'name': 'Left out of the daily file',
                    'number': '001/103',
                    'raw_price_usd': 1,
                    'tcgplayer_product_id': '1',
                }],
            }
            # A second product that is only in the cache must not be added.
            cache = {
                'sourceDate': '2026-11-21',
                'sourceBuildAt': '2026-11-21T20:06:04Z',
                'cards': [
                    {'productId': '726567', 'points': [
                        {'day': '2026-11-16', 'usd': 32.68, 'status': 'ok'},
                        {'day': '2026-11-21', 'usd': 23.68, 'status': 'ok'},
                    ]},
                    {'productId': '999', 'inIndex': False, 'points': [
                        {'day': '2026-11-21', 'usd': 9, 'status': 'ok'},
                    ]},
                ],
            }
            (root / 'data' / 'prices' / 'delta-reign.json').write_text(json.dumps(snapshot))
            (root / 'data' / 'market-cache' / 'delta-reign-current.json').write_text(json.dumps(cache))
            with self.assertRaises(ValueError):
                price_release.rebuild_price_snapshots(root)
            snapshot['cards'] = snapshot['cards'][:1]
            (root / 'data' / 'prices' / 'delta-reign.json').write_text(json.dumps(snapshot))
            written = price_release.rebuild_price_snapshots(root)
            self.assertEqual(written, ['data/prices/delta-reign.json'])
            updated = json.loads((root / 'data' / 'prices' / 'delta-reign.json').read_text())
            self.assertEqual(updated['source_date'], '2026-11-21')
            self.assertEqual(updated['generated_at'], '2026-11-21T20:06:04Z')
            self.assertEqual([card['tcgplayer_product_id'] for card in updated['cards']], ['726567'])
            self.assertEqual(updated['cards'][0]['raw_price_usd'], 23.68)
            self.assertEqual(updated['cards'][0]['name'], 'Kecleon')

    def test_a_cache_from_another_day_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data' / 'prices').mkdir(parents=True)
            (root / 'data' / 'market-cache').mkdir(parents=True)
            (root / 'refresh-status.json').write_text(json.dumps({'sourceDate': '2026-11-21'}))
            (root / 'data' / 'prices' / 'sv-151.json').write_text(json.dumps({
                'source_date': '2026-11-16',
                'cards': [{'name': 'A', 'tcgplayer_product_id': '1', 'raw_price_usd': 1}],
            }))
            (root / 'data' / 'market-cache' / 'sv-151-current.json').write_text(json.dumps({
                'sourceDate': '2026-11-16',
                'cards': [{'productId': '1', 'points': [{'day': '2026-11-16', 'usd': 1, 'status': 'ok'}]}],
            }))
            with self.assertRaises(ValueError):
                price_release.rebuild_price_snapshots(root)


class LiveReleaseTests(unittest.TestCase):
    def test_committed_price_pages_match_the_daily_release(self):
        release = price_release.release_date(ROOT)
        for slug, index in price_release.SLUGS:
            snapshot = json.loads((ROOT / 'data' / 'prices' / f'{slug}.json').read_text())
            cache = json.loads((ROOT / 'data' / 'market-cache' / f'{index}-current.json').read_text())
            price_release.assert_price_as_of(snapshot['source_date'], release)
            self.assertEqual(cache['sourceDate'], release)
            by_id = price_release._rows_by_product(cache)
            self.assertGreater(len(snapshot['cards']), 0)
            for card in snapshot['cards']:
                pid = str(card['tcgplayer_product_id'])
                point = price_release._guide(by_id[pid][0], release)
                self.assertEqual(card['raw_price_usd'], point['usd'], f'{slug} {pid}')


if __name__ == '__main__':
    unittest.main()
