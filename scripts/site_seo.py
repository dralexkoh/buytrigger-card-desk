"""Google News / Discover helpers for the public BuyTrigger.Cards build."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape
import json
import os
import re

from PIL import Image, ImageDraw

BASE = 'https://buytrigger.cards/'
BRAND = 'BuyTrigger.Cards'
NEWS_WINDOW = timedelta(days=2)
PUBLISHER_LOGO = 'assets/publisher-logo-600x60.png'
FAMILY_WIDE = 'assets/family-wide.jpg'
SHARE_FALLBACK = 'assets/newsroom-share-fallback.jpg'
MIN_IMAGE_WIDTH = 1200
SHARE_SIZE = (1600, 900)
PAPER = (244, 244, 241)
RED = (223, 36, 43)
ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')

# Google Search Console HTML-tag verification. Set BT_GOOGLE_SITE_VERIFICATION
# or a one-line google-site-verification.txt in the repo root (gitignored).
# Do not invent a token. Alex completes the Search Console signup himself.
VERIFICATION_ENV = 'BT_GOOGLE_SITE_VERIFICATION'
VERIFICATION_FILE = 'google-site-verification.txt'


def article_url(slug):
    return f'{BASE}stories/{slug}/'


def news_url(item_id):
    return f'{BASE}news/{item_id}/'


def parse_when(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_datetime(value):
    dt = parse_when(value)
    if not dt:
        return None
    if dt.time() == datetime.min.time() and dt.utcoffset() == timedelta(0):
        return dt.date().isoformat()
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def in_news_window(value, now=None):
    dt = parse_when(value)
    now = now or datetime.now(timezone.utc)
    return bool(dt and dt >= (now - NEWS_WINDOW))


def publisher():
    return {
        '@type': 'Organization',
        'name': BRAND,
        'logo': {
            '@type': 'ImageObject',
            'url': BASE + PUBLISHER_LOGO,
            'width': 600,
            'height': 60,
        },
    }


def image_object(url, width=None, height=None):
    obj = {'@type': 'ImageObject', 'url': url}
    if width:
        obj['width'] = int(width)
    if height:
        obj['height'] = int(height)
    return obj


def news_article_schema(*, headline, url, date_published, date_modified, image, author, description=None):
    published = iso_datetime(date_published) or date_published
    modified = iso_datetime(date_modified) or published
    schema = {
        '@context': 'https://schema.org',
        '@type': 'NewsArticle',
        'headline': headline,
        'datePublished': published,
        'dateModified': modified,
        'image': image,
        'author': author,
        'publisher': publisher(),
        'mainEntityOfPage': {'@type': 'WebPage', '@id': url},
    }
    if description:
        schema['description'] = description
    return schema


def urlset_xml(entries):
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for item in entries:
        loc = escape(item['url'])
        lastmod = escape(str(item['lastmod']))
        parts.append(f'<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>')
    parts.append('</urlset>')
    return ''.join(parts)


def news_sitemap_xml(entries):
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">']
    for item in entries:
        parts.append(
            '<url>'
            f'<loc>{escape(item["url"])}</loc>'
            '<news:news>'
            '<news:publication>'
            f'<news:name>{escape(BRAND)}</news:name>'
            '<news:language>en</news:language>'
            '</news:publication>'
            f'<news:publication_date>{escape(item["date"])}</news:publication_date>'
            f'<news:title>{escape(item["title"])}</news:title>'
            '</news:news>'
            '</url>'
        )
    parts.append('</urlset>')
    return ''.join(parts)


def robots_txt():
    return (
        'User-agent: *\n'
        'Allow: /\n'
        f'Sitemap: {BASE}sitemap.xml\n'
        f'Sitemap: {BASE}news-sitemap.xml\n'
    )


def local_image(root: Path, image):
    if not image or str(image).startswith(('http://', 'https://', '//')):
        return None
    path = root / image
    return path if path.is_file() else None


def image_size(path: Path):
    with Image.open(path) as im:
        return im.size


def letterbox_share(src: Path, dest: Path, logo: Path):
    """Place an existing photo on a 1600x900 paper canvas. Does not crop or redraw it."""
    canvas = Image.new('RGB', SHARE_SIZE, PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, SHARE_SIZE[0], 8), fill=RED)
    logo_im = Image.open(logo).convert('RGBA')
    # Keep the official rectangular wordmark at native 600x60, or scale if needed.
    canvas.paste(logo_im, (48, 28), logo_im if logo_im.mode == 'RGBA' else None)
    photo = Image.open(src).convert('RGB')
    inner = (48, 120, SHARE_SIZE[0] - 48, SHARE_SIZE[1] - 48)
    box_w = inner[2] - inner[0]
    box_h = inner[3] - inner[1]
    scale = min(box_w / photo.width, box_h / photo.height)
    new_size = (max(1, round(photo.width * scale)), max(1, round(photo.height * scale)))
    fitted = photo.resize(new_size, Image.Resampling.LANCZOS)
    x = inner[0] + (box_w - fitted.width) // 2
    y = inner[1] + (box_h - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, 'JPEG', quality=90, optimize=True)
    return SHARE_SIZE


def schema_image(root: Path, dist: Path, image, *, kind, slug, fallback_to_family=False):
    """Pick a >=1200px-wide public image, writing a share derivative only when needed."""
    fallback = FAMILY_WIDE if fallback_to_family and (root / FAMILY_WIDE).is_file() else SHARE_FALLBACK
    src = local_image(root, image)
    if src:
        width, height = image_size(src)
        if width >= MIN_IMAGE_WIDTH:
            return image_object(BASE + image, width, height), image, (width, height)
        # Prefer a prepared wide version of the same picture when one exists.
        if fallback_to_family and (root / FAMILY_WIDE).is_file():
            width, height = image_size(root / FAMILY_WIDE)
            return image_object(BASE + FAMILY_WIDE, width, height), FAMILY_WIDE, (width, height)
        dest_rel = f'assets/share/{kind}/{slug}.jpg'
        dest = dist / dest_rel
        letterbox_share(src, dest, root / PUBLISHER_LOGO)
        return image_object(BASE + dest_rel, *SHARE_SIZE), dest_rel, SHARE_SIZE
    dest_rel = fallback
    path = root / dest_rel
    width, height = image_size(path) if path.is_file() else SHARE_SIZE
    return image_object(BASE + dest_rel, width, height), dest_rel, (width, height)


def collect_news_entries(editorial, now=None):
    entries = []
    for article in editorial.get('articles', []):
        if article.get('status') not in (None, 'published'):
            continue
        published = article.get('publishedAt') or editorial.get('publishedAt')
        if not in_news_window(published, now=now):
            continue
        if not ID_RE.fullmatch(article['slug']):
            raise ValueError('Unusable article slug for /stories/ URL: ' + article['slug'])
        entries.append({
            'url': article_url(article['slug']),
            'title': article['title'],
            'date': iso_datetime(published),
            'kind': 'article',
            'id': article['slug'],
        })
    for item in editorial.get('wire', []):
        published = item.get('date') or item.get('sourcePublishedAt')
        if not in_news_window(published, now=now):
            continue
        if not ID_RE.fullmatch(item['id']):
            raise ValueError('Unusable wire id for /news/ URL: ' + item['id'])
        entries.append({
            'url': news_url(item['id']),
            'title': item['title'],
            'date': iso_datetime(published),
            'kind': 'news',
            'id': item['id'],
        })
    return entries


def collect_sitemap_entries(editorial, static_urls, now_lastmod='2026-11-04'):
    entries = [{'url': url, 'lastmod': now_lastmod} for url in static_urls]
    for article in editorial.get('articles', []):
        if not ID_RE.fullmatch(article['slug']):
            raise ValueError('Unusable article slug for /stories/ URL: ' + article['slug'])
        lastmod = article.get('updatedAt') or article.get('publishedAt') or editorial.get('publishedAt') or now_lastmod
        entries.append({'url': article_url(article['slug']), 'lastmod': str(lastmod)[:10]})
    for item in editorial.get('wire', []):
        if not ID_RE.fullmatch(item['id']):
            raise ValueError('Unusable wire id for /news/ URL: ' + item['id'])
        lastmod = (item.get('checkedAt') or item.get('date') or now_lastmod)
        entries.append({'url': news_url(item['id']), 'lastmod': str(lastmod)[:10]})
    return entries


def verification_token(root: Path):
    token = (os.environ.get(VERIFICATION_ENV) or '').strip()
    path = root / VERIFICATION_FILE
    if not token and path.is_file():
        token = path.read_text(encoding='utf-8').strip().splitlines()[0].strip() if path.read_text(encoding='utf-8').strip() else ''
    if token and re.fullmatch(r'[A-Za-z0-9_-]{8,200}', token):
        return token
    return None


def ensure_robots_preview(soup):
    existing = soup.select_one('meta[name="robots"]')
    if existing:
        content = existing.get('content') or ''
        if 'max-image-preview' not in content.lower():
            existing['content'] = (content + ', ' if content.strip() else '') + 'max-image-preview:large'
        return
    tag = soup.new_tag('meta')
    tag['name'] = 'robots'
    tag['content'] = 'max-image-preview:large'
    soup.head.append(tag)


def upsert_meta(soup, *, attr, key, content):
    if attr == 'property':
        tag = soup.select_one(f'meta[property="{key}"]')
    else:
        tag = soup.select_one(f'meta[name="{key}"]')
    if not tag:
        tag = soup.new_tag('meta')
        tag[attr] = key
        soup.head.append(tag)
    tag['content'] = content
    return tag


def apply_share_tags(soup, *, url, title, description, image, og_type='article'):
    brand_title = title if title.endswith(' · ' + BRAND) else f'{title} · {BRAND}'
    if soup.title:
        soup.title.string = brand_title
    else:
        tag = soup.new_tag('title')
        tag.string = brand_title
        soup.head.append(tag)
    canonical = soup.select_one('link[rel=canonical]')
    if not canonical:
        canonical = soup.new_tag('link')
        canonical['rel'] = 'canonical'
        soup.head.append(canonical)
    canonical['href'] = url
    upsert_meta(soup, attr='name', key='description', content=description)
    upsert_meta(soup, attr='property', key='og:title', content=brand_title)
    upsert_meta(soup, attr='property', key='og:description', content=description)
    upsert_meta(soup, attr='property', key='og:url', content=url)
    upsert_meta(soup, attr='property', key='og:type', content=og_type)
    upsert_meta(soup, attr='property', key='og:image', content=image)
    upsert_meta(soup, attr='name', key='twitter:card', content='summary_large_image')
    upsert_meta(soup, attr='name', key='twitter:title', content=brand_title)
    upsert_meta(soup, attr='name', key='twitter:description', content=description)
    upsert_meta(soup, attr='name', key='twitter:image', content=image)
    ensure_robots_preview(soup)


def set_json_ld(soup, schema):
    for tag in list(soup.select('script[type="application/ld+json"]')):
        try:
            data = json.loads(tag.string or '{}')
        except json.JSONDecodeError:
            continue
        if data.get('@type') in ('Article', 'NewsArticle') or (
            isinstance(data.get('@type'), list) and {'Article', 'NewsArticle'} & set(data.get('@type'))
        ):
            tag.decompose()
    script = soup.new_tag('script', type='application/ld+json')
    script.string = json.dumps(schema, ensure_ascii=False).replace('</', '<\\/')
    soup.head.append(script)


def schema_main_entity_url(schema):
    value = schema.get('mainEntityOfPage')
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get('@id') or value.get('url')
    return None


def validate_news_article(schema, *, url, min_width=MIN_IMAGE_WIDTH):
    problems = []
    types = schema.get('@type')
    types = types if isinstance(types, list) else [types]
    if 'NewsArticle' not in types:
        problems.append('missing NewsArticle type')
    for key in ('headline', 'datePublished', 'dateModified', 'image', 'author', 'publisher', 'mainEntityOfPage'):
        if not schema.get(key):
            problems.append('missing ' + key)
    if schema_main_entity_url(schema) != url:
        problems.append('mainEntityOfPage does not match canonical URL')
    publisher_node = schema.get('publisher') or {}
    if publisher_node.get('name') != BRAND or publisher_node.get('@type') != 'Organization':
        problems.append('publisher must be Organization BuyTrigger.Cards')
    logo = publisher_node.get('logo') or {}
    if not (isinstance(logo, dict) and str(logo.get('url', '')).startswith(BASE) and int(logo.get('width') or 0) >= 112):
        problems.append('publisher logo missing or too small')
    image = schema.get('image')
    images = image if isinstance(image, list) else [image]
    wide_enough = False
    for item in images:
        if isinstance(item, str) and item.startswith(BASE):
            # Width unknown from a bare URL; accepted only when caller already checked.
            wide_enough = True
        elif isinstance(item, dict) and str(item.get('url', '')).startswith(BASE):
            if int(item.get('width') or 0) >= min_width:
                wide_enough = True
        else:
            problems.append('image is not on the public domain')
    if images and not wide_enough:
        problems.append(f'image width must be at least {min_width}px')
    return problems


def apply_verification_meta(soup, token):
    if not token:
        return
    existing = soup.select_one('meta[name="google-site-verification"]')
    if existing:
        existing['content'] = token
        return
    tag = soup.new_tag('meta')
    tag['name'] = 'google-site-verification'
    tag['content'] = token
    soup.head.append(tag)
