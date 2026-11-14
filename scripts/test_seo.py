"""SEO / Google News helpers and built-artifact checks."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_seo as seo

NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9',
      'n': 'http://www.google.com/schemas/sitemap-news/0.9'}
NOW = datetime(2026, 11, 14, 12, 28, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


class NewsWindowTests(unittest.TestCase):
    def test_includes_last_48_hours_and_excludes_older(self):
        self.assertTrue(seo.in_news_window('2026-11-14', now=NOW))
        self.assertTrue(seo.in_news_window('2026-11-13T08:50:00Z', now=NOW))
        self.assertFalse(seo.in_news_window('2026-11-12', now=NOW))  # midnight is >48h earlier
        self.assertFalse(seo.in_news_window('2026-11-11', now=NOW))


class SitemapTests(unittest.TestCase):
    def test_news_sitemap_is_valid_xml_and_matches_the_spec(self):
        xml = seo.news_sitemap_xml([
            {'url': 'https://buytrigger.cards/stories/example/',
             'title': 'Four cards & a test',
             'date': '2026-11-14'},
        ])
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
        loc = root.find('s:url/s:loc', NS).text
        title = root.find('s:url/n:news/n:title', NS).text
        language = root.find('s:url/n:news/n:publication/n:language', NS).text
        name = root.find('s:url/n:news/n:publication/n:name', NS).text
        date = root.find('s:url/n:news/n:publication_date', NS).text
        self.assertEqual(loc, 'https://buytrigger.cards/stories/example/')
        self.assertEqual(title, 'Four cards & a test')
        self.assertEqual(language, 'en')
        self.assertEqual(name, 'BuyTrigger.Cards')
        self.assertEqual(date, '2026-11-14')

    def test_robots_lists_both_sitemaps(self):
        text = seo.robots_txt()
        self.assertIn('Sitemap: https://buytrigger.cards/sitemap.xml', text)
        self.assertIn('Sitemap: https://buytrigger.cards/news-sitemap.xml', text)

    def test_collect_uses_desk_date_and_story_urls(self):
        editorial = {
            'publishedAt': '2026-11-03',
            'articles': [
                {'slug': 'fresh-story', 'title': 'Fresh', 'publishedAt': '2026-11-14', 'status': 'published'},
                {'slug': 'old-story', 'title': 'Old', 'publishedAt': '2026-11-03', 'status': 'published'},
            ],
            'wire': [
                {'id': 'fresh-brief-2026-11-13', 'title': 'Brief', 'date': '2026-11-13', 'sourcePublishedAt': '2026-10-30'},
                {'id': 'old-brief-2026-11-01', 'title': 'Older', 'date': '2026-11-01'},
            ],
        }
        entries = seo.collect_news_entries(editorial, now=NOW)
        urls = {item['url'] for item in entries}
        self.assertEqual(urls, {
            'https://buytrigger.cards/stories/fresh-story/',
            'https://buytrigger.cards/news/fresh-brief-2026-11-13/',
        })


class SchemaTests(unittest.TestCase):
    def test_news_article_has_required_fields_and_wide_image(self):
        schema = seo.news_article_schema(
            headline='A headline',
            url='https://buytrigger.cards/stories/example/',
            date_published='2026-11-14',
            date_modified='2026-11-14',
            image=seo.image_object('https://buytrigger.cards/assets/family-wide.jpg', 1600, 900),
            author={'@type': 'Person', 'name': 'Alex Koh'},
            description='A summary.',
        )
        problems = seo.validate_news_article(schema, url='https://buytrigger.cards/stories/example/')
        self.assertEqual(problems, [])
        self.assertEqual(schema['publisher']['name'], 'BuyTrigger.Cards')
        self.assertEqual(schema['publisher']['logo']['width'], 600)
        self.assertGreaterEqual(schema['image']['width'], 1200)

    def test_rejects_a_narrow_image(self):
        schema = seo.news_article_schema(
            headline='A headline',
            url='https://buytrigger.cards/stories/example/',
            date_published='2026-11-14',
            date_modified='2026-11-14',
            image=seo.image_object('https://buytrigger.cards/assets/family.png', 850, 478),
            author={'@type': 'Organization', 'name': 'BuyTrigger.Cards'},
        )
        problems = seo.validate_news_article(schema, url='https://buytrigger.cards/stories/example/')
        self.assertTrue(any('1200' in item for item in problems))


class ShareImageTests(unittest.TestCase):
    def test_letterbox_is_1600_wide_and_does_not_crop(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            src = folder / 'narrow.jpg'
            from PIL import Image
            Image.new('RGB', (400, 700), (20, 20, 20)).save(src)
            dest = folder / 'out.jpg'
            size = seo.letterbox_share(src, dest, ROOT / seo.PUBLISHER_LOGO)
            self.assertEqual(size, (1600, 900))
            with Image.open(dest) as im:
                self.assertEqual(im.size, (1600, 900))


class CommittedAssetTests(unittest.TestCase):
    def test_publisher_logo_and_fallback_meet_the_width_rule(self):
        logo_w, logo_h = seo.image_size(ROOT / seo.PUBLISHER_LOGO)
        self.assertEqual((logo_w, logo_h), (600, 60))
        family_w, family_h = seo.image_size(ROOT / seo.FAMILY_WIDE)
        self.assertGreaterEqual(family_w, 1200)
        fall_w, fall_h = seo.image_size(ROOT / seo.SHARE_FALLBACK)
        self.assertGreaterEqual(fall_w, 1200)
        self.assertEqual((fall_w, fall_h), (1600, 900))


if __name__ == '__main__':
    unittest.main()
