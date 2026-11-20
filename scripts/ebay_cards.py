"""Optional Buy on eBay card blocks for a news brief, plus checks for Feature blocks.

This file only writes the README's `data-ebay-card` block. It builds no link:
`commerce.js` turns each block into the Shop this card box when the page loads.

Front matter, on a wire brief:

    "ebay_cards": [
      {"name": "Raikou ex", "number": "136/103", "set": "Delta Reign"}
    ]

The placement is always `story-` plus the brief id. Omit `ebay_cards` and the
page is unchanged. A Feature carries the same block written in its section HTML.
"""
import re

FIELDS = ('name', 'number', 'set')
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
BLOCK = re.compile(r'<div data-ebay-card\b[^>]*>', re.S)
ATTR = re.compile(r'data-ebay-(name|number|set|placement)="([^"]*)"')
URLISH = re.compile(r'https?:|www\.|ebay\.|\$|£|US\$|€')
MAX_CUSTOM_ID = 64  # commerce.js placementId(): story-<slug>-psa10 must fit


def esc(value):
    return (str('' if value is None else value)
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


def placement_for(slug):
    return 'story-' + slug


def _check_placement(placement, label):
    if not placement.startswith('story-') or not SLUG.fullmatch(placement[len('story-'):]):
        raise ValueError(f'{label}: eBay placement must be story-<slug>')
    if len(placement + '-psa10') > MAX_CUSTOM_ID:
        raise ValueError(f'{label}: eBay placement {placement} is too long for the 64-character custom id')


def _check_card(card, where):
    if not isinstance(card, dict):
        raise ValueError(f'{where} must be an object')
    unknown = set(card) - set(FIELDS)
    if unknown:
        raise ValueError(f'{where} has unexpected field {sorted(unknown)[0]}')
    for field in FIELDS:
        value = card.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{where} needs {field}')
        if URLISH.search(value):
            raise ValueError(f'{where} {field} must not carry a URL or price')


def validate_ebay_cards(item, slug, label):
    """Wire brief front matter. Absence is valid."""
    cards = item.get('ebay_cards')
    if cards is None:
        return
    if not isinstance(cards, list) or not cards:
        raise ValueError(f'{label}: ebay_cards needs at least one card')
    _check_placement(placement_for(slug), label)
    seen = set()
    for index, card in enumerate(cards, 1):
        _check_card(card, f'{label}: eBay card {index}')
        key = (card['name'].strip(), card['number'].strip())
        if key in seen:
            raise ValueError(f'{label}: eBay card {index} is a duplicate')
        seen.add(key)


def validate_section_blocks(article, label):
    """Feature section HTML: every block names its card and uses this story's placement."""
    slug = article['slug']
    seen = set()
    for section in article.get('sections', []):
        for tag in BLOCK.findall(section.get('html', '')):
            attrs = dict(ATTR.findall(tag))
            card = {k: attrs.get(k, '') for k in FIELDS}
            _check_card(card, f'{label}: eBay block')
            if attrs.get('placement') != placement_for(slug):
                raise ValueError(f'{label}: eBay block placement must be {placement_for(slug)}')
            _check_placement(attrs['placement'], label)
            key = (card['name'], card['number'])
            if key in seen:
                raise ValueError(f'{label}: duplicate eBay block for {card["name"]} {card["number"]}')
            seen.add(key)


def render_ebay_cards(item, slug):
    cards = item.get('ebay_cards')
    if not cards:
        return ''
    placement = esc(placement_for(slug))
    return ''.join(
        f'<div data-ebay-card data-ebay-name="{esc(c["name"])}" data-ebay-number="{esc(c["number"])}" '
        f'data-ebay-set="{esc(c["set"])}" data-ebay-placement="{placement}"></div>'
        for c in cards)
