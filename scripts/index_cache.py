"""Per-index shared-DB caches built from the existing collector's committed observations.

No network calls. Reuses data/refresh/observations + receipts written by daily_refresh.py
(the same TCGCSV fetch), so this is not a second collector. Cards that are also in the
30th roster copy their points from thirtieth-current.json so both indices carry identical
observations. A missing or non-positive source is null for that day; earlier positive
points keep their own day. Zero is never written.

Output: data/market-cache/<index>-current.json, the file card_market_tcgcsv_refresh()
fetches at 14:30 Europe/London. The object matches the 30th cache contract: schemaVersion
1, index, sourceSystem shared-cards-market-cache, grade Raw, currency USD, measure
tcgcsv_market, sourceDate, sourceBuildAt, expiresAt, and cards[]. Each card has
productId, groupId, name, set, number, language, printing, image, and points[] of
{day, usd, status, source, sourceSha256} with status ok, no_price, or source_anomaly.
"""
from datetime import datetime, timedelta
from pathlib import Path
import json, math, re

WINDOW = 7
INDEX = re.compile(r'^[a-z0-9][a-z0-9-]{2,80}$')
RESERVED = {'thirtieth', 'thirtieth-anniversary'}
SHA = re.compile(r'^[a-f0-9]{64}$')
DAY = re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
IMAGE = re.compile(r'^assets/[a-z0-9][a-z0-9-]{1,80}/[0-9]+\.jpg$')
DIGITS = re.compile(r'^[0-9]{1,9}$')

def _positive(n): return isinstance(n,(int,float)) and not isinstance(n,bool) and math.isfinite(n) and n>0

def _days(root):
    out=[]
    for d in sorted(p for p in (root/'data/refresh/observations').iterdir() if p.is_dir()):
        files=sorted(d.glob('raw-*.json'))
        if not files: continue
        obs=json.loads(files[-1].read_text())
        rec=json.loads((root/'data/refresh/receipts'/f"{obs['id']}.json").read_text())
        if rec.get('sourceDate')!=d.name: raise ValueError('Receipt/day mismatch')
        out.append((d.name,{o['key']:o for o in obs['observations']},{s['url']:s['sha256'] for s in rec['sources']},rec['sourceBuildAt']))
    return out[-WINDOW:]

def _source_ok(source, group_id, day):
    live = f'https://tcgcsv.com/tcgplayer/3/{group_id}/prices'
    archive = f'https://tcgcsv.com/archive/tcgplayer/prices-{day}.ppmd.7z'
    return source==live or source==archive

def _check(cache):
    # Same rejection rules the shared Cards apply uses, so a bad file is skipped
    # instead of being published for the database to refuse.
    if cache.get('schemaVersion')!=1 or cache.get('grade')!='Raw' or cache.get('currency')!='USD' or cache.get('measure')!='tcgcsv_market':
        raise ValueError('Invalid exact-set public cache')
    index=cache.get('index')
    if not isinstance(index,str) or not INDEX.fullmatch(index) or index in RESERVED: raise ValueError('Unexpected roster')
    if cache.get('sourceSystem')!='shared-cards-market-cache': raise ValueError('Unexpected source')
    if not DAY.fullmatch(cache.get('sourceDate') or '') or not str(cache.get('sourceBuildAt','')).startswith(cache['sourceDate']+'T'):
        raise ValueError('Source build date mismatch')
    cards=cache.get('cards')
    if not isinstance(cards,list) or not 1<=len(cards)<=2000: raise ValueError('Unexpected card count')
    seen=set()
    for c in cards:
        ident=(c.get('productId'),c.get('printing'),c.get('language'))
        if ident in seen: raise ValueError('Duplicate printing')
        seen.add(ident)
        if not DIGITS.fullmatch(str(c.get('productId') or '')) or not DIGITS.fullmatch(str(c.get('groupId') or '')): raise ValueError('Invalid printing in public cache')
        if any(not c.get(field) for field in ('language','printing','set','name','number')): raise ValueError('Invalid printing in public cache')
        if c.get('image') and not IMAGE.fullmatch(c['image']): raise ValueError('Invalid printing in public cache')
        pts=c.get('points')
        if not isinstance(pts,list) or not 1<=len(pts)<=366: raise ValueError('Invalid printing in public cache')
        days=set()
        for p in pts:
            if p.get('day') in days: raise ValueError('Duplicate source day')
            days.add(p.get('day'))
            if not DAY.fullmatch(p.get('day') or '') or p['day']>cache['sourceDate']: raise ValueError('Invalid source observation')
            if p.get('status') not in ('ok','no_price','source_anomaly'): raise ValueError('Invalid source observation')
            usd=p.get('usd')
            if (p['status']=='ok')!=(usd is not None) or (usd is not None and not _positive(usd)): raise ValueError('Invalid mixed-condition source value')
            if p.get('reportedUsd') is not None and not _positive(p['reportedUsd']): raise ValueError('Invalid mixed-condition source value')
            if not SHA.fullmatch(p.get('sourceSha256') or '') or not _source_ok(p.get('source'), c['groupId'], p['day']): raise ValueError('Invalid source observation')
    return cache

def build(root, roster):
    root=Path(root)
    index=roster.get('index')
    if roster.get('schemaVersion')!=1 or not isinstance(index,str) or not INDEX.fullmatch(index) or index in RESERVED: raise ValueError('Unexpected roster')
    cards=roster['cards']
    if not cards or len({(c['productId'],c['printing'],c['language']) for c in cards})!=len(cards): raise ValueError('Duplicate printing')
    days=_days(root)
    if not days: raise ValueError('No observations')
    t30_path=root/'data/market-cache/thirtieth-current.json'
    t30={c['productId']:c for c in json.loads(t30_path.read_text())['cards']} if t30_path.exists() else {}
    out=[]
    for c in cards:
        ident={k:c[k] for k in ['productId','groupId','name','set','number','language','printing','image']}
        shared=t30.get(int(c['productId'])) or t30.get(str(c['productId']))
        if shared:
            pts=shared['points']
            if any(p.get('usd') is not None and not _positive(p.get('usd')) for p in pts): raise ValueError(f"Non-positive shared price for {c['productId']}")
            out.append({**ident,'points':pts}); continue
        url=f"https://tcgcsv.com/tcgplayer/3/{c['groupId']}/prices"; key=f"{c['productId']}|{c['printing']}"; pts=[]
        for day,obs,src,_ in days:
            o=obs.get(key); sha=src.get(url)
            if o is None or sha is None: continue
            if o['status']=='accepted' and _positive(o['amount']): p={'day':day,'usd':o['amount'],'status':'ok'}
            elif o['status']=='held' and _positive(o['amount']): p={'day':day,'usd':None,'status':'source_anomaly','reportedUsd':o['amount']}
            else: p={'day':day,'usd':None,'status':'no_price'}
            p.update(source=url,sourceSha256=sha); pts.append(p)
        if not pts: raise ValueError(f'No observations for {key}')
        out.append({**ident,'points':pts})
    day,_,_,build_at=days[-1]
    b=datetime.fromisoformat(str(build_at).replace('Z','+00:00'))
    if b.date().isoformat()!=day: raise ValueError('Source build date mismatch')
    cache=dict(schemaVersion=1,index=index,sourceSystem='shared-cards-market-cache',grade='Raw',currency='USD',measure='tcgcsv_market',
               sourceDate=day,sourceBuildAt=b.isoformat(),expiresAt=(b+timedelta(hours=48)).isoformat(),cards=out)
    return _check(cache)

def write_all(root):
    root=Path(root); written=[]
    folder=root/'data/market-rosters'
    if not folder.is_dir(): return written
    for f in sorted(folder.glob('*.json')):
        label='?'
        try:
            roster=json.loads(f.read_text())
            label=roster.get('index','?')
            cache=build(root,roster)
            dest=root/'data/market-cache'/f"{cache['index']}-current.json"
            if dest.name=='thirtieth-current.json' or dest.parent!=root/'data/market-cache': raise ValueError('Refusing to rewrite the 30th Anniversary cache')
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(cache,separators=(',',':'),sort_keys=True,allow_nan=False)+'\n')
            written.append(str(dest.relative_to(root)))
        except (ValueError,KeyError,OSError,TypeError) as exc:
            # Never block the public refresh; the DB keeps the last valid prices
            # and dates when an index cache is missing or expired.
            print(f"index cache skipped for {label}: {exc}")
    return written

if __name__=='__main__':
    import sys; print('\n'.join(write_all(sys.argv[1] if len(sys.argv)>1 else '.')))
