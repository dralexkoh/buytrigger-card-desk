from pathlib import Path
from bs4 import BeautifulSoup
import json, html, shutil, hashlib, subprocess
from datetime import datetime, timezone
from email.utils import format_datetime
from editorial_visuals import validate_editorial_visuals
from xml.sax.saxutils import escape
import site_seo as seo
P=Path(__file__).resolve().parents[1];D=P/'dist';BASE='https://buytrigger.cards/'
# Existing item IDs remain stable across the custom-domain move.
FEED_GUID_BASE='https://dralexkoh.github.io/buytrigger-card-desk/'
BRAND='BuyTrigger.Cards';BYLINE='BuyTrigger Cards'
if D.exists():shutil.rmtree(D)
D.mkdir()
FILES=['public-targets.js','public-targets.css','public-targets-config.json','shared-market-engine.js','shared-market.js','shared-market.css','shared-market-config.json','article-authors.js','article-features.css','commerce.js','commerce.css','refinement.css','index-refinement.css','card-art.js','homepage.css','typography.css','CNAME','analytics.js','analytics-config.json','index.html','tcg-modern-index.html','site.css','header.css','social.css','site.js','social.js','modern.css','modern.js','catalogue.js','editorial.js','market-engine.js','market-history.js','market-release.json','image-sources.json','market-sources.json','top-50.html','top50.css','top50.js','top50-data.js','top50-feature.js','top50-release.json','top50-sources.json','top50-image-sources.json','refresh-status.js','refresh-status.json']
FILES+=['bluechip-raw-archive.html','bluechip-engine.js','bluechip.js','bluechip.css','bluechip-release.json']
FILES+=['bluechip-collection-data.js','bluechip-collection-sources.json']
FILES+=['grading-calculator.js','grading-calculator.css']
FILES+=['thirtieth-engine.js','thirtieth.js','thirtieth.css','thirtieth-catalogue.json','thirtieth-release.json']
for name in FILES:shutil.copy2(P/name,D/name)
bluechip=json.loads((P/'bluechip-release.json').read_text())
bluechip_check=json.loads(subprocess.check_output(['node','-e',"const fs=require('node:fs'),B=require('./bluechip-engine.js');const d=JSON.parse(fs.readFileSync('bluechip-release.json'));process.stdout.write(JSON.stringify(B.review(d)));"],cwd=P))
if bluechip.get('status')=='released' and not bluechip_check['published']:raise ValueError('BlueChip release held: '+'; '.join(bluechip_check['issues']))
public_bluechip=bluechip if bluechip_check['published'] else {k:bluechip[k] for k in ['status','asOf','sourceSystem','constituentCount','rankingGrade','rankingBasis','weightingMethod','performanceStatus']}
if not bluechip_check['published']:public_bluechip['cards']=[]
(D/'bluechip-data.js').write_text('window.BT_BLUECHIP='+json.dumps(public_bluechip,ensure_ascii=False).replace('</','<\\/')+';\n')
shutil.copytree(P/'assets',D/'assets')
shutil.copytree(P/'data/market-cache',D/'data/market-cache')
# Public, immutable collector receipts only; no operational state or private files.
refresh=P/'data'/'refresh'
if refresh.exists():
 for folder in ['receipts','observations','review']:
  for receipt in (refresh/folder).rglob('*.json'):
   target=D/receipt.relative_to(P);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(receipt,target)
drops=json.loads((P/'drops.json').read_text())
from validate_drops import validate_drops
validate_drops(drops,P)
(D/'drops.js').write_text('window.BT_DROPS='+json.dumps(drops,ensure_ascii=False)+';\n')
from drops_offers import validate_offers
commerce=json.loads((P/'commerce.json').read_text())
offers=json.loads((P/'drops-offers.json').read_text())
validate_offers(offers,commerce)
(D/'commerce-data.js').write_text('window.BT_COMMERCE='+json.dumps(commerce,ensure_ascii=False)+';\nwindow.BT_DROPS_OFFERS='+json.dumps(offers,ensure_ascii=False)+';\n')
e=json.loads((P/'editorial.json').read_text())
validate_editorial_visuals(e,P)
from build_tracking_catalogue import create_catalogue
traffic_catalogue=create_catalogue(e)
(D/'traffic-catalogue.json').write_text(json.dumps(traffic_catalogue,ensure_ascii=False)+'\n')
(D/'tracking-catalogue.js').write_text('window.BT_TRAFFIC_CATALOGUE='+json.dumps(traffic_catalogue,ensure_ascii=False).replace('</','<\\/')+';\n')
authors=json.loads(subprocess.check_output(['node',str(P/'scripts/render_article_authors.cjs')],input=json.dumps(e['articles']).encode()))
featured=next(a for a in e['articles'] if a['slug']==e.get('featuredArticle','psa-value-returns'))
assert featured.get('image') and (P/featured['image']).is_file(), 'Featured story needs real editorial artwork'
for a in e['articles']:
 soup=BeautifulSoup((P/'index.html').read_text(),'html.parser');soup.body['data-route']='read/'+a['slug'];soup.head.insert(0,soup.new_tag('base',href='../../'))
 soup.title.string=a['title']+' · '+BRAND;url=BASE+'stories/'+a['slug']+'/'
 soup.select_one('link[rel=canonical]')['href']=url
 for key,val in [('og:title',a['title']+' · '+BRAND),('og:description',a['summary']),('og:url',url),('og:type','article')]:soup.select_one('meta[property="'+key+'"]')['content']=val
 soup.select_one('meta[name=description]')['content']=a['summary']
 published=a.get('publishedAt',e['publishedAt']);modified=a.get('updatedAt',published)
 persons=[{'@type':'Person','name':person['name'],'url':url+'#author-'+person['id']} for person in authors[a['slug']]['people']]
 author=persons[0] if len(persons)==1 else persons if persons else {'@type':'Organization','name':BRAND}
 picture=a['image']
 image_schema,share_path,share_size=seo.schema_image(P,D,picture,kind='stories',slug=a['slug'],fallback_to_family=a['slug']=='welcome')
 seo.apply_share_tags(soup,url=url,title=a['title'],description=a['summary'],image=BASE+share_path,og_type='article')
 schema=seo.news_article_schema(headline=a['title'],url=url,date_published=published,date_modified=modified,image=image_schema,author=author,description=a['summary'])
 seo.set_json_ld(soup,schema)
 main=soup.select_one('main');main.clear()
 content=f'<header class="reading-head"><a class="back-link" href="index.html#journal">← Back to features</a><span class="kicker red-text">{html.escape(a["eyebrow"])}</span><h1>{html.escape(a["title"])}</h1><p>{html.escape(a["summary"])}</p>'+(authors[a['slug']]['byline'] or '<p>BuyTrigger Cards · Published '+html.escape(published)+(' · Source story '+html.escape(a['sourcePublishedAt']) if a.get('sourcePublishedAt') else '')+'</p>')+'</header>'
 cover_class = "story-cover full-image" if a.get("visualStyle") == "source-media-v1" else "story-cover"
 content+=f'<figure class="reading-image"><div class="{cover_class}"><img src="{picture}" style="object-fit:contain;background:#fff" alt="{html.escape(a["imageAlt"])}"></div><figcaption>{html.escape(a["imageCredit"])}</figcaption></figure><div class="reading-layout"><article class="article-body">'
 for sec in a['sections']:content+=f'<section><h2>{html.escape(sec["heading"])}</h2>{sec["html"]}</section>'
 content+=authors[a['slug']]['profile']
 content+='<div class="source-box"><h3>Sources &amp; reading notes</h3>'+''.join(f'<a href="{html.escape(s["url"])}" rel="noopener noreferrer">{html.escape(s["label"])} ↗</a>' for s in a['sources'])+'</div><a class="btn red" href="index.html#journal">More features →</a></article></div>'
 main.append(BeautifulSoup(content,'html.parser'));folder=D/'stories'/a['slug'];folder.mkdir(parents=True);(folder/'index.html').write_text(str(soup))
soup=BeautifulSoup((P/'index.html').read_text(),'html.parser');soup.body['data-route']='drops';soup.title.string='Drops · Release Calendar · BuyTrigger.Cards'
soup.select_one('link[rel=canonical]')['href']=BASE+'drops.html';soup.select_one('meta[property="og:url"]')['content']=BASE+'drops.html'
soup.select_one('meta[property="og:title"]')['content']='Drops · Release Calendar · BuyTrigger.Cards'
soup.select_one('meta[name=description]')['content']='Pokémon product release dates for the UK, US and Asia, with official sources and regional availability notes.'
soup.select_one('main').clear();soup.select_one('main').append(BeautifulSoup('<section class="page-intro"><h1>Pokémon release calendar</h1>'+''.join('<p>'+html.escape(x['title'])+' · '+x['date']+' · '+x['country']+' · <a href="'+x['sourceUrl']+'">Official source</a></p>' for x in drops['items'])+'</section>','html.parser'))
(D/'drops.html').write_text(str(soup))
for route, filename, title, description in [('calculator','grading-calculator.html','Grading Calculator','Compare selling a card raw with grading. Calculate what you keep, break-even sale prices and a buy limit for each grade.'),('market','market.html','Market','Explore the existing card benchmarks and set trackers.'),('thirtieth','30th-anniversary-index.html','30th Anniversary Index','Follow the 30th Celebration chases, numbered Pikachu, RGB Mews and four Day & Night promos, with a Top 20 Raw ranking and dated histories.')]:
 soup=BeautifulSoup((P/'index.html').read_text(),'html.parser');soup.body['data-route']=route
 soup.title.string=title+' · '+BRAND
 soup.select_one('link[rel=canonical]')['href']=BASE+filename
 soup.select_one('meta[property="og:url"]')['content']=BASE+filename
 soup.select_one('meta[property="og:title"]')['content']=title+' · '+BRAND
 soup.select_one('meta[name=description]')['content']=description
 soup.select_one('meta[property="og:description"]')['content']=description
 soup.select_one('main').clear();soup.select_one('main').append(BeautifulSoup('<section class="page-intro"><h1>'+title+'</h1><p>'+description+'</p></section>','html.parser'))
 (D/filename).write_text(str(soup))
targets=json.loads((P/'public-targets-config.json').read_text())
for route,filename,language,code in [('targets','undervalued.html','English','en'),('japan','undervalued-japanese.html','Japanese','ja')]:
 soup=BeautifulSoup((P/'index.html').read_text(),'html.parser');soup.body['data-route']=route
 title=f'Undervalued {language} cards';description=f'Reviewed {language} Pokémon card opportunities, with exact-printing checks, delivered prices and UK sales evidence.'
 soup.title.string=title+' · BuyTrigger.Cards'
 for tag,key,value in [('link[rel=canonical]','href',BASE+filename),('meta[property="og:url"]','content',BASE+filename),('meta[property="og:title"]','content',title+' · BuyTrigger.Cards'),('meta[property="og:description"]','content',description),('meta[name=description]','content',description)]:
  soup.select_one(tag)[key]=value
 r=targets['review'];n=r['listingsChecked'][code];day=r['checkedAt']
 examples=[card for card in r.get('psaUpside',[]) if card['language']==code]
 if examples:
  def gbp(value):return f'£{value/100:,.2f}'
  overview=''.join(
   f"<p>{html.escape(card['name'])} {html.escape(card['number'])} · PSA 10 scenario. "
   f"Raw {gbp(card['rawMinor'])} delivered + PSA grading {gbp(card['gradingMinor'])}. "
   f"PSA 10 sale {gbp(card['psa10Minor'])} on {html.escape(card['soldOn'])}, leaving {gbp(card['psa10Minor']-card['rawMinor']-card['gradingMinor'])} before grading postage and selling costs. "
   f"Raw and grading checked {html.escape(card.get('checkedAt',day))}.</p>"
   for card in examples)
 else:
  overview=''
 findings=r.get('findings',{}).get(code,[])
 findings_html=('<ul class="target-review-findings" aria-label="What held the picks back">'+
                ''.join(f'<li>{html.escape(line)}</li>' for line in findings)+'</ul>') if findings else ''
 soup.select_one('main').clear();soup.select_one('main').append(BeautifulSoup(f'<section class="page-intro"><h1>{title}</h1><h2>Dated PSA 10 scenarios</h2>{overview}<details><summary>Earlier downside review</summary><p>{n} listings checked on <time datetime="{day}">{day}</time>. No card passed that review.</p>{findings_html}</details><nav aria-label="Undervalued card language"><a href="undervalued.html">English cards</a> · <a href="undervalued-japanese.html">Japanese cards</a></nav></section>','html.parser'))
 (D/filename).write_text(str(soup))

# Indexable Card Desk / Newsroom pages. Hash URLs (#desk/<id>) keep working.
for w in e.get('wire',[]):
 if not seo.ID_RE.fullmatch(w['id']):raise ValueError('Unusable wire id for /news/ URL: '+w['id'])
 soup=BeautifulSoup((P/'index.html').read_text(),'html.parser');soup.body['data-route']='news/'+w['id'];soup.head.insert(0,soup.new_tag('base',href='../../'))
 url=seo.news_url(w['id'])
 published=w.get('date') or w.get('sourcePublishedAt') or e['publishedAt']
 modified=w.get('checkedAt') or published
 picture=w.get('image')
 image_schema,share_path,share_size=seo.schema_image(P,D,picture,kind='news',slug=w['id'])
 author_name=(w.get('author') or {}).get('name')
 author={ '@type':'Person','name':author_name } if author_name else { '@type':'Organization','name':BRAND }
 seo.apply_share_tags(soup,url=url,title=w['title'],description=w.get('summary') or w['title'],image=BASE+share_path,og_type='article')
 schema=seo.news_article_schema(headline=w['title'],url=url,date_published=published,date_modified=modified,image=image_schema,author=author,description=w.get('summary') or w['title'])
 seo.set_json_ld(soup,schema)
 main=soup.select_one('main');main.clear()
 byline=html.escape(author_name) if author_name else 'BuyTrigger.Cards'
 source=''
 if w.get('url') and w.get('sourceLabel'):
  source='<p class="news-source"><a href="'+html.escape(w['url'])+'" rel="noopener noreferrer">Source: '+html.escape(w['sourceLabel'])+' ↗</a></p>'
 paragraphs=''.join('<p>'+html.escape(part)+'</p>' for part in (w.get('summary') or '').split('\n\n') if part.strip())
 img=''
 if picture and not str(picture).startswith(('http://','https://','//')) and (P/picture).is_file():
  img=f'<figure class="reading-image"><div class="story-cover full-image"><img src="{html.escape(picture)}" alt="{html.escape(w.get("imageAlt") or w["title"])}" style="object-fit:contain;background:#fff"></div><figcaption>{html.escape(w.get("imageCredit") or "")}</figcaption></figure>'
 content=f'<header class="reading-head"><a class="back-link" href="index.html#desk">← Back to the newsroom</a><span class="kicker red-text">{html.escape(w.get("category") or "Newsroom")}</span><h1>{html.escape(w["title"])}</h1><p>{html.escape(w.get("summary") or "")}</p><p class="news-credit"><span class="news-author">{byline}</span> · {html.escape(w.get("kind") or "Newsroom")} · {html.escape(w.get("displayDate") or published)}</p></header>{img}<div class="reading-layout"><article class="article-body">{paragraphs}{source}<p class="small">This brief is also listed on the <a href="index.html#desk/{html.escape(w["id"])}">Card Desk</a>.</p><a class="btn red" href="index.html#desk">More from the newsroom →</a></article></div>'
 main.append(BeautifulSoup(content,'html.parser'));folder=D/'news'/w['id'];folder.mkdir(parents=True);(folder/'index.html').write_text(str(soup))

static_urls=[BASE,BASE+'grading-calculator.html',BASE+'undervalued.html',BASE+'undervalued-japanese.html',BASE+'market.html',BASE+'30th-anniversary-index.html',BASE+'drops.html',BASE+'tcg-modern-index.html',BASE+'top-50.html',BASE+'bluechip-raw-archive.html']
(D/'sitemap.xml').write_text(seo.urlset_xml(seo.collect_sitemap_entries(e,static_urls)))
(D/'news-sitemap.xml').write_text(seo.news_sitemap_xml(seo.collect_news_entries(e)))
(D/'robots.txt').write_text(seo.robots_txt())
items=''.join('<item><title>'+escape(a['title'])+'</title><link>'+BASE+'stories/'+a['slug']+'/</link><guid>'+FEED_GUID_BASE+'stories/'+a['slug']+'/</guid><pubDate>'+format_datetime(datetime.fromisoformat(a.get('publishedAt',e['publishedAt'])).replace(tzinfo=timezone.utc),usegmt=True)+'</pubDate><description>'+escape(a['summary'])+'</description></item>'for a in e['articles'])
(D/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>BuyTrigger.Cards — Newsroom</title><link>'+BASE+'</link><description>Free news and practical card collecting research.</description><language>en-gb</language>'+items+'</channel></rss>')
(D/'404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found · BuyTrigger.Cards</title><body style="background:#f7f5ef;color:#171719;font-family:Arial;padding:10vw"><h1>That card slipped out of the binder.</h1><p>This page could not be found.</p><a style="color:#c01922" href="'+BASE+'">Back to BuyTrigger.Cards →</a></body></html>')
(D/'.nojekyll').write_text('')
# Content fingerprints prevent a cached old script/style from pairing with a
# newer daily price edition. Source HTML remains readable and build-independent.
verification=seo.verification_token(P)
for document in D.rglob('*.html'):
 soup=BeautifulSoup(document.read_text(),'html.parser')
 if soup.head:
  seo.ensure_robots_preview(soup)
  og_title=soup.select_one('meta[property="og:title"]')
  og_description=soup.select_one('meta[property="og:description"]')
  og_image=soup.select_one('meta[property="og:image"]')
  if og_title and not soup.select_one('meta[name="twitter:title"]'):
   seo.upsert_meta(soup,attr='name',key='twitter:title',content=og_title.get('content',''))
  if og_description and not soup.select_one('meta[name="twitter:description"]'):
   seo.upsert_meta(soup,attr='name',key='twitter:description',content=og_description.get('content',''))
  if og_image and not soup.select_one('meta[name="twitter:image"]'):
   seo.upsert_meta(soup,attr='name',key='twitter:image',content=og_image.get('content',''))
  if not soup.select_one('meta[name="twitter:card"]'):
   seo.upsert_meta(soup,attr='name',key='twitter:card',content='summary_large_image')
  seo.apply_verification_meta(soup,verification)
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
print(f'Built {len(list(D.rglob("*")))} public files/directories. {len(e["articles"])} articles, {len(e.get("wire",[]))} news briefs, RSS, sitemap and news sitemap.')
