"""TCG Modern cache reuses the collector already run for the public refresh."""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path

import daily_refresh as D
import index_cache
import run_daily_pipeline as P
from commit_refresh import promoted_path_allowed, reject_unexpected

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
        prior = {'cards': [{'productId': 717607, 'set': shared['set'], 'number': shared['number'],
                            'language': shared['language'], 'printing': shared['printing'], 'points': points}]}
        original = json.dumps(prior, sort_keys=True)
        self.seed([('2026-11-13', [row(shared, 'accepted', 1)])], cards=(shared,), prior=prior)
        (self.root / 'data/market-cache/thirtieth-current.json').write_text(original)
        written = index_cache.write_all(self.root)
        self.assertEqual(written, ['data/market-cache/tcg-modern-current.json'])
        self.assertEqual((self.root / 'data/market-cache/thirtieth-current.json').read_text(), original)
        cache = json.loads((self.root / 'data/market-cache/tcg-modern-current.json').read_text())
        self.assertEqual(cache['cards'][0]['points'], points)
        self.assertEqual(cache['grade'], 'Raw')

    def test_product_id_match_with_a_different_printing_does_not_copy_thirtieth_history(self):
        shared = {**CARD, 'productId': '717607', 'groupId': '24722', 'name': 'Mew - R/RGB',
                  'set': 'ME: 30th Celebration', 'number': '999/999', 'image': 'assets/thirtieth/717607.jpg'}
        copied = [{'day': '2026-11-13', 'usd': 10.5, 'status': 'ok', 'source': 'https://tcgcsv.com/tcgplayer/3/24722/prices', 'sourceSha256': SHA}]
        prior = {'cards': [{'productId': 717607, 'set': 'ME: 30th Celebration', 'number': 'R/RGB',
                            'language': 'English', 'printing': 'Holofoil', 'points': copied}]}
        self.seed([('2026-11-13', [row(shared, 'accepted', 4.25)])], cards=(shared,), prior=prior)
        log = io.StringIO()
        with redirect_stdout(log):
            cache = index_cache.build(self.root, roster(shared))
        self.assertIn('index cache warning: product 717607', log.getvalue())
        self.assertIn('not copying that history', log.getvalue())
        point = cache['cards'][0]['points'][0]
        self.assertEqual(point['usd'], 4.25)
        self.assertEqual(point['status'], 'ok')
        self.assertNotEqual(cache['cards'][0]['points'], copied)

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
        prior = {'cards': [{'productId': 717607, 'set': shared['set'], 'number': shared['number'],
                 'language': shared['language'], 'printing': shared['printing'],
                 'points': [{'day': '2026-11-13', 'usd': 0, 'status': 'ok',
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
        self.assertTrue(promoted_path_allowed('data/market-cache/delta-reign-current.json'))
        self.assertTrue(promoted_path_allowed('data/market-cache/sv-151-current.json'))
        self.assertTrue(promoted_path_allowed('data/market-cache/prismatic-evolutions-current.json'))
        self.assertTrue(promoted_path_allowed('data/prices/thirtieth-anniversary.json'))
        self.assertTrue(promoted_path_allowed('data/prices/tcg-modern.json'))
        self.assertTrue(promoted_path_allowed('data/prices/delta-reign.json'))
        self.assertTrue(promoted_path_allowed('data/prices/sv-151.json'))
        self.assertTrue(promoted_path_allowed('data/prices/prismatic-evolutions.json'))
        self.assertFalse(promoted_path_allowed('data/prices/other.json'))
        self.assertTrue(promoted_path_allowed('data/market-cache/thirtieth-current.json'))
        self.assertFalse(promoted_path_allowed('data/market-cache/other-current.json'))
        self.assertFalse(promoted_path_allowed('data/market-cache/thirtieth-anniversary-current.json'))
        self.assertTrue(promoted_path_allowed('catalogue.js'))
        self.assertTrue(promoted_path_allowed('data/refresh/observations/2026-11-13/raw.json'))
        self.assertTrue(promoted_path_allowed('data/psa10/cardz-approved.json'))
        self.assertTrue(promoted_path_allowed('data/refresh/psa10-holds/2026-11-16.json'))
        self.assertFalse(promoted_path_allowed('data/psa10/other.json'))
        self.assertFalse(promoted_path_allowed('data/psa10/cardz-approved.json.bak'))
        self.assertFalse(promoted_path_allowed('data/psa10/nested/cardz-approved.json'))
        self.assertFalse(promoted_path_allowed('data/market-cache/tcg-modern-current.json.bak'))
        self.assertFalse(promoted_path_allowed('data/market-cache/nested/tcg-modern-current.json'))
        self.assertFalse(promoted_path_allowed('data/market-rosters/tcg-modern.json'))
        self.assertFalse(promoted_path_allowed('../data/market-cache/tcg-modern-current.json'))
        self.assertFalse(promoted_path_allowed('/tmp/tcg-modern-current.json'))
        self.assertFalse(promoted_path_allowed('data/refresh/state.txt'))

    def test_cardz_allowlist_commit_passes_and_an_unknown_path_still_fails(self):
        paths = [
            'catalogue.js', 'market-history.js', 'market-release.json', 'market-sources.json',
            'top50-data.js', 'top50-release.json', 'top50-sources.json', 'refresh-status.json',
            'data/market-cache/thirtieth-current.json', 'data/market-cache/tcg-modern-current.json',
            'data/market-cache/delta-reign-current.json',
            'data/market-cache/sv-151-current.json',
            'data/market-cache/prismatic-evolutions-current.json',
            'bluechip-collection-data.js', 'bluechip-collection-sources.json',
            'data/refresh/state.json', 'data/refresh/psa10-holds/2026-11-17.json',
            'data/psa10/cardz-approved.json',
        ]
        reject_unexpected(paths)
        with self.assertRaises(SystemExit) as caught:
            reject_unexpected([*paths, 'data/psa10/cardz-snapshot.json'])
        self.assertEqual(caught.exception.code, 'Unexpected pipeline commit path')

    def test_commit_refresh_dry_run_accepts_promoted_paths_without_pushing(self):
        receipt = self.root / 'dry-receipt.json'
        paths = [
            'catalogue.js', 'refresh-status.json',
            'data/market-cache/delta-reign-current.json',
            'data/market-cache/sv-151-current.json',
            'data/market-cache/prismatic-evolutions-current.json',
            'data/refresh/state.json', 'data/psa10/cardz-approved.json',
        ]
        receipt.write_text(json.dumps({'promotedPaths': paths}))
        proc = subprocess.run(
            [sys.executable, str(SITE / 'scripts/commit_refresh.py'), '--receipt', str(receipt), '--dry-run'],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('No commit and no push', proc.stdout)
        for name in paths:
            self.assertIn(name, proc.stdout)
        rejected = self.root / 'bad-receipt.json'
        rejected.write_text(json.dumps({'promotedPaths': paths + ['data/market-rosters/delta-reign.json']}))
        failed = subprocess.run(
            [sys.executable, str(SITE / 'scripts/commit_refresh.py'), '--receipt', str(rejected), '--dry-run'],
            capture_output=True, text=True,
        )
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('Unexpected pipeline commit path', failed.stderr)

    def test_roster_caches_match_identity_bytes_for_each_new_group(self):
        identity_fields = ('productId', 'groupId', 'name', 'set', 'number', 'language', 'printing', 'image')
        shared_images = {
            ('sv-151', '517045'),
            ('prismatic-evolutions', '610511'),
            ('prismatic-evolutions', '610516'),
        }
        chosen = []
        for index, group, product in (
            ('delta-reign', '24831', None),
            ('sv-151', '23237', '517045'),
            ('prismatic-evolutions', '23821', '610516'),
        ):
            document = json.loads((SITE / 'data/market-rosters' / f'{index}.json').read_text())
            for shared_index, shared_id in shared_images:
                if shared_index != index:
                    continue
                shared = next(card for card in document['cards'] if card['productId'] == shared_id)
                self.assertEqual(shared['image'], f'assets/tcg-modern/{shared_id}.jpg')
            card = next(item for item in document['cards'] if item['productId'] == product) if product else document['cards'][0]
            self.assertEqual(str(card['groupId']), group)
            chosen.append((index, card))
        day = '2026-11-16'
        obs = observation(day, [row(card, 'accepted', 1.25) for _, card in chosen])
        folder = self.root / 'data/refresh/observations' / day
        folder.mkdir(parents=True)
        (folder / f"{obs['id']}.json").write_text(json.dumps(obs))
        sources = [{'url': f"https://tcgcsv.com/tcgplayer/3/{card['groupId']}/prices", 'sha256': SHA} for _, card in chosen]
        receipt = {'id': obs['id'], 'sourceDate': day, 'sourceBuildAt': obs['sourceBuildAt'], 'sources': sources}
        rec = self.root / 'data/refresh/receipts'
        rec.mkdir(parents=True)
        (rec / f"{obs['id']}.json").write_text(json.dumps(receipt))
        roster_dir = self.root / 'data/market-rosters'
        roster_dir.mkdir(parents=True)
        for index, card in chosen:
            D.write_json(roster_dir / f'{index}.json', roster(card, index=index))
        written = index_cache.write_all(self.root)
        self.assertEqual(written, [
            'data/market-cache/delta-reign-current.json',
            'data/market-cache/prismatic-evolutions-current.json',
            'data/market-cache/sv-151-current.json',
        ])
        for index, card in chosen:
            raw = (self.root / 'data/market-cache' / f'{index}-current.json').read_bytes()
            published = json.loads(raw)['cards'][0]
            ident = {field: card[field] for field in identity_fields}
            published_ident = {field: published[field] for field in identity_fields}
            self.assertEqual(
                json.dumps(published_ident, separators=(',', ':'), sort_keys=True, ensure_ascii=False).encode(),
                json.dumps(ident, separators=(',', ':'), sort_keys=True, ensure_ascii=False).encode(),
            )
            self.assertIn(json.dumps(ident['image']).encode(), raw)
            self.assertEqual(published['points'][0]['usd'], 1.25)
            self.assertNotEqual(published['points'][0]['usd'], 0)
            self.assertEqual(published['points'][0]['source'], f"https://tcgcsv.com/tcgplayer/3/{card['groupId']}/prices")

    def test_prismatic_cache_has_347_db_cards_and_the_index_view_has_180(self):
        roster = json.loads((SITE / 'data/market-rosters/prismatic-evolutions.json').read_text())
        cards = roster['cards']
        index_cards = [card for card in cards if card.get('inIndex', True) is not False]
        parallels = [card for card in cards if card.get('inIndex') is False]
        self.assertEqual(len(cards), 347)
        self.assertEqual(len(index_cards), 180)
        self.assertEqual(len(parallels), 167)
        self.assertEqual(len({(card['productId'], card['printing']) for card in cards}), 347)
        by_number = {card['number']: card for card in index_cards}
        self.assertEqual(len(by_number), 180)
        shared_modern = {'610511', '610516'}

        def expected_image(product_id):
            product_id = str(product_id)
            if product_id in shared_modern:
                return f'assets/tcg-modern/{product_id}.jpg'
            return f'assets/prismatic-evolutions/{product_id}.jpg'

        for card in cards:
            self.assertEqual(card['image'], expected_image(card['productId']))
        for card in parallels:
            self.assertIn('Ball Pattern', card['name'])
            self.assertNotEqual(card['image'], by_number[card['number']]['image'])
            self.assertNotIn('chase_rank', card)
            self.assertEqual(card['groupId'], '23821')
            self.assertEqual(card['set'], 'SV: Prismatic Evolutions')
            self.assertEqual(card['language'], 'English')
            self.assertEqual(card['printing'], 'Holofoil')
        for product_id in shared_modern:
            shared = next(card for card in index_cards if card['productId'] == product_id)
            self.assertEqual(shared['image'], f'assets/tcg-modern/{product_id}.jpg')
            self.assertNotIn('inIndex', shared)
        ranks = sorted((card['chase_rank'], card['productId']) for card in cards if 'chase_rank' in card)
        self.assertEqual(ranks, [
            (1, '610516'), (2, '610511'), (3, '610499'), (4, '610510'), (5, '610505'),
            (6, '610504'), (7, '610501'), (8, '610508'), (9, '610522'), (10, '610517'),
        ])
        cache = index_cache.build(SITE, roster)
        identity = ('productId', 'groupId', 'name', 'set', 'number', 'language', 'printing', 'image')
        self.assertEqual(len(cache['cards']), 347)
        self.assertEqual(
            [(card['productId'], card['printing']) for card in cache['cards']],
            [(card['productId'], card['printing']) for card in cards],
        )
        for source, published in zip(cards, cache['cards']):
            self.assertEqual({field: published[field] for field in identity}, {field: source[field] for field in identity})
            self.assertNotIn('inIndex', published)
            for point in published['points']:
                self.assertNotEqual(point.get('usd'), 0)
                if point['status'] == 'ok':
                    self.assertGreater(point['usd'], 0)
                else:
                    self.assertIsNone(point['usd'])
                if point.get('reportedUsd') is not None:
                    self.assertGreater(point['reportedUsd'], 0)
        text = json.dumps(cache, separators=(',', ':'), sort_keys=True, allow_nan=False)
        self.assertNotRegex(text, r'"usd":0(?:\.0+)?(?![0-9.])')
        published_file = json.loads((SITE / 'data/market-cache/prismatic-evolutions-current.json').read_text())
        self.assertEqual(len(published_file['cards']), 347)
        self.assertEqual(
            {(card['productId'], card['printing']) for card in published_file['cards']},
            {(card['productId'], card['printing']) for card in cards},
        )
        for card in (*cache['cards'], *published_file['cards']):
            self.assertEqual(card['image'], expected_image(card['productId']))
        snapshot = json.loads((SITE / 'prismatic-evolutions-market-snapshot.json').read_text())
        self.assertEqual(len(snapshot['cards']), 180)
        self.assertEqual(snapshot['baseline'], {'date': '2025-01-17', 'usd': None, 'proposed': False})
        self.assertFalse(any('Ball Pattern' in card['name'] for card in snapshot['cards']))
        snapshot_ids = {card['key'].rsplit('-', 2)[-2] for card in snapshot['cards']}
        self.assertEqual(snapshot_ids, {card['productId'] for card in index_cards})


if __name__ == '__main__':
    unittest.main()
