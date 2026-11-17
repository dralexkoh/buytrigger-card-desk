"""Public raw-price page for the English Pokémon Prismatic Evolutions set.

Refresh: replace data/prices/prismatic-evolutions.json and rebuild.
Rows, the card count and the as-of date all come from that file.
"""
from __future__ import annotations

from pathlib import Path

import raw_price_page as engine

SNAPSHOT = Path('data/prices/prismatic-evolutions.json')
PAGE_REL = Path('prices/prismatic-evolutions/index.html')
PRICE_PAGE_URL = 'https://buytrigger.cards/prices/prismatic-evolutions/'
CAMPAIGN = 'prismatic-evolutions-prices'
SOURCE_NAME = engine.SOURCE_NAME
SET_LABEL = 'Prismatic Evolutions'


def accept_set(set_name):
    if not isinstance(set_name, str) or not set_name.strip():
        raise ValueError('Card rarity missing')
    return set_name.strip()


def accept_image(product_id, image_path):
    expected = f'assets/prismatic-evolutions/{product_id}.jpg'
    if image_path != expected:
        raise ValueError('Unexpected image path for ' + product_id)
    return image_path


def intro(cards):
    secrets = sum(1 for card in cards if int(card['number'].split('/', 1)[0]) > 131)
    return (
        f'All {len(cards)} English cards from {SET_LABEL}, including {secrets} secret rares.'
    )


def description(cards, date_text):
    count = len(cards)
    return (
        f'Raw (ungraded) market guide prices in USD for all {count} English Pokémon {SET_LABEL} cards. '
        f'{SOURCE_NAME} as of {date_text}. US-market references, not offers.'
    )


SPEC = {
    'snapshot': SNAPSHOT,
    'page_rel': PAGE_REL,
    'url': PRICE_PAGE_URL,
    'campaign': CAMPAIGN,
    'form_id': 'prismatic-evolutions-prices',
    'data_page': 'prismatic-evolutions-prices',
    'footer_href': 'prices/prismatic-evolutions/',
    'footer_label': 'Prismatic Evolutions prices',
    'title': 'Pokémon Prismatic Evolutions raw prices · BuyTrigger.Cards',
    'kicker': 'ENGLISH / RAW PRICE REFERENCE',
    'heading': 'Prismatic Evolutions raw prices',
    'source_lead': 'Raw (ungraded) market guide prices, source: {source}, as of {date}',
    'source_note': 'US-market references in USD, not offers. These figures are dated 16 November 2026 and will stay on that date until the daily refresh for this set is switched on.',
    'price_header': 'Raw price',
    'group_header': 'Rarity',
    'group_attr': 'rarity',
    'group_class': 'price-rarity',
    'number_sort': True,
    'group_sort': False,
    'filter_placeholder': 'Name, number or rarity',
    'region_label': 'Prismatic Evolutions raw prices',
    'caption': 'English Pokémon Prismatic Evolutions raw prices in USD',
    'accept_set': accept_set,
    'accept_image': accept_image,
    'intro': intro,
    'description': description,
    'image_credit': 'Card image: The Pokémon Company / pokemon.com',
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
