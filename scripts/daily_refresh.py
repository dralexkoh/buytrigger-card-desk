#!/usr/bin/env python3
"""Incremental, public-only TCGCSV Raw collector (Python standard library).

Always writes to a separate --output-dir; the caller validates and promotes the
allowlisted outputs as one release. No private inputs, database, trading, image
or graded-price access. This is a guide feed, not verified individual sales.

Output: catalogue.js, market-history.js, market-release.json, market-sources.json,
top50-data.js, top50-release.json, top50-sources.json, refresh-status.json, and
append-only data/refresh/{observations,receipts,review}/ plus state.json.
The data/refresh directory must be committed durably with each published update.
Cache responses are optional accelerators, never the only copy of provenance.

Factor-of-two daily changes trigger REVIEW, not a declaration of a bad price.
Existing historical exclusions and accepted sharp changes remain untouched.
A held source amount stays in the immutable observation and history array, with
an exclusion preventing chart use. The displayed last-valid quote keeps its
original source date. Review decisions are an explicit later operator action;
this collector cannot silently approve a hold or reconstitute either basket.

Backfill downloads only missing dates after the original daily baseline, at most
--max-backfill-days per run (default 7); archives are cached and never refetched
when a durable receipt exists. Earlier monthly gaps are intentional. 7z/7zz is
required only when recovering an actual missed archive. Unsupported dates remain
gaps. A live partial upstream build fails atomically without changing payloads.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import email.utils
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

SCHEMA = 1
BASE = "https://tcgcsv.com"
USER_AGENT = "BuyTrigger.Cards/1.1 (+https://buytrigger.cards/)"
FILES = ("catalogue.js", "market-history.js", "market-release.json", "market-sources.json",
         "top50-data.js", "top50-release.json", "top50-sources.json")
PUBLIC_OUTPUTS = (*FILES, "refresh-status.json", "data/refresh")
POLICY = {"id": "daily-factor-two-review-v1", "factor": 2,
          "minimumPreviousObservations": 3, "recentWindow": 7,
          "meaning": "Review trigger only; genuine source-guide moves can exceed this threshold.",
          "historicalApplication": "None: existing reviewed observations and exclusions are preserved."}
UTC = dt.timezone.utc


class RefreshError(Exception):
    pass


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def timestamp(value):
    try:
        normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", value.strip().replace("Z", "+00:00"))
        parsed = dt.datetime.fromisoformat(normalized)
    except (ValueError, TypeError) as exc:
        raise RefreshError("Invalid provider build timestamp") from exc
    if parsed.tzinfo is None:
        raise RefreshError("Provider build timestamp must contain a timezone")
    return parsed.astimezone(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def read_json(path):
    return json.loads(path.read_text())


def read_js(path, variable):
    text = path.read_text()
    match = re.fullmatch(r"\s*" + re.escape(variable) + r"\s*=\s*(.*?)\s*;?\s*", text, re.S)
    if not match:
        raise RefreshError(f"Unexpected public payload format: {path.name}")
    return json.loads(match.group(1).rstrip(";"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def immutable_json(path, value):
    data = canonical(value)
    if path.exists() and path.read_bytes() != data:
        raise RefreshError(f"Immutable receipt conflict: {path.name}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def write_js(path, variable, value):
    path.write_text(variable + "=" + canonical(value).decode().strip().replace("</", "<\\/") + ";\n")


def key(card):
    return f"{card['productId']}|{card['printing']}"


def date_range(start, end):
    first, last = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    return [(first + dt.timedelta(days=i)).isoformat() for i in range(max(0, (last - first).days + 1))]


class Provider:
    """Cache keyed by build/resource; fixture mode performs no network requests."""
    def __init__(self, cache, fixture=None):
        self.cache = cache
        self.fixture = fixture
        self.requests = []
        self.previous_request = 0.0
        self.marker_reads = 0

    def get(self, path, namespace=None):
        self.requests.append(path)
        cache = self.cache / namespace / (sha(path.encode()) + ".json") if namespace else None
        if cache and cache.exists():
            result = read_json(cache)
            if sha(result["body"].encode()) != result["sha256"]:
                raise RefreshError("Cached response checksum mismatch")
            return result
        if self.fixture:
            name = path.lstrip("/")
            if name == "last-updated.txt":
                self.marker_reads += 1
                alternate = self.fixture / "last-updated-after.txt"
                if self.marker_reads > 1 and alternate.exists():
                    name = "last-updated-after.txt"
            local = self.fixture / name
            if not local.exists():
                raise RefreshError(f"Source unavailable: {path}")
            body = local.read_text()
            header_file = local.with_name(local.name + ".headers.json")
            headers = read_json(header_file) if header_file.exists() else {}
        else:
            time.sleep(max(0, .11 - (time.monotonic() - self.previous_request)))
            req = urllib.request.Request(BASE + "/" + path.lstrip("/"), headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
            try:
                with urllib.request.urlopen(req, timeout=45) as response:
                    body = response.read().decode("utf-8")
                    headers = {k.lower(): v for k, v in response.headers.items()}
            except (urllib.error.URLError, TimeoutError, UnicodeError) as exc:
                raise RefreshError(f"Source unavailable: {path}: {type(exc).__name__}") from exc
            finally:
                self.previous_request = time.monotonic()
        result = {"url": BASE + "/" + path.lstrip("/"), "body": body, "sha256": sha(body.encode()),
                  "bytes": len(body.encode()), "lastModified": headers.get("last-modified"), "etag": headers.get("etag")}
        if cache:
            write_json(cache, result)
        return result

    def marker(self):
        receipt = self.get("last-updated.txt")
        return timestamp(receipt["body"]), receipt

    def live(self, identities, build):
        resources = []
        groups = {}
        namespace = build.strftime("%Y%m%dT%H%M%SZ")
        for group in sorted({c["groupId"] for c in identities.values()}):
            result = self.get(f"tcgplayer/3/{group}/prices", namespace)
            try:
                modified = email.utils.parsedate_to_datetime(result["lastModified"]).astimezone(UTC)
            except (ValueError, TypeError, AttributeError) as exc:
                raise RefreshError(f"Group {group}: missing or invalid source Last-Modified") from exc
            if modified.date() != build.date() or modified > build:
                raise RefreshError(f"Group {group}: source resource is outside the published build")
            groups[group] = parse_group(result["body"], group)
            resources.append({k: v for k, v in result.items() if k != "body"})
        after, _ = self.marker()
        if after != build:
            raise RefreshError("Provider build changed during collection; no mixed build published")
        return groups, resources

    def archive(self, date, identities):
        path = f"archive/tcgplayer/prices-{date}.ppmd.7z"
        if self.fixture:
            root = self.fixture / "archives" / date
            groups = {}
            for group in sorted({c["groupId"] for c in identities.values()}):
                local = root / "3" / str(group) / "prices"
                if not local.exists():
                    raise RefreshError(f"Archive unavailable: {date}")
                groups[group] = parse_group(local.read_text(), group)
            payload = canonical(groups)
            return groups, [{"url": BASE + "/" + path, "sha256": sha(payload), "bytes": len(payload), "archiveDate": date}]
        archive = self.cache / "archives" / Path(path).name
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            time.sleep(max(0, .11 - (time.monotonic() - self.previous_request)))
            req = urllib.request.Request(BASE + "/" + path, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=90) as response:
                    data = response.read()
                temp = archive.with_suffix(".part")
                temp.write_bytes(data)
                temp.replace(archive)
            except (urllib.error.URLError, TimeoutError) as exc:
                raise RefreshError(f"Archive unavailable: {date}: {type(exc).__name__}") from exc
            finally:
                self.previous_request = time.monotonic()
        self.requests.append(path)
        extractor = shutil.which("7zz") or shutil.which("7z")
        if not extractor:
            raise RefreshError("Recovery requires 7zz or 7z; source gap retained")
        groups = {}
        for group in sorted({c["groupId"] for c in identities.values()}):
            result = subprocess.run([extractor, "x", "-so", str(archive), f"{date}/3/{group}/prices"], capture_output=True, timeout=60)
            if result.returncode or not result.stdout:
                raise RefreshError(f"Archive {date}: required group {group} missing")
            groups[group] = parse_group(result.stdout.decode(), group)
        return groups, [{"url": BASE + "/" + path, "sha256": sha(archive.read_bytes()), "bytes": archive.stat().st_size, "archiveDate": date}]


def parse_group(body, group):
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise RefreshError(f"Invalid JSON in group {group}") from exc
    if payload.get("success") is not True or payload.get("errors") or not isinstance(payload.get("results"), list):
        raise RefreshError(f"Provider error in group {group}")
    result = {}
    for row in payload["results"]:
        if not isinstance(row.get("productId"), int) or not isinstance(row.get("subTypeName"), str):
            raise RefreshError(f"Malformed identity in group {group}")
        row_key = f"{row['productId']}|{row['subTypeName']}"
        if row_key in result:
            raise RefreshError(f"Duplicate product/printing in group {group}: {row_key}")
        result[row_key] = row
    return result


def validate_baseline(modern, history, top):
    """Identity and frozen cohort guards independent of changing daily values."""
    expected = ((modern, history, 100, {"january": 82, "current": 99}),
                (top, top["history"], 50, {"history": 14, "current": 50}))
    identities = {}
    for data, hist, count, cohorts in expected:
        if len(data["cards"]) != count or len({key(c) for c in data["cards"]}) != count:
            raise RefreshError("Public membership identity/count changed")
        if hist["dates"] != sorted(set(hist["dates"])):
            raise RefreshError("Duplicate or unordered history dates")
        ids = {c["id"] for c in data["cards"]}
        for cohort, size in cohorts.items():
            members = hist["cohorts"][cohort]["members"]
            if len(members) != size or len(set(members)) != size or not set(members) <= ids:
                raise RefreshError("Frozen cohort membership is invalid")
        for card in data["cards"]:
            if card["language"] != "English" or not card.get("printing") or not isinstance(card["productId"], int) or not isinstance(card["groupId"], int):
                raise RefreshError("Unapproved public source identity")
            if len(hist["prices"][str(card["id"])]) != len(hist["dates"]):
                raise RefreshError("History length mismatch")
            prior = identities.get(key(card))
            if prior and prior["groupId"] != card["groupId"]:
                raise RefreshError("Overlapping baskets disagree about group identity")
            # This dated EUR guide is intentionally outside the daily USD collector.
            if card["productId"] != 85203:
                identities[key(card)] = {"productId": card["productId"], "groupId": card["groupId"], "printing": card["printing"], "language": "English", "currency": "USD"}
    return identities


def prior_values(card_key, date, datasets):
    observations = {}
    for data, hist in datasets:
        card = next((c for c in data["cards"] if key(c) == card_key), None)
        if not card:
            continue
        held = {(e["cardId"], e["date"]) for e in hist.get("exclusions", [])}
        for day, amount in zip(hist["dates"], hist["prices"][str(card["id"])]):
            if day < date and positive(amount) and (card["id"], day) not in held:
                observations[day] = amount
    return sorted(observations.items())[-7:]


def suspicion(amount, previous, date):
    if not positive(amount) or len(previous) < POLICY["minimumPreviousObservations"]:
        return None
    # Monthly legacy snapshots are not treated as one-day errors.
    if (dt.date.fromisoformat(date) - dt.date.fromisoformat(previous[-1][0])).days > 7:
        return None
    latest = previous[-1][1]
    median = statistics.median(v for _, v in previous)
    ratio = lambda a, b: max(a / b, b / a)
    if ratio(amount, latest) >= POLICY["factor"] and ratio(amount, median) >= POLICY["factor"]:
        return {"reason": "New source guide differs by at least a factor of two from both the previous valid guide and recent median; review required, not confirmed erroneous.",
                "previousDate": previous[-1][0], "previousValue": latest, "recentMedian": median, "policy": POLICY["id"]}
    return None


def collect_observations(date, groups, identities, datasets):
    rows = []
    for card_key, identity in sorted(identities.items()):
        raw = groups[identity["groupId"]].get(card_key)
        amount = raw.get("marketPrice") if raw else None
        reason = None
        if raw and raw.get("currency", "USD") != "USD":
            reason = "Unexpected source currency; exact USD guide missing"
        elif not raw:
            reason = "Exact product and printing absent from source"
        elif not positive(amount):
            reason = "Null, nonpositive or invalid source marketPrice"
        review = suspicion(amount, prior_values(card_key, date, datasets), date) if not reason else None
        rows.append({"key": card_key, **identity, "amount": amount if positive(amount) else None,
                     "status": "missing" if reason else "held" if review else "accepted",
                     "reason": reason, "review": review, "sourceRow": raw})
    return rows


def add_date(hist, date):
    if date in hist["dates"]:
        return hist["dates"].index(date)
    index = next((i for i, old in enumerate(hist["dates"]) if old > date), len(hist["dates"]))
    hist["dates"].insert(index, date)
    for values in hist["prices"].values():
        values.insert(index, None)
    return index


def apply_observations(observation, datasets, review_root):
    date = observation["sourceDate"]
    rows = {row["key"]: row for row in observation["observations"]}
    for name, data, hist in datasets:
        index = add_date(hist, date)
        hist.setdefault("sourceReceipts", {})[date] = "data/refresh/receipts/" + observation["id"] + ".json"
        for card in data["cards"]:
            row = rows.get(key(card))
            if not row:
                continue
            existing = hist["prices"][str(card["id"])][index]
            amount = row["amount"]
            if existing is not None and existing != amount:
                raise RefreshError("A source-date revision cannot replace an immutable existing observation")
            if card.get("releaseDate") and date < card["releaseDate"]:
                continue
            hist["prices"][str(card["id"])][index] = amount if row["status"] != "missing" else None
            if row["status"] == "held":
                hold = {"cardId": card["id"], "productId": card["productId"], "date": date,
                        "reportedValue": amount, "currency": "USD", "reason": row["review"]["reason"],
                        "source": observation["sources"][0]["url"] if observation["kind"] == "archive" else f"{BASE}/tcgplayer/3/{card['groupId']}/prices",
                        "reviewStatus": "pending", "policy": POLICY["id"]}
                if not any(e["cardId"] == card["id"] and e["date"] == date for e in hist.get("exclusions", [])):
                    hist.setdefault("exclusions", []).append(hold)
                immutable_json(review_root / f"{date}-{name}-{card['id']}.json", {**hold, "sourceObservationId": observation["id"], "review": row["review"]})


def coverage_and_quotes(data, hist, source_date):
    counts = {"total": len(data["cards"]), "priced": 0, "usd": 0, "eur": 0, "missing": 0, "held": 0, "stale": 0}
    held = {(e["cardId"], e["date"]) for e in hist.get("exclusions", [])}
    for card in data["cards"]:
        quote = card.get("quotes", {}).get("Raw")
        if card["productId"] == 85203:
            counts["eur"] += bool(quote and quote.get("currency") == "EUR")
            # A separately dated EUR reference is not today's fresh USD coverage.
            if quote:
                counts["stale"] += quote.get("date") != source_date
            continue
        values = hist["prices"][str(card["id"])]; index = hist["dates"].index(source_date)
        value = values[index]; excluded = (card["id"], source_date) in held
        if positive(value) and not excluded:
            counts["priced"] += 1; counts["usd"] += 1
            if not quote:
                quote = {"currency": "USD", "provider": "TCGplayer market via TCGCSV", "source": f"https://www.tcgplayer.com/product/{card['productId']}", "method": "Exact product and printing; mixed-condition Raw USD guide, not a checked individual sale."}
                card.setdefault("quotes", {})["Raw"] = quote
            quote.update({"price": value, "date": source_date, "currency": "USD"})
            card["rawRefresh"] = {"status": "current", "sourceDate": source_date}
        else:
            counts["held" if excluded else "missing"] += 1
            valid = [(day, v) for day, v in zip(hist["dates"], values) if day <= source_date and positive(v) and (card["id"], day) not in held]
            if valid and quote:
                quote.update({"price": valid[-1][1], "date": valid[-1][0]})
                counts["stale"] += 1
            elif quote:
                card["quotes"].pop("Raw", None)
            card["rawRefresh"] = {"status": "held" if excluded else "missing", "sourceDate": source_date,
                                  "lastValidDate": valid[-1][0] if valid else None}
    counts["references"] = sum("Raw" in c.get("quotes", {}) for c in data["cards"])
    return counts


def release_metadata(data, hist, source_date, now, status, name, source_manifest):
    release = data["release"]
    release.setdefault("selectionDate", release["sourceDate"])
    if name == "top50":
        release.setdefault("rankingSourceDate", release["selectionDate"])
    release.update({"published": now[:10], "sourceDate": source_date, "historyEnd": hist["dates"][-1],
                    "dataReleaseId": status["dataReleaseId"], "retrievedAt": now,
                    "sourceBuildAt": status.get("sourceBuildAt"), "automaticRefreshActive": status["automaticRefreshActive"],
                    "refreshStatus": status["status"], "lastSuccessfulCheck": status["lastSuccessfulCheck"],
                    "coverage": status["coverage"][name], "incompleteArchiveDates": status["gaps"]})
    release["historyDays"] = len(hist["dates"])
    documented_dates = {r["date"] for r in source_manifest.get("archives", [])} | {r["date"] for r in source_manifest.get("dailyReceipts", [])}
    release["observedSourceDays"] = len(documented_dates - set(status["gaps"]))
    usable = lambda card, date, amount: positive(amount) and not any(e["cardId"] == card["id"] and e["date"] == date for e in hist.get("exclusions", []))
    if name == "modern":
        release["expectedDays"] = len(date_range(hist["dates"][0], hist["dates"][-1]))
        release["archiveDays"] = len(source_manifest.get("archives", []))
        release["usdPrices"] = status["coverage"][name]["usd"]
        release["rawReferences"] = status["coverage"][name]["references"]
        data["captured"] = now
        data["coverage"]["Raw"] = release["rawReferences"]
        q = release.setdefault("historyQuality", {})
        q["reportedPrices"] = sum(positive(v) for values in hist["prices"].values() for v in values)
        q["sourceAnomaliesHeld"] = len(hist.get("exclusions", []))
        q["sourceGaps"] = sum(v is None and d >= c["releaseDate"] for c in data["cards"] for d, v in zip(hist["dates"], hist["prices"][str(c["id"])]))
    else:
        release["archiveCount"] = len(source_manifest.get("archives", []))
        release["historyObservations"] = sum(usable(c, d, v) for c in data["cards"] for d, v in zip(hist["dates"], hist["prices"][str(c["id"])]))
        release["heldSourceObservations"] = len(hist.get("exclusions", []))
        source_manifest["heldObservations"] = copy.deepcopy(hist.get("exclusions", []))


def run(args):
    site, output = args.site_dir.resolve(), args.output_dir.resolve()
    if output == site or site.is_relative_to(output) or output.is_relative_to(site):
        raise RefreshError("Output must be isolated outside the public source directory")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RefreshError("Output directory must be empty; prevents partial-stage replay")
    for file in FILES:
        shutil.copy2(site / file, output / file)
    if (site / "data/refresh").exists():
        shutil.copytree(site / "data/refresh", output / "data/refresh")
    prior_status = read_json(site / "refresh-status.json") if (site / "refresh-status.json").exists() else {}
    modern = read_js(site / "catalogue.js", "window.MODERN_PREVIEW_DATA")
    history = read_js(site / "market-history.js", "window.BT_HISTORY")
    top = read_js(site / "top50-data.js", "window.BT_TOP50")
    identities = validate_baseline(modern, history, top)
    shared_path = site / "thirtieth-catalogue.json"
    shared_catalogue = read_json(shared_path) if shared_path.exists() else None
    collection_identities = dict(identities)
    if shared_catalogue:
        from shared_set_cache import identities as set_identities
        for card_key, card in set_identities(shared_catalogue).items():
            collection_identities.setdefault(card_key, card)
        shared_cache = site / "data/market-cache/thirtieth-current.json"
        if shared_cache.exists():
            destination = output / "data/market-cache/thirtieth-current.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(shared_cache, destination)
    sources = {"modern": read_json(site / "market-sources.json"), "top50": read_json(site / "top50-sources.json")}
    datasets = [(modern, history), (top, top["history"])]
    named = [("modern", modern, history), ("top50", top, top["history"])]
    now = iso(timestamp(args.now)) if args.now else iso(dt.datetime.now(UTC))
    state_path = output / "data/refresh/state.json"
    baseline_end = min(history["dates"][-1], top["history"]["dates"][-1])
    state = read_json(state_path) if state_path.exists() else {"schemaVersion": SCHEMA, "baselineEndDate": baseline_end, "processedBuilds": [], "observedArchiveDates": [], "gaps": []}
    provider = Provider(args.cache_dir.resolve(), args.fixture_dir)
    status = {"schemaVersion": SCHEMA, "runKind": args.run_kind, "checkedAt": now,
              "lastSuccessfulCheck": prior_status.get("lastSuccessfulCheck"), "sourceDate": baseline_end,
              "sourceBuildAt": prior_status.get("sourceBuildAt"),
              "schedulerEnabled": args.activate or prior_status.get("schedulerEnabled", False),
              "lastSuccessfulScheduledCheck": prior_status.get("lastSuccessfulScheduledCheck"),
              "automaticRefreshActive": (args.activate or prior_status.get("schedulerEnabled", False)) and bool(prior_status.get("lastSuccessfulScheduledCheck")),
              "dataReleaseId": prior_status.get("dataReleaseId", "raw-baseline-" + baseline_end),
              "changedCount": 0, "missingCount": 0, "heldCount": 0, "newObservationDates": [],
              "gaps": state.get("gaps", []), "lastError": None, "anomalyPolicy": POLICY,
              "selectionDates": {name: data["release"].get("selectionDate", "2026-11-02") for name, data, _ in named}}
    try:
        build, marker_receipt = provider.marker()
        if build > timestamp(now) + dt.timedelta(minutes=5):
            raise RefreshError("Source build timestamp is in the future")
        source_date = build.date().isoformat()
        status["sourceBuildAt"] = iso(build)
        if source_date < baseline_end:
            raise RefreshError("Provider build is older than the accepted public baseline")
        pending = []
        # A baseline matching the same source day already has reviewed archive provenance.
        # Record marker verification without downloading/replacing that day's data.
        build_key = build.strftime("%Y%m%dT%H%M%SZ")
        if not state["processedBuilds"] and source_date == state["baselineEndDate"]:
            state["processedBuilds"].append(iso(build))
            immutable_json(output / f"data/refresh/receipts/baseline-{build_key}.json", {
                "schemaVersion": SCHEMA, "kind": "reviewed-baseline-marker-check", "sourceDate": source_date,
                "sourceBuildAt": iso(build), "checkedAt": now,
                "marker": {k: v for k, v in marker_receipt.items() if k != "body"},
                "payloadChecksums": {f: sha((site / f).read_bytes()) for f in FILES}})
        elif iso(build) not in state["processedBuilds"]:
            if (output / f"data/refresh/review/revision-raw-{source_date}-{build_key}.json").exists():
                raise RefreshError("This source-date revision is already retained and awaiting explicit review; no repeated source download")
            if state["processedBuilds"] and build <= max(timestamp(b) for b in state["processedBuilds"]):
                raise RefreshError("Provider build did not advance monotonically")
            groups, resources = provider.live(collection_identities, build)
            pending.append((source_date, "live", iso(build), groups, resources))
        # Recover genuine post-baseline gaps, not intentionally sampled older months.
        first = (dt.date.fromisoformat(state["baselineEndDate"]) + dt.timedelta(days=1)).isoformat()
        last = (build.date() - dt.timedelta(days=1)).isoformat()
        required = set(date_range(first, last)) | set(state.get("gaps", []))
        if args.backfill_from:
            if args.backfill_from <= state["baselineEndDate"]:
                raise RefreshError("Backfill cannot revise the reviewed baseline")
            if args.backfill_to and args.backfill_to >= source_date:
                raise RefreshError("Backfill end must precede the current published source date")
            required |= set(date_range(args.backfill_from, args.backfill_to or last))
        observed_live = {timestamp(b).date().isoformat() for b in state["processedBuilds"]}
        required -= observed_live | set(state["observedArchiveDates"])
        gaps = set(required)
        recovery_errors = []
        for day in sorted(required)[:args.max_backfill_days]:
            try:
                groups, resources = provider.archive(day, identities)
                pending.append((day, "archive", None, groups, resources))
                gaps.discard(day)
            except RefreshError as exc:
                recovery_errors.append(str(exc))
        pending.sort(key=lambda item: (item[0], item[1]))
        for day, kind, build_at, groups, resources in pending:
            rows = collect_observations(day, groups, identities, datasets)
            if kind == "live" and shared_catalogue:
                from shared_set_cache import build_cache
                cache_file = output / "data/market-cache/thirtieth-current.json"
                prior_cache = read_json(cache_file) if cache_file.exists() else None
                shared_result = build_cache(shared_catalogue, groups, resources, build, prior_cache, suspicion)
                write_json(cache_file, shared_result)
            observation_id = f"raw-{day}-" + (build_key if kind == "live" else "archive")
            observation = {"schemaVersion": SCHEMA, "id": observation_id, "kind": kind,
                           "sourceDate": day, "sourceBuildAt": build_at, "retrievedAt": now,
                           "currency": "USD", "provider": "TCGplayer market via TCGCSV",
                           "sources": resources, "observations": rows}
            # First receipt wins. A same-date source revision cannot silently overwrite history.
            for data, hist in datasets:
                if day in hist["dates"]:
                    for card in data["cards"]:
                        row = next((r for r in rows if r["key"] == key(card)), None)
                        old = hist["prices"][str(card["id"])][hist["dates"].index(day)]
                        if row and old is not None and old != row["amount"]:
                            immutable_json(output / f"data/refresh/review/revision-{observation_id}.json", observation)
                            raise RefreshError("Changed values in an already observed source date require explicit revision review")
            immutable_json(output / f"data/refresh/observations/{day}/{observation_id}.json", observation)
            apply_observations(observation, named, output / "data/refresh/review")
            counts = {s: sum(r["status"] == s for r in rows) for s in ("accepted", "missing", "held")}
            receipt = {"schemaVersion": SCHEMA, "id": observation_id, "sourceDate": day,
                       "sourceBuildAt": build_at, "retrievedAt": now, "kind": kind,
                       "observationSha256": sha(canonical(observation)), "sources": resources,
                       "counts": counts, "uniqueExactPrintings": len(rows)}
            immutable_json(output / f"data/refresh/receipts/{observation_id}.json", receipt)
            status["changedCount"] += sum(r["status"] == "accepted" and (not prior_values(r["key"], day, datasets) or prior_values(r["key"], day, datasets)[-1][1] != r["amount"]) for r in rows)
            status["newObservationDates"].append(day)
            if kind == "live":
                state["processedBuilds"].append(build_at)
            else:
                state["observedArchiveDates"].append(day)
            for name in sources:
                sources[name].setdefault("dailyReceipts", []).append({"date": day, "id": observation_id, "sourceBuildAt": build_at, "receipt": f"data/refresh/receipts/{observation_id}.json", "observationSha256": receipt["observationSha256"]})
                if kind == "archive":
                    sources[name].setdefault("archives", []).append({"date": day, **resources[0]})
        # Insert explicit daily gaps so charts cannot bridge unsupported observations.
        for day in date_range(first, source_date):
            for _, _, hist in named:
                add_date(hist, day)
        status["sourceDate"] = source_date
        status["lastSuccessfulCheck"] = now
        if args.run_kind == "schedule":
            status["lastSuccessfulScheduledCheck"] = now
        status["automaticRefreshActive"] = status["schedulerEnabled"] and bool(status["lastSuccessfulScheduledCheck"])
        status["gaps"] = sorted(gaps)
        state["gaps"] = status["gaps"]
        status["coverage"] = {name: coverage_and_quotes(data, hist, source_date) for name, data, hist in named}
        status["missingCount"] = sum(v["missing"] for v in status["coverage"].values())
        status["heldCount"] = sum(v["held"] for v in status["coverage"].values())
        delayed = timestamp(now) - build > dt.timedelta(hours=30)
        status["status"] = "delayed" if delayed else "partial" if status["gaps"] or status["missingCount"] or status["heldCount"] else "current"
        status["lastError"] = "; ".join(recovery_errors) or None
        if pending:
            fingerprint = sha(canonical({"build": iso(build), "receipts": [p[0:3] for p in pending]}))[:10]
            status["dataReleaseId"] = f"raw-{source_date}-{fingerprint}"
        for name, data, hist in named:
            release_metadata(data, hist, source_date, now, status, name, sources[name])
        write_js(output / "catalogue.js", "window.MODERN_PREVIEW_DATA", modern)
        write_js(output / "market-history.js", "window.BT_HISTORY", history)
        write_js(output / "top50-data.js", "window.BT_TOP50", top)
        write_json(output / "market-release.json", modern["release"])
        write_json(output / "top50-release.json", top["release"])
        write_json(output / "market-sources.json", sources["modern"])
        write_json(output / "top50-sources.json", sources["top50"])
        write_json(state_path, state)
        status["requestCount"] = len(provider.requests)
        status["uniqueExactPrintings"] = len(identities)
        write_json(output / "refresh-status.json", status)
        return status, 0
    except (RefreshError, ValueError, KeyError, OSError) as exc:
        # Payloads on disk are still the original baseline; staging is not publishable.
        status.update({"status": "failed", "lastError": str(exc), "requestCount": len(provider.requests)})
        status["sourceDate"] = baseline_end
        status["coverage"] = prior_status.get("coverage", {})
        write_json(output / "refresh-status.json", status)
        return status, 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True, help="Empty isolated staging directory, outside site-dir")
    parser.add_argument("--cache-dir", type=Path, default=Path(tempfile.gettempdir()) / "buytrigger-cards-tcgcsv-cache")
    parser.add_argument("--fixture-dir", type=Path, help="Offline fixture directory; no network requests")
    parser.add_argument("--now", help="Explicit UTC time for deterministic tests")
    parser.add_argument("--run-kind", choices=("manual", "schedule"), default="manual")
    parser.add_argument("--activate", action="store_true", help="Record owner-authorized scheduler enablement; does not claim a successful timer run")
    parser.add_argument("--backfill-from")
    parser.add_argument("--backfill-to")
    parser.add_argument("--max-backfill-days", type=int, default=7)
    args = parser.parse_args()
    if args.max_backfill_days < 0 or args.max_backfill_days > 31:
        parser.error("max-backfill-days must be 0..31")
    if args.backfill_to and not args.backfill_from:
        parser.error("backfill-to requires backfill-from")
    try:
        status, code = run(args)
    except (RefreshError, ValueError, KeyError, OSError) as exc:
        print(json.dumps({"status": "failed", "lastError": str(exc)}))
        raise SystemExit(1)
    print(json.dumps({k: status.get(k) for k in ("status", "sourceDate", "sourceBuildAt", "dataReleaseId", "newObservationDates", "changedCount", "missingCount", "heldCount", "gaps", "requestCount", "lastError")}, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
