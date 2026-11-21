"""Behavioral collector tests. Build only synthetic source-day responses in temp dirs.
Run: python3 -m unittest discover -s scripts -p 'test_daily_refresh.py' -v
"""
import argparse
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("daily_refresh", Path(__file__).with_name("daily_refresh.py"))
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)
SITE = Path(__file__).resolve().parents[1]


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.site = self.root / "site"
        self.site.mkdir()
        baseline = json.loads(gzip.decompress((SITE / "scripts/fixtures/public-baseline-2026-11-02.json.gz").read_bytes()))
        for file in D.FILES:
            (self.site / file).write_text(baseline["files"][file])
        self.fixture = self.root / "fixture"
        self.fixture.mkdir()
        self.cache = self.root / "cache"
        self.modern = D.read_js(self.site / "catalogue.js", "window.MODERN_PREVIEW_DATA")
        self.hist = D.read_js(self.site / "market-history.js", "window.BT_HISTORY")
        self.top = D.read_js(self.site / "top50-data.js", "window.BT_TOP50")
        self.identities = D.validate_baseline(self.modern, self.hist, self.top)
        self.counter = 0

    def tearDown(self):
        self.tmp.cleanup()

    def fixture_day(self, date, overrides=None, archive=False):
        overrides = overrides or {}
        prices = {D.key(c): c["quotes"]["Raw"]["price"] for c in self.modern["cards"] + self.top["cards"] if c.get("quotes", {}).get("Raw", {}).get("price")}
        groups = {}
        for key, card in self.identities.items():
            value = overrides.get(key, prices[key])
            if value == "absent":
                continue
            row = {"productId": card["productId"], "subTypeName": card["printing"], "marketPrice": value,
                   "lowPrice": None, "midPrice": value, "highPrice": value, "directLowPrice": None}
            groups.setdefault(card["groupId"], []).append(row)
        for group in {c["groupId"] for c in self.identities.values()}:
            folder = self.fixture / "archives" / date / "3" / str(group) if archive else self.fixture / "tcgplayer/3" / str(group)
            folder.mkdir(parents=True, exist_ok=True)
            p = folder / "prices"
            D.write_json(p, {"success": True, "errors": [], "results": groups.get(group, [])})
            # HTTP receipt resource must precede this build marker on the same day.
            if not archive:
                stamp = D.timestamp(date + "T20:02:00Z")
                D.write_json(p.with_name("prices.headers.json"), {"last-modified": stamp.strftime("%a, %d %b %Y %H:%M:%S GMT")})
        if not archive:
            (self.fixture / "last-updated.txt").write_text(date + "T20:06:18+0000")

    def run_refresh(self, site=None, now="2026-11-03T22:00:00Z", **kw):
        self.counter += 1
        output = self.root / f"out-{self.counter}"
        args = argparse.Namespace(site_dir=site or self.site, output_dir=output, cache_dir=self.cache,
            fixture_dir=self.fixture, now=now, run_kind="manual", activate=True,
            backfill_from=None, backfill_to=None, max_backfill_days=7)
        for k, v in kw.items():
            setattr(args, k, v)
        status, code = D.run(args)
        return status, code, output

    def test_nov2_noop_preserves_exact_history_cohorts_and_eur(self):
        self.fixture_day("2026-11-02")
        status, code, out = self.run_refresh(now="2026-11-03T13:00:00Z")
        self.assertEqual(code, 0)
        self.assertEqual(status["sourceDate"], "2026-11-02")
        self.assertEqual(status["requestCount"], 1)
        self.assertEqual(status["newObservationDates"], [])
        self.assertTrue(status["schedulerEnabled"])
        self.assertFalse(status["automaticRefreshActive"])
        self.assertFalse(D.read_json(out / "top50-release.json")["automaticRefreshActive"])
        self.assertIsNone(status["lastSuccessfulScheduledCheck"])
        self.assertEqual(D.read_js(out / "market-history.js", "window.BT_HISTORY"), self.hist)
        top = D.read_js(out / "top50-data.js", "window.BT_TOP50")
        self.assertEqual(top["history"], self.top["history"])
        modern = D.read_js(out / "catalogue.js", "window.MODERN_PREVIEW_DATA")
        self.assertFalse(any(c["productId"] == 85203 for c in modern["cards"]))
        rayquaza = next(c for c in modern["cards"] if c["productId"] == 728061)
        self.assertEqual(rayquaza["releaseDate"], "2026-11-06")
        self.assertNotIn("Raw", rayquaza["quotes"])
        self.assertEqual(top["release"]["rankingSourceDate"], "2026-11-02")
        # 6 Nov is after this 2 Nov baseline, so the new card is a visible gap, not a priced row.
        self.assertEqual(status["coverage"]["modern"]["priced"], 99)
        self.assertEqual(status["coverage"]["modern"]["missing"], 1)
        self.assertEqual(status["coverage"]["modern"]["usd"], 99)
        self.assertEqual(status["coverage"]["modern"]["eur"], 0)
        self.assertEqual(status["coverage"]["modern"]["total"], 100)

    def test_new_build_dedup_and_same_date_replay(self):
        self.fixture_day("2026-11-03")
        status, code, out = self.run_refresh()
        self.assertEqual(code, 0, status)
        self.assertEqual(status["newObservationDates"], ["2026-11-03"])
        modern_release = D.read_json(out / "market-release.json")
        top_release = D.read_json(out / "top50-release.json")
        self.assertEqual(modern_release["archiveDays"], 306)
        self.assertEqual(modern_release["historyDays"], 307)
        self.assertEqual(modern_release["expectedDays"], 307)
        self.assertEqual(modern_release["observedSourceDays"], 307)
        self.assertEqual(top_release["archiveCount"], 330)
        self.assertEqual(top_release["historyDays"], 331)
        self.assertEqual(top_release["observedSourceDays"], 331)
        self.assertEqual(status["requestCount"], len({c["groupId"] for c in self.identities.values()}) + 2)
        receipts = list((out / "data/refresh/observations").rglob("*.json"))
        self.assertEqual(len(receipts), 1)
        new_history = D.read_js(out / "market-history.js", "window.BT_HISTORY")
        receipt_link = new_history["sourceReceipts"]["2026-11-03"]
        self.assertTrue((out / receipt_link).exists())
        self.assertEqual(D.read_js(out / "top50-data.js", "window.BT_TOP50")["history"]["sourceReceipts"]["2026-11-03"], receipt_link)
        observation = D.read_json(receipts[0])
        self.assertEqual(len(observation["observations"]), len(self.identities))
        self.assertLess(len(self.identities), 149)
        second, code, out2 = self.run_refresh(site=out, now="2026-11-03T23:00:00Z")
        self.assertEqual(code, 0)
        self.assertEqual(second["requestCount"], 1)
        self.assertEqual(second["newObservationDates"], [])
        self.assertEqual(second["dataReleaseId"], status["dataReleaseId"])
        self.assertEqual(D.read_js(out2 / "market-history.js", "window.BT_HISTORY"), D.read_js(out / "market-history.js", "window.BT_HISTORY"))
        self.assertEqual(next((out2 / "data/refresh/observations").rglob("*.json")).read_bytes(), receipts[0].read_bytes())
        self.assertEqual(D.read_js(out2 / "top50-data.js", "window.BT_TOP50")["history"]["cohorts"], self.top["history"]["cohorts"])

    def test_missing_and_held_originals_keep_gap_and_last_valid_date(self):
        shared = D.key(self.modern["cards"][0])
        missing = D.key(self.modern["cards"][4])
        self.fixture_day("2026-11-03", {shared: 5, missing: None})
        status, code, out = self.run_refresh()
        self.assertEqual(code, 0, status)
        self.assertEqual(status["status"], "partial")
        h = D.read_js(out / "market-history.js", "window.BT_HISTORY")
        m = D.read_js(out / "catalogue.js", "window.MODERN_PREVIEW_DATA")
        self.assertEqual(h["prices"]["1"][-1], 5)
        self.assertTrue(any(e["cardId"] == 1 and e["date"] == "2026-11-03" for e in h["exclusions"]))
        self.assertIsNone(h["prices"]["5"][-1])
        self.assertEqual(m["cards"][0]["quotes"]["Raw"]["date"], "2026-11-02")
        self.assertEqual(m["cards"][0]["rawRefresh"]["status"], "held")
        self.assertEqual(m["cards"][4]["rawRefresh"]["status"], "missing")
        obs = D.read_json(next((out / "data/refresh/observations").rglob("*.json")))
        self.assertEqual(next(r for r in obs["observations"] if r["key"] == shared)["sourceRow"]["marketPrice"], 5)
        self.assertEqual(h["exclusions"][:len(self.hist["exclusions"])], self.hist["exclusions"])

    def test_isolated_jump_then_reversal_keeps_original_hold_and_recovers_current(self):
        card_key = D.key(self.modern["cards"][0])
        self.fixture_day("2026-11-03", {card_key: 5})
        status, code, held = self.run_refresh()
        self.assertEqual(code, 0, status)
        self.fixture_day("2026-11-04")
        status, code, recovered = self.run_refresh(site=held, now="2026-11-04T22:00:00Z")
        self.assertEqual(code, 0, status)
        modern = D.read_js(recovered / "catalogue.js", "window.MODERN_PREVIEW_DATA")
        history = D.read_js(recovered / "market-history.js", "window.BT_HISTORY")
        self.assertEqual(modern["cards"][0]["rawRefresh"]["status"], "current")
        self.assertEqual(modern["cards"][0]["quotes"]["Raw"]["date"], "2026-11-04")
        self.assertEqual(history["prices"]["1"][-2], 5)
        self.assertTrue(any(e["cardId"] == 1 and e["date"] == "2026-11-03" for e in history["exclusions"]))
        self.assertFalse(any(e["cardId"] == 1 and e["date"] == "2026-11-04" for e in history["exclusions"]))

    def test_changed_marker_and_mixed_last_modified_fail_without_payload_change(self):
        self.fixture_day("2026-11-03")
        (self.fixture / "last-updated-after.txt").write_text("2026-11-04T20:06:18+0000")
        status, code, out = self.run_refresh()
        self.assertEqual(code, 1)
        self.assertIn("changed during collection", status["lastError"])
        for file in D.FILES:
            self.assertEqual((out / file).read_bytes(), (self.site / file).read_bytes())
        (self.fixture / "last-updated-after.txt").unlink()
        shutil.rmtree(self.cache)
        p = next((self.fixture / "tcgplayer").rglob("prices.headers.json"))
        D.write_json(p, {"last-modified": "Wed, 04 Nov 2026 20:02:00 GMT"})
        status, code, out = self.run_refresh()
        self.assertEqual(code, 1)
        self.assertIn("outside the published build", status["lastError"])

    def test_missing_source_fails_and_retry_recovers(self):
        self.fixture_day("2026-11-03")
        p = next((self.fixture / "tcgplayer").rglob("prices"))
        original = p.read_bytes(); p.unlink()
        status, code, out = self.run_refresh()
        self.assertEqual(code, 1)
        self.assertEqual((out / "market-history.js").read_bytes(), (self.site / "market-history.js").read_bytes())
        p.write_bytes(original)
        status, code, out = self.run_refresh()
        self.assertEqual(code, 0, status)
        self.assertEqual(status["newObservationDates"], ["2026-11-03"])

    def test_backfill_gap_then_recovery_and_no_repeat_archive(self):
        self.fixture_day("2026-11-05")
        self.fixture_day("2026-11-03", archive=True)
        status, code, out = self.run_refresh(now="2026-11-05T22:00:00Z")
        self.assertEqual(code, 0, status)
        self.assertEqual(status["gaps"], ["2026-11-04"])
        h = D.read_js(out / "market-history.js", "window.BT_HISTORY")
        self.assertEqual(h["dates"][-3:], ["2026-11-03", "2026-11-04", "2026-11-05"])
        self.assertIsNone(h["prices"]["1"][-2])
        release = D.read_json(out / "market-release.json")
        self.assertEqual(release["archiveDays"], 307)
        self.assertEqual(release["historyDays"], 309)
        self.assertEqual(release["expectedDays"], 309)
        self.assertEqual(release["observedSourceDays"], 308)
        self.fixture_day("2026-11-04", archive=True)
        shutil.rmtree(self.fixture / "archives/2026-11-03")
        status, code, recovered = self.run_refresh(site=out, now="2026-11-06T07:17:00Z", run_kind="schedule")
        self.assertEqual(code, 0, status)
        self.assertEqual(status["gaps"], [])
        self.assertEqual(status["newObservationDates"], ["2026-11-04"])
        self.assertEqual(status["sourceDate"], "2026-11-05")
        self.assertEqual(status["lastSuccessfulScheduledCheck"], "2026-11-06T07:17:00Z")
        self.assertTrue(status["automaticRefreshActive"])
        self.assertTrue(D.read_json(recovered / "top50-release.json")["automaticRefreshActive"])
        h = D.read_js(recovered / "market-history.js", "window.BT_HISTORY")
        self.assertGreater(h["prices"]["1"][-2], 0)
        self.assertEqual(h["cohorts"], self.hist["cohorts"])
        self.assertEqual(len(list((recovered / "data/refresh/observations").rglob("*.json"))), 3)
        release = D.read_json(recovered / "market-release.json")
        self.assertEqual(release["archiveDays"], 308)
        self.assertEqual(release["observedSourceDays"], 309)

    def test_same_date_revision_held_and_not_overwritten(self):
        self.fixture_day("2026-11-03")
        status, code, out = self.run_refresh()
        self.assertEqual(code, 0)
        self.fixture_day("2026-11-03", {D.key(self.modern["cards"][0]): 4000})
        (self.fixture / "last-updated.txt").write_text("2026-11-03T21:06:18+0000")
        status, code, revised = self.run_refresh(site=out)
        self.assertEqual(code, 1)
        self.assertIn("revision review", status["lastError"])
        self.assertEqual((revised / "market-history.js").read_bytes(), (out / "market-history.js").read_bytes())
        self.assertTrue(list((revised / "data/refresh/review").glob("revision-*.json")))

    def test_duplicate_exact_printing_or_wrong_currency_cannot_pass(self):
        self.fixture_day("2026-11-03")
        p = next((self.fixture / "tcgplayer").rglob("prices"))
        payload = D.read_json(p); payload["results"].append(copy.deepcopy(payload["results"][0])); D.write_json(p, payload)
        status, code, out = self.run_refresh()
        self.assertEqual(code, 1)
        self.assertIn("Duplicate product/printing", status["lastError"])
        payload["results"].pop(); payload["results"][0]["currency"] = "EUR"; D.write_json(p, payload)
        shutil.rmtree(self.cache)
        status, code, out = self.run_refresh()
        self.assertEqual(code, 0)
        self.assertGreater(status["missingCount"], 0)

    def test_rollback_is_previous_public_snapshot_and_deterministic_replay(self):
        self.fixture_day("2026-11-03")
        status1, code, out1 = self.run_refresh()
        self.assertEqual(code, 0, status1)
        status2, code, out2 = self.run_refresh()
        self.assertEqual(status1, status2)
        for file in D.PUBLIC_OUTPUTS[:-1]:
            self.assertEqual((out1 / file).read_bytes(), (out2 / file).read_bytes())
        self.assertEqual(D.read_js(self.site / "market-history.js", "window.BT_HISTORY"), self.hist)
        self.assertFalse((self.site / "data/refresh").exists())

    def test_no_future_build_and_input_dir_is_protected(self):
        self.fixture_day("2026-11-04")
        status, code, out = self.run_refresh()
        self.assertEqual(code, 1)
        self.assertIn("future", status["lastError"])
        with self.assertRaises(D.RefreshError):
            self.run_refresh(output_dir=self.site)

    def test_anomaly_screen_is_review_only_and_ignores_monthly_sampling(self):
        previous = [("2026-10-30", 100), ("2026-10-31", 101), ("2026-11-01", 100)]
        self.assertIsNone(D.suspicion(150, previous, "2026-11-02"))
        self.assertIsNotNone(D.suspicion(500, previous, "2026-11-02"))
        self.assertIsNotNone(D.suspicion(1, previous, "2026-11-02"))
        self.assertIsNone(D.suspicion(500, previous, "2026-11-30"))
        # Existing accepted large source changes remain in historical arrays, unmodified.
        self.assertEqual(D.POLICY["historicalApplication"], "None: existing reviewed observations and exclusions are preserved.")

    def write_roster(self, index, cards):
        folder = self.site / "data/market-rosters"
        folder.mkdir(parents=True, exist_ok=True)
        D.write_json(folder / f"{index}.json", {"schemaVersion": 1, "index": index, "cards": cards})

    def add_group_price(self, group, product, printing, price, date="2026-11-03"):
        folder = self.fixture / "tcgplayer/3" / str(group)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "prices"
        payload = D.read_json(path) if path.exists() else {"success": True, "errors": [], "results": []}
        payload["results"].append({"productId": product, "subTypeName": printing, "marketPrice": price,
                                   "lowPrice": None, "midPrice": price, "highPrice": price, "directLowPrice": None})
        D.write_json(path, payload)
        if not path.with_name("prices.headers.json").exists():
            stamp = D.timestamp(date + "T20:02:00Z")
            D.write_json(path.with_name("prices.headers.json"), {"last-modified": stamp.strftime("%a, %d %b %Y %H:%M:%S GMT")})

    def test_roster_groups_are_observed_without_joining_public_baskets(self):
        self.fixture_day("2026-11-03")
        cards = [
            {"productId": "726510", "groupId": "24831", "name": "Masquerain - 003/103", "set": "ME06: Delta Reign",
             "number": "003/103", "language": "English", "printing": "Normal", "image": "assets/delta-reign/726510.jpg"},
            {"productId": "502548", "groupId": "23237", "name": "Squirtle - 007/165", "set": "SV: Scarlet & Violet 151",
             "number": "007/165", "language": "English", "printing": "Normal", "image": "assets/sv-151/502548.jpg"},
            {"productId": "610509", "groupId": "23821", "name": "Iron Hands ex - 154/131", "set": "SV: Prismatic Evolutions",
             "number": "154/131", "language": "English", "printing": "Holofoil", "image": "assets/prismatic-evolutions/610509.jpg"},
        ]
        self.write_roster("delta-reign", [cards[0]])
        self.write_roster("sv-151", [cards[1]])
        self.write_roster("prismatic-evolutions", [cards[2]])
        self.add_group_price(24831, 726510, "Normal", 0.08)
        self.add_group_price(23237, 502548, "Normal", 0.15)
        self.add_group_price(23821, 610509, "Holofoil", 1.25)
        before = (len(self.modern["cards"]), len(self.top["cards"]), len(self.identities))
        status, code, out = self.run_refresh()
        self.assertEqual(code, 0, status)
        modern = D.read_js(out / "catalogue.js", "window.MODERN_PREVIEW_DATA")
        top = D.read_js(out / "top50-data.js", "window.BT_TOP50")
        self.assertEqual((len(modern["cards"]), len(top["cards"]), status["uniqueExactPrintings"]), before)
        self.assertEqual(D.validate_baseline(modern, D.read_js(out / "market-history.js", "window.BT_HISTORY"), top), self.identities)
        self.assertEqual(status["coverage"]["modern"]["total"], 100)
        self.assertEqual(status["coverage"]["top50"]["total"], 50)
        groups = {c["groupId"] for c in self.identities.values()}
        self.assertIn(24831, groups)
        self.assertEqual(status["requestCount"], len(groups) + 2)
        observation = D.read_json(next((out / "data/refresh/observations").rglob("*.json")))
        by_key = {row["key"]: row for row in observation["observations"]}
        self.assertEqual(len(by_key), len(self.identities) + 3)
        self.assertTrue(set(self.identities) <= set(by_key))
        self.assertEqual(by_key["726510|Normal"]["status"], "accepted")
        self.assertEqual(by_key["726510|Normal"]["amount"], 0.08)
        self.assertEqual(by_key["502548|Normal"]["amount"], 0.15)
        self.assertEqual(by_key["610509|Holofoil"]["amount"], 1.25)
        urls = {source["url"]: source["sha256"] for source in observation["sources"]}
        for group in (24831, 23237, 23821):
            self.assertIn(f"https://tcgcsv.com/tcgplayer/3/{group}/prices", urls)
            self.assertEqual(len(urls[f"https://tcgcsv.com/tcgplayer/3/{group}/prices"]), 64)
        shutil.copytree(self.site / "data/market-rosters", out / "data/market-rosters")
        second, code, _out2 = self.run_refresh(site=out, now="2026-11-03T23:00:00Z")
        self.assertEqual(code, 0, second)
        self.assertEqual(second["requestCount"], 1)
        self.assertEqual(second["newObservationDates"], [])
        self.assertEqual(second["coverage"]["modern"]["total"], 100)

    def test_roster_hold_and_missing_keep_no_invented_price(self):
        self.fixture_day("2026-11-03")
        card = {"productId": "726511", "groupId": "24831", "name": "Virizion", "set": "ME06: Delta Reign",
                "number": "009/103", "language": "English", "printing": "Normal", "image": "assets/delta-reign/726511.jpg"}
        absent = {"productId": "726512", "groupId": "24831", "name": "Mega Golisopod ex - 011/103", "set": "ME06: Delta Reign",
                  "number": "011/103", "language": "English", "printing": "Holofoil", "image": "assets/delta-reign/726512.jpg"}
        self.write_roster("delta-reign", [card, absent])
        for day in ("2026-10-30", "2026-10-31", "2026-11-01"):
            folder = self.site / "data/refresh/observations" / day
            folder.mkdir(parents=True)
            D.write_json(folder / f"raw-{day}-prior.json", {"id": f"raw-{day}-prior", "sourceDate": day,
                         "observations": [{"key": "726511|Normal", "status": "accepted", "amount": 10}]})
        self.add_group_price(24831, 726511, "Normal", 100)
        self.add_group_price(24831, 726512, "Holofoil", None)
        status, code, out = self.run_refresh()
        self.assertEqual(code, 0, status)
        observation = D.read_json(next(path for path in (out / "data/refresh/observations").rglob("*.json") if "2026-11-03" in str(path)))
        by_key = {row["key"]: row for row in observation["observations"]}
        held = by_key["726511|Normal"]
        missing = by_key["726512|Holofoil"]
        self.assertEqual(held["status"], "held")
        self.assertEqual(held["amount"], 100)
        self.assertNotEqual(held["amount"], 0)
        self.assertEqual(missing["status"], "missing")
        self.assertIsNone(missing["amount"])
        self.assertEqual(status["coverage"]["modern"]["total"], 100)
        self.assertEqual(status["uniqueExactPrintings"], len(self.identities))

    def test_already_processed_build_records_roster_groups_on_a_later_receipt(self):
        self.fixture_day("2026-11-03")
        status, code, out = self.run_refresh()
        self.assertEqual(code, 0, status)
        original = next((out / "data/refresh/observations").rglob("*.json")).read_bytes()
        cards = [
            {"productId": "726510", "groupId": "24831", "name": "Masquerain - 003/103", "set": "ME06: Delta Reign",
             "number": "003/103", "language": "English", "printing": "Normal", "image": "assets/delta-reign/726510.jpg"},
            {"productId": "502548", "groupId": "23237", "name": "Squirtle - 007/165", "set": "SV: Scarlet & Violet 151",
             "number": "007/165", "language": "English", "printing": "Normal", "image": "assets/sv-151/502548.jpg"},
            {"productId": "610509", "groupId": "23821", "name": "Iron Hands ex - 154/131", "set": "SV: Prismatic Evolutions",
             "number": "154/131", "language": "English", "printing": "Holofoil", "image": "assets/prismatic-evolutions/610509.jpg"},
        ]
        roster_root = out / "data/market-rosters"
        for index, card in zip(("delta-reign", "sv-151", "prismatic-evolutions"), cards):
            D.write_json(roster_root / f"{index}.json", {"schemaVersion": 1, "index": index, "cards": [card]})
        self.add_group_price(24831, 726510, "Normal", 0.08)
        self.add_group_price(23237, 502548, "Normal", 0.15)
        self.add_group_price(23821, 610509, "Holofoil", 1.25)
        shutil.rmtree(self.cache)
        second, code, repaired = self.run_refresh(site=out)
        self.assertEqual(code, 0, second)
        self.assertEqual(second["newObservationDates"], [])
        self.assertEqual(second["requestCount"], 5)
        self.assertEqual(second["coverage"]["modern"]["total"], 100)
        files = sorted((repaired / "data/refresh/observations").rglob("*.json"))
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].read_bytes(), original)
        self.assertTrue(files[1].name.endswith(".rosters.json"))
        added = D.read_json(files[1])
        by_key = {row["key"]: row for row in added["observations"]}
        self.assertEqual(by_key["726510|Normal"]["amount"], 0.08)
        self.assertEqual(by_key["502548|Normal"]["status"], "accepted")
        self.assertEqual(by_key["610509|Holofoil"]["status"], "accepted")
        self.assertGreater(len(by_key), len(self.identities))
        receipt = D.read_json(repaired / "data/refresh/receipts" / f"{added['id']}.json")
        urls = {source["url"] for source in receipt["sources"]}
        for group in (24831, 23237, 23821):
            self.assertIn(f"https://tcgcsv.com/tcgplayer/3/{group}/prices", urls)
        history = D.read_js(repaired / "market-history.js", "window.BT_HISTORY")
        self.assertEqual(len(history["dates"]), len(D.read_js(out / "market-history.js", "window.BT_HISTORY")["dates"]))


    def test_bluechip_outlier_hold_keeps_the_last_accepted_guide(self):
        self.assertIsNone(D.bluechip_outlier(100, 90, {"midPrice": 95, "lowPrice": 80}))
        self.assertIsNone(D.bluechip_outlier(3.5, None, {}))
        low_only = D.bluechip_outlier(1, None, {"midPrice": None, "lowPrice": 100})
        self.assertIn("same-release-lowPrice", low_only["reason"])
        over = D.bluechip_outlier(10000, 100, {"midPrice": 110})
        self.assertIn("last-accepted-guide", {item["field"] for item in over["crossChecks"]})
        both = D.bluechip_outlier(3.5, 800, {"midPrice": 750, "lowPrice": 9000})
        self.assertEqual({item["field"] for item in both["crossChecks"]}, {"last-accepted-guide", "same-release-midPrice"})
        stray_ask = D.bluechip_outlier(1574.99, 1574.99, {"midPrice": 19999.99, "lowPrice": 19999.99})
        self.assertIsNone(stray_ask)
        features = [{"image": "assets/fresh.jpg", "alt": "Fresh"}, {"image": "assets/old.jpg", "alt": "Old"}]
        collection = {"release": {"sourceDate": "2026-11-21"}, "cards": [
            {"image": "assets/fresh.jpg", "quotes": {"Raw": {"date": "2026-11-20", "price": 10}}},
            {"image": "assets/old.jpg", "quotes": {"Raw": {"date": "2026-09-01", "price": 10}}}]}
        D.annotate_feature_prices(features, collection)
        self.assertNotIn("priceLabel", features[0])
        self.assertEqual(features[1]["priceLabel"], "No current price")
        self.assertNotIn("PriceCharting", both["reason"])
        hist = {"dates": ["2026-11-20"], "prices": {"1": [800.0]}, "exclusions": []}
        card = {"id": 1, "productId": 85668, "groupId": 1372, "printing": "Holofoil", "releaseDate": "2003-05-12",
                "quotes": {"Raw": {"price": 800.0, "date": "2026-11-20", "currency": "USD"}}}
        data = {"cards": [card]}
        observation = {"id": "raw-test", "kind": "live", "sourceDate": "2026-11-21",
                       "sources": [{"url": "https://tcgcsv.com/tcgplayer/3/1372/prices"}],
                       "observations": [{"key": "85668|Holofoil", "amount": 3.5, "status": "accepted",
                                         "sourceRow": {"marketPrice": 3.5, "midPrice": 10000, "lowPrice": 10000}}]}
        review = self.root / "review"
        review.mkdir()
        D.apply_observations(observation, [("bluechip", data, hist)], review)
        self.assertEqual(hist["exclusions"][0]["policy"], D.BLUECHIP_OUTLIER["id"])
        self.assertEqual(hist["exclusions"][0]["reportedValue"], 3.5)
        D.coverage_and_quotes(data, hist, "2026-11-21")
        self.assertEqual(card["quotes"]["Raw"]["price"], 800.0)
        self.assertEqual(card["quotes"]["Raw"]["date"], "2026-11-20")
        self.assertEqual(card["rawRefresh"]["status"], "held")
        self.assertEqual(D.bluechip_hold_notes([("bluechip", data, hist)], "2026-11-21")[0]["reason"], hist["exclusions"][0]["reason"])
        plain = {"dates": ["2026-11-20"], "prices": {"1": [800.0]}, "exclusions": []}
        plain_card = {"id": 1, "productId": 1, "groupId": 1, "printing": "Holofoil",
                      "quotes": {"Raw": {"price": 800.0, "date": "2026-11-20", "currency": "USD"}}}
        plain_data = {"cards": [plain_card]}
        ok = {"id": "raw-ok", "kind": "live", "sourceDate": "2026-11-21", "sources": [{"url": "https://tcgcsv.com/x"}],
              "observations": [{"key": "1|Holofoil", "amount": 820, "status": "accepted", "sourceRow": {"midPrice": 810, "lowPrice": 700}}]}
        D.apply_observations(ok, [("top50", plain_data, plain)], review)
        self.assertEqual(plain["exclusions"], [])
        D.coverage_and_quotes(plain_data, plain, "2026-11-21")
        self.assertEqual(plain_card["quotes"]["Raw"]["price"], 820)


if __name__ == "__main__":
    unittest.main()
