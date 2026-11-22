"""Rebuild the public price snapshots from the daily market caches.

The public-site job already fetches TCGCSV and writes
data/market-cache/*-current.json. /prices/ pages render data/prices/<slug>.json.
This module copies each page's existing card list (membership stays put) and
replaces the guide and the as-of date with that cache's source date, which is
the public data release in refresh-status.json.
"""
from __future__ import annotations

from pathlib import Path
import json
import re

# Price-page slug, then the daily cache index name.
SLUGS = (
    ('thirtieth-anniversary', 'thirtieth'),
    ('tcg-modern', 'tcg-modern'),
    ('delta-reign', 'delta-reign'),
    ('sv-151', 'sv-151'),
    ('prismatic-evolutions', 'prismatic-evolutions'),
    ('paldean-fates', 'paldean-fates'),
    ('crown-zenith', 'crown-zenith'),
    ('fusion-strike', 'fusion-strike'),
)
PRICE_SNAPSHOTS = tuple(f'data/prices/{slug}.json' for slug, _index in SLUGS)
DAY = re.compile(r'\d{4}-\d{2}-\d{2}')
AS_OF = re.compile(r'as of (\d{1,2} [A-Z][a-z]{2} \d{4})')


def release_date(root: Path) -> str:
    status = json.loads((Path(root) / 'refresh-status.json').read_text())
    day = status.get('sourceDate')
    if not isinstance(day, str) or not DAY.fullmatch(day):
        raise ValueError('refresh-status sourceDate is missing')
    return day


def assert_price_as_of(page_date: str, release: str) -> None:
    """Fail when a /prices/ page's as-of date is not the latest data release."""
    if page_date != release:
        raise AssertionError(
            f'/prices/ as-of {page_date} does not match the latest data release {release}'
        )


def visible_as_of_dates(text: str) -> set[str]:
    return set(AS_OF.findall(text))


def _guide(card: dict, day: str):
    for point in card.get('points') or []:
        if point.get('day') == day:
            return point
    return None


def _rows_by_product(cache: dict) -> dict:
    found: dict[str, list] = {}
    for card in cache.get('cards') or []:
        # Ball-pattern parallels are in the Prismatic cache and out of the public page.
        if card.get('inIndex') is False:
            continue
        found.setdefault(str(card.get('productId')), []).append(card)
    return found


def rebuild_price_snapshots(root: Path) -> list[str]:
    """Write data/prices/<slug>.json from the daily caches. Returns repo-relative paths."""
    root = Path(root)
    prices = root / 'data' / 'prices'
    if not prices.is_dir():
        return []
    present = [pair for pair in SLUGS if (prices / f'{pair[0]}.json').is_file()]
    if not present:
        return []
    release = release_date(root)
    written = []
    for slug, index in present:
        snap_path = prices / f'{slug}.json'
        cache_path = root / 'data' / 'market-cache' / f'{index}-current.json'
        if not cache_path.is_file():
            raise ValueError(f'Missing daily cache for {slug}')
        snapshot = json.loads(snap_path.read_text())
        cache = json.loads(cache_path.read_text())
        if cache.get('sourceDate') != release:
            raise ValueError(
                f'{index} cache sourceDate {cache.get("sourceDate")} != data release {release}'
            )
        by_id = _rows_by_product(cache)
        cards = snapshot.get('cards')
        if not isinstance(cards, list) or not cards:
            raise ValueError(f'{slug} price snapshot has no cards')
        for card in cards:
            pid = str(card.get('tcgplayer_product_id'))
            options = by_id.get(pid) or []
            if len(options) != 1:
                raise ValueError(f'{slug} product {pid} has {len(options)} daily rows')
            point = _guide(options[0], release)
            usd = None if point is None else point.get('usd')
            if not point or point.get('status') != 'ok' or isinstance(usd, bool) or not isinstance(usd, (int, float)) or usd <= 0:
                raise ValueError(f'{slug} product {pid} has no {release} guide')
            card['raw_price_usd'] = usd
        snapshot['source_date'] = release
        if cache.get('sourceBuildAt'):
            snapshot['generated_at'] = cache['sourceBuildAt']
        snap_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n')
        written.append(f'data/prices/{slug}.json')
    return written
