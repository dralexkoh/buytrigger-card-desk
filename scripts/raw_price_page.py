"""Build a public raw price page from data/prices/<slug>.json.

Rows, the card count and the "as of" date are read from that file at build
time. Replacing the JSON and rebuilding the site republishes the page.
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

SOURCE_NAME = 'TCGCSV market price'
SHARE_IMAGE = 'https://buytrigger.cards/assets/family-wide.jpg'
STYLESHEET = 'prices-table.css'
SCRIPTS = ('prices-table.js', 'analytics.js')


def load_snapshot(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get('cards'), list):
        raise ValueError('Price snapshot must be an object with a cards array')
    return data


def format_source_date(iso_date: str) -> str:
    day = datetime.strptime(iso_date, '%Y-%m-%d')
    return f'{day.day} {day.strftime("%b")} {day.year}'


def snapshot_source_date(snapshot: dict) -> str:
    value = snapshot.get('source_date') if isinstance(snapshot, dict) else None
    if not isinstance(value, str):
        raise ValueError('Price snapshot source_date is missing')
    format_source_date(value)
    return value


def read_source_date(root: Path, snapshot_path: Path) -> str:
    return snapshot_source_date(load_snapshot(root / snapshot_path))


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


def usd(value):
    if value is None:
        return '—'
    return f'${float(value):,.2f}'


def price_attr(value):
    if value is None:
        return ''
    text = format(float(value), 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text


def display_price(value):
    number = _price(value)
    return price_attr(number), usd(number)


def _jpeg_size(path: Path):
    data = path.read_bytes()
    if data[:2] != b'\xff\xd8':
        return None
    index = 2
    while index + 8 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack('>HH', data[index + 5:index + 9])
            return width, height
        if marker in (0xD8, 0xD9):
            index += 2
            continue
        length = struct.unpack('>H', data[index + 2:index + 4])[0]
        index += 2 + length
    return None


def prepare_cards(snapshot: dict, root: Path, spec: dict):
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
        if not isinstance(image_path, str):
            raise ValueError('Image path missing for ' + product_id)
        label = spec['accept_set'](subset)
        if not re.fullmatch(r'\d{3,12}', product_id):
            raise ValueError('Bad TCGplayer product id: ' + product_id)
        if product_id in seen:
            raise ValueError('Duplicate product id: ' + product_id)
        seen.add(product_id)
        spec['accept_image'](product_id, image_path)
        price = _price(raw.get('raw_price_usd'))
        image_file = root / image_path
        cards.append({
            'name': name.strip(),
            'number': number.strip(),
            'subset': subset,
            'label': label,
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


def _row(card, spec):
    name = html.escape(card['name'])
    number = html.escape(card['number'])
    label = html.escape(card['label'])
    attr_name = spec['group_attr']
    search = html.escape(' '.join((
        card['name'], card['number'], card['label'], str(card['subset']),
    )).casefold(), quote=True)
    if card['image']:
        size = ''
        if card['image_size']:
            width, height = card['image_size']
            size = f' width="{width}" height="{height}"'
        image = (
            f'<img src="{html.escape(card["image"], quote=True)}" alt="{html.escape(card["name"], quote=True)}, {html.escape(card["number"], quote=True)}"'
            f'{size} loading="lazy" decoding="async">'
        )
    else:
        image = f'<span class="price-card-fallback">{name}</span>'
    href = f'https://www.tcgplayer.com/product/{card["product_id"]}'
    shown = usd(card['price'])
    return (
        f'<tr data-name="{html.escape(card["name"], quote=True)}" data-number="{html.escape(card["number"], quote=True)}" '
        f'data-{attr_name}="{html.escape(card["label"], quote=True)}" '
        f'data-price="{price_attr(card["price"])}" data-id="{card["product_id"]}" data-search="{search}">'
        f'<td class="price-card">{image}</td>'
        f'<td class="price-name">{name}</td>'
        f'<td class="price-number">{number}</td>'
        f'<td class="{spec["group_class"]}">{label}</td>'
        f'<td class="price-usd">{shown}</td>'
        f'<td class="price-link"><a href="{href}" rel="nofollow noopener" target="_blank">Check price</a></td>'
        '</tr>'
    )


def _sort_options(options):
    parts = []
    for value, label, selected in options:
        selected_attr = ' selected' if selected else ''
        parts.append(f'<option value="{html.escape(value, quote=True)}"{selected_attr}>{html.escape(label)}</option>')
    return ''.join(parts)


def _column_heading(label, sort_key=None, selected=None, extra_class=''):
    class_attr = f' class="{extra_class}"' if extra_class else ''
    if not sort_key:
        return f'<th{class_attr} scope="col">{html.escape(label)}</th>'
    aria = selected or 'none'
    return (
        f'<th{class_attr} scope="col" aria-sort="{aria}">'
        f'<button type="button" data-sort="{html.escape(sort_key, quote=True)}">{html.escape(label)}</button></th>'
    )


def _table_head(spec):
    number = _column_heading('Number', 'number' if spec.get('number_sort') else None)
    group = _column_heading(spec['group_header'], 'set' if spec.get('group_sort') else None)
    price = _column_heading(spec['price_header'], 'price', selected='descending', extra_class='price-usd-col')
    return (
        '<thead><tr>'
        + _column_heading('Card', extra_class='price-card-col')
        + _column_heading('Name', 'name')
        + number
        + group
        + price
        + _column_heading('Check price')
        + '</tr></thead>'
    )


def root_absolute_href(href: str) -> str:
    """Site links that must not depend on a document's directory or <base>."""
    if not isinstance(href, str) or href.startswith(('http://', 'https://', '//', 'mailto:', 'tel:')):
        return href
    if href.startswith('/'):
        return href
    if href.startswith('#'):
        return '/index.html' + href
    return '/' + href


def absolutize_document_nav(page):
    for region in page.select('header.masthead, footer'):
        for link in region.select('a[href]'):
            link['href'] = root_absolute_href(link.get('href', ''))


def _guard_language(rendered: str, spec: dict):
    if re.search(r'PSA', rendered):
        raise ValueError('Price page contains PSA')
    text = BeautifulSoup(rendered, 'html.parser').get_text(' ')
    if re.search(r'\b(buy|sell|accumulate|invest)\b', text, re.I):
        raise ValueError('Price page contains buy, sell, accumulate or invest wording')
    for pattern in spec.get('text_bans') or []:
        if re.search(pattern, text, re.I):
            raise ValueError('Price page contains forbidden wording')
    phrase = spec.get('only_sale_phrase')
    if phrase:
        if re.search(r'sale', re.sub(re.escape(phrase), '', text, flags=re.I), re.I):
            raise ValueError('Price page contains sale wording')
        if re.search(r'sale', re.sub(re.escape(phrase), '', rendered, flags=re.I), re.I):
            raise ValueError('Price page contains sale wording')
    return rendered


def render_page(root: Path, spec: dict, snapshot: dict | None = None) -> str:
    snapshot = snapshot if snapshot is not None else load_snapshot(root / spec['snapshot'])
    date_text = format_source_date(snapshot_source_date(snapshot))
    cards = prepare_cards(snapshot, root, spec)
    if not cards:
        raise ValueError('Price snapshot has no cards')
    sentence = spec['source_lead'].format(source=SOURCE_NAME, date=date_text)
    count = len(cards)
    description = spec['description'](cards, date_text)
    title = spec['title']
    rows = ''.join(_row(card, spec) for card in cards)
    digest = digest_signup_html(spec['form_id'], campaign=spec['campaign'])
    main = f'''
<section class="page-intro">
<span class="kicker red-text">{html.escape(spec['kicker'])}</span>
<h1>{html.escape(spec['heading'])}<span class="red-text">.</span></h1>
<p>{html.escape(spec['intro'](cards))}</p>
<p class="price-source"><strong>{html.escape(sentence)}.</strong> {html.escape(spec['source_note'])}</p>
</section>
<section class="price-sheet" aria-labelledby="price-table-title">
<div class="price-tools">
<label for="price-filter">Filter<input id="price-filter" type="search" placeholder="{html.escape(spec['filter_placeholder'], quote=True)}" autocomplete="off"></label>
<label for="price-sort">Sort<select id="price-sort">
{_sort_options(spec['sort_options'])}
</select></label>
<p id="price-count" role="status">{count} cards</p>
</div>
<h2 id="price-table-title">All {count} cards</h2>
<div class="price-table-wrap" tabindex="0" role="region" aria-label="{html.escape(spec['region_label'], quote=True)}">
<table class="price-table" id="price-table">
<caption class="visually-hidden">{html.escape(spec['caption'])}</caption>
{_table_head(spec)}
<tbody>{rows}</tbody>
</table>
</div>
<p id="price-empty" hidden>No cards match that filter.</p>
</section>
{digest}
'''
    page = BeautifulSoup((root / 'index.html').read_text(), 'html.parser')
    page.body['class'] = ['editorial-page', 'price-page']
    page.body['data-page'] = spec['data_page']
    if page.body.has_attr('data-route'):
        del page.body['data-route']
    for node in page.select('dialog, script'):
        node.decompose()
    base = page.new_tag('base', href='../../')
    page.head.insert(0, base)
    page.title.string = title
    page.select_one('meta[name=description]')['content'] = description
    page.select_one('link[rel=canonical]')['href'] = spec['url']
    for key, value in (
        ('og:title', title),
        ('og:description', description),
        ('og:url', spec['url']),
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
    style = page.new_tag('link', rel='stylesheet', href=STYLESHEET)
    page.head.append(style)
    main_node = page.select_one('main')
    main_node.clear()
    main_node.append(BeautifulSoup(main, 'html.parser'))
    footer_link = page.select_one(f'footer a[href="{spec["footer_href"]}"]')
    if footer_link is None or footer_link.get_text() != spec['footer_label']:
        raise ValueError('Footer is missing the ' + spec['footer_label'] + ' link')
    footer_link['aria-current'] = 'page'
    absolutize_document_nav(page)
    for src in SCRIPTS:
        script = page.new_tag('script', src=src)
        script['defer'] = ''
        page.body.append(script)
    return _guard_language(str(page), spec)


def publish_price_page(root: Path, dist: Path, spec: dict):
    target = dist / spec['page_rel']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_page(root, spec))
