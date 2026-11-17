"""Optional chase-card strip for a story or news brief.

Front matter, on an article or a wire brief:

    "chase_cards": [
      {"name": "Gold Mega Rayquaza ex", "image": "assets/....jpg", "alt": "...",
       "set": "Delta Reign", "number": "141/103", "link": "https://..."}
    ],
    "chase_cards_credit": "Card image: TCGplayer. Card artwork © Pokémon."

`name`, `image` and `alt` are required. `set`, `number` and `link` are optional.
Three to six cards. `chase_cards_credit` is required with the strip so the
pictures keep a credit line. Omit `chase_cards` and the page is unchanged.
"""
from pathlib import Path
from urllib.parse import urlsplit
import re

REQUIRED = ('name', 'image', 'alt')
OPTIONAL = ('set', 'number', 'link')
ASSET_PATH = re.compile(r'assets/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_.-]+\.(?:avif|jpg|jpeg|png|webp)')


def esc(value):
    return (str('' if value is None else value)
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


def _https(value):
    if not isinstance(value, str) or not value or '\\' in value or any(c.isspace() for c in value):
        return False
    parsed = urlsplit(value)
    return (parsed.scheme == 'https' and parsed.hostname and '.' in parsed.hostname
            and not parsed.username and not parsed.password)


def validate_chase_cards(item, root, label):
    """Reject a present strip that is incomplete. Absence is valid."""
    root = Path(root).resolve()
    has_cards = 'chase_cards' in item and item.get('chase_cards') is not None
    has_credit = 'chase_cards_credit' in item and item.get('chase_cards_credit') is not None
    if not has_cards and not has_credit:
        return
    cards = item.get('chase_cards')
    if not isinstance(cards, list) or not 3 <= len(cards) <= 6:
        raise ValueError(f'{label}: chase_cards needs 3 to 6 cards')
    credit = item.get('chase_cards_credit')
    if not isinstance(credit, str) or not credit.strip():
        raise ValueError(f'{label}: chase card strip needs a credit')
    for index, card in enumerate(cards, 1):
        where = f'{label}: chase card {index}'
        if not isinstance(card, dict):
            raise ValueError(f'{where} must be an object')
        unknown = set(card) - set(REQUIRED) - set(OPTIONAL)
        if unknown:
            raise ValueError(f'{where} has unexpected field {sorted(unknown)[0]}')
        for field in REQUIRED:
            if not isinstance(card.get(field), str) or not card[field].strip():
                raise ValueError(f'{where} needs {field}')
        for field in ('set', 'number'):
            if field in card and (not isinstance(card[field], str) or not card[field].strip()):
                raise ValueError(f'{where} has an empty {field}')
        path = card['image']
        asset = (root / path).resolve()
        if not ASSET_PATH.fullmatch(path) or not asset.is_relative_to(root / 'assets') or not asset.is_file():
            raise ValueError(f'{where} image must be a local asset')
        if 'link' in card and not _https(card['link']):
            raise ValueError(f'{where} link must be a public https URL')


def render_chase_cards(item):
    """HTML for the strip, or '' when the story has no chase_cards."""
    cards = item.get('chase_cards') if isinstance(item, dict) else None
    if not isinstance(cards, list) or not cards:
        return ''
    tiles = []
    for card in cards:
        meta = ' · '.join(esc(card[field]) for field in ('set', 'number') if card.get(field))
        image = (f'<img src="{esc(card.get("image"))}" alt="{esc(card.get("alt"))}" '
                 f'loading="lazy" decoding="async">')
        caption = f'<span class="chase-strip-name">{esc(card.get("name"))}</span>'
        if meta:
            caption += f'<span class="chase-strip-meta">{meta}</span>'
        body = image + caption
        link = card.get('link')
        if link:
            inner = (f'<a class="chase-strip-card" href="{esc(link)}" '
                     f'target="_blank" rel="noopener noreferrer">{body}</a>')
        else:
            inner = f'<div class="chase-strip-card">{body}</div>'
        tiles.append(f'<li>{inner}</li>')
    credit = item.get('chase_cards_credit')
    credit_html = f'<p class="chase-strip-credit">{esc(credit)}</p>' if isinstance(credit, str) and credit.strip() else ''
    return ('<section class="chase-strip" aria-label="Chase cards">'
            '<h2 class="chase-strip-title">Chase cards</h2>'
            f'<ul class="chase-strip-row">{"".join(tiles)}</ul>'
            f'{credit_html}</section>')
