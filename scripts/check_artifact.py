from pathlib import Path
import xml.etree.ElementTree as ET
import re,json,math,hashlib,os
from bs4 import BeautifulSoup
p=Path(__file__).resolve().parents[1];d=Path(os.environ.get('BT_CARD_DESK_ARTIFACT_DIR',p/'dist'));fail=[]
PUBLIC_BASE='https://buytrigger.cards/'
shared=json.loads((d/'shared-market-config.json').read_text())
assert set(shared)=={'schemaVersion','enabled','endpoint'} and shared['schemaVersion']==1 and isinstance(shared['enabled'],bool)
APPROVED_MARKET='https://ukblxmvsqihnnyysvxes.supabase.co/functions/v1/card-market-view'
set_release=json.loads((d/'thirtieth-release.json').read_text())
assert set_release['constituentCount']==set_release['imageReviewCount']==191 and set_release['sourceSystem']=='shared-cards-market'
assert set_release['grade']=='Raw' and set_release['measure']=='tcgcsv_market' and set_release['baselineDate']=='2026-10-08'
assert set_release['providerTerms']=='https://tcgcsv.com/faq'
if shared['enabled']:
 assert shared['endpoint']==APPROVED_MARKET and set_release['status']=='live' and set_release['publicReadVerified'] is True
 assert re.fullmatch('[a-f0-9]{64}',set_release['sourceVersion'])
else:assert shared['endpoint'] is None

targets=json.loads((d/'public-targets-config.json').read_text())
assert set(targets)=={'schemaVersion','enabled','endpoint','review'}
assert targets['schemaVersion']==1 and targets['enabled'] is False and targets['endpoint'] is None, 'Enable the feed only after the reviewed shared Cards release'
review=targets['review']
assert set(review)=={'checkedAt','listingsChecked','findings','psaUpside'} and re.fullmatch(r'\d{4}-\d{2}-\d{2}',review['checkedAt'])
assert set(review['findings'])=={'en','ja'} and all(
    isinstance(lines,list) and 1<=len(lines)<=3 and
    all(isinstance(line,str) and line.strip() and len(line)<=280 for line in lines)
    for lines in review['findings'].values()
)
assert set(review['listingsChecked'])=={'en','ja'} and all(type(v) is int and 0<v<=500 for v in review['listingsChecked'].values())
for card in review['psaUpside']:
 assert re.fullmatch(r'assets/public-targets/[a-z0-9_-]+\.webp',card['image']) and (d/card['image']).is_file()
 assert card['psa10Minor']>card['rawMinor']+card['gradingMinor']>0
APPROVED_TARGET_READER='https://ukblxmvsqihnnyysvxes.supabase.co/functions/v1/public-card-targets'
assert (d/'CNAME').read_text()=='buytrigger.cards\n', 'Wrong public domain contract'
APPROVED_COLLECTOR='https://brzawmbpwkdundruicca.supabase.co/functions/v1/cards-traffic-ingest'
analytics=json.loads((d/'analytics-config.json').read_text())
assert set(analytics)=={'schemaVersion','enabled','provider','collectorEndpoint','privacyReviewed','consentVersion','origins','campaigns','campaignSources','campaignMediums','campaignContent'}
assert analytics['schemaVersion']==1 and analytics['provider']=='buytrigger-crm'
assert analytics['collectorEndpoint']==APPROVED_COLLECTOR
assert isinstance(analytics['enabled'],bool) and isinstance(analytics['privacyReviewed'],bool)
assert not analytics['enabled'] or analytics['privacyReviewed']
assert {(site['origin'],site['basePath']) for site in analytics['origins']}=={
 ('https://buytrigger.cards','/'),('https://www.buytrigger.cards','/'),
 ('https://dralexkoh.github.io','/buytrigger-card-desk/')}
for f in d.rglob('*'):
 if not f.is_file():continue
 if re.search(r' \d+(?:\.|$)',f.name):fail.append(f'Unexpected duplicate generated filename: {f.relative_to(d)}')
 if any(x in f.name.lower() for x in ['owner','backup','research.json','.env','.map','traffic-preview']):fail.append(str(f))
 if f.suffix not in ['.html','.js','.css','.json','.xml','.txt','.svg']:continue
 s=f.read_text()
 if f.name=='public-targets.js':
  s=s.replace(APPROVED_TARGET_READER,'https://approved-public-target-reader.invalid')
 if f.name=='shared-market-config.json':
  s=s.replace(APPROVED_MARKET,'https://approved-public-market.invalid')
 if f.name in ['analytics.js','analytics-config.json']:
  s=re.sub(re.escape(APPROVED_COLLECTOR)+r'''(?=['"\s<>]|$)''','https://approved-public-card-traffic-collector.invalid',s)
 for pattern in [r'/Users/',r'/var/folders/',r'ACQI?-\d{6}',r'CT-\d{6}',r'TGT-\d{6}',r'eyJ[a-zA-Z0-9_-]{30}',r'gh[pousr]_[a-zA-Z0-9]{20}',r'supabase\.co\b',r'(?i)service_role',r'(?i)unpublished draft',r'(?i)local full-site preview']:
  if re.search(pattern,s):fail.append(f'{f.relative_to(d)}: {pattern}')
 if f.suffix=='.html':
  soup=BeautifulSoup(s,'html.parser');base=(f.parent/'../../').resolve()if soup.select_one('base') else f.parent
  for t in soup.select('script[src],link[href],img[src]'):
   v=t.get('src')or t.get('href')
   if not v or v.startswith(('http:','https:','data:','#')):continue
   if not (base/v.split('#')[0].split('?')[0]).exists():fail.append(f'{f.relative_to(d)}: missing {v}')
  if not soup.title:fail.append(f'{f}: missing title')
  if f.name!='404.html':
   relative=str(f.relative_to(d));route='' if relative=='index.html' else relative.removesuffix('index.html') if relative.startswith('stories/') else relative
   expected=PUBLIC_BASE+route
   canonical=soup.select_one('link[rel=canonical]');og=soup.select_one('meta[property="og:url"]');picture=soup.select_one('meta[property="og:image"]')
   if not canonical or canonical.get('href')!=expected:fail.append(f'{relative}: wrong canonical URL')
   if not og or og.get('content')!=expected:fail.append(f'{relative}: wrong sharing URL')
   if not picture or not picture.get('content','').startswith(PUBLIC_BASE):fail.append(f'{relative}: wrong sharing picture origin')
   if 'https://dralexkoh.github.io/buytrigger-card-desk/' in s:fail.append(f'{relative}: old public domain in page')
   for tag in soup.select('script[type="application/ld+json"]'):
    structured=json.loads(tag.string)
    if structured.get('@type')=='Article' and (structured.get('mainEntityOfPage')!=expected or not structured.get('image','').startswith(PUBLIC_BASE)):
     fail.append(f'{relative}: wrong article metadata domain')
  analytics_tags=[tag for tag in soup.select('script[src]') if tag['src'].split('?',1)[0]=='analytics.js']
  if f.name!='404.html' and len(analytics_tags)!=1:fail.append(f'{f.relative_to(d)}: expected exactly one optional analytics client')
site_map=ET.fromstring((d/'sitemap.xml').read_text())
assert all(node.text.startswith(PUBLIC_BASE) for node in site_map.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc'))
feed=ET.fromstring((d/'rss.xml').read_text())
assert all(node.text.startswith(PUBLIC_BASE) for node in feed.iter('link'))
# Stable legacy GUIDs identify existing feed items; they are not current links.
assert all(node.text.startswith('https://dralexkoh.github.io/buytrigger-card-desk/stories/') for node in feed.iter('guid'))
assert 'Sitemap: '+PUBLIC_BASE+'sitemap.xml' in (d/'robots.txt').read_text()
assert PUBLIC_BASE in (d/'404.html').read_text()
cat=(d/'catalogue.js').read_text();data=json.loads(cat[cat.index('=')+1:].strip().rstrip(';'))
assert len(data['cards'])==100
assert all(set(c['quotes'])<= {'Raw'} for c in data['cards'])
assert all((d/c['image']).exists() for c in data['cards'])
assert all((d/c['imageLarge']).exists() for c in data['cards'])
assert len({c['productId'] for c in data['cards']})==100
image_sources=json.loads((d/'image-sources.json').read_text())
assert len(image_sources['cards'])==100
for card in image_sources['cards']:
 for f in card['files'].values():
  assert hashlib.sha256((d/'assets'/f['file']).read_bytes()).hexdigest()==f['sha256']
release=json.loads((d/'market-release.json').read_text())
assert release.get('refreshStatus') in (None,'current','partial','delayed','failed')
assert release['archiveDays'] <= release.get('historyDays',release['expectedDays'])
hs=(d/'market-history.js').read_text();hist=json.loads(hs[hs.index('=')+1:].strip().rstrip(';'))
assert len(hist['dates'])==release.get('historyDays',release['expectedDays'])
assert hist['dates']==sorted(set(hist['dates']))
assert hist['dates'][-1]==release['historyEnd']==release['sourceDate']
sources=json.loads((d/'market-sources.json').read_text())
assert len(sources['archives'])==release['archiveDays']
source_dates={a['date'] for a in sources['archives']} | {a['date'] for a in sources.get('dailyReceipts',[])}
assert set(hist['dates'])==source_dates | set(release['incompleteArchiveDates'])
assert not source_dates.intersection(release['incompleteArchiveDates'])
assert all(re.fullmatch('[a-f0-9]{64}',a['sha256']) for a in sources['archives'])
for cohort in hist['cohorts'].values():
 assert len(cohort['members'])==len(set(cohort['members']))
 assert all(member in {c['id'] for c in data['cards']} for member in cohort['members'])
for c in data['cards']:
 values=hist['prices'][str(c['id'])]
 assert len(values)==len(hist['dates'])
 assert all(v is None for date,v in zip(hist['dates'],values) if date<c['releaseDate'])
 assert all(v is None or isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0 for v in values)
editorial=json.loads((p/'editorial.json').read_text())
assert {f.parent.name for f in (d/'stories').glob('*/index.html')}=={a['slug'] for a in editorial['articles']}
for article in editorial['articles']:
 page=BeautifulSoup((d/'stories'/article['slug']/'index.html').read_text(),'html.parser')
 schema=next(json.loads(t.string) for t in page.select('script[type="application/ld+json"]') if json.loads(t.string).get('@type')=='Article')
 assert schema['datePublished']==article.get('publishedAt',editorial['publishedAt'])
 if article.get('author',{}).get('type') in ('person','family'):
  declared=article['author'];ids=declared['members'] if declared['type']=='family' else [declared['id']]
  expected=[{'alex-koh':'Alex Koh','oscar':'Oscar'}[i] for i in ids]
  actual=schema['author'] if isinstance(schema['author'],list) else [schema['author']]
  assert [x['name'] for x in actual]==expected and all(x['@type']=='Person' for x in actual)
  assert page.select_one('.person-byline')
  for author_id in ids:assert page.select_one('#author-'+author_id)
 else:assert schema['author']['@type']=='Organization'
bluechip=json.loads((d/'bluechip-data.js').read_text().split('=',1)[1].strip().rstrip(';'))
assert bluechip['rankingGrade']=='PSA 10' and bluechip['constituentCount']==50
bluechip_page=BeautifulSoup((d/'top-50.html').read_text(),'html.parser')
assert bluechip_page.select_one('#card-gallery')
assert bluechip_page.select_one('script[src^="bluechip-collection-data.js"]')
assert bluechip_page.select_one('a[href="bluechip-raw-archive.html"]')
archive_page=BeautifulSoup((d/'bluechip-raw-archive.html').read_text(),'html.parser')
assert archive_page.select_one('script[src^="top50-data.js"]')
if bluechip['status']!='released':assert bluechip['cards']==[]
collection=json.loads((d/'bluechip-collection-data.js').read_text().split('=',1)[1].strip().rstrip(';'))
collection_sources=json.loads((d/'bluechip-collection-sources.json').read_text())
selected=collection_sources['selection']
curated=collection['cards']
assert len(curated)==len(selected)==len({(c['productId'],c['printing']) for c in curated})==50
assert [c['id'] for c in curated]==list(range(1,51))
assert all(c['year']<2019 for c in curated[:44]) and all(c['year']>=2019 for c in curated[44:])
assert collection['release']['selectionDate']==collection_sources['selectionDate']=='2026-11-04'
collection_history=collection['history']
assert collection_history['cohorts']['history']['members']==[3,4,5,41,44]
assert collection_history['cohorts']['current']['members']==[c['id'] for c in curated]
collection_days=collection_history['dates']
assert collection_days==sorted(set(collection_days))
assert collection_days[-1]==collection['release']['sourceDate']
held={(e['cardId'],e['date']) for e in collection_history['exclusions']}
for card,reviewed in zip(curated,selected):
 assert all(card[k]==reviewed[k] for k in ('id','productId','groupId','name','number','set','printing','year','language','image','imageSource'))
 assert card['language']=='English' and card['imageExactPrinting'] and card['imageLarge']==card['image']
 assert hashlib.sha256((d/card['image']).read_bytes()).hexdigest()==reviewed['imageSha256']
 values=collection_history['prices'][str(card['id'])]
 assert len(values)==len(collection_days)
 assert all(value is None or type(value) in (float,int) and math.isfinite(value) and value>0 for value in values)
 valid=[(day,value) for day,value in zip(collection_days,values) if value is not None and (card['id'],day) not in held]
 quote=card['quotes'].get('Raw')
 assert set(card['quotes'])<= {'Raw'}
 assert (quote is not None)==bool(valid)
 if quote:assert quote['currency']=='USD' and (quote['date'],quote['price'])==valid[-1]
toptext=(d/'top50-data.js').read_text();top=json.loads(toptext.split('=',1)[1].strip().rstrip(';'))
assert len(top['cards'])==50
assert len({(c['productId'],c['printing']) for c in top['cards']})==50
assert all(set(c['quotes'])=={'Raw'} and c['quotes']['Raw']['currency']=='USD' for c in top['cards'])
assert top['release']['rankingProof']['unresolvedPositiveRowsAtOrAboveRank50']==0
assert len(top['history']['dates'])==top['release'].get('historyDays',top['release']['archiveCount'])
assert top['history']['dates']==sorted(set(top['history']['dates']))
assert top['history']['dates'][-1]==top['release']['historyEnd']==top['release']['sourceDate']
assert top['history']['dates'][0]=='2024-02-08'
ts=json.loads((d/'top50-sources.json').read_text())
assert len(ts['archives'])==top['release']['archiveCount']
top_source_dates={a['date'] for a in ts['archives']} | {a['date'] for a in ts.get('dailyReceipts',[])}
assert set(top['history']['dates'])==top_source_dates | set(top['release']['incompleteArchiveDates'])
assert not top_source_dates.intersection(top['release']['incompleteArchiveDates'])
assert all(re.fullmatch('[a-f0-9]{64}',a['sha256']) for a in ts['archives'])
ti=json.loads((d/'top50-image-sources.json').read_text())
assert len(ti['cards'])==50 and 'pending' not in ti['status'].lower()
assert 'reports/' not in (d/'top50-image-sources.json').read_text()
for c in ti['cards']:
 for f in c['files'].values():
  assert hashlib.sha256((d/f['publicPath']).read_bytes()).hexdigest()==f['sha256']
for c in top['cards']:
 assert (d/c['image']).exists() and (d/c['imageLarge']).exists() and c['imageNote']
 assert c['rank']==c['id'] and c['language']=='English'
 assert len(top['history']['prices'][str(c['id'])])==len(top['history']['dates'])
 for date,value in zip(top['history']['dates'],top['history']['prices'][str(c['id'])]):
  assert value is None or isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0
  assert value is None or not c.get('releaseDate') or date>=c['releaseDate']
for history,source_manifest in [(hist,sources),(top['history'],ts),(collection_history,collection_sources)]:
 for day,path in history.get('sourceReceipts',{}).items():
  assert day in history['dates'] and re.fullmatch(r'data/refresh/receipts/[a-zA-Z0-9_.-]+\.json',path)
  receipt=json.loads((d/path).read_text())
  assert receipt['sourceDate']==day and receipt['observationSha256']
  matches=list((d/'data/refresh/observations'/day).glob('*.json'))
  assert any(hashlib.sha256(f.read_bytes()).hexdigest()==receipt['observationSha256'] for f in matches)
 for item in source_manifest.get('dailyReceipts',[]):
  assert history.get('sourceReceipts',{}).get(item['date'])==item['receipt']
status=json.loads((d/'refresh-status.json').read_text())
assert status['schemaVersion']==1 and status['status'] in ['current','partial','delayed','failed']
assert status['sourceDate']==release['sourceDate']==top['release']['sourceDate']
assert status['sourceDate']==collection['release']['sourceDate']
assert not (d/'data/refresh/state.json').exists()
if fail:raise SystemExit('\n'.join(fail))
print('PASS: public-only artifact; Modern100 + preserved Raw50 archive; PSA10 publication gate, explicit withheld artwork, complete declared archive retrieval, explicit price gaps, no private records/secrets/graded dataset; all declared article paths, dates and authors present.')
