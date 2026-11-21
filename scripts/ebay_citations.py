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


def tag_html(markup, custom_id):
    """Return markup with untracked eBay citations tagged. Other anchors stay put."""
    def replace(match):
        before, quote, href, after, inner = match.groups()
        url = unescape(href)
        if not is_ebay(url) or has_campid(url):
            return match.group(0)
        tracked = escape(add_tracking(url, custom_id), quote=True)
        label = ' <span class="ebay-cite">Affiliate link</span>'
        return f'<a{before}href={quote}{tracked}{quote}{after}>{inner}</a>{label}'
    return ANCHOR.sub(replace, markup)


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
    leftover = []
    for path in sorted(dist.rglob('*.html')):
        rel = path.relative_to(dist).as_posix()
        leftover.extend((rel, url) for url in untracked_hrefs(path.read_text()))
    if leftover:
        sample = leftover[0]
        raise ValueError(f'{len(leftover)} untracked eBay links remain, including {sample[0]}')
    return len(list(dist.rglob('*.html')))
