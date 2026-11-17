"""Acceptance tests for the public CardZ PSA 10 importer. See the 16 Nov 2026 spec."""
import copy
import io
import json
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import daily_refresh as D
import modern_psa10 as P
import test_daily_refresh as fixtures

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "scripts/fixtures/cardz-psa10-public-2026-11-16.json"
RUN = "2026-11-16"
QUOTE_KEYS = {
    "price", "currency", "source", "provider", "as_of", "date", "url", "credit",
    "licence", "licenceUrl", "confidence", "method", "status",
}


def load_catalogue():
    return D.read_js(ROOT / "catalogue.js", "window.MODERN_PREVIEW_DATA")


def route():
    return json.loads(FIXTURE.read_text())


def allowlist():
    return P.load_allowlist(ROOT / "data/psa10/cardz-approved.json")


def stripped():
    data = load_catalogue()
    for card in data["cards"]:
        card.get("quotes", {}).pop("PSA 10", None)
    data.get("coverage", {}).pop("PSA 10", None)
    return data


class Response:
    def __init__(self, body, status=200):
        self.status = status
        self._body = body if isinstance(body, bytes) else body.encode()

    def read(self, n=-1):
        return self._body if n < 0 else self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ModernPsa10Tests(unittest.TestCase):
    def apply(self, data, resp, approved=None, run_date=RUN, holds_dir=None, unavailable=None):
        return P.apply_psa10(data, resp, [] if approved is None else approved, copy.deepcopy(data), run_date, holds_dir, unavailable)

    def test_01_fixture_prices_fifty_and_holds_latias(self):
        data = stripped()
        counts, holds = self.apply(data, P.validate(route(), RUN), allowlist())
        priced = [c for c in data["cards"] if "PSA 10" in c["quotes"]]
        self.assertEqual(len(priced), 50)
        self.assertEqual(counts["priced"], 50)
        self.assertEqual(holds, [])
        latias = next(c for c in data["cards"] if c["id"] == 1)
        self.assertNotIn("PSA 10", latias["quotes"])
        self.assertEqual(latias["productId"], 183899)
        P.annotate_release(data, counts, route()["effectiveDay"])
        self.assertEqual(data["coverage"]["PSA 10"], 50)
        self.assertNotIn("PSA 9", data["coverage"])

    def test_02_every_quote_matches_the_cardz_contract(self):
        data = stripped()
        self.apply(data, P.validate(route(), RUN), allowlist())
        for card in data["cards"]:
            quote = card["quotes"].get("PSA 10")
            if not quote:
                continue
            self.assertEqual(set(quote), QUOTE_KEYS)
            self.assertTrue(P._valid_price(quote["price"]))
            self.assertEqual(quote["currency"], "USD")
            self.assertEqual(quote["source"], "CardZ")
            self.assertRegex(quote["as_of"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertLessEqual(quote["as_of"], RUN)
            self.assertEqual(quote["date"], quote["as_of"])
            self.assertIn(f"CardZ Marketcap, https://cardzmarketcap.com, data as of {quote['as_of']}", quote["credit"])
            self.assertIn("CC BY 4.0", quote["credit"])
            self.assertRegex(quote["url"], r"^https://cardzmarketcap\.com/card/cmc_[0-9a-f]{24}$")
            self.assertEqual(card["sources"]["PSA 10"], quote["url"])

    def test_03_double_lock_rejects_allowlist_or_cmc_mismatches(self):
        data = stripped()
        resp = route()
        approved = allowlist()
        dropped = approved.pop(0)
        approved[0] = {**approved[0], "cmcId": "0" * 24}
        missing = resp["rows"].pop(2)
        resp["count"] = len(resp["rows"])
        extra = copy.deepcopy(resp["rows"][0])
        extra["card_id"] = "en-tcg-modern-183899-holofoil"
        extra["public_id"] = 1
        extra["cardz_url"] = "https://cardzmarketcap.com/card/cmc_" + "ab" * 12
        resp["rows"].append(extra)
        resp["count"] = len(resp["rows"])
        self.apply(data, P.validate(resp, RUN), approved)
        by_series = {P.card_series(c): c for c in data["cards"]}
        self.assertNotIn("PSA 10", by_series[dropped["seriesKey"]]["quotes"])
        self.assertNotIn("PSA 10", by_series[approved[0]["seriesKey"]]["quotes"])
        self.assertNotIn("PSA 10", by_series[missing["card_id"]]["quotes"])
        self.assertNotIn("PSA 10", next(c for c in data["cards"] if c["id"] == 1)["quotes"])
        self.assertEqual(sum("PSA 10" in c["quotes"] for c in data["cards"]), 47)

    def test_04_source_down_keeps_last_price_and_publish_succeeds(self):
        calls = []

        def opener(request, timeout=15):
            headers = {name.lower(): value for name, value in request.header_items()}
            calls.append(headers)
            self.assertNotIn("authorization", headers)
            self.assertNotIn("apikey", headers)
            self.assertNotIn("origin", headers)
            self.assertEqual(headers.get("user-agent"), P.USER_AGENT)
            if len(calls) == 1:
                raise urllib.error.HTTPError(P.ROUTE_URL, 503, "down", hdrs=None, fp=io.BytesIO(b'{"available":false}'))
            raise urllib.error.HTTPError(P.ROUTE_URL, 503, "down", hdrs=None, fp=io.BytesIO(b'{"available":false}'))

        with self.assertRaises(P.SourceUnavailable):
            P.fetch_route(retry_delay=0, opener=opener)
        self.assertEqual(len(calls), 2)

        def once(status):
            def open_once(request, timeout=15):
                headers = {name.lower(): value for name, value in request.header_items()}
                self.assertNotIn("authorization", headers)
                self.assertNotIn("apikey", headers)
                raise urllib.error.HTTPError(P.ROUTE_URL, status, "err", hdrs=None, fp=io.BytesIO(b"no"))
            with self.assertRaises(P.SourceUnavailable):
                P.fetch_route(retry_delay=0, opener=open_once)

        once(500)
        once(400)
        with self.assertRaises(P.SourceUnavailable):
            P.fetch_route(retry_delay=0, opener=lambda request, timeout=15: (_ for _ in ()).throw(TimeoutError("timed out")))
        with self.assertRaises(P.SourceUnavailable):
            P.fetch_route(retry_delay=0, opener=lambda request, timeout=15: Response(b"{"))
        bad = route()
        bad["notes"] = "secret"
        with self.assertRaises(P.SourceUnavailable):
            P.validate(bad, RUN)
        unknown = route()
        unknown["extra"] = True
        with self.assertRaises(P.SourceUnavailable):
            P.validate(unknown, RUN)

        data = stripped()
        previous = {"price": 2222, "currency": "USD", "source": "CardZ", "provider": "CardZ Marketcap",
                    "as_of": "2026-11-01", "date": "2026-11-01", "status": "ok",
                    "url": "https://cardzmarketcap.com/card/cmc_" + "a" * 24,
                    "credit": P.expected_credit("2026-11-01"), "licence": "CC BY 4.0",
                    "licenceUrl": P.LICENCE_URL, "confidence": "high", "method": P.METHOD}
        data["cards"][1]["quotes"]["PSA 10"] = copy.deepcopy(previous)
        raw_before = copy.deepcopy(data["cards"][1]["quotes"]["Raw"])
        counts, _holds = self.apply(data, None, unavailable="HTTP 503")
        kept = data["cards"][1]["quotes"]["PSA 10"]
        self.assertEqual(kept["price"], 2222)
        self.assertEqual(kept["status"], "stale")
        self.assertEqual(data["cards"][1]["quotes"]["Raw"], raw_before)
        self.assertEqual(data["psa10Refresh"]["status"], "source_unavailable")
        self.assertGreater(counts["stale"], 0)

        helper = fixtures.CollectorTests()
        helper.setUp()
        try:
            seeded = copy.deepcopy(helper.modern)
            seeded["cards"][1]["quotes"]["PSA 10"] = copy.deepcopy(previous)
            D.write_js(helper.site / "catalogue.js", "window.MODERN_PREVIEW_DATA", seeded)
            shutil.copytree(ROOT / "data/psa10", helper.site / "data/psa10")
            helper.fixture_day("2026-11-03")
            with mock.patch("modern_psa10.fetch_route", side_effect=P.SourceUnavailable("HTTP 503")):
                status, code, out = helper.run_refresh()
            self.assertEqual(code, 0, status)
            published = D.read_js(out / "catalogue.js", "window.MODERN_PREVIEW_DATA")
            quote = published["cards"][1]["quotes"]["PSA 10"]
            self.assertEqual(quote["price"], 2222)
            self.assertNotEqual(quote["price"], 0)
            self.assertIsNotNone(quote["price"])
            self.assertEqual(quote["status"], "stale")
            self.assertEqual(published["psa10Refresh"]["status"], "source_unavailable")
            self.assertGreater(published["cards"][1]["quotes"]["Raw"]["price"], 0)
        finally:
            helper.tearDown()

    def test_05_jump_and_sanity_guards_hold_the_new_price(self):
        data = stripped()
        resp = route()
        approved = allowlist()
        row = next(r for r in resp["rows"] if r["public_id"] == 24)
        card = next(c for c in data["cards"] if c["id"] == 24)
        card["quotes"]["PSA 10"] = {"price": 1000, "currency": "USD", "source": "CardZ", "status": "ok",
                                     "as_of": "2026-11-01", "date": "2026-11-01",
                                     "url": row["cardz_url"], "credit": P.expected_credit("2026-11-01")}
        row["psa10_last_sale_usd"] = 4000
        with tempfile.TemporaryDirectory() as tmp:
            _counts, holds = self.apply(data, P.validate(resp, RUN), approved, holds_dir=Path(tmp))
            self.assertEqual(holds[0]["reason"], "jump")
            self.assertEqual(holds[0]["newPrice"], 4000)
            self.assertEqual(holds[0]["previousPrice"], 1000)
            self.assertEqual(card["quotes"]["PSA 10"]["price"], 1000)
            self.assertEqual(card["quotes"]["PSA 10"]["status"], "stale")
            receipt = json.loads((Path(tmp) / f"{RUN}.json").read_text())
            self.assertEqual(receipt[0]["reason"], "jump")
        fresh = stripped()
        low = route()
        target = next(r for r in low["rows"] if r["public_id"] == 24)
        target_card = next(c for c in fresh["cards"] if c["id"] == 24)
        target["psa10_last_sale_usd"] = target_card["quotes"]["Raw"]["price"]
        _counts, holds = self.apply(fresh, P.validate(low, RUN), allowlist())
        self.assertEqual(holds[0]["reason"], "sanity")
        self.assertNotIn("PSA 10", next(c for c in fresh["cards"] if c["id"] == 24)["quotes"])

    def test_06_staleness_is_a_render_rule(self):
        """Stored quotes keep their sale. The page test checks 5-day and 31-day rendering."""
        data = stripped()
        resp = route()
        row = resp["rows"][0]
        row["as_of"] = "2026-11-11"
        row["credit"] = P.expected_credit("2026-11-11")
        row["status"] = "ok"
        self.apply(data, P.validate(resp, RUN), allowlist())
        quote = next(c for c in data["cards"] if c["id"] == row["public_id"])["quotes"]["PSA 10"]
        self.assertEqual(quote["status"], "stale")
        self.assertEqual(P._classify(quote, RUN), "stale")
        quote["as_of"] = quote["date"] = "2026-10-16"
        quote["status"] = "ok"
        self.assertEqual(P._classify(quote, RUN), "pending")

    def test_07_no_psa9_price_and_no_private_provider(self):
        text = (ROOT / "catalogue.js").read_text()
        data = json.loads(text[text.index("=") + 1:].strip().rstrip(";"))
        self.assertNotIn("pokemonpricetracker", text.lower())
        self.assertNotIn("pokemonpricetracker", (ROOT / "market-release.json").read_text().lower())
        self.assertNotIn("PSA 9", data["coverage"])
        for card in data["cards"]:
            self.assertNotIn("PSA 9", card["quotes"])
            self.assertNotIn("PSA 9", card.get("sources", {}))
            quote = card["quotes"].get("PSA 10")
            if quote:
                self.assertTrue(P._valid_price(quote["price"]))
                self.assertIsNotNone(quote["price"])
        self.assertEqual(text.count("PSA 9"), 1)
        self.assertIn("PSA 9 not tracked", data["release"]["gradedStatus"])

    def test_08_raw_fields_stay_byte_identical(self):
        original = load_catalogue()
        history = (ROOT / "market-history.js").read_bytes()
        raw_before = {c["id"]: json.dumps(c["quotes"].get("Raw"), sort_keys=True) for c in original["cards"]}
        release_before = {key: copy.deepcopy(original["release"].get(key)) for key in (
            "usdPrices", "rawReferences", "sourceDate", "historyStart", "historyEnd", "historyDays",
            "cohorts", "historyQuality", "coverage", "selectionDate")}
        data = copy.deepcopy(original)
        for card in data["cards"]:
            card.get("quotes", {}).pop("PSA 10", None)
        self.apply(data, P.validate(route(), RUN), allowlist())
        P.annotate_release(data, P._counts(data, RUN, 0), route()["effectiveDay"])
        raw_after = {c["id"]: json.dumps(c["quotes"].get("Raw"), sort_keys=True) for c in data["cards"]}
        self.assertEqual(raw_before, raw_after)
        self.assertEqual((ROOT / "market-history.js").read_bytes(), history)
        for key, value in release_before.items():
            self.assertEqual(data["release"][key], value)
        self.assertEqual(data["coverage"]["Raw"], original["coverage"]["Raw"])

    def test_09_page_contract(self):
        html = (ROOT / "tcg-modern-index.html").read_text()
        script = (ROOT / "modern.js").read_text()
        self.assertNotIn('data-grade="PSA 9"', html)
        self.assertIn('data-grade="PSA 10"', html)
        self.assertIn('id="psa-credit"', html)
        self.assertIn("PSA 10 · CardZ Marketcap", html)
        self.assertIn("Shows cards with a reviewed PSA 10 last sale. The rest stay Pending.", html)
        self.assertIn("PSA 10 · last sale (CardZ)", script)
        self.assertIn("last priced", script)
        self.assertIn("psaCredit", script)
        self.assertNotIn("Graded prices are not connected yet", script)
        self.assertNotIn("quoteMoney", script)

    def test_10_published_cards_match_the_reviewed_sample(self):
        """Named cards keep their roles. Amounts and the sale day follow the published release."""
        data = load_catalogue()
        mewtwo = next(c for c in data["cards"] if c["id"] == 24)
        magikarp = next(c for c in data["cards"] if c["id"] == 89)
        latias = next(c for c in data["cards"] if c["id"] == 1)
        self.assertEqual(mewtwo["name"], "Mewtwo GX")
        self.assertEqual(magikarp["number"], "203/193")
        self.assertNotIn("PSA 10", latias["quotes"])
        day = data["release"]["psa10"]["effectiveDay"]
        for card in (mewtwo, magikarp):
            quote = card["quotes"]["PSA 10"]
            self.assertTrue(P._valid_price(quote["price"]))
            self.assertEqual(quote["currency"], "USD")
            self.assertRegex(quote["as_of"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertLessEqual(quote["as_of"], day)
            self.assertRegex(quote["url"], r"^https://cardzmarketcap\.com/card/cmc_[0-9a-f]{24}$")
            self.assertIn(P._classify(quote, day), {"priced", "stale"})
        shown = sum(1 for c in data["cards"] if P._classify(c["quotes"].get("PSA 10"), day) == "priced")
        stale = sum(1 for c in data["cards"] if P._classify(c["quotes"].get("PSA 10"), day) == "stale")
        self.assertEqual(shown, data["release"]["psa10"]["priced"])
        self.assertEqual(stale, data["release"]["psa10"]["stale"])
        self.assertEqual(data["coverage"]["PSA 10"], shown + stale)
        self.assertGreater(shown + stale, 0)


if __name__ == "__main__":
    unittest.main()
