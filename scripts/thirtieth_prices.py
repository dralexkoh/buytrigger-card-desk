"""Public raw-price page for the English Pokémon 30th Anniversary set.

Refresh: replace data/prices/thirtieth-anniversary.json and rebuild.
Rows, the card count and the as-of date all come from that file.
"""
from __future__ import annotations

from pathlib import Path

import raw_price_page as engine

SNAPSHOT = Path('data/prices/thirtieth-anniversary.json')
PAGE_REL = Path('prices/thirtieth-anniversary/index.html')
PRICE_PAGE_URL = 'https://buytrigger.cards/prices/thirtieth-anniversary/'
CAMPAIGN = 'thirtieth-anniversary-prices'
SOURCE_NAME = engine.SOURCE_NAME

SUBSET_LABELS = {
    'ME: 30th Celebration': 'ME: 30th Celebration',
    'ME: 30th Celebration Classic Collection': 'Classic Collection',
    'ME: Mega Evolution Promo': 'Mega Evolution Promo',
}
SUBSET_ORDER = list(SUBSET_LABELS)


def accept_set(set_name):
    if set_name not in SUBSET_LABELS:
        raise ValueError('Unknown subset: ' + str(set_name))
    return SUBSET_LABELS[set_name]


def accept_image(product_id, image_path):
    expected = f'assets/thirtieth/{product_id}.jpg'
    if image_path != expected:
        raise ValueError('Unexpected image path for ' + product_id)
    return image_path


def subset_summary(cards):
    counts = {}
    for card in cards:
        counts[card['subset']] = counts.get(card['subset'], 0) + 1
    parts = [f'{SUBSET_LABELS[name]} ({counts[name]})' for name in SUBSET_ORDER if counts.get(name)]
    if len(parts) == 1:
        return parts[0]
    if not parts:
        return 'no subsets'
    return ', '.join(parts[:-1]) + ' and ' + parts[-1]


def intro(cards):
    return f'All {len(cards)} English cards: {subset_summary(cards)}.'


def description(cards, date_text):
    count = len(cards)
    return (
        f'Raw (ungraded) US-market prices in USD for all {count} English Pokémon 30th Anniversary cards. '
        f'{SOURCE_NAME} as of {date_text}. A price reference, not an offer.'
    )


SPEC = {
    'snapshot': SNAPSHOT,
    'page_rel': PAGE_REL,
    'url': PRICE_PAGE_URL,
    'campaign': CAMPAIGN,
    'form_id': 'thirtieth-prices',
    'data_page': 'thirtieth-prices',
    'footer_href': 'prices/thirtieth-anniversary/',
    'footer_label': '30th Anniversary prices',
    'title': 'Pokémon 30th Anniversary raw prices · BuyTrigger.Cards',
    'kicker': 'ENGLISH / RAW PRICE REFERENCE',
    'heading': '30th Anniversary raw prices',
    'source_lead': 'Raw (ungraded) prices, source: {source}, as of {date}',
    'source_note': 'Prices are US-market references in USD, not offers.',
    'price_header': 'Raw price',
    'group_header': 'Subset',
    'group_attr': 'subset',
    'group_class': 'price-subset',
    'number_sort': True,
    'group_sort': False,
    'filter_placeholder': 'Name, number or subset',
    'region_label': '30th Anniversary raw prices',
    'caption': 'English Pokémon 30th Anniversary raw prices in USD',
    'accept_set': accept_set,
    'accept_image': accept_image,
    'intro': intro,
    'description': description,
    'sort_options': [
        ('price-desc', 'Price, high to low', True),
        ('price-asc', 'Price, low to high', False),
        ('name-asc', 'Name, A to Z', False),
        ('name-desc', 'Name, Z to A', False),
        ('number-asc', 'Number, low to high', False),
        ('number-desc', 'Number, high to low', False),
    ],
}


def load_snapshot(path: Path) -> dict:
    return engine.load_snapshot(path)


def prepare_cards(snapshot: dict, root: Path):
    return engine.prepare_cards(snapshot, root, SPEC)


def render_page(root: Path, snapshot: dict | None = None) -> str:
    return engine.render_page(root, SPEC, snapshot)


def publish_price_page(root: Path, dist: Path):
    engine.publish_price_page(root, dist, SPEC)


def source_date(root: Path) -> str:
    return engine.read_source_date(root, SNAPSHOT)


def format_source_date(iso_date: str) -> str:
    return engine.format_source_date(iso_date)
