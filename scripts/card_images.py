"""Pictures for Buy on eBay blocks on Features and news briefs.

Each block names a card. This maps that card to a picture the repository already
ships. It does not fetch anything.

Preference:
1. The set-tracker TCGplayer file, assets/<set>/<productId>.jpg, when the set
   matches and the file exists.
2. The Modern Index TCGdex file, assets/modern-NNN-low.webp, when the set
   matches and the file exists.
3. For a pattern card whose set-tracker jpg was never saved, the one other
   local image already named with that product id.

A 30th Celebration block matches the Classic Collection printing in that set
tracker. Name, number and set still have to agree, and the file has to exist.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

INDEX_FOLDER = {
    'delta-reign': 'delta-reign',
    'sv-151': 'sv-151',
    'prismatic-evolutions': 'prismatic-evolutions',
    'paldean-fates': 'paldean-fates',
    'crown-zenith': 'crown-zenith',
    'fusion-strike': 'fusion-strike',
    'thirtieth-anniversary': 'thirtieth',
}
SET_JPG = re.compile(r'^assets/[a-z0-9-]+/\d+\.jpg$')
MODERN_LOW = re.compile(r'^assets/modern-\d{3}-low\.webp$')
PRODUCT_ID = re.compile(r'(?:^|[^0-9])(\d{5,})(?=[^0-9]|$)')
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp'}


def canon_set(value):
    text = html.unescape(str(value or ''))
    text = text.replace('\u2014', ' ').replace('\u2013', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[A-Z]{2,4}\d{0,3}:\s+', '', text)
    return re.sub(r'\s+', ' ', text).strip().casefold()


def sets_match(block_set, source_set):
    block, source = canon_set(block_set), canon_set(source_set)
    if not block or not source:
        return False
    if block == source:
        return True
    # Blocks say "30th Celebration". Those reprints live in the Classic Collection.
    return block == '30th celebration' and source.startswith('30th celebration ')


def canon_number(value):
    parts = []
    for part in str(value or '').strip().split('/'):
        parts.append(str(int(part)) if part.isdigit() else part)
    return '/'.join(parts)


def canon_name(value):
    text = html.unescape(str(value or ''))
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+-\s+\d{1,3}/\d{1,3}$', '', text)
    return re.sub(r'\s+', ' ', text).strip().casefold()


def block_cards(root):
    """Every card named on a Feature or news block, in first-seen order."""
    root = Path(root)
    editorial = json.loads((root / 'editorial.json').read_text())
    found = []
    seen = set()

    def add(name, number, set_name):
        key = (str(name), str(number), str(set_name))
        if key in seen or not all(part.strip() for part in key):
            return
        seen.add(key)
        found.append({'name': key[0], 'number': key[1], 'set': key[2]})

    for wire in editorial.get('wire') or []:
        for card in wire.get('ebay_cards') or []:
            if isinstance(card, dict):
                add(card.get('name'), card.get('number'), card.get('set'))
    for article in editorial.get('articles') or []:
        for section in article.get('sections') or []:
            markup = section.get('html') or ''
            for div in BeautifulSoup(markup, 'html.parser').select('div[data-ebay-card]'):
                add(div.get('data-ebay-name'), div.get('data-ebay-number'), div.get('data-ebay-set'))
    return found


def _tracker_cards(root):
    cards = []
    folder = Path(root) / 'data' / 'market-rosters'
    for path in sorted(folder.glob('*.json')):
        data = json.loads(path.read_text())
        index = data.get('index')
        if index not in INDEX_FOLDER or not isinstance(data.get('cards'), list):
            continue
        for card in data['cards']:
            if not isinstance(card, dict):
                continue
            product_id = str(card.get('productId') or '')
            if not product_id.isdigit():
                continue
            cards.append({
                'index': index,
                'name': card.get('name') or '',
                'number': card.get('number') or '',
                'set': card.get('set') or '',
                'productId': product_id,
                'printing': card.get('printing') or '',
                'inIndex': card.get('inIndex', True) is not False,
                'image': card.get('image') or '',
            })
    return cards


def _modern_cards(root):
    text = (Path(root) / 'catalogue.js').read_text()
    data = json.loads(text[text.index('=') + 1:].strip().rstrip(';'))
    return data.get('cards') or []


def _product_files(root):
    """product id -> path, only when exactly one shipped image carries that id."""
    found = {}
    assets = Path(root) / 'assets'
    if not assets.is_dir():
        return found
    for path in assets.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXT:
            continue
        if 'hero' in path.name.lower():
            continue
        rel = path.relative_to(root).as_posix()
        if not rel.startswith('assets/') or '..' in rel.split('/'):
            continue
        for match in PRODUCT_ID.finditer(path.name):
            found.setdefault(match.group(1), set()).add(rel)
    return {product_id: next(iter(paths)) for product_id, paths in found.items() if len(paths) == 1}


def _set_jpg(root, card):
    folder = INDEX_FOLDER.get(card['index'])
    product_id = card['productId']
    if folder:
        path = f'assets/{folder}/{product_id}.jpg'
        if SET_JPG.fullmatch(path) and (Path(root) / path).is_file():
            return path
    listed = card['image']
    if (SET_JPG.fullmatch(listed) and listed.endswith('/' + product_id + '.jpg')
            and not listed.startswith('assets/tcg-modern/') and (Path(root) / listed).is_file()):
        return listed
    return None


def _same_card(card, name, number, set_name):
    return (canon_name(card.get('name')) == canon_name(name)
            and canon_number(card.get('number')) == canon_number(number)
            and sets_match(set_name, card.get('set')))


def image_for(root, name, number, set_name, tracker=None, modern=None, product_files=None):
    """Local picture for one block card, or None when this repo has no file."""
    root = Path(root)
    tracker = _tracker_cards(root) if tracker is None else tracker
    modern = _modern_cards(root) if modern is None else modern
    product_files = _product_files(root) if product_files is None else product_files
    hits = []
    product_ids = []
    for card in tracker:
        if not _same_card(card, name, number, set_name):
            continue
        product_ids.append(card['productId'])
        path = _set_jpg(root, card)
        if path:
            hits.append((0 if card['inIndex'] else 1, 0 if card['printing'] == 'Holofoil' else 1, card['productId'], path))
    if hits:
        hits.sort()
        return hits[0][3]
    for card in modern:
        image = card.get('image') or ''
        if _same_card(card, name, number, set_name) and MODERN_LOW.fullmatch(image) and (root / image).is_file():
            return image
    extras = []
    for product_id in dict.fromkeys(product_ids):
        path = product_files.get(product_id)
        if path and (root / path).is_file():
            extras.append(path)
    if len(set(extras)) == 1:
        return extras[0]
    return None


def card_images(root):
    """Map of block cards that have a local picture. Key is name|number|set."""
    root = Path(root)
    tracker = _tracker_cards(root)
    modern = _modern_cards(root)
    product_files = _product_files(root)
    images = {}
    for card in block_cards(root):
        path = image_for(root, card['name'], card['number'], card['set'], tracker, modern, product_files)
        if not path:
            continue
        images[f"{card['name']}|{card['number']}|{card['set']}"] = path
    return dict(sorted(images.items()))
