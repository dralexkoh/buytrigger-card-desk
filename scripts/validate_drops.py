"""Release metadata checks; factual verification remains an editorial task."""
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

def validate_drops(data, root):
    date.fromisoformat(data['checkedAt'])
    assert data['coverage'].strip()
    ids = set()
    for item in data['items']:
        assert item['id'] not in ids, 'Duplicate regional release'
        ids.add(item['id'])
        assert item['region'] in {'UK', 'US', 'Asia'}
        assert item['country'] not in {'Asia', 'Worldwide', ''}, 'Name the actual market'
        assert item['event'] in {'Release', 'Preorder', 'Restock'}
        date.fromisoformat(item['date'])
        for key in ['title', 'language', 'publisher', 'dateBasis', 'summary', 'where', 'stock', 'imageCredit', 'sourceLabel']:
            assert isinstance(item[key], str) and item[key].strip(), key
        for key in ['sourceUrl', 'shopUrl', 'supportUrl']:
            if item.get(key):
                url=urlsplit(item[key]);assert url.scheme=='https' and url.hostname and not url.username, key
        assert item.get('sourceUrl'), 'An exact dated release needs its source'
        if item['stock'] != 'Not checked':
            assert item.get('stockSourceUrl') and item.get('stockCheckedAt') and item.get('stockExpiresAt'), 'Stock requires separate evidence and expiry'
            checked=datetime.fromisoformat(item['stockCheckedAt'].replace('Z','+00:00'))
            expires=datetime.fromisoformat(item['stockExpiresAt'].replace('Z','+00:00'))
            assert checked.tzinfo and expires.tzinfo and checked < expires and expires > datetime.now(timezone.utc), 'Expired stock claim'
        if item.get('image'):
            asset=Path(item['image']);assert not asset.is_absolute() and '..' not in asset.parts
            assert (root/asset).is_file() and item['imageAlt'].strip(), 'Image and alt required'
        else:
            assert item.get('visual'), 'Deliberate graphic required'
    return True
