"""The 191-card feed reuses one collector and its existing anomaly policy."""
import copy
import json
from pathlib import Path
import shutil
import unittest
import test_daily_refresh as refresh_fixture
from shared_set_cache import build_cache, identities
D, SITE = refresh_fixture.D, refresh_fixture.SITE


class SharedSetTests(unittest.TestCase):
    def setUp(self):
        self.fixture = refresh_fixture.CollectorTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.catalogue = D.read_json(SITE / 'thirtieth-catalogue.json')
        shutil.copy2(SITE / 'thirtieth-catalogue.json', self.fixture.site)
        self.prior = D.read_json(SITE / 'data/market-cache/thirtieth-current.json')
        for card in self.prior['cards']:
            card['points'] = [{**card['points'][-1], 'day':'2026-11-02', 'usd':100, 'status':'ok'}]
            card['lastGoodUsd'], card['lastGoodDay'] = 100, '2026-11-02'
            card['recentGood'] = [[f'2026-10-{d}', 100] for d in range(27, 32)] + [['2026-11-01', 100], ['2026-11-02', 100]]
        D.write_json(self.fixture.site / 'data/market-cache/thirtieth-current.json', self.prior)
        self.target = next(c for c in self.catalogue['cards'] if c['groupId'] == 24837)

    def source(self, overrides=None):
        self.fixture.fixture_day('2026-11-03')
        for group_id in (24722, 24837):
            file = self.fixture.fixture / f'tcgplayer/3/{group_id}/prices'
            body = D.read_json(file) if file.exists() else dict(success=True, errors=[], results=[])
            existing = {f"{r['productId']}|{r['subTypeName']}": r for r in body['results']}
            for card in self.catalogue['cards']:
                if card['groupId'] != group_id: continue
                existing.setdefault(D.key(card), dict(productId=card['productId'], subTypeName='Holofoil', marketPrice=100))
                existing[D.key(card)].update((overrides or {}).get(card['productId'], {}))
            body['results'] = list(existing.values())
            D.write_json(file, body)
            D.write_json(file.with_name('prices.headers.json'), {'last-modified': 'Tue, 03 Nov 2026 20:02:00 GMT'})

    def test_one_fetch_per_group_complete_cache_and_same_build_noop(self):
        self.source()
        status, code, out = self.fixture.run_refresh()
        self.assertEqual(code, 0, status)
        groups = {c['groupId'] for c in self.fixture.identities.values()} | {24722, 24837}
        self.assertEqual(status['requestCount'], len(groups) + 2)
        cache = D.read_json(out / 'data/market-cache/thirtieth-current.json')
        self.assertEqual(len(cache['cards']), 191)
        self.assertEqual(sum(c['groupId'] == 24837 for c in cache['cards']), 30)
        self.assertTrue(all(c['points'][0]['source'].endswith(f"/{c['groupId']}/prices") for c in cache['cards']))
        self.assertTrue(all(len(c['recentGood']) <= 7 for c in cache['cards']))
        self.assertTrue(all([p['day']for p in c['points']]==['2026-11-02','2026-11-03']for c in cache['cards']))
        shutil.copy2(self.fixture.site / 'thirtieth-catalogue.json', out)
        status, code, out2 = self.fixture.run_refresh(site=out)
        self.assertEqual(code, 0, status)
        self.assertEqual(status['requestCount'], 1)
        self.assertEqual((out / 'data/market-cache/thirtieth-current.json').read_bytes(), (out2 / 'data/market-cache/thirtieth-current.json').read_bytes())

    def test_missing_and_factor_two_hold_preserve_reported_value_and_good_history(self):
        other = next(c for c in self.catalogue['cards'] if c['groupId'] == 24837 and c != self.target)
        self.source({self.target['productId']: {'marketPrice': 5}, other['productId']: {'marketPrice': None}})
        status, code, out = self.fixture.run_refresh()
        self.assertEqual(code, 0, status)
        cards = {c['productId']: c for c in D.read_json(out / 'data/market-cache/thirtieth-current.json')['cards']}
        held = cards[self.target['productId']]
        self.assertEqual(held['points'][-1]['status'], 'source_anomaly')
        self.assertEqual(held['points'][-1]['reportedUsd'], 5)
        self.assertIsNone(held['points'][-1]['usd'])
        self.assertEqual(held['lastGoodUsd'], 100)
        self.assertEqual(held['recentGood'], self.prior['cards'][next(i for i,c in enumerate(self.prior['cards']) if c['productId'] == self.target['productId'])]['recentGood'])
        self.assertEqual(cards[other['productId']]['points'][-1]['status'], 'no_price')

    def test_foreign_currency_and_mixed_build_never_replace_cache(self):
        for mode in ('currency', 'build'):
            with self.subTest(mode=mode):
                self.source({self.target['productId']: {'currency': 'EUR'}} if mode == 'currency' else None)
                if mode == 'build': (self.fixture.fixture / 'last-updated-after.txt').write_text('2026-11-04T20:06:18+0000')
                status, code, out = self.fixture.run_refresh()
                self.assertEqual(code, 1)
                self.assertEqual((out / 'data/market-cache/thirtieth-current.json').read_bytes(), (self.fixture.site / 'data/market-cache/thirtieth-current.json').read_bytes())
                shutil.rmtree(self.fixture.cache)

    def test_catalogue_cannot_change_language_or_drop_printing(self):
        for change in ('language', 'count'):
            bad = copy.deepcopy(self.catalogue)
            if change == 'language': bad['cards'][0]['language'] = 'Japanese'
            else: bad['cards'].pop()
            with self.assertRaises(ValueError): identities(bad)


if __name__ == '__main__': unittest.main()
