"""Fail publication when an article lacks deliberate, traceable visual coverage."""
from pathlib import Path
import json
from bs4 import BeautifulSoup

STYLES={'editorial-ink-v1','family-anime-v1','brand-graphic-v1','japan-editorial-v1','source-media-v1'}

def validate_editorial_visuals(editorial,root):
    root=Path(root).resolve()
    for article in editorial['articles']:
        slug=article.get('slug','unnamed')
        for field in ('image','imageAlt','imageCredit','visualStyle'):
            if not isinstance(article.get(field),str) or not article[field].strip():
                raise ValueError(f'{slug}: missing editorial {field}')
        if article['visualStyle'] not in STYLES:
            raise ValueError(f'{slug}: unrecognised visual treatment')
        if article.get('pressAsset') and article['visualStyle']!='source-media-v1':
            raise ValueError(f'{slug}: press media must retain its source-media classification')
        for field in ('image','thumbnail'):
            if field not in article:continue
            value=article[field]
            if not isinstance(value,str) or not value.startswith('assets/'):
                raise ValueError(f'{slug}: {field} must be an explicit local public asset')
            asset=(root/value).resolve()
            if not asset.is_relative_to(root/'assets') or not asset.is_file():
                raise ValueError(f'{slug}: missing or unsafe {field} asset')
        if article.get('editorialFormat')=='visual-quick-read-v1':
            body=BeautifulSoup(''.join(s['html'] for s in article.get('sections',[])),'html.parser')
            if not body.select_one('.quick-verdict') or not body.select_one('.closing-call'):
                raise ValueError(f'{slug}: visual quick read needs an opening takeaway and closing verdict')
            if not body.select_one('.feature-reference img'):
                raise ValueError(f'{slug}: visual quick read needs a subject-specific inline picture')
            for figure in body.select('figure'):
                if not figure.find('figcaption') or not figure.find('figcaption').get_text(strip=True):
                    raise ValueError(f'{slug}: inline figure needs a caption and source/illustration context')
            for image in body.select('img'):
                path=image.get('src','');asset=(root/path).resolve()
                if not image.get('alt','').strip():raise ValueError(f'{slug}: inline picture needs alt text')
                if not path.startswith('assets/') or not asset.is_relative_to(root/'assets') or not asset.is_file():
                    raise ValueError(f'{slug}: missing or unsafe inline picture')
    return len(editorial['articles'])

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    count=validate_editorial_visuals(json.loads((root/'editorial.json').read_text()),root)
    print(f'PASS: all {count} articles have classified artwork, alt text and credit; assets exist.')
