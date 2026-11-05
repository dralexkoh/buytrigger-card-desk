"""Fail publication when an article lacks deliberate, traceable visual coverage."""
from pathlib import Path
from urllib.parse import urlsplit
import json,re
from bs4 import BeautifulSoup

STYLES={'editorial-ink-v1','family-anime-v1','brand-graphic-v1','japan-editorial-v1','source-media-v1'}
WIRE_MEDIA=('image','imageAlt','imageCredit','imageSourceUrl')
WIRE_MEDIA_PATH=re.compile(r'assets/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_.-]+\.(?:avif|jpg|jpeg|png|webp)')

def validate_wire_media(wire,root):
    fields=(*WIRE_MEDIA,'imageLicenseUrl')
    if not any(field in wire for field in fields):
        return
    story=wire.get('id','wire story')
    if any(not isinstance(wire.get(field),str) or not wire[field].strip() for field in WIRE_MEDIA):
        raise ValueError(f'{story}: wire picture needs alt text, credit and its public source')
    path=wire['image']
    if not WIRE_MEDIA_PATH.fullmatch(path) or not (root/path).resolve().is_relative_to(root/'assets') or not (root/path).is_file():
        raise ValueError(f'{story}: missing or unsafe wire picture')
    for field in ('imageSourceUrl','imageLicenseUrl'):
        if field not in wire:
            continue
        value=wire[field]
        if not isinstance(value,str) or not value or '\\' in value or any(c.isspace() for c in value):
            raise ValueError(f'{story}: invalid {field}')
        parsed=urlsplit(value)
        if parsed.scheme!='https' or not parsed.hostname or '.' not in parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f'{story}: {field} must be a public HTTPS reference')

def validate_editorial_visuals(editorial,root):
    root=Path(root).resolve()
    for wire in editorial.get('wire',[]):
        validate_wire_media(wire,root)
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
    print(f'PASS: all {count} articles have classified artwork; article and wire image assets and credits verified.')
