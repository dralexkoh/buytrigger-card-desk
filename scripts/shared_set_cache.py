"""Rebuildable shared-DB input from the existing collector's fetched groups.

No network calls, credentials or private data. The shared Cards database imports
this output; the public set page reads that database, never this cache directly.
"""
from datetime import timedelta
import math

def positive(n):return isinstance(n,(int,float))and not isinstance(n,bool)and math.isfinite(n)and n>0

PROMOS = {713257:('107','Pikachu ex - 107 (30th Celebration)'),713258:('108','Espeon ex - 108 (30th Celebration)'),713256:('109','Pikachu ex - 109 (30th Celebration)'),713259:('110','Umbreon ex - 110 (30th Celebration)')}

def identities(catalogue):
    if catalogue.get('schemaVersion')!=1 or catalogue.get('index')!='thirtieth-anniversary':raise ValueError('Unexpected set catalogue')
    cards=catalogue['cards']
    if len(cards) not in (191,195) or len({(c['productId'],c['printing'])for c in cards})!=len(cards):raise ValueError('Expected 191 or 195 exact printings')
    if sum(c['groupId']==24722 for c in cards)!=161 or sum(c['groupId']==24837 for c in cards)!=30:raise ValueError('Incorrect set partition')
    promos = [c for c in cards if c['groupId']==24451]
    if len(promos)!=len(cards)-191 or {c['productId'] for c in promos} not in (set(),set(PROMOS)):raise ValueError('Incorrect four-promo membership')
    for c in cards:
        if c['groupId'] not in (24722,24837,24451):raise ValueError('Unreviewed source group')
        if c['groupId']==24451 and (c['number'],c['name'],c['set']) != (*PROMOS[c['productId']],'ME: Mega Evolution Promo'):raise ValueError('Promo identity changed')
        if c['language']!='English'or c['printing']!='Holofoil'or c['image']!=f"assets/thirtieth/{c['productId']}.jpg":raise ValueError('Unreviewed printing')
    return {str(c['productId'])+'|'+c['printing']:c for c in cards}

def build_cache(catalogue,groups,resources,build,prior=None,review=None):
    cards=identities(catalogue);by_group={int(r['url'].split('/')[-2]):r for r in resources if '/tcgplayer/3/'in r['url']}
    old={c['productId']:c for c in (prior or{}).get('cards',[])};out=[]
    for c in cards.values():
        group=groups.get(c['groupId'],groups.get(str(c['groupId'])));resource=by_group.get(c['groupId'])
        if group is None or resource is None:raise ValueError('Shared set group not collected')
        q=group.get(str(c['productId'])+'|'+c['printing']);n=q.get('marketPrice')if q else None
        if q and q.get('currency','USD')!='USD':raise ValueError('Unexpected shared source currency')
        if n is not None and not positive(n):raise ValueError('Invalid mixed-condition source value')
        previous=old.get(c['productId'],{});oldpoint=(previous.get('points')or[{}])[-1]
        last_good=previous.get('lastGoodUsd',oldpoint.get('usd'));last_day=previous.get('lastGoodDay',oldpoint.get('day'))
        recent=[(p[0],p[1])for p in previous.get('recentGood',[])if isinstance(p,list)and len(p)==2 and p[0]<build.date().isoformat()and positive(p[1])]
        if not recent and positive(last_good)and last_day and last_day<build.date().isoformat():recent=[(last_day,last_good)]
        held=bool(review(n,recent,build.date().isoformat()))if review else False
        point=dict(day=build.date().isoformat(),usd=None if held else n,status='source_anomaly'if held else'ok'if n else'no_price',source=resource['url'],sourceSha256=resource['sha256'])
        if held:point['reportedUsd']=n
        if positive(n)and not held:
            last_good,last_day=n,point['day'];recent.append((last_day,last_good))
        # A missed database import can replay the last seven observed days from
        # this one collector. Never manufacture observations for missing days.
        points={p['day']:p for p in previous.get('points',[])if p['day']<point['day']}
        points[point['day']]=point
        retained=[points[d]for d in sorted(points)[-7:]]
        out.append({**{k:c[k]for k in ['productId','groupId','name','set','number','language','printing','image']},'points':retained,'lastGoodUsd':last_good,'lastGoodDay':last_day,'recentGood':recent[-7:]})
    return dict(schemaVersion=1,index='thirtieth-anniversary',sourceSystem='shared-cards-market-cache',grade='Raw',currency='USD',measure='tcgcsv_market',sourceDate=build.date().isoformat(),sourceBuildAt=build.isoformat(),expiresAt=(build+timedelta(hours=48)).isoformat(),cards=out)
