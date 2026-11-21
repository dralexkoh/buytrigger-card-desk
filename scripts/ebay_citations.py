"""Add eBay Partner Network parameters to citation links that do not have them.

Item and sold-listing citations keep their visible wording. A link that already
carries campid is left unchanged. This module never requests the URL.
"""
import re
from html import escape, unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CAMPAIGN = '5339239680'
UK_ROTATION = '710-53481-19255-0'
US_ROTATION = '711-53200-19255-0'
CUSTOM_ID = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
REL_REQUIRED = ('sponsored', 'nofollow', 'noopener')
REL_ATTR = re.compile(r'\brel=(["\'])(.*?)\1', re.I)
ANCHOR = re.compile(
    r'<a\b([^>]*?)href=(["\'])(https://[^"\']+)\2([^>]*)>(.*?)</a>',
    re.I | re.S,
)


def rotation_for(host):
    host = (host or '').lower()
    if host in ('ebay.com', 'www.ebay.com'):
        return US_ROTATION
    if 'ebay.' in host:
        return UK_ROTATION
    return None


def is_ebay(url):
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme == 'https' and rotation_for(parts.hostname) is not None


def has_campid(url):
    return any(key == 'campid' for key, _ in parse_qsl(urlsplit(url).query, keep_blank_values=True))


def cite_custom_id(rel):
    """Citation id for a built page, using the same 64-character rule as placementId."""
    rel = str(rel).replace('\\', '/')
    if rel == 'undervalued.html':
        return 'uv-cite'
    if rel == 'undervalued-japanese.html':
        return 'uvjp-cite'
    story = re.fullmatch(r'stories/([a-z0-9]+(?:-[a-z0-9]+)*)/(?:index\.html)?', rel)
    if story:
        custom = f'story-{story.group(1)}-cite'
        return custom if CUSTOM_ID.fullmatch(custom) else None
    news = re.fullmatch(r'news/([a-z0-9-]+)/(?:index\.html)?', rel)
    if news:
        slug = news.group(1)[:45].rstrip('-')
        custom = f'story-{slug}-cite'
        return custom if CUSTOM_ID.fullmatch(custom) else None
    return None


def add_tracking(url, custom_id):
    if not CUSTOM_ID.fullmatch(custom_id or ''):
        raise ValueError('Citation id must match placementId and fit in 64 characters')
    parts = urlsplit(url)
    mkrid = rotation_for(parts.hostname)
    if not mkrid or has_campid(url):
        return url
    query = parse_qsl(parts.query, keep_blank_values=True)
    present = {key for key, _ in query}
    for key, value in (
        ('mkevt', '1'),
        ('mkcid', '1'),
        ('mkrid', mkrid),
        ('campid', CAMPAIGN),
        ('toolid', '10001'),
        ('customid', custom_id),
    ):
        if key not in present:
            query.append((key, value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def merge_rel(value):
    """Keep existing tokens, then add sponsored, nofollow and noopener once each."""
    tokens = []
    for token in re.split(r'\s+', value or ''):
        if token and token not in tokens:
            tokens.append(token)
    for token in REL_REQUIRED:
        if token not in tokens:
            tokens.append(token)
    return ' '.join(tokens)


def with_affiliate_rel(opening):
    """Add the affiliate rel tokens. Leave target and every other attribute alone."""
    found = REL_ATTR.search(opening)
    if not found:
        return opening[:-1] + ' rel="sponsored nofollow noopener">'
    merged = merge_rel(found.group(2))
    if merged == found.group(2):
        return opening
    return opening[:found.start()] + f'rel={found.group(1)}{merged}{found.group(1)}' + opening[found.end():]


def tag_html(markup, custom_id):
    """Return markup with untracked eBay citations tagged. Other anchors stay put."""
    def replace(match):
        before, quote, href, after, inner = match.groups()
        url = unescape(href)
        if not is_ebay(url) or has_campid(url):
            return match.group(0)
        tracked = escape(add_tracking(url, custom_id), quote=True)
        opening = with_affiliate_rel(f'<a{before}href={quote}{tracked}{quote}{after}>')
        label = ' <span class="ebay-cite">Affiliate link</span>'
        return f'{opening}{inner}</a>{label}'
    return ANCHOR.sub(replace, markup)


def ensure_sponsored(markup):
    """Give every eBay href that already has campid the affiliate rel tokens."""
    def replace(match):
        before, quote, href, after, inner = match.groups()
        url = unescape(href)
        if not is_ebay(url) or not has_campid(url):
            return match.group(0)
        opening = f'<a{before}href={quote}{href}{quote}{after}>'
        updated = with_affiliate_rel(opening)
        if updated == opening:
            return match.group(0)
        return f'{updated}{inner}</a>'
    return ANCHOR.sub(replace, markup)


def missing_sponsored(markup):
    found = []
    for match in ANCHOR.finditer(markup):
        url = unescape(match.group(3))
        if not is_ebay(url) or not has_campid(url):
            continue
        opening = f'<a{match.group(1)}href={match.group(2)}{match.group(3)}{match.group(2)}{match.group(4)}>'
        rel = REL_ATTR.search(opening)
        tokens = set(rel.group(2).split()) if rel else set()
        if 'sponsored' not in tokens:
            found.append(url)
    return found


def untracked_hrefs(markup):
    found = []
    for match in ANCHOR.finditer(markup):
        url = unescape(match.group(3))
        if is_ebay(url) and not has_campid(url):
            found.append(url)
    return found


def tag_tree(dist):
    """Tag every built page that has a citation id. Raise if any eBay href is still bare."""
    dist = Path(dist)
    for path in dist.rglob('*.html'):
        rel = path.relative_to(dist).as_posix()
        text = path.read_text()
        if not untracked_hrefs(text):
            continue
        custom = cite_custom_id(rel)
        if not custom:
            raise ValueError(f'Untracked eBay link on {rel} has no citation id')
        path.write_text(tag_html(text, custom))
    for path in dist.rglob('*.html'):
        text = path.read_text()
        updated = ensure_sponsored(text)
        if updated != text:
            path.write_text(updated)
    leftover = []
    unsponsored = []
    for path in sorted(dist.rglob('*.html')):
        rel = path.relative_to(dist).as_posix()
        text = path.read_text()
        leftover.extend((rel, url) for url in untracked_hrefs(text))
        unsponsored.extend((rel, url) for url in missing_sponsored(text))
    if leftover:
        sample = leftover[0]
        raise ValueError(f'{len(leftover)} untracked eBay links remain, including {sample[0]}')
    if unsponsored:
        sample = unsponsored[0]
        raise ValueError(f'{len(unsponsored)} eBay affiliate links lack sponsored, including {sample[0]}')
    return len(list(dist.rglob('*.html')))
