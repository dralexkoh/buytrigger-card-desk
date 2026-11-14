"""TCG Modern cache reuses the collector already run for the public refresh."""
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import daily_refresh as D
import index_cache
import run_daily_pipeline as P
from commit_refresh import promoted_path_allowed

SITE = Path(__file__).resolve().parents[1]
SHA = 'a' * 64
CARD = dict(productId='183899', groupId='2377', name='Latias & Latios GX (Alternate Full Art)',
            set='SM - Team Up', number='170/181', language='English', printing='Holofoil',
            image='assets/tcg-modern/183899.jpg')


def roster(*cards, index='tcg-modern'):
    return dict(schemaVersion=1, index=index, cards=list(cards))


def observation(day, rows, build_at=None):
    return {'id': f'raw-{day}-test', 'sourceDate': day, 'sourceBuildAt': build_at or f'{day}T20:05:52Z',
            'observations': rows}


def row(card, status, amount):
    return {'key': f"{card['productId']}|{card['printing']}", 'status': status, 'amount': amount,
            'productId': card['productId'], 'groupId': int(card['groupId']), 'printing': card['printing']}


class IndexCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def seed(self, days, cards=(CARD,), prior=None, index='tcg-modern'):
        for day, rows in days:
            obs = observation(day, rows)
            folder = self.root / 'data/refresh/observations' / day
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{obs['id']}.json").write_text(json.dumps(obs))
            sources = [{'url': f"https://tcgcsv.com/tcgplayer/3/{c['groupId']}/prices", 'sha256': SHA} for c in cards]
            receipt = {'id': obs['id'], 'sourceDate': day, 'sourceBuildAt': obs['sourceBuildAt'], 'sources': sources}
            rec = self.root / 'data/refresh/receipts'
            rec.mkdir(parents=True, exist_ok=True)
            (rec / f"{obs['id']}.json").write_text(json.dumps(receipt))
        if prior is not None:
            D.write_json(self.root / 'data/market-cache/thirtieth-current.json', prior)
        (self.root / 'data/market-rosters').mkdir(parents=True, exist_ok=True)
        D.write_json(self.root / 'data/market-rosters' / f'{index}.json', roster(*cards, index=index))
        return roster(*cards, index=index)

    def test_real_modern_cache_matches_consumer_contract_and_reuses_observations(self):
        approved = json.loads((SITE / 'data/market-rosters/tcg-modern.json').read_text())
        catalogue = D.read_js(SITE / 'catalogue.js', 'window.MODERN_PREVIEW_DATA')
        public_ids = {str(c['productId']) for c in catalogue['cards']}
        self.assertEqual({c['productId'] for c in approved['cards']}, public_ids - {'85203'})
        self.assertEqual(approved['excluded'][0]['productId'], 85203)
        thirtieth_before = (SITE / 'data/market-cache/thirtieth-current.json').read_bytes()
        catalogue_before = (SITE / 'catalogue.js').read_bytes()
        cache = index_cache.build(SITE, approved)
        self.assertEqual((SITE / 'data/market-cache/thirtieth-current.json').read_bytes(), thirtieth_before)
        self.assertEqual((SITE / 'catalogue.js').read_bytes(), catalogue_before)
        self.assertEqual(cache['schemaVersion'], 1)
        self.assertEqual(cache['index'], 'tcg-modern')
        self.assertEqual(cache['sourceSystem'], 'shared-cards-market-cache')
        self.assertEqual(cache['grade'], 'Raw')
        self.assertEqual(cache['currency'], 'USD')
        self.assertEqual(cache['measure'], 'tcgcsv_market')
        latest = sorted(p.name for p in (SITE / 'data/refresh/observations').iterdir() if p.is_dir())[-1]
        self.assertEqual(cache['sourceDate'], latest)
        built = datetime.fromisoformat(cache['sourceBuildAt'])
        self.assertEqual(built.date().isoformat(), cache['sourceDate'])
        self.assertEqual(cache['expiresAt'], (built + timedelta(hours=48)).isoformat())
        self.assertEqual(len(cache['cards']), 99)
        self.assertNotIn('85203', {c['productId'] for c in cache['cards']})
        shared = {str(c['productId']): c for c in json.loads(thirtieth_before)['cards']}
        for card in cache['cards']:
            self.assertEqual(card['language'], 'English')
            self.assertEqual(card['printing'], 'Holofoil')
            self.assertTrue(card['image'].endswith(f"/{card['productId']}.jpg"))
            self.assertGreaterEqual(len(card['points']), 1)
            for point in card['points']:
                self.assertLessEqual(point['day'], cache['sourceDate'])
                self.assertIn(point['status'], ('ok', 'no_price', 'source_anomaly'))
                self.assertNotEqual(point.get('usd'), 0)
                if point['status'] == 'ok':
                    self.assertGreater(point['usd'], 0)
                else:
                    self.assertIsNone(point['usd'])
                if point.get('reportedUsd') is not None:
                    self.assertGreater(point['reportedUsd'], 0)
            if card['productId'] in {'717607', '717608', '717609'}:
                self.assertEqual(card['points'], shared[card['productId']]['points'])
                self.assertEqual(card['image'], f"assets/thirtieth/{card['productId']}.jpg")
        text = json.dumps(cache, separators=(',', ':'), sort_keys=True, allow_nan=False)
        self.assertNotRegex(text, r'"usd":0(?:\.0+)?(?![0-9.])')
        self.assertNotIn('"grade":"PSA', text)

    def test_missing_and_zero_sources_keep_the_last_positive_price_and_date(self):
        self.seed([
            ('2026-11-12', [row(CARD, 'accepted', 12.5)]),
            ('2026-11-13', [row(CARD, 'missing', 0)]),
        ])
        cache = index_cache.build(self.root, roster(CARD))
        points = cache['cards'][0]['points']
        self.assertEqual([(p['day'], p['usd'], p['status']) for p in points],
                         [('2026-11-12', 12.5, 'ok'), ('2026-11-13', None, 'no_price')])
        self.assertEqual(cache['sourceDate'], '2026-11-13')

    def test_absent_row_omits_the_day_instead_of_writing_zero(self):
        self.seed([
            ('2026-11-12', [row(CARD, 'accepted', 9)]),
            ('2026-11-13', []),
        ])
        points = index_cache.build(self.root, roster(CARD))['cards'][0]['points']
        self.assertEqual(points[0]['day'], '2026-11-12')
        self.assertEqual(points[0]['usd'], 9)
        self.assertEqual([p['day'] for p in points], ['2026-11-12'])

    def test_held_positive_amount_is_an_anomaly_and_non_positive_hold_is_not_a_price(self):
        self.seed([('2026-11-13', [row(CARD, 'held', 40)])])
        anomaly = index_cache.build(self.root, roster(CARD))['cards'][0]['points'][0]
        self.assertEqual(anomaly['status'], 'source_anomaly')
        self.assertIsNone(anomaly['usd'])
        self.assertEqual(anomaly['reportedUsd'], 40)
        self.seed([('2026-11-13', [row(CARD, 'held', 0)])])
        held_zero = index_cache.build(self.root, roster(CARD))['cards'][0]['points'][0]
        self.assertEqual(held_zero['status'], 'no_price')
        self.assertIsNone(held_zero['usd'])
        self.assertNotIn('reportedUsd', held_zero)

    def test_shared_cards_copy_thirtieth_points_and_do_not_rewrite_that_file(self):
        shared = {**CARD, 'productId': '717607', 'groupId': '24722', 'name': 'Mew - R/RGB',
                  'set': 'ME: 30th Celebration', 'number': 'R/RGB', 'image': 'assets/thirtieth/717607.jpg'}
        points = [{'day': '2026-11-13', 'usd': 10.5, 'status': 'ok', 'source': 'https://tcgcsv.com/tcgplayer/3/24722/prices', 'sourceSha256': SHA}]
        prior = {'cards': [{'productId': 717607, 'points': points}]}
        original = json.dumps(prior, sort_keys=True)
        self.seed([('2026-11-13', [row(shared, 'accepted', 1)])], cards=(shared,), prior=prior)
        (self.root / 'data/market-cache/thirtieth-current.json').write_text(original)
        written = index_cache.write_all(self.root)
        self.assertEqual(written, ['data/market-cache/tcg-modern-current.json'])
        self.assertEqual((self.root / 'data/market-cache/thirtieth-current.json').read_text(), original)
        cache = json.loads((self.root / 'data/market-cache/tcg-modern-current.json').read_text())
        self.assertEqual(cache['cards'][0]['points'], points)
        self.assertEqual(cache['grade'], 'Raw')

    def test_failure_skips_the_cache_and_never_overwrites_thirtieth(self):
        prior = self.root / 'data/market-cache/thirtieth-current.json'
        prior.parent.mkdir(parents=True)
        prior.write_text('{"cards":[]}\n')
        before = prior.read_bytes()
        (self.root / 'data/market-rosters').mkdir(parents=True)
        (self.root / 'data/market-rosters/bad.json').write_text('{')
        (self.root / 'data/market-rosters/thirtieth.json').write_text(json.dumps(roster(CARD, index='thirtieth')))
        self.assertEqual(index_cache.write_all(self.root), [])
        self.assertEqual(prior.read_bytes(), before)
        self.assertFalse((self.root / 'data/market-cache/tcg-modern-current.json').exists())

    def test_non_positive_shared_price_is_not_published(self):
        shared = {**CARD, 'productId': '717607', 'groupId': '24722', 'image': 'assets/thirtieth/717607.jpg'}
        prior = {'cards': [{'productId': 717607, 'points': [{'day': '2026-11-13', 'usd': 0, 'status': 'ok',
                 'source': 'https://tcgcsv.com/tcgplayer/3/24722/prices', 'sourceSha256': SHA}]}]}
        self.seed([('2026-11-13', [row(shared, 'accepted', 10)])], cards=(shared,), prior=prior)
        self.assertEqual(index_cache.write_all(self.root), [])
        self.assertFalse((self.root / 'data/market-cache/tcg-modern-current.json').exists())

    def test_pipeline_stages_modern_cache_without_changing_thirtieth_bytes(self):
        self.seed([('2026-11-13', [row(CARD, 'accepted', 18.25)])])
        output = self.root / 'output'
        stage = self.root / 'stage'
        shutil.copytree(self.root / 'data', stage / 'data')
        thirtieth = {'schemaVersion': 1, 'index': 'thirtieth-anniversary', 'cards': []}
        D.write_json(output / 'data/market-cache/thirtieth-current.json', thirtieth)
        expected = (output / 'data/market-cache/thirtieth-current.json').read_bytes()
        for name in [*D.FILES, 'refresh-status.json']:
            file = output / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('{}\n')
        selected = P.apply_output(output, stage, False)
        self.assertIn('data/market-cache/thirtieth-current.json', selected)
        self.assertIn('data/market-cache/tcg-modern-current.json', selected)
        self.assertEqual((output / 'data/market-cache/thirtieth-current.json').read_bytes(), expected)
        self.assertEqual((stage / 'data/market-cache/thirtieth-current.json').read_bytes(), expected)
        published = json.loads((stage / 'data/market-cache/tcg-modern-current.json').read_text())
        self.assertEqual(published['index'], 'tcg-modern')
        self.assertEqual(published['cards'][0]['points'][0]['usd'], 18.25)
        self.assertEqual(published['grade'], 'Raw')

    def test_commit_allowlist_accepts_index_caches_and_existing_outputs_only(self):
        self.assertTrue(promoted_path_allowed('data/market-cache/tcg-modern-current.json'))
        self.assertTrue(promoted_path_allowed('data/market-cache/thirtieth-current.json'))
        self.assertTrue(promoted_path_allowed('catalogue.js'))
        self.assertTrue(promoted_path_allowed('data/refresh/observations/2026-11-13/raw.json'))
        self.assertFalse(promoted_path_allowed('data/market-cache/tcg-modern-current.json.bak'))
        self.assertFalse(promoted_path_allowed('data/market-cache/nested/tcg-modern-current.json'))
        self.assertFalse(promoted_path_allowed('data/market-rosters/tcg-modern.json'))
        self.assertFalse(promoted_path_allowed('../data/market-cache/tcg-modern-current.json'))
        self.assertFalse(promoted_path_allowed('/tmp/tcg-modern-current.json'))
        self.assertFalse(promoted_path_allowed('data/refresh/state.txt'))


if __name__ == '__main__':
    unittest.main()
