"""Optional Buy on eBay card blocks for a news brief, plus checks for Feature blocks.

This file only writes the README's `data-ebay-card` block. It builds no link:
`commerce.js` turns each block into the compact Buy on eBay control when the page loads.

Front matter, on a wire brief:

    "ebay_cards": [
      {"name": "Raikou ex", "number": "136/103", "set": "Delta Reign"}
    ]

Placement (Captain, 20 Nov 2026): a news brief uses `story-` plus the first 45
characters of its id, with any trailing hyphen trimmed. A Feature uses `story-`
plus its full slug, and it must fit. Either way `story-<...>-psa10` stays within
commerce.js's 64-character custom id. Omit `ebay_cards` and the page is unchanged.
A Feature carries the same block written in its section HTML.
"""
import re

FIELDS = ('name', 'number', 'set')
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
BLOCK = re.compile(r'<div data-ebay-card\b[^>]*>', re.S)
ATTR = re.compile(r'data-ebay-(name|number|set|placement)="([^"]*)"')
URLISH = re.compile(r'https?:|www\.|ebay\.|\$|£|US\$|€')
MAX_CUSTOM_ID = 64  # commerce.js placementId(): story-<slug>-psa10 must fit
NEWS_SLUG_CHARS = 45


def esc(value):
    return (str('' if value is None else value)
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


def placement_for(slug):
    """Feature placement: the full slug."""
    return 'story-' + slug


def news_placement_for(news_id):
    """News placement: the first 45 characters of the id, trailing hyphens trimmed."""
    return 'story-' + news_id[:NEWS_SLUG_CHARS].rstrip('-')


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
    _check_placement(news_placement_for(slug), label)
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


def render_ebay_block(card, slug):
    placement = esc(news_placement_for(slug))
    return (f'<div data-ebay-card data-ebay-name="{esc(card["name"])}" data-ebay-number="{esc(card["number"])}" '
            f'data-ebay-set="{esc(card["set"])}" data-ebay-placement="{placement}"></div>')


def render_ebay_cards(item, slug, skip=()):
    cards = item.get('ebay_cards')
    if not cards:
        return ''
    skipped = set(skip)
    return ''.join(render_ebay_block(c, slug) for c in cards if (c['name'], c['number']) not in skipped)


def summary_paragraphs(summary):
    """Lead paragraphs of a news brief, split on a blank line."""
    return [part.strip() for part in re.split(r'\n{2,}', summary or '') if part.strip()]


def news_insert_at(count):
    """Paragraphs that stay above the card-image and eBay unit.

    Four or more paragraphs: after paragraph 3. Three: after paragraph 2.
    Fewer: after the last lead paragraph.
    """
    if count >= 4:
        return 3
    if count == 3:
        return 2
    return count


def render_news_paragraphs(summary, unit_html=''):
    """Split summary paragraphs with the eBay and chase unit in the agreed place."""
    paras = ['<p>' + esc(part) + '</p>' for part in summary_paragraphs(summary)]
    cut = news_insert_at(len(paras))
    return ''.join(paras[:cut]) + (unit_html or '') + ''.join(paras[cut:])


def news_standfirst(summary):
    parts = summary_paragraphs(summary)
    return parts[0] if parts else ''


def check_rendered_news_placements(markup, news_id, label, summary=None):
    """Every block on a built news page uses the expected truncated placement and fits.

    When the markup is a full news page, the card-image and eBay unit sits inside
    the article body, after the lead paragraphs agreed with the SPA.
    """
    expected = news_placement_for(news_id)
    for tag in BLOCK.findall(markup):
        placement = dict(ATTR.findall(tag)).get('placement')
        if placement != expected:
            raise ValueError(f'{label}: eBay placement {placement} should be {expected}')
        _check_placement(placement, label)
    if 'article-body' not in markup:
        return
    body_at = markup.find('article-body')
    for needle in ('data-ebay-card', 'class="story-chase"', "class='story-chase'"):
        at = markup.find(needle)
        if at != -1 and at < body_at:
            raise ValueError(f'{label}: eBay or chase block is above the article body')
    if summary is None:
        return
    unit_at = markup.find('news-ebay-unit', body_at)
    body = markup[body_at:]
    has_block = 'data-ebay-card' in body or 'story-chase' in body
    if not has_block:
        if unit_at != -1:
            raise ValueError(f'{label}: empty news eBay unit')
        return
    if unit_at == -1:
        raise ValueError(f'{label}: eBay or chase block is not in one news unit')
    paragraphs = markup[body_at:unit_at].count('<p>')
    expected_after = news_insert_at(len(summary_paragraphs(summary)))
    if paragraphs != expected_after:
        raise ValueError(
            f'{label}: eBay unit follows {paragraphs} paragraphs, expected {expected_after}'
        )
