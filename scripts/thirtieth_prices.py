"""Public raw-price page for the English Pokémon 30th Anniversary set.

Refresh: replace data/prices/thirtieth-anniversary.json with a new TCGCSV
marketPrice snapshot (same fields) and run the site build. The page lists
every card in that file. It publishes raw USD references only.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import html
import json
import math
import re
import struct

from bs4 import BeautifulSoup

from digest_signup import digest_signup_html

SNAPSHOT = Path('data/prices/thirtieth-anniversary.json')
PAGE_REL = Path('prices/thirtieth-anniversary/index.html')
PRICE_PAGE_URL = 'https://buytrigger.cards/prices/thirtieth-anniversary/'
CAMPAIGN = 'thirtieth-anniversary-prices'
SOURCE_NAME = 'TCGCSV market price'
SHARE_IMAGE = 'https://buytrigger.cards/assets/family-wide.jpg'

# Display labels for the three subset names stored on the snapshot.
SUBSET_LABELS = {
    'ME: 30th Celebration': 'ME: 30th Celebration',
    'ME: 30th Celebration Classic Collection': 'Classic Collection',
    'ME: Mega Evolution Promo': 'Mega Evolution Promo',
}
SUBSET_ORDER = list(SUBSET_LABELS)


def load_snapshot(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get('cards'), list):
        raise ValueError('Price snapshot must be an object with a cards array')
    return data


def source_sentence(iso_date: str) -> str:
    day = datetime.strptime(iso_date, '%Y-%m-%d')
    return f'Raw (ungraded) prices, source: {SOURCE_NAME}, as of {day.day} {day.strftime("%b")} {day.year}'


def number_key(value: str):
    parts = []
    for part in re.split(r'(\d+)', value):
        if not part:
            continue
        parts.append((0, int(part)) if part.isdigit() else (1, part.casefold()))
    return tuple(parts)


def _price(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('Raw price must be a positive number or null')
    return float(value)


def _jpeg_size(path: Path):
    data = path.read_bytes()
    if data[:2] != b'\xff\xd8':
        return None
    i = 2
    while i + 8 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack('>HH', data[i + 5:i + 9])
            return width, height
        if marker in (0xD8, 0xD9):
            i += 2
            continue
        length = struct.unpack('>H', data[i + 2:i + 4])[0]
        i += 2 + length
    return None


def prepare_cards(snapshot: dict, root: Path):
    seen = set()
    cards = []
    for raw in snapshot['cards']:
        name = raw.get('name')
        number = raw.get('number')
        subset = raw.get('set_name')
        product_id = str(raw.get('tcgplayer_product_id') or '')
        image_path = raw.get('image_path') or ''
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Card name missing')
        if not isinstance(number, str) or not number.strip():
            raise ValueError('Card number missing')
        if subset not in SUBSET_LABELS:
            raise ValueError('Unknown subset: ' + str(subset))
        if not re.fullmatch(r'\d{3,12}', product_id):
            raise ValueError('Bad TCGplayer product id: ' + product_id)
        if product_id in seen:
            raise ValueError('Duplicate product id: ' + product_id)
        seen.add(product_id)
        expected_image = f'assets/thirtieth/{product_id}.jpg'
        if image_path != expected_image:
            raise ValueError('Unexpected image path for ' + product_id)
        price = _price(raw.get('raw_price_usd'))
        image_file = root / image_path
        cards.append({
            'name': name.strip(),
            'number': number.strip(),
            'subset': subset,
            'label': SUBSET_LABELS[subset],
            'price': price,
            'product_id': product_id,
            'image': image_path if image_file.is_file() else None,
            'image_size': _jpeg_size(image_file) if image_file.is_file() else None,
        })
    cards.sort(key=lambda card: (
        card['price'] is None,
        -(card['price'] or 0),
        card['name'].casefold(),
        number_key(card['number']),
        card['product_id'],
    ))
    return cards


def usd(value):
    if value is None:
        return '—'
    return f'${value:,.2f}'


def price_attr(value):
    if value is None:
        return ''
    text = format(value, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text


def subset_summary(cards):
    counts = {}
    for card in cards:
        counts[card['subset']] = counts.get(card['subset'], 0) + 1
    parts = [f'{SUBSET_LABELS[name]} ({counts[name]})' for name in SUBSET_ORDER if counts.get(name)]
    if len(parts) == 1:
        return parts[0]
    return ', '.join(parts[:-1]) + ' and ' + parts[-1]


def _row(card):
    name = html.escape(card['name'])
    number = html.escape(card['number'])
    label = html.escape(card['label'])
    search = html.escape(' '.join((
        card['name'], card['number'], card['label'], card['subset'],
    )).casefold())
    if card['image']:
        size = ''
        if card['image_size']:
            width, height = card['image_size']
            size = f' width="{width}" height="{height}"'
        image = (
            f'<img src="{html.escape(card["image"])}" alt="{name}, {number}"'
            f'{size} loading="lazy" decoding="async">'
        )
    else:
        image = f'<span class="price-card-fallback">{name}</span>'
    href = f'https://www.tcgplayer.com/product/{card["product_id"]}'
    return (
        f'<tr data-name="{name}" data-number="{number}" data-subset="{label}" '
        f'data-price="{price_attr(card["price"])}" data-id="{card["product_id"]}" data-search="{search}">'
        f'<td class="price-card">{image}</td>'
        f'<td class="price-name">{name}</td>'
        f'<td class="price-number">{number}</td>'
        f'<td class="price-subset">{label}</td>'
        f'<td class="price-usd">{usd(card["price"])}</td>'
        f'<td class="price-link"><a href="{href}" rel="nofollow noopener" target="_blank">Check price</a></td>'
        '</tr>'
    )


def _retarget(header):
    for link in header.select('a[href]'):
        href = link['href']
        if href.startswith('#'):
            link['href'] = 'index.html' + href


def render_page(root: Path, snapshot: dict | None = None) -> str:
    snapshot = snapshot if snapshot is not None else load_snapshot(root / SNAPSHOT)
    cards = prepare_cards(snapshot, root)
    if not cards:
        raise ValueError('Price snapshot has no cards')
    sentence = source_sentence(snapshot.get('source_date') or '')
    count = len(cards)
    description = (
        f'Raw (ungraded) US-market prices in USD for all {count} English Pokémon 30th Anniversary cards. '
        f'{SOURCE_NAME} as of {sentence.split("as of ", 1)[1]}. A price reference, not an offer.'
    )
    title = 'Pokémon 30th Anniversary raw prices · BuyTrigger.Cards'
    rows = ''.join(_row(card) for card in cards)
    digest = digest_signup_html('thirtieth-prices', campaign=CAMPAIGN)
    main = f'''
<section class="page-intro">
<span class="kicker red-text">ENGLISH / RAW PRICE REFERENCE</span>
<h1>30th Anniversary raw prices<span class="red-text">.</span></h1>
<p>All {count} English cards: {html.escape(subset_summary(cards))}.</p>
<p class="price-source"><strong>{html.escape(sentence)}.</strong> Prices are US-market references in USD, not offers.</p>
</section>
<section class="price-sheet" aria-labelledby="price-table-title">
<div class="price-tools">
<label for="price-filter">Filter<input id="price-filter" type="search" placeholder="Name, number or subset" autocomplete="off"></label>
<label for="price-sort">Sort<select id="price-sort">
<option value="price-desc" selected>Price, high to low</option>
<option value="price-asc">Price, low to high</option>
<option value="name-asc">Name, A to Z</option>
<option value="name-desc">Name, Z to A</option>
<option value="number-asc">Number, low to high</option>
<option value="number-desc">Number, high to low</option>
</select></label>
<p id="price-count" role="status">{count} cards</p>
</div>
<h2 id="price-table-title">All {count} cards</h2>
<div class="price-table-wrap" tabindex="0" role="region" aria-label="30th Anniversary raw prices">
<table class="price-table" id="price-table">
<caption class="visually-hidden">English Pokémon 30th Anniversary raw prices in USD</caption>
<thead><tr>
<th class="price-card-col" scope="col">Card</th>
<th scope="col" aria-sort="none"><button type="button" data-sort="name">Name</button></th>
<th scope="col" aria-sort="none"><button type="button" data-sort="number">Number</button></th>
<th scope="col">Subset</th>
<th class="price-usd-col" scope="col" aria-sort="descending"><button type="button" data-sort="price">Raw price</button></th>
<th scope="col">Check price</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
<p id="price-empty" hidden>No cards match that filter.</p>
</section>
{digest}
'''
    page = BeautifulSoup((root / 'index.html').read_text(), 'html.parser')
    page.body['class'] = ['editorial-page', 'price-page']
    page.body['data-page'] = 'thirtieth-prices'
    if page.body.has_attr('data-route'):
        del page.body['data-route']
    for node in page.select('dialog, script'):
        node.decompose()
    base = page.new_tag('base', href='../../')
    page.head.insert(0, base)
    page.title.string = title
    page.select_one('meta[name=description]')['content'] = description
    page.select_one('link[rel=canonical]')['href'] = PRICE_PAGE_URL
    for key, value in (
        ('og:title', title),
        ('og:description', description),
        ('og:url', PRICE_PAGE_URL),
        ('og:type', 'website'),
        ('og:image', SHARE_IMAGE),
    ):
        tag = page.select_one(f'meta[property="{key}"]')
        if tag:
            tag['content'] = value
    for key, value in (
        ('twitter:card', 'summary_large_image'),
        ('twitter:title', title),
        ('twitter:description', description),
        ('twitter:image', SHARE_IMAGE),
        ('robots', 'index, follow, max-image-preview:large'),
        ('theme-color', '#df242b'),
    ):
        tag = page.select_one(f'meta[name="{key}"]')
        if tag:
            tag['content'] = value
    style = page.new_tag('link', rel='stylesheet', href='prices-thirtieth.css')
    page.head.append(style)
    _retarget(page.select_one('header.masthead'))
    main_node = page.select_one('main')
    main_node.clear()
    main_node.append(BeautifulSoup(main, 'html.parser'))
    footer_link = page.select_one('footer a[href="prices/thirtieth-anniversary/"]')
    if footer_link is None:
        raise ValueError('Footer is missing the 30th Anniversary prices link')
    footer_link['aria-current'] = 'page'
    for src in ('prices-thirtieth.js', 'analytics.js'):
        script = page.new_tag('script', src=src)
        script['defer'] = ''
        page.body.append(script)
    rendered = str(page)
    if re.search(r'PSA', rendered):
        raise ValueError('Price page contains PSA')
    if re.search(r'\b(buy|sell|accumulate|invest)\b', BeautifulSoup(rendered, 'html.parser').get_text(' '), re.I):
        raise ValueError('Price page contains buy, sell, accumulate or invest wording')
    return rendered


def publish_price_page(root: Path, dist: Path):
    target = dist / PAGE_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_page(root))
