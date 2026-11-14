"""Public raw market-guide page for the TCG Modern English Holofoil list.

Refresh: replace data/prices/tcg-modern.json and rebuild.
Rows, the card count and the as-of date all come from that file.
Graded values, index levels and performance figures are not published here.
"""
from __future__ import annotations

from pathlib import Path

import raw_price_page as engine

SNAPSHOT = Path('data/prices/tcg-modern.json')
PAGE_REL = Path('prices/tcg-modern/index.html')
PRICE_PAGE_URL = 'https://buytrigger.cards/prices/tcg-modern/'
CAMPAIGN = 'tcg-modern-prices'
SOURCE_NAME = engine.SOURCE_NAME

# The three 30th Anniversary Mews already have artwork under assets/thirtieth/.
MEW_IMAGE_IDS = frozenset({'717607', '717608', '717609'})


def accept_set(set_name):
    if not isinstance(set_name, str) or not set_name.strip():
        raise ValueError('Card set missing')
    return set_name.strip()


def accept_image(product_id, image_path):
    modern = f'assets/tcg-modern/{product_id}.jpg'
    classic = f'assets/thirtieth/{product_id}.jpg'
    if image_path == classic:
        if product_id not in MEW_IMAGE_IDS:
            raise ValueError('Unexpected thirtieth image path for ' + product_id)
        return image_path
    if image_path != modern:
        raise ValueError('Unexpected image path for ' + product_id)
    return image_path


def _set_count(cards):
    return len({card['label'] for card in cards})


def intro(cards):
    return f'All {len(cards)} English Holofoil cards across {_set_count(cards)} sets.'


def description(cards, date_text):
    count = len(cards)
    sets = _set_count(cards)
    return (
        f'Raw (ungraded) market guide prices in USD for all {count} English Holofoil TCG Modern cards across {sets} sets. '
        f'{SOURCE_NAME} as of {date_text}. US-market references, not sales or offers.'
    )


SPEC = {
    'snapshot': SNAPSHOT,
    'page_rel': PAGE_REL,
    'url': PRICE_PAGE_URL,
    'campaign': CAMPAIGN,
    'form_id': 'tcg-modern-prices',
    'data_page': 'tcg-modern-prices',
    'footer_href': 'prices/tcg-modern/',
    'footer_label': 'TCG Modern prices',
    'title': 'TCG Modern raw market guide prices · BuyTrigger.Cards',
    'kicker': 'ENGLISH / RAW MARKET GUIDE',
    'heading': 'TCG Modern raw market guide prices',
    'source_lead': 'Raw (ungraded) market guide prices, source: {source}, as of {date}',
    'source_note': 'US-market references in USD, not sales or offers.',
    'price_header': 'Market guide',
    'group_header': 'Set',
    'group_attr': 'set',
    'group_class': 'price-set',
    'number_sort': False,
    'group_sort': True,
    'filter_placeholder': 'Name, number or set',
    'region_label': 'TCG Modern raw market guide prices',
    'caption': 'English TCG Modern raw market guide prices in USD',
    'accept_set': accept_set,
    'accept_image': accept_image,
    'intro': intro,
    'description': description,
    'sort_options': [
        ('price-desc', 'Price, high to low', True),
        ('price-asc', 'Price, low to high', False),
        ('name-asc', 'Name, A to Z', False),
        ('name-desc', 'Name, Z to A', False),
        ('set-asc', 'Set, A to Z', False),
        ('set-desc', 'Set, Z to A', False),
    ],
    'only_sale_phrase': 'not sales or offers',
    'text_bans': [
        r'(?<!un)graded',
        r'index level',
        r'index change',
        r'week-on-week',
        r'week on week',
        r'\b7-day\b',
        r'\b7 day\b',
        r'\bperformance\b',
        r'\bmultiplier\b',
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
