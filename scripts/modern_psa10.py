#!/usr/bin/env python3
"""Public PSA 10 prices for the TCG Modern index.

Reads the keyless CardZ route once per run. A card is priced only when that
route and the committed allow-list agree on the same CardZ id. A failed or
empty response keeps the last published PSA 10 quote and marks it stale.
Raw quotes are never written here.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROUTE_URL = "https://ukblxmvsqihnnyysvxes.supabase.co/functions/v1/card-market-view?view=cardz-psa10-public"
USER_AGENT = "buytrigger-desk-refresh"
MAX_BODY = 600_000
REVIEW = "pricing/reviews/2026-11-16-cardz-public-outliers"
GRADED_STATUS = "PSA 10: CardZ last sale (CC BY 4.0), reviewed 16 Nov 2026. PSA 9 not tracked (PSA 10 only)."
METHOD = "Most recent PSA 10 sale carried forward by CardZ (one sale, not a median). Exact English printing match; reviewed 16 Nov 2026 against public PSA 10 sold comps."
LABEL = "PSA 10 · last sale (CardZ)"
HOME = "https://cardzmarketcap.com"
LICENCE = "CC BY 4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"

TOP_KEYS = {
    "schemaVersion", "available", "view", "index", "grade", "currency", "label",
    "source", "sourceHome", "licence", "licenceUrl", "effectiveDay", "credit",
    "count", "rows", "generatedAt", "sourceVersion",
}
ROW_KEYS = {
    "card_id", "public_id", "name", "number", "set", "language", "printing",
    "grade", "psa10_last_sale_usd", "currency", "as_of", "status", "confidence",
    "cardz_url", "label", "credit",
}
ALLOW_KEYS = {"publicId", "seriesKey", "cmcId", "approvedOn", "confidence", "review"}
FORBIDDEN = {
    "owner_id", "item_id", "run_id", "holding_id", "details", "rationale",
    "review_note", "payload", "cost", "notes", "photos",
}
QUOTE_KEYS = {
    "price", "currency", "source", "provider", "as_of", "date", "url", "credit",
    "licence", "licenceUrl", "confidence", "method", "status",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CARD_RE = re.compile(r"^en-tcg-modern-[0-9]+-holofoil$")
CMC_URL_RE = re.compile(r"^https://cardzmarketcap\.com/card/cmc_([0-9a-f]{24})$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceUnavailable(Exception):
    """The public route cannot be used. Callers keep the last good quotes."""


def expected_credit(as_of):
    return (
        "PSA 10 last sale: CardZ Marketcap, https://cardzmarketcap.com, "
        f"data as of {as_of}. CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)."
    )


def card_series(card):
    return f"en-tcg-modern-{card['productId']}-holofoil"


def _valid_price(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _date(value):
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        raise SourceUnavailable("bad date")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise SourceUnavailable("bad date") from exc


def _age(as_of, run_date):
    return (_date(run_date) - _date(as_of)).days


def _forbidden_keys(value, found):
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN:
                found.append(key)
            _forbidden_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            _forbidden_keys(item, found)


def _request(url):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    names = {name.lower() for name, _value in req.header_items()}
    if names & {"authorization", "apikey", "origin"}:
        raise SourceUnavailable("refusing to send credentials or an Origin header")
    return req


def _read_response(response):
    status = getattr(response, "status", None) or getattr(response, "code", 200)
    raw = response.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise SourceUnavailable("response larger than 600 kB")
    return status, raw


def fetch_route(url=ROUTE_URL, timeout=15, retry_delay=10, opener=None):
    """One GET, no key and no Origin. Retries once after a timeout or 5xx."""
    open_url = opener or urllib.request.urlopen
    last = "source unavailable"
    for attempt in (1, 2):
        try:
            request = _request(url)
            with open_url(request, timeout=timeout) as response:
                status, raw = _read_response(response)
            if status != 200:
                raise urllib.error.HTTPError(url, status, "unexpected status", hdrs=None, fp=None)
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SourceUnavailable("bad JSON") from exc
            if not isinstance(parsed, dict):
                raise SourceUnavailable("response is not an object")
            return parsed
        except SourceUnavailable:
            raise
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code >= 500 and attempt == 1:
                time.sleep(retry_delay)
                continue
            raise SourceUnavailable(last) from exc
        except TimeoutError as exc:
            last = "timeout"
            if attempt == 1:
                time.sleep(retry_delay)
                continue
            raise SourceUnavailable(last) from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            timed_out = isinstance(reason, TimeoutError) or "timed out" in str(reason).lower()
            last = "timeout" if timed_out else f"network error: {reason}"
            if timed_out and attempt == 1:
                time.sleep(retry_delay)
                continue
            raise SourceUnavailable(last) from exc
    raise SourceUnavailable(last)


def validate(resp, run_date):
    if not isinstance(resp, dict):
        raise SourceUnavailable("response is not an object")
    encoded = json.dumps(resp, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_BODY:
        raise SourceUnavailable("response larger than 600 kB")
    found = []
    _forbidden_keys(resp, found)
    if found:
        raise SourceUnavailable("forbidden key")
    if set(resp) != TOP_KEYS:
        raise SourceUnavailable("unexpected response keys")
    run = _date(run_date)
    if resp["schemaVersion"] != 1 or type(resp["schemaVersion"]) is not int:
        raise SourceUnavailable("schemaVersion")
    if resp["available"] is not True:
        raise SourceUnavailable("available")
    if resp["view"] != "cardz-psa10-public" or resp["index"] != "tcg-modern":
        raise SourceUnavailable("view")
    if resp["grade"] != "PSA 10" or resp["currency"] != "USD" or resp["licence"] != LICENCE:
        raise SourceUnavailable("grade")
    if resp["label"] != LABEL or resp["source"] != "CardZ Marketcap" or resp["sourceHome"] != HOME:
        raise SourceUnavailable("source")
    if resp["licenceUrl"] != LICENCE_URL:
        raise SourceUnavailable("licence")
    effective = _date(resp["effectiveDay"])
    if effective > run or resp["credit"] != expected_credit(resp["effectiveDay"]):
        raise SourceUnavailable("credit")
    rows = resp["rows"]
    if not isinstance(rows, list) or resp["count"] != len(rows) or type(resp["count"]) is not int or resp["count"] > 100:
        raise SourceUnavailable("count")
    if not isinstance(resp["generatedAt"], str) or not resp["generatedAt"]:
        raise SourceUnavailable("generatedAt")
    version = resp["sourceVersion"]
    if version is not None and (not isinstance(version, str) or not HEX64_RE.fullmatch(version)):
        raise SourceUnavailable("sourceVersion")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            raise SourceUnavailable("row keys")
        if not isinstance(row["card_id"], str) or not CARD_RE.fullmatch(row["card_id"]) or row["card_id"] in seen:
            raise SourceUnavailable("card_id")
        seen.add(row["card_id"])
        if type(row["public_id"]) is not int or row["public_id"] <= 0:
            raise SourceUnavailable("public_id")
        if not _valid_price(row["psa10_last_sale_usd"]) or row["currency"] != "USD":
            raise SourceUnavailable("price")
        as_of = _date(row["as_of"])
        if as_of > run or row["status"] not in {"ok", "stale"}:
            raise SourceUnavailable("as_of")
        if row["confidence"] not in {"high", "medium"}:
            raise SourceUnavailable("confidence")
        if not isinstance(row["cardz_url"], str) or not CMC_URL_RE.fullmatch(row["cardz_url"]):
            raise SourceUnavailable("cardz_url")
        if row["grade"] != "PSA 10" or row["label"] != LABEL or row["credit"] != expected_credit(row["as_of"]):
            raise SourceUnavailable("row credit")
        if row["language"] != "English" or row["printing"] != "Holofoil":
            raise SourceUnavailable("printing")
    return resp


def load_allowlist(path):
    path = Path(path)
    if not path.is_file():
        raise SourceUnavailable(f"allowlist missing: {path}")
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceUnavailable("allowlist unreadable") from exc
    if not isinstance(data, list) or not data or len(data) > 100:
        raise SourceUnavailable("allowlist length")
    seen = set()
    for row in data:
        if not isinstance(row, dict) or set(row) != ALLOW_KEYS:
            raise SourceUnavailable("allowlist keys")
        if type(row["publicId"]) is not int or row["publicId"] <= 0 or row["publicId"] in seen:
            raise SourceUnavailable("allowlist publicId")
        seen.add(row["publicId"])
        if not isinstance(row["seriesKey"], str) or not CARD_RE.fullmatch(row["seriesKey"]):
            raise SourceUnavailable("allowlist seriesKey")
        if not isinstance(row["cmcId"], str) or not re.fullmatch(r"[0-9a-f]{24}", row["cmcId"]):
            raise SourceUnavailable("allowlist cmcId")
        if not isinstance(row["approvedOn"], str) or not DATE_RE.fullmatch(row["approvedOn"]):
            raise SourceUnavailable("allowlist approvedOn")
        if row["confidence"] not in {"high", "medium"}:
            raise SourceUnavailable("allowlist confidence")
        if row["review"] != REVIEW:
            raise SourceUnavailable("allowlist review")
    return data


def _snapshot(data):
    saved = {}
    for card in data.get("cards", []):
        quote = (card.get("quotes") or {}).get("PSA 10")
        if isinstance(quote, dict) and _valid_price(quote.get("price")):
            saved[card["id"]] = copy.deepcopy(quote)
    return saved


def _strip_psa9(card):
    card.get("quotes", {}).pop("PSA 9", None)
    sources = card.get("sources")
    if isinstance(sources, dict):
        sources.pop("PSA 9", None)


def _classify(quote, run_date):
    if not isinstance(quote, dict) or not _valid_price(quote.get("price")):
        return "pending"
    as_of = quote.get("as_of") or quote.get("date")
    try:
        age = _age(as_of, run_date)
    except SourceUnavailable:
        return "pending"
    if age < 0 or age > 30:
        return "pending"
    if quote.get("status") == "stale" or age > 3:
        return "stale"
    return "priced"


def _counts(modern, run_date, held):
    priced = stale = pending = 0
    for card in modern["cards"]:
        kind = _classify((card.get("quotes") or {}).get("PSA 10"), run_date)
        if kind == "priced":
            priced += 1
        elif kind == "stale":
            stale += 1
        else:
            pending += 1
    return {"priced": priced, "stale": stale, "pending": pending, "held": held}


def _write_holds(holds_dir, run_date, holds):
    if not holds or holds_dir is None:
        return None
    path = Path(holds_dir) / f"{run_date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        try:
            loaded = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            loaded = []
        existing = loaded if isinstance(loaded, list) else [loaded]
    existing.extend(holds)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n")
    return path


def _restore_stale(modern, previous_quotes, status, reason, run_date, holds, holds_dir):
    for card in modern["cards"]:
        _strip_psa9(card)
        quotes = card.setdefault("quotes", {})
        previous = previous_quotes.get(card["id"])
        if previous and _valid_price(previous.get("price")):
            kept = copy.deepcopy(previous)
            kept["status"] = "stale"
            quotes["PSA 10"] = kept
            if kept.get("url"):
                card.setdefault("sources", {})["PSA 10"] = kept["url"]
        else:
            quotes.pop("PSA 10", None)
    modern["psa10Refresh"] = {"status": status, "reason": reason, "runDate": run_date}
    _write_holds(holds_dir, run_date, holds)
    return _counts(modern, run_date, sum(1 for hold in holds if hold.get("reason") in {"jump", "sanity"})), holds


def _quote(row, run_date):
    status = "stale" if row["status"] == "stale" or _age(row["as_of"], run_date) > 3 else "ok"
    return {
        "price": row["psa10_last_sale_usd"],
        "currency": "USD",
        "source": "CardZ",
        "provider": "CardZ Marketcap",
        "as_of": row["as_of"],
        "date": row["as_of"],
        "url": row["cardz_url"],
        "credit": row["credit"],
        "licence": LICENCE,
        "licenceUrl": LICENCE_URL,
        "confidence": row["confidence"],
        "method": METHOD,
        "status": status,
    }


def apply_psa10(modern_data, resp, allowlist, previous_data, run_date, holds_dir=None, unavailable=None):
    """Return ({priced, stale, pending, held}, holds). Never writes Raw or PSA 9."""
    _date(run_date)
    previous_quotes = _snapshot(previous_data if previous_data is not None else modern_data)
    if unavailable:
        return _restore_stale(modern_data, previous_quotes, "source_unavailable", str(unavailable), run_date, [], holds_dir)
    try:
        rows = {row["card_id"]: row for row in resp["rows"]}
        if resp["count"] == 0 and len(previous_quotes) > 10:
            receipt = [{"reason": "source_empty", "previousPriced": len(previous_quotes), "asOf": run_date}]
            return _restore_stale(modern_data, previous_quotes, "source_empty", "empty route", run_date, receipt, holds_dir)
        allow_by_series = {row["seriesKey"]: row for row in allowlist}
        holds = []
        for card in modern_data["cards"]:
            _strip_psa9(card)
            series = card_series(card)
            approved = allow_by_series.get(series)
            row = rows.get(series)
            matched = None
            if approved and row and approved["publicId"] == card["id"] == row["public_id"]:
                cmc = CMC_URL_RE.fullmatch(row["cardz_url"])
                if cmc and cmc.group(1) == approved["cmcId"] and approved["seriesKey"] == row["card_id"]:
                    matched = row
            quotes = card.setdefault("quotes", {})
            if not matched:
                quotes.pop("PSA 10", None)
                continue
            new_price = matched["psa10_last_sale_usd"]
            previous = previous_quotes.get(card["id"])
            raw = quotes.get("Raw") or {}
            reason = None
            if previous and _valid_price(previous.get("price")) and (new_price > previous["price"] * 3 or new_price * 3 < previous["price"]):
                reason = "jump"
            elif raw.get("currency") == "USD" and _valid_price(raw.get("price")) and new_price <= raw["price"]:
                reason = "sanity"
            if reason:
                holds.append({
                    "cardId": card["id"], "productId": card["productId"], "newPrice": new_price,
                    "previousPrice": previous.get("price") if previous else None,
                    "asOf": matched["as_of"], "reason": reason,
                })
                if previous and _valid_price(previous.get("price")):
                    kept = copy.deepcopy(previous)
                    kept["status"] = "stale"
                    quotes["PSA 10"] = kept
                    if kept.get("url"):
                        card.setdefault("sources", {})["PSA 10"] = kept["url"]
                else:
                    quotes.pop("PSA 10", None)
                continue
            quote = _quote(matched, run_date)
            if set(quote) != QUOTE_KEYS or not _valid_price(quote["price"]):
                raise SourceUnavailable("quote")
            quotes["PSA 10"] = quote
            card.setdefault("sources", {})["PSA 10"] = quote["url"]
        modern_data["psa10Refresh"] = {"status": "ok", "runDate": run_date, "effectiveDay": resp["effectiveDay"]}
        _write_holds(holds_dir, run_date, holds)
        return _counts(modern_data, run_date, len(holds)), holds
    except Exception as exc:
        reason = str(exc) or exc.__class__.__name__
        return _restore_stale(modern_data, previous_quotes, "source_unavailable", reason, run_date, [], holds_dir)


def annotate_release(data, counts, effective_day):
    coverage = data.setdefault("coverage", {})
    coverage.pop("PSA 9", None)
    coverage["PSA 10"] = counts["priced"] + counts["stale"]
    release = data.setdefault("release", {})
    release["gradedStatus"] = GRADED_STATUS
    previous = release.get("psa10") if isinstance(release.get("psa10"), dict) else {}
    release["psa10"] = {
        "source": "CardZ Marketcap",
        "licence": LICENCE,
        "effectiveDay": effective_day or previous.get("effectiveDay"),
        "priced": counts["priced"],
        "stale": counts["stale"],
        "pending": counts["pending"],
        "held": counts["held"],
        "review": "2026-11-16",
    }


def refresh_modern(modern, allowlist_path, holds_dir, run_date, fetch=None):
    """Apply one route read. Any failure keeps the last PSA 10 quotes and returns."""
    fetch = fetch or fetch_route
    effective = None
    try:
        allowlist = load_allowlist(allowlist_path)
        resp = validate(fetch(), run_date)
        counts, _holds = apply_psa10(modern, resp, allowlist, modern, run_date, holds_dir=holds_dir)
        effective = resp.get("effectiveDay")
    except SourceUnavailable as exc:
        print(f"PSA 10 source unavailable: {exc}", file=sys.stderr)
        counts, _holds = apply_psa10(modern, None, [], modern, run_date, holds_dir=holds_dir, unavailable=str(exc))
        previous = (modern.get("release") or {}).get("psa10")
        effective = previous.get("effectiveDay") if isinstance(previous, dict) else None
    except Exception as exc:
        print(f"PSA 10 source unavailable: {exc}", file=sys.stderr)
        counts, _holds = apply_psa10(
            modern, None, [], modern, run_date, holds_dir=holds_dir, unavailable=f"importer error: {exc}")
    modern["_psa10Import"] = {"counts": counts, "effectiveDay": effective}
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-date", default=dt.date.today().isoformat())
    parser.add_argument("--fixture", type=Path, help="Saved route JSON. Omit to GET the public route.")
    parser.add_argument("--write", action="store_true", help="Write catalogue.js and market-release.json")
    args = parser.parse_args(argv)
    root = args.site_dir
    import daily_refresh as refresh
    modern = refresh.read_js(root / "catalogue.js", "window.MODERN_PREVIEW_DATA")
    holds = root / "data/refresh/psa10-holds"

    def fetch():
        if args.fixture:
            return json.loads(args.fixture.read_text())
        return fetch_route()

    counts = refresh_modern(modern, root / "data/psa10/cardz-approved.json", holds, args.run_date, fetch=fetch)
    info = modern.pop("_psa10Import")
    annotate_release(modern, info["counts"], info["effectiveDay"])
    print(json.dumps({"counts": counts, "psa10Refresh": modern.get("psa10Refresh"), "gradedStatus": modern["release"]["gradedStatus"]}, indent=2))
    if args.write:
        refresh.write_js(root / "catalogue.js", "window.MODERN_PREVIEW_DATA", modern)
        refresh.write_json(root / "market-release.json", modern["release"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
