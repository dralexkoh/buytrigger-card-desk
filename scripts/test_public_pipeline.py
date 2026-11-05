"""Promotion boundary tests using the real collector and mocked build commands.

Build/calculation/privacy checks have their own tests. Mocking execute prevents
recursive invocation when this test is itself run by the pipeline's npm test.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest import mock

import daily_refresh as D
import run_daily_pipeline as P
import test_daily_refresh as fixtures


class PublicPipelineTests(unittest.TestCase):
    def setUp(self):
        self.helper = fixtures.CollectorTests()
        self.helper.setUp()
        self.root = self.helper.root
        self.site = self.helper.site
        (self.site / "scripts").mkdir()
        shutil.copy2(Path(__file__).with_name("daily_refresh.py"), self.site / "scripts/daily_refresh.py")
        (self.site / "index.html").write_text("<title>Public fixture</title>")
        (self.site / "package.json").write_text('{"scripts":{}}')
        self.build_calls = []
        self.counter = 0

    def tearDown(self):
        self.helper.tearDown()

    def fake_execute(self, argv, cwd):
        self.build_calls.append(tuple(argv))
        if argv == ["npm", "run", "build"]:
            (cwd / "dist").mkdir()
            for name in [*D.FILES, "refresh-status.json"]:
                shutil.copy2(cwd / name, cwd / "dist" / name)

    def test_curated_prices_join_and_promote_through_the_same_collector(self):
        collection = D.read_js(self.site / "top50-data.js", "window.BT_TOP50")
        cohort = collection["history"]["cohorts"]["history"]
        cohort["members"] = cohort["members"][:5]
        card = collection["cards"][0]
        price = card["quotes"]["Raw"]["price"]
        card["productId"] = 9999901
        D.write_js(self.site / D.COLLECTION_FILES[0], "window.BT_TOP50", collection)
        D.write_json(self.site / D.COLLECTION_FILES[1], {"archives": []})
        self.helper.fixture_day("2026-11-03")
        group = self.helper.fixture / "tcgplayer/3" / str(card["groupId"]) / "prices"
        rows = D.read_json(group)
        rows["results"].append({"productId": card["productId"], "subTypeName": card["printing"], "marketPrice": price})
        D.write_json(group, rows)
        with mock.patch.object(P, "execute", side_effect=self.fake_execute):
            receipt, _ = self.pipeline()
        self.assertFalse(receipt["sourceFailed"])
        self.assertTrue(set(D.COLLECTION_FILES) <= set(receipt["promotedPaths"]))
        updated = D.read_js(self.site / D.COLLECTION_FILES[0], "window.BT_TOP50")
        self.assertEqual(updated["cards"][0]["quotes"]["Raw"]["date"], "2026-11-03")
        self.assertEqual(updated["history"]["cohorts"]["history"]["members"], cohort["members"])

    def pipeline(self, **overrides):
        self.counter += 1
        args = argparse.Namespace(site_dir=self.site, dist_out=self.root / f"dist-{self.counter}",
            receipt=self.root / f"receipt-{self.counter}.json", cache_dir=self.helper.cache,
            run_kind="manual", activate=True, fixture_dir=self.helper.fixture,
            now="2026-11-03T22:00:00Z")
        for key, value in overrides.items():
            setattr(args, key, value)
        P.run(args)
        return D.read_json(args.receipt), args

    def test_source_failure_promotes_status_only_and_preserves_prices(self):
        original = {name: (self.site / name).read_bytes() for name in D.FILES}
        with mock.patch.object(P, "execute", side_effect=self.fake_execute):
            receipt, args = self.pipeline()
        self.assertTrue(receipt["sourceFailed"])
        self.assertEqual(receipt["promotedPaths"], ["refresh-status.json"])
        self.assertEqual(D.read_json(self.site / "refresh-status.json")["status"], "failed")
        for name, content in original.items():
            self.assertEqual((self.site / name).read_bytes(), content)
            self.assertEqual((args.dist_out / name).read_bytes(), content)
        self.assertEqual(self.build_calls, [("npm", "test"), ("npm", "run", "typecheck"), ("npm", "run", "build"), ("npm", "run", "check:artifact")])

    def test_validation_failure_cannot_promote_or_replace_previous_distribution(self):
        self.helper.fixture_day("2026-11-03")
        previous_dist = self.root / "existing-dist"
        previous_dist.mkdir(); (previous_dist / "sentinel").write_text("last verified release")
        original = {name: (self.site / name).read_bytes() for name in D.FILES}
        def reject(argv, cwd):
            self.fake_execute(argv, cwd)
            if argv == ["npm", "run", "check:artifact"]:
                raise subprocess.CalledProcessError(1, argv)
        with mock.patch.object(P, "execute", side_effect=reject):
            with self.assertRaises(subprocess.CalledProcessError):
                self.pipeline(dist_out=previous_dist)
        for name, content in original.items():
            self.assertEqual((self.site / name).read_bytes(), content)
        self.assertFalse((self.site / "refresh-status.json").exists())
        self.assertFalse((self.site / "data").exists())
        self.assertEqual((previous_dist / "sentinel").read_text(), "last verified release")

    def test_success_persists_state_then_replay_avoids_price_fetch(self):
        self.helper.fixture_day("2026-11-03")
        with mock.patch.object(P, "execute", side_effect=self.fake_execute):
            receipt, args = self.pipeline()
        self.assertFalse(receipt["sourceFailed"])
        self.assertIn("data/refresh/state.json", receipt["promotedPaths"])
        self.assertTrue(any(p.startswith("data/refresh/observations/") for p in receipt["promotedPaths"]))
        first = (self.site / "market-history.js").read_bytes()
        shutil.rmtree(self.helper.fixture / "tcgplayer")
        shutil.rmtree(self.helper.cache)
        with mock.patch.object(P, "execute", side_effect=self.fake_execute):
            receipt, args = self.pipeline(now="2026-11-03T23:17:00Z", run_kind="schedule")
        self.assertFalse(receipt["sourceFailed"])
        status = D.read_json(self.site / "refresh-status.json")
        self.assertEqual(status["requestCount"], 1)
        self.assertEqual(status["lastSuccessfulScheduledCheck"], "2026-11-03T23:17:00Z")
        self.assertEqual((self.site / "market-history.js").read_bytes(), first)

    def test_failed_revision_original_becomes_durable_without_state_or_price_change(self):
        self.helper.fixture_day("2026-11-03")
        with mock.patch.object(P, "execute", side_effect=self.fake_execute):
            self.pipeline()
        history = (self.site / "market-history.js").read_bytes()
        state = (self.site / "data/refresh/state.json").read_bytes()
        self.helper.fixture_day("2026-11-03", {D.key(self.helper.modern["cards"][0]): 4000})
        (self.helper.fixture / "last-updated.txt").write_text("2026-11-03T21:06:18+0000")
        with mock.patch.object(P, "execute", side_effect=self.fake_execute):
            receipt, args = self.pipeline()
        self.assertTrue(receipt["sourceFailed"])
        revisions = list((self.site / "data/refresh/review").glob("revision-*.json"))
        self.assertEqual(len(revisions), 1)
        self.assertTrue(any(r["amount"] == 4000 for r in D.read_json(revisions[0])["observations"]))
        self.assertEqual((self.site / "market-history.js").read_bytes(), history)
        self.assertEqual((self.site / "data/refresh/state.json").read_bytes(), state)
        self.assertTrue(all(p == "refresh-status.json" or p.startswith("data/refresh/review/revision-") for p in receipt["promotedPaths"]))
        shutil.rmtree(self.helper.fixture / "tcgplayer")
        shutil.rmtree(self.helper.cache)
        with mock.patch.object(P, "execute", side_effect=self.fake_execute):
            receipt, args = self.pipeline(now="2026-11-03T23:00:00Z")
        status = D.read_json(self.site / "refresh-status.json")
        self.assertTrue(receipt["sourceFailed"])
        self.assertEqual(status["requestCount"], 1)
        self.assertIn("already retained", status["lastError"])

    def test_apply_failure_rejects_changed_existing_revision_receipt(self):
        output, stage = self.root / "output", self.root / "stage"
        for root in [output, stage]:
            (root / "data/refresh/review").mkdir(parents=True)
        D.write_json(output / "refresh-status.json", {"status": "failed"})
        D.write_json(output / "data/refresh/review/revision-test.json", {"amount": 2})
        D.write_json(stage / "data/refresh/review/revision-test.json", {"amount": 1})
        with self.assertRaises(ValueError):
            P.apply_output(output, stage, True)

    def test_isolated_build_keeps_domain_contract_without_broad_file_copy(self):
        (self.site / 'CNAME').write_text('buytrigger.cards\n')
        (self.site / 'not-public.txt').write_text('must not enter build stage')
        stage = self.root / 'domain-stage'
        P.copy_source(self.site, stage)
        self.assertEqual((stage / 'CNAME').read_text(), 'buytrigger.cards\n')
        self.assertFalse((stage / 'not-public.txt').exists())


if __name__ == "__main__":
    unittest.main()
