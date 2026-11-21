"""Fail when the same card shows two prices from one data release.

Compares the figure a visitor would see on the price pages, the index pages
and the catalogue files. Set indexes use data/market-cache/<index>-current.json
once their page adapts that file, and the committed snapshot until then.
The 30th Anniversary index follows thirtieth-current.json. TCG Modern follows
catalogue.js. The Raw archive follows top50-data.js. BlueChip is a separate
list and is not compared here.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
import sys

SET_INDEXES = ('delta-reign', 'sv-151', 'prismatic-evolutions')


def _cents(value):
    return round(float(value) + 1e-9, 2)


def _load_js(path: Path):
    text = path.read_text()
    return json.loads(text[text.index('=') + 1:].strip().rstrip(';'))


def _reads_daily(root: Path, index: str) -> bool:
    text = (root / f'{index}.js').read_text()
    return 'data/market-cache/' in text and 'adaptDailyCache' in text


def _cache_guides(root: Path, index: str, public_ids=None):
    cache = json.loads((root / 'data' / 'market-cache' / f'{index}-current.json').read_text())
    guides = {}
    for card in cache['cards']:
        if card.get('inIndex') is False:
            continue
        pid = str(card['productId'])
        if public_ids is not None and pid not in public_ids:
            continue
        point = next((row for row in card['points'] if row.get('day') == cache['sourceDate'] and row.get('status') == 'ok'), None)
        if point and point.get('usd') is not None:
            guides[pid] = _cents(point['usd'])
    return guides


def _snapshot_guides(root: Path, index: str):
    snapshot = json.loads((root / f'{index}-market-snapshot.json').read_text())
    guides = {}
    for card in snapshot['cards']:
        match = re.search(r'(\d+)\.jpg$', card['image'])
        if not match:
            continue
        last = snapshot['points'][card['key']][-1]
        if last[0] == snapshot['sourceDate'] and last[2] == 'ok' and last[1] is not None:
            guides[match.group(1)] = _cents(last[1])
    return guides


def _public_ids(root: Path, index: str):
    snapshot = json.loads((root / f'{index}-market-snapshot.json').read_text())
    ids = set()
    for card in snapshot['cards']:
        match = re.search(r'(\d+)\.jpg$', card['image'])
        if match:
            ids.add(match.group(1))
    return ids


def displayed_prices(root: Path) -> dict:
    """product id -> {surface: cents} for every surface that shows that card."""
    root = Path(root)
    surfaces: dict[str, dict] = {}

    def put(pid, surface, price):
        if price is None:
            return
        surfaces.setdefault(str(pid), {})[surface] = _cents(price)

    for slug in ('thirtieth-anniversary', 'tcg-modern', 'delta-reign', 'sv-151', 'prismatic-evolutions'):
        snapshot = json.loads((root / 'data' / 'prices' / f'{slug}.json').read_text())
        for card in snapshot['cards']:
            put(card['tcgplayer_product_id'], f'price:{slug}', card.get('raw_price_usd'))

    catalogue = _load_js(root / 'catalogue.js')
    for card in catalogue['cards']:
        quote = (card.get('quotes') or {}).get('Raw') or {}
        if quote.get('currency') == 'USD':
            put(card['productId'], 'modern', quote.get('price'))

    for pid, price in _cache_guides(root, 'thirtieth').items():
        put(pid, 'idx:thirtieth', price)

    for index in SET_INDEXES:
        if _reads_daily(root, index):
            guides = _cache_guides(root, index, _public_ids(root, index))
        else:
            guides = _snapshot_guides(root, index)
        for pid, price in guides.items():
            put(pid, f'idx:{index}', price)

    archive = _load_js(root / 'top50-data.js')
    for card in archive['cards']:
        quote = (card.get('quotes') or {}).get('Raw') or {}
        if quote.get('currency') == 'USD':
            put(card['productId'], 'top50', quote.get('price'))
    return surfaces


def mismatches(root: Path) -> list:
    found = []
    for pid, prices in displayed_prices(root).items():
        if len(prices) < 2:
            continue
        if len(set(prices.values())) > 1:
            found.append((pid, prices))
    return found


def assert_same_release(root: Path) -> int:
    found = mismatches(root)
    if found:
        sample = '; '.join(f'{pid} {prices}' for pid, prices in found[:3])
        raise AssertionError(f'{len(found)} same-card price mismatches from this release. {sample}')
    return 0


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    found = mismatches(root)
    print(f'same-card price mismatches: {len(found)}')
    for pid, prices in found[:20]:
        print(pid, prices)
    if found:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
