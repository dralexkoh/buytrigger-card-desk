"""Public offer contract and deterministic links. Evidence is reviewed privately."""
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import math
import re

ROTATIONS = {'www.ebay.co.uk': '710-53481-19255-0', 'www.ebay.com': '711-53200-19255-0'}
FIELDS = {'id', 'productKey', 'title', 'summary', 'region', 'country', 'language',
          'retailer', 'seller', 'fulfilment', 'event', 'availability', 'productUrl',
          'sourceUrl', 'checkedAt', 'expiresAt', 'affiliateProvider', 'affiliateUrl',
          'price', 'revision'}
REQUIRED = FIELDS - {'price'}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('A dated, timezone-aware check is required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone is required')
    return result


def validate_config(config):
    if set(config) != {'schemaVersion', 'ebay', 'amazonUk', 'placements'} or config['schemaVersion'] != 1:
        raise ValueError('Unknown commerce configuration')
    if (set(config['placements']) != {'home', 'drops'}
            or any(type(v) is not bool for v in config['placements'].values())):
        raise ValueError('Placement activation must be explicit')
    if set(config['ebay']) != {'enabled', 'campaignId'} or type(config['ebay']['enabled']) is not bool:
        raise ValueError('Invalid eBay configuration')
    if not re.fullmatch(r'\d{10}', config['ebay']['campaignId']):
        raise ValueError('A verified EPN campaign is required')
    if set(config['amazonUk']) != {'enabled', 'trackingId'} or config['amazonUk']['enabled'] is not False:
        raise ValueError('Amazon requires a separately reviewed programme adapter before activation')
    return True


def ebay_link(target, config, custom_id=None, listing=True):
    validate_config(config)
    if not config['ebay']['enabled']:
        raise ValueError('eBay affiliate programme is disabled')
    parsed = urlsplit(target)
    if (parsed.scheme != 'https' or parsed.netloc not in ROTATIONS or parsed.username
            or parsed.fragment or '\\' in target):
        raise ValueError('Use the exact HTTPS eBay marketplace')
    if listing:
        if not re.fullmatch(r'/itm/\d{9,15}', parsed.path):
            raise ValueError('A specific eBay listing is required for a verified offer')
        allowed = {'var'}
    else:
        if parsed.path != '/sch/i.html':
            raise ValueError('Expected an explicitly labelled eBay search')
        allowed = {'_nkw'}
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if any(key not in allowed for key, _ in pairs) or len({k for k, _ in pairs}) != len(pairs):
        raise ValueError('Canonical target contains tracking or unknown parameters')
    if listing and any(not value.isdigit() for _, value in pairs):
        raise ValueError('Invalid eBay variant')
    pairs += [('mkevt', '1'), ('mkcid', '1'), ('mkrid', ROTATIONS[parsed.netloc]),
              ('campid', config['ebay']['campaignId']), ('toolid', '10001')]
    if custom_id:
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', custom_id):
            raise ValueError('Invalid non-personal placement identifier')
        pairs.append(('customid', custom_id))
    return urlunsplit(('https', parsed.netloc, parsed.path, urlencode(pairs), ''))


def validate_offers(data, config, now=None, require_fresh=False):
    validate_config(config)
    now = now or datetime.now(timezone.utc)
    if set(data) != {'schemaVersion', 'updatedAt', 'items'} or data['schemaVersion'] != 1:
        raise ValueError('Unknown public offers payload')
    timestamp(data['updatedAt'])
    if not isinstance(data['items'], list) or len(data['items']) > 40:
        raise ValueError('Expected a bounded offers list')
    ids, keys = set(), set()
    for row in data['items']:
        if not isinstance(row, dict) or set(row) - FIELDS or not REQUIRED <= set(row):
            raise ValueError('Private/unknown fields or missing public offer fields')
        for key in REQUIRED - {'revision'}:
            if not isinstance(row[key], str) or not row[key].strip():
                raise ValueError('Missing public field: ' + key)
        if not re.fullmatch(r'[a-z0-9-]{1,80}', row['id']) or row['id'] in ids:
            raise ValueError('Invalid or duplicate offer ID')
        if len(row['title']) > 160 or len(row['summary']) > 320:
            raise ValueError('Offer copy is too long')
        if any('<' in row[k] or '>' in row[k] for k in ('title', 'summary', 'seller', 'fulfilment')):
            raise ValueError('Public copy must be plain text')
        if row['region'] not in {'UK', 'US', 'Asia'} or row['country'] in {'Asia', 'Worldwide', ''}:
            raise ValueError('Name the actual regional market')
        if row['region'] == 'UK' and row['country'] != 'United Kingdom':
            raise ValueError('UK offer country mismatch')
        if row['region'] == 'US' and row['country'] != 'United States':
            raise ValueError('US offer country mismatch')
        identity = (row['productKey'], row['country'], row['retailer'], row['event'])
        if identity in keys:
            raise ValueError('Duplicate product/market/retailer event')
        if row['event'] not in {'Available', 'Preorder', 'Restock'}:
            raise ValueError('Unknown retail event')
        if row['availability'] not in {'In stock', 'Preorder', 'Invitation', 'Sold out', 'Unknown'}:
            raise ValueError('Unknown availability')
        checked, expires = timestamp(row['checkedAt']), timestamp(row['expiresAt'])
        if not 0 < (expires - checked).total_seconds() <= 900 or checked > now:
            raise ValueError('Checks must be real, with at most 15 minutes of freshness')
        if require_fresh and expires <= now:
            raise ValueError('Offer expired before publication; recheck its primary source')
        if type(row['revision']) is not int or row['revision'] < 1:
            raise ValueError('A positive revision is required')
        if row['sourceUrl'] != row['productUrl'] or row['retailer'] != 'eBay':
            raise ValueError('First adapter requires the exact original eBay listing as evidence')
        if row['affiliateProvider'] != 'ebay':
            raise ValueError('Only the reviewed eBay affiliate adapter is active')
        if row['affiliateUrl'] != ebay_link(row['productUrl'], config, row['id']):
            raise ValueError('Affiliate destination or campaign differs from the verified offer')
        if row['region'] == 'UK' and urlsplit(row['productUrl']).netloc != 'www.ebay.co.uk':
            raise ValueError('UK offers must open the UK marketplace')
        if row.get('price') is not None:
            price = row['price']
            if (not isinstance(price, dict) or set(price) != {'amount', 'currency', 'basis'}
                    or type(price['amount']) not in {int, float} or not math.isfinite(price['amount'])
                    or price['amount'] <= 0 or price['currency'] not in {'GBP', 'USD'}
                    or price['basis'] != 'Item price; delivery shown by seller'):
                raise ValueError('Price requires an explicit item-only basis')
        ids.add(row['id']); keys.add(identity)
    return True
