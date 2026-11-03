from pathlib import Path
from bs4 import BeautifulSoup
import json, html, shutil, hashlib
from xml.sax.saxutils import escape
P=Path(__file__).resolve().parents[1];D=P/'dist';BASE='https://buytrigger.cards/'
# Existing item IDs remain stable across the custom-domain move.
FEED_GUID_BASE='https://dralexkoh.github.io/buytrigger-card-desk/'
BRAND='BuyTrigger.Cards';BYLINE='Alex & Oscar'
if D.exists():shutil.rmtree(D)
D.mkdir()
FILES=['index-refinement.css','card-art.js','homepage.css','typography.css','CNAME','analytics.js','analytics-config.json','index.html','tcg-modern-index.html','site.css','header.css','social.css','site.js','social.js','modern.css','modern.js','catalogue.js','editorial.js','market-engine.js','market-history.js','market-release.json','image-sources.json','market-sources.json','top-50.html','top50.css','top50.js','top50-data.js','top50-feature.js','top50-release.json','top50-sources.json','top50-image-sources.json','refresh-status.js','refresh-status.json']
for name in FILES:shutil.copy2(P/name,D/name)
shutil.copytree(P/'assets',D/'assets')
# Public, immutable collector receipts only; no operational state or private files.
refresh=P/'data'/'refresh'
if refresh.exists():
 for folder in ['receipts','observations','review']:
  for receipt in (refresh/folder).rglob('*.json'):
   target=D/receipt.relative_to(P);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(receipt,target)
e=json.loads((P/'editorial.json').read_text())
featured=next(a for a in e['articles'] if a['slug']==e.get('featuredArticle','psa-value-returns'))
assert featured.get('image') and (P/featured['image']).is_file(), 'Featured story needs real editorial artwork'
for a in e['articles']:
 soup=BeautifulSoup((P/'index.html').read_text(),'html.parser');soup.body['data-route']='read/'+a['slug'];soup.head.insert(0,soup.new_tag('base',href='../../'))
 soup.title.string=a['title']+' · '+BRAND;url=BASE+'stories/'+a['slug']+'/'
 soup.select_one('link[rel=canonical]')['href']=url
 for key,val in [('og:title',a['title']+' · '+BRAND),('og:description',a['summary']),('og:url',url),('og:type','article')]:soup.select_one('meta[property="'+key+'"]')['content']=val
 soup.select_one('meta[name=description]')['content']=a['summary']
 picture=a.get('image') or ('assets/family.png' if a['slug']=='welcome' else 'assets/japan.jpg' if a['slug']=='japanese-card-research' else 'assets/family.png')
 soup.select_one('meta[property="og:image"]')['content']=BASE+picture
 schema=soup.new_tag('script',type='application/ld+json');schema.string=json.dumps({'@context':'https://schema.org','@type':'Article','headline':a['title'],'description':a['summary'],'datePublished':'2026-11-03','dateModified':'2026-11-03','author':{'@type':'Organization','name':BYLINE},'publisher':{'@type':'Organization','name':BRAND},'mainEntityOfPage':url,'image':BASE+picture},ensure_ascii=False).replace('</','<\\/');soup.head.append(schema)
 main=soup.select_one('main');main.clear()
 content=f'<header class="reading-head"><a class="back-link" href="index.html#journal">← Back to features</a><span class="kicker red-text">{html.escape(a["eyebrow"])}</span><h1>{html.escape(a["title"])}</h1><p>{html.escape(a["summary"])}</p><p>Alex &amp; Oscar · BuyTrigger.Cards · Published 3 November 2026'+ (' · Source story '+a['sourcePublishedAt'] if a.get('sourcePublishedAt') else '')+'</p></header>'
 content+=f'<figure class="reading-image"><div class="story-cover"><img src="{picture}" style="object-fit:contain;background:#fff" alt="{html.escape(a.get("imageAlt",a["title"]))}"></div></figure><div class="reading-layout"><article class="article-body">'
 for sec in a['sections']:content+=f'<section><h2>{html.escape(sec["heading"])}</h2>{sec["html"]}</section>'
 content+='<div class="source-box"><h3>Sources &amp; reading notes</h3>'+''.join(f'<a href="{html.escape(s["url"])}" rel="noopener noreferrer">{html.escape(s["label"])} ↗</a>' for s in a['sources'])+'</div><a class="btn red" href="index.html#journal">More features →</a></article></div>'
 main.append(BeautifulSoup(content,'html.parser'));folder=D/'stories'/a['slug'];folder.mkdir(parents=True);(folder/'index.html').write_text(str(soup))
urls=[BASE,BASE+'tcg-modern-index.html',BASE+'top-50.html']+[BASE+'stories/'+a['slug']+'/' for a in e['articles']]
(D/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(u)+'</loc><lastmod>2026-11-03</lastmod></url>'for u in urls)+'</urlset>')
(D/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+BASE+'sitemap.xml\n')
items=''.join('<item><title>'+escape(a['title'])+'</title><link>'+BASE+'stories/'+a['slug']+'/</link><guid>'+FEED_GUID_BASE+'stories/'+a['slug']+'/</guid><pubDate>Tue, 03 Nov 2026 00:00:00 GMT</pubDate><description>'+escape(a['summary'])+'</description></item>'for a in e['articles'])
(D/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>BuyTrigger.Cards — Newsroom by Alex &amp; Oscar</title><link>'+BASE+'</link><description>Free news and practical card collecting research.</description><language>en-gb</language>'+items+'</channel></rss>')
(D/'404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found · BuyTrigger.Cards</title><body style="background:#f7f5ef;color:#171719;font-family:Arial;padding:10vw"><h1>That card slipped out of the binder.</h1><p>This page could not be found.</p><a style="color:#c01922" href="'+BASE+'">Back to BuyTrigger.Cards →</a></body></html>')
(D/'.nojekyll').write_text('')
# Content fingerprints prevent a cached old script/style from pairing with a
# newer daily price edition. Source HTML remains readable and build-independent.
for document in D.rglob('*.html'):
 soup=BeautifulSoup(document.read_text(),'html.parser')
 base=(document.parent/'../../').resolve() if soup.select_one('base') else document.parent
 for tag in soup.select('script[src],link[rel=stylesheet][href]'):
  attribute='src' if tag.name=='script' else 'href'
  value=tag[attribute]
  if value.startswith(('http:','https:','//','data:')):continue
  relative=value.split('?',1)[0].split('#',1)[0]
  resource=base/relative
  if not resource.is_file():raise ValueError('Missing public script/style: '+relative)
  tag[attribute]=relative+'?v='+hashlib.sha256(resource.read_bytes()).hexdigest()[:16]
 document.write_text(str(soup))
print(f'Built {len(list(D.rglob("*")))} public files/directories. Ten articles, RSS, sitemap and research page.')
