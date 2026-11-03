"""Build the public-only market payload from reviewed, separately staged inputs."""
from pathlib import Path
import argparse, datetime as dt, hashlib, json, shutil, math

parser=argparse.ArgumentParser()
parser.add_argument('review_directory',type=Path)
parser.add_argument('--allow-incomplete-preview',action='store_true')
args=parser.parse_args();review=args.review_directory;root=Path(__file__).resolve().parents[1]
roster=json.loads((review/'membership-working.json').read_text())
history=json.loads((review/'history-research/raw-history.json').read_text())
images=json.loads((review/'image-provenance.public.json').read_text())
assert len(roster)==100 and len({c['product_id'] for c in roster})==100
assert history['roster_sha256']==hashlib.sha256((review/'membership-working.json').read_bytes()).hexdigest()
if history['missing_archive_dates'] and not args.allow_incomplete_preview:
    raise SystemExit('History retrieval is incomplete; refusing a public-ready payload.')
old=(root/'catalogue.js').read_text();old=json.loads(old[old.index('=')+1:].strip().rstrip(';'))
previous={c['id']:c for c in old['cards']}
art={c['rank']:c for c in images['cards']}
start=dt.date.fromisoformat(history['date_range']['from']);end=dt.date.fromisoformat(history['date_range']['to'])
dates=[(start+dt.timedelta(days=i)).isoformat() for i in range((end-start).days+1)]
assert dates[0]=='2026-01-01' and dates[-1]=='2026-11-02', 'This reviewed v1 importer is frozen; a later date requires an explicit new release version.'
prices={};cards=[]
for c in roster:
    record=history['cards'][str(c['id'])]
    assert record['product_id']==c['product_id'] and record['group_id']==c['group_id']
    assert record['release_date']==c['release_date'] and record['printing']=='Holofoil'
    assert len({o['date'] for o in record['observations']})==len(record['observations'])
    observations={o['date']:o['amount'] for o in record['observations']}
    values=[observations.get(d) if d>=c['release_date'] else None for d in dates]
    assert all(v is None or isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0 for v in values)
    prices[str(c['id'])]=values
    a=art[c['id']];assert a['number']==c['number']
    for f in a['files'].values():
        source=review/'image-assets'/f['file'];assert hashlib.sha256(source.read_bytes()).hexdigest()==f['sha256']
        shutil.copyfile(source,root/'assets'/f['file'])
    q={};amount=values[-1]
    if amount:
        q['Raw']={'price':amount,'currency':'USD','date':dates[-1],'source':c['source'],
            'provider':'TCGplayer market via TCGCSV','method':'Exact English catalogue issue and Holofoil printing. Combined-condition market guide; not a Near Mint-only sale, available offer or net profit.','count':None}
    card={'id':c['id'],'name':c['name'],'set':c['set'],'number':c['number'],'language':'English','rarity':c['rarity'],
        'releaseDate':c['release_date'],'productId':c['product_id'],'groupId':c['group_id'],'printing':'Holofoil',
        'image':'assets/'+a['files']['low']['file'],'imageLarge':'assets/'+a['files']['high']['file'],
        'imageProvider':a['image_provider'],'imageSource':a['source_metadata_url'],
        'origin':c['origin'],'membershipReason':c['membership_reason'].replace('owner-selected original90','original curated 90'),'quotes':q,
        'sources':previous.get(c['id'],{}).get('sources',{}) | {'Raw':c['source']}}
    cards.append(card)
# The one unpriced USD issue has a separately identified European guide. Never feed it to the USD index.
alt=json.loads((review/'source-catalogue/empoleon-tcgdex.json').read_text())
assert alt['id']=='bw9-117' and alt['thirdParty']['tcgplayer']==85203
cm=alt['pricing']['cardmarket'];emp=next(c for c in cards if c['productId']==85203)
if not emp['quotes'].get('Raw') and cm.get('trend'):
    emp['quotes']['Raw']={'price':cm['trend'],'currency':'EUR','date':cm['updated'][:10],
        'source':'https://api.tcgdex.net/v2/en/cards/bw9-117','provider':'Cardmarket trend via TCGdex',
        'method':'European mixed-condition/language trend for this issue. Separate from TCGplayer USD; excluded from the USD benchmark. No currency conversion or historical splice.','count':None}
    emp['usdGap']='TCGplayer has no current market row for this exact issue. Its historical USD observations remain visible; the current EUR reference is separate.'
anomaly_date='2026-10-07'
assert prices['3'][dates.index(anomaly_date)]==5, 'Reviewed anomaly receipt changed; stop for review.'
exclusions=[{'cardId':3,'date':anomaly_date,'reportedValue':5,'currency':'USD','reason':'Isolated $5 source quote immediately followed by $1,702.50; held from charts and returns as a source anomaly, not a verified market move.','reviewedOn':'2026-11-03','source':'https://tcgcsv.com/archive/tcgplayer/prices-2026-10-07.ppmd.7z'}]
next(c for c in cards if c['id']==3)['historyNote']='7 Oct: anomalous $5 source quote held out of charts and returns. The original receipt is retained under Evidence.'
captured=history['retrieved_at']
release={'version':'modern100-raw-v1','published':'2026-11-03','sourceDate':dates[-1],'retrievedAt':captured,
    'memberCount':100,'usdPrices':sum(c['quotes'].get('Raw',{}).get('currency')=='USD' for c in cards),
    'rawReferences':sum('Raw' in c['quotes'] for c in cards),'images':100,
    'historyStart':dates[0],'historyEnd':dates[-1],'archiveDays':history['complete_archive_days'],
    'expectedDays':len(dates),'incompleteArchiveDates':history['missing_archive_dates'],
    'gradedStatus':'Pending by owner direction, 3 November 2026',
    'basis':'Retrospective research of the current selected basket; not a fund, buy list or point-in-time trading strategy.'}
payload={'cards':cards,'logo':'assets/logo.png','family':'assets/family.png','captured':captured,
    'coverage':{'Raw':release['rawReferences'],'PSA 9':0,'PSA 10':0},'release':release}
(root/'catalogue.js').write_text('window.MODERN_PREVIEW_DATA='+json.dumps(payload,separators=(',',':'),ensure_ascii=False)+';\n')
cohorts={'january':{'id':'bt-public-modern100-raw-v1-complete-year','rule':'Every daily USD observation present for 1 January to 2 November 2026; retrospectively selected and fixed.','members':[c['id'] for c in cards if c['releaseDate']<=dates[0] and all(prices[str(c['id'])])]},'current':{'id':'bt-public-modern100-raw-v1-nov','members':[c['id'] for c in cards if c['quotes'].get('Raw',{}).get('currency')=='USD' and prices[str(c['id'])][-1]]}}
release['cohorts']=cohorts
release['historyQuality']={'reportedPrices':29259,'sourceGaps':277,'sourceAnomaliesHeld':1,'fullYearMembers':len(cohorts['january']['members']),'jan1PricedMembers':87,'jan1MembersExcludedForGaps':[1,9,19,45,64],'all100BaselineAvailable':False}
assert len(cohorts['january']['members'])==82
payload['release']=release
(root/'catalogue.js').write_text('window.MODERN_PREVIEW_DATA='+json.dumps(payload,separators=(',',':'),ensure_ascii=False)+';\n')
hist={'exclusions':exclusions,'cohorts':cohorts,'dates':dates,'prices':prices,'source':'TCGplayer market via TCGCSV','currency':'USD',
    'archivePattern':'https://tcgcsv.com/archive/tcgplayer/prices-{date}.ppmd.7z'}
(root/'market-history.js').write_text('window.BT_HISTORY='+json.dumps(hist,separators=(',',':'))+';\n')
(root/'market-release.json').write_text(json.dumps(release,indent=2)+'\n')
sources={'provider':'TCGCSV / TCGplayer','printing':'Holofoil','currency':'USD','condition':'Combined guide','archives':[{'date':d,'url':a['source_url'],'sha256':a['sha256'],'bytes':a['bytes']} for d,a in sorted(history['archives'].items()) if a.get('sha256')]}
(root/'market-sources.json').write_text(json.dumps(sources,indent=2)+'\n')
(root/'image-sources.json').write_text(json.dumps(images,indent=2)+'\n')
for file in ['TCGDEX-LICENSE.txt','SOURCE-NOTICE.txt']:shutil.copyfile(review/'image-assets'/file,root/'assets'/file)
print(json.dumps(release,indent=2))
