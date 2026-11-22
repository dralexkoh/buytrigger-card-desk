"""Build the Paldean Fates, Crown Zenith and Fusion Strike public trackers.

Membership is the English base printing only: Holofoil, or Normal when that
card has no Holofoil row. Reverse Holofoil is a second copy of the same card.
Sealed products have no collector number and are left out. Nothing here reads
an eBay URL, an affiliate link, or a price archive. The one guide is the
TCGCSV prices file dated with the public release (21 Nov 2026). Launch-day
history is not invented, so each index baseline stores usd null.

Official scans come from images.pokemontcg.io, the Pokémon TCG image host,
resized to a 200px JPEG. Artwork is not redrawn.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import urllib.request

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '2026-11-21'
BUILT_AT = '2026-11-21T20:03:19+00:00'
EXPIRES_AT = '2026-11-23T20:03:19+00:00'
CREDIT = 'Card image: The Pokémon Company / pokemon.com'
UA = 'buytrigger-cards-set-tracker/1.0'


def ext(product):
    return {row.get('name'): row.get('value') for row in (product.get('extendedData') or [])}


def load_group(group_id):
    folder = Path('/tmp/tcgcsv')
    products = json.loads((folder / f'{group_id}-products.json').read_text())['results']
    prices = json.loads((folder / f'{group_id}-prices.json').read_text())['results']
    digest = sha256((folder / f'{group_id}-prices.json').read_bytes()).hexdigest()
    by_id = {}
    for row in prices:
        by_id.setdefault(row['productId'], {})[row['subTypeName']] = row
    return products, by_id, digest


def image_token(number):
    head = number.split('/', 1)[0]
    if head.upper().startswith('GG'):
        return head.upper()
    return str(int(head))


def choose(group_id, set_name):
    products, prices, digest = load_group(group_id)
    chosen = []
    sealed = 0
    for product in products:
        number = ext(product).get('Number')
        if not number:
            sealed += 1
            continue
        rows = prices.get(product['productId']) or {}
        if 'Holofoil' in rows:
            printing = 'Holofoil'
        elif 'Normal' in rows:
            printing = 'Normal'
        else:
            raise SystemExit(f'{product["productId"]} {number} has no base printing')
        usd = rows[printing].get('marketPrice')
        if isinstance(usd, bool) or not isinstance(usd, (int, float)) or usd <= 0:
            raise SystemExit(f'{product["productId"]} has no positive guide')
        rarity = ext(product).get('Rarity') or ''
        chosen.append({
            'productId': str(product['productId']),
            'groupId': str(group_id),
            'name': product['name'],
            'set': set_name,
            'number': number,
            'language': 'English',
            'printing': printing,
            'rarity': rarity,
            'usd': usd,
            'url': product.get('url') or f'https://www.tcgplayer.com/product/{product["productId"]}',
            'image_token': image_token(number),
        })
    return chosen, sealed, digest


def number_key(number):
    head = number.split('/', 1)[0]
    if head.upper().startswith('GG'):
        return (1, int(head[2:]), number)
    if head.isdigit():
        return (0, int(head), number)
    return (2, 0, number)


SPECS = [
    {
        'index': 'paldean-fates',
        'title': 'Paldean Fates',
        'full': 'Paldean Fates',
        'count': 245,
        'baseline': '2024-01-26',
        'baseline_text': '26 January 2024',
        'groups': [(23353, 'SV: Paldean Fates', 'sv4pt5')],
        'search_set': 'SV: Paldean Fates',
        'source_groups': '23353',
        'heroes': [('534919', 'Mew ex 232/091'), ('535090', 'Charizard ex 234/091'), ('535101', 'Iono 237/091')],
        'chase': ['534919', '535090', '535101'],
        'gallery_js': '"shiny":c=>{const n=parseInt(c.number,10);return n>=92&&n<=226;},\n  "secret":c=>parseInt(c.number,10)>226',
        'labels_js': '{"all": "All 245 cards", "top20": "Top 20 by Raw", "shiny": "Shiny Vault", "secret": "Secret rares"}',
        'options': '<option value="all">All 245 cards</option><option value="top20">Top 20 by Raw</option><option value="shiny">Shiny Vault</option><option value="secret">Secret rares</option>',
        'issue': "if(n>226)return 'Secret rare · '+c.number;\n if(n>=92)return 'Shiny Vault · '+c.number;\n return c.number;",
        'intro': 'All 245 English cards from Paldean Fates, one of each base printing: 91 main-set cards, the Shiny Vault (092–226) and 19 secret rares (227–245). Open any card for its dated Raw market guides. Prices follow the daily Raw market-guide release. The source date is shown with the index. The index start date is 26 January 2024, the set’s English launch day; the index stays at — until a complete launch-day set of guides is available. Reverse holofoils and sealed products are left out.',
        'price_intro': 'All {count} English cards from Paldean Fates, including the Shiny Vault and {secrets} secret rares.',
        'secret_over': 226,
        'footer': 'Paldean Fates prices',
        'page_title': 'Pokémon Paldean Fates raw prices · BuyTrigger.Cards',
        'heading': 'Paldean Fates raw prices',
        'kicker_set': 'Paldean Fates',
    },
    {
        'index': 'crown-zenith',
        'title': 'Crown Zenith',
        'full': 'Crown Zenith',
        'count': 230,
        'baseline': '2023-01-20',
        'baseline_text': '20 January 2023',
        'groups': [
            (17688, 'SWSH: Crown Zenith', 'swsh12pt5'),
            (17689, 'SWSH: Crown Zenith Galarian Gallery', 'swsh12pt5gg'),
        ],
        'search_set': 'Crown Zenith',
        'source_groups': '(?:17688|17689)',
        'heroes': [('478101', 'Arceus VSTAR GG70/GG70'), ('478098', 'Radiant Charizard 020/159'), ('478103', 'Pikachu 160/159')],
        'chase': ['478101', '478098', '478103'],
        'gallery_js': '"galarian":c=>String(c.number).startsWith(\'GG\'),\n  "secret":c=>parseInt(c.number,10)>159',
        'labels_js': '{"all": "All 230 cards", "top20": "Top 20 by Raw", "galarian": "Galarian Gallery", "secret": "Secret rares"}',
        'options': '<option value="all">All 230 cards</option><option value="top20">Top 20 by Raw</option><option value="galarian">Galarian Gallery</option><option value="secret">Secret rares</option>',
        'issue': "if(String(c.number).startsWith('GG'))return 'Galarian Gallery · '+c.number;\n if(n>159)return 'Secret rare · '+c.number;\n return c.number;",
        'intro': 'All 230 English cards from Crown Zenith, one of each base printing: 160 from the main set, including Pikachu 160/159, and all 70 Galarian Gallery cards (GG01–GG70). Open any card for its dated Raw market guides. Prices follow the daily Raw market-guide release. The source date is shown with the index. The index start date is 20 January 2023, the set’s English launch day; the index stays at — until a complete launch-day set of guides is available. Reverse holofoils and sealed products are left out. This is the first tracker that reads two TCGCSV groups.',
        'price_intro': 'All {count} English cards from Crown Zenith: 160 from the main set and all 70 Galarian Gallery cards.',
        'secret_over': None,
        'footer': 'Crown Zenith prices',
        'page_title': 'Pokémon Crown Zenith raw prices · BuyTrigger.Cards',
        'heading': 'Crown Zenith raw prices',
    },
    {
        'index': 'fusion-strike',
        'title': 'Fusion Strike',
        'full': 'Fusion Strike',
        'count': 284,
        'baseline': '2021-11-12',
        'baseline_text': '12 November 2021',
        'groups': [(2906, 'SWSH08: Fusion Strike', 'swsh8')],
        'search_set': 'SWSH08: Fusion Strike',
        'source_groups': '2906',
        'heroes': [('253266', 'Gengar VMAX 271/264'), ('253177', 'Mew VMAX 269/264'), ('253265', 'Espeon VMAX 270/264')],
        'chase': ['253266', '253177', '253265'],
        'gallery_js': '"secret":c=>parseInt(c.number,10)>264',
        'labels_js': '{"all": "All 284 cards", "top20": "Top 20 by Raw", "secret": "Secret rares"}',
        'options': '<option value="all">All 284 cards</option><option value="top20">Top 20 by Raw</option><option value="secret">Secret rares</option>',
        'issue': "if(n>264)return 'Secret rare · '+c.number;\n return c.number;",
        'intro': 'All 284 English cards from Fusion Strike, one of each base printing, including 20 secret rares and Gengar VMAX 271/264. Open any card for its dated Raw market guides. Prices follow the daily Raw market-guide release. The source date is shown with the index. The index start date is 12 November 2021, the set’s English launch day; the index stays at — until a complete launch-day set of guides is available. Reverse holofoils and sealed products are left out.',
        'price_intro': 'All {count} English cards from Fusion Strike, including {secrets} secret rares.',
        'secret_over': 264,
        'footer': 'Fusion Strike prices',
        'page_title': 'Pokémon Fusion Strike raw prices · BuyTrigger.Cards',
        'heading': 'Fusion Strike raw prices',
    },
]


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def save_jpeg(png, dest):
    image = Image.open(BytesIO(png)).convert('RGB')
    width = 200
    height = max(1, round(image.height * width / image.width))
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    image.save(dest, 'JPEG', quality=78, optimize=True)
    return width, height


def download_one(card, folder):
    token = card['image_token']
    api_set = card['api_set']
    urls = [
        f'https://images.pokemontcg.io/{api_set}/{token}_hires.png',
        f'https://images.pokemontcg.io/{api_set}/{token}.png',
    ]
    last = None
    for url in urls:
        try:
            png = fetch(url)
            dest = folder / f"{card['productId']}.jpg"
            width, height = save_jpeg(png, dest)
            return {
                'productId': card['productId'],
                'number': card['number'],
                'name': card['name'],
                'source_url': url,
                'file': f"{card['image_dir']}/{card['productId']}.jpg",
                'width': width,
                'height': height,
                'sha256': sha256(dest.read_bytes()).hexdigest(),
            }
        except Exception as exc:
            last = exc
    raise RuntimeError(f"{card['productId']} {card['number']}: {last}")


def js_source(spec):
    index = spec['index']
    heroes = ', '.join(f'[{pid}, "{label}"]' for pid, label in spec['heroes'])
    sets = ', '.join(json.dumps(name) for _, name, _ in spec['groups'])
    return f"""(()=>{{'use strict';
const Factory=window.BTSetIndexEngine;
const E=Factory.createEngine({{
 index:'{index}',
 cardCount:{spec['count']},
 baselineDate:'{spec['baseline']}',
 proposedBaseline:false,
 imagePattern:'assets/{index}/[0-9]+\\\\.jpg',
 keyPattern:'en-{index}-[0-9]+-(holofoil|normal)',
 sourcePattern:'https://tcgcsv\\\\.com/(?:archive/tcgplayer/prices-\\\\d{{4}}-\\\\d{{2}}-\\\\d{{2}}\\\\.ppmd\\\\.7z|tcgplayer/3/{spec['source_groups']}/prices)',
 allowedSets:[{sets}],
 allowedPrintings:['Holofoil','Normal'],
 gallery:{{
  {spec['gallery_js']}
 }}
}});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const money=n=>new Intl.NumberFormat('en-US',{{style:'currency',currency:'USD'}}).format(n);
const date=s=>new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}});
let epoch=0,data=null,chaseRoster=null,controller=null,timer=null,expiry=null,active=false,search='',collection='all',period='All',sort='default',returnFocus=null;
const CREDIT='{CREDIT}';
const heroes=[{heroes}];
const galleryLabels={spec['labels_js']};

function page(){{
 return `
 <div id="chase-slot"></div>
 <section class="page-intro thirtieth-intro">
  <a class="back-link" href="market.html">← All markets</a>
  <div class="thirtieth-hero">
   <div>
    <span class="kicker red-text">ENGLISH / RAW MARKET GUIDES</span>
    <h1>{spec['title']} <em>Index.</em></h1>
    <p>{spec['intro']}</p>
    <a class="btn red" href="#{index}-cards" data-set-scroll>Explore the cards ↓</a>
   </div>
   <div class="thirtieth-fan" aria-label="English {spec['full']} cards">${{heroes.map(([id,label])=>`<img src="assets/{index}/${{id}}.jpg" alt="${{label}} · English {spec['full']} official card image">`).join('')}}</div>
  </div>
 </section>
 <section class="thirtieth-market" aria-label="{spec['full']} market tracker">
  <div class="set-chart-head">
   <div><span class="kicker">RAW GUIDE INDEX</span><h2 id="set-index-title">All {spec['count']} cards.</h2></div>
  </div>
  <div id="{index}-summary" aria-live="polite"><p class="set-status">Loading the latest Raw guides…</p></div>
  <div class="shared-periods" role="group" aria-label="History window">${{['7D','30D','All'].map(p=>`<button data-set-period="${{p}}" aria-pressed="${{p===period}}">${{p==='All'?'All history':p}}</button>`).join('')}}</div>
  <div id="{index}-chart"></div>
  <details class="set-method">
   <summary>How the chart works</summary>
   <p>The index adds the Raw market guide for one of each of the {spec['count']} English base printings and sets that total to 100 on {spec['baseline_text']}, the set’s English launch day. The index stays at — until a complete launch-day set of guides is available, because the dated guides in this snapshot do not include one. A day needs every price in the set. Missing dates stay as gaps.</p>
   <p>Prices are TCGplayer mixed-condition market guides via <a href="https://tcgcsv.com/faq" target="_blank" rel="noopener">TCGCSV</a>, in USD. Each figure is that printing’s guide on the daily release. These are guide prices, not verified sales or offers.</p>
  </details>
 </section>
 <section class="thirtieth-catalogue" id="{index}-cards">
  <header class="set-list-head"><div><span class="kicker">EXACT ENGLISH PRINTINGS</span><h2>Find your card.</h2></div><span id="set-count" aria-live="polite"></span></header>
  <div class="set-tools">
   <label>Find a card<input type="search" id="set-search" placeholder="Name or card number" autocomplete="off"></label>
   <label>Collection<select id="set-collection">{spec['options']}</select></label>
   <label>Sort<select id="set-sort"><option value="default">Card number</option><option value="price">Raw price: high to low</option><option value="number">Card number</option><option value="name">Name</option></select></label>
  </div>
  <p class="set-chart-note" id="set-ranking-note" hidden></p>
  <div class="set-grid" id="set-grid"></div>
  <p class="set-credit">${{CREDIT}}</p>
 </section>
 <dialog class="set-dialog" id="set-dialog"><button type="button" class="set-dialog-close" aria-label="Close card">×</button><div id="set-dialog-body"></div></dialog>`;
}}

function chart(points,value,label){{
 const good=points.filter(p=>E.positive(value(p)));
 if(!good.length)return '<p class="set-status">No supported observations for this view.</p>';
 const lo=Math.min(...good.map(value)),hi=Math.max(...good.map(value)),span=hi-lo||Math.max(1,hi*.1),start=Date.parse(points[0].date),end=Date.parse(points.at(-1).date),x=p=>55+(Date.parse(p.date)-start)/(end-start||86400000)*700,y=p=>215-(value(p)-lo+span*.1)/(span*1.2)*170;
 const lines=E.segments(points,value).filter(a=>a.length>1).map(a=>`<path d="${{a.map((p,i)=>(i?'L':'M')+x(p).toFixed(2)+','+y(p).toFixed(2)).join(' ')}}"/>`).join('');
 return `<svg viewBox="0 0 800 270" role="img" aria-label="${{esc(label)}}"><text x="7" y="31">${{hi.toLocaleString('en-US',{{maximumFractionDigits:1}})}}</text><text x="7" y="222">${{lo.toLocaleString('en-US',{{maximumFractionDigits:1}})}}</text><line x1="55" y1="230" x2="760" y2="230"/>${{lines}}${{good.map(p=>`<circle cx="${{x(p)}}" cy="${{y(p)}}" r="3"><title>${{date(p.date)}} · ${{value(p).toFixed(2)}}</title></circle>`).join('')}}<text x="55" y="258">${{date(points[0].date)}}</text><text x="755" y="258" text-anchor="end">${{date(points.at(-1).date)}}</text></svg>`;
}}

function draw(){{
 if(!data)return;
 const cards=E.focus(data).all;
 const history=E.basket(data,cards);
 const latest=history.points.find(p=>p.date===data.sourceDate);
 document.getElementById('{index}-summary').innerHTML=`<div class="set-stats">
  <div><span>Raw guide total</span><strong>${{latest?.usd?money(latest.usd):'—'}}</strong><small>{spec['count']} singles · USD</small></div>
  <div><span>Raw index</span><strong>${{latest?.value?latest.value.toFixed(2):'—'}}</strong><small>100 on ${{date(history.baseDate)}}</small></div>
  <div><span>Since the start date</span><strong class="${{latest?.value>=100?'positive':''}}">${{latest?.value?(latest.value>=100?'+':'')+(latest.value-100).toFixed(2)+'%':'—'}}</strong><small>All {spec['count']} cards</small></div>
  <div><span>Source date</span><strong class="set-source-day">${{date(data.sourceDate)}}</strong><small>${{latest?.count??0}} / ${{cards.length}} Raw guides</small></div>
 </div>`;
 const cutoff=period==='All'?'':new Date(Date.parse(data.sourceDate+'T12:00:00Z')-(period==='7D'?6:29)*86400000).toISOString().slice(0,10);
 const points=history.points.filter(p=>!cutoff||p.date>=cutoff);
 const indexReady=points.some(p=>E.positive(p.value));
 const chartValue=indexReady?(p=>p.value):(p=>p.usd);
 const chartLabel=indexReady?'{spec['full']} Raw market-guide index':'{spec['full']} Raw market-guide total in USD';
 const chartNote=indexReady
  ?`{spec['count']} fixed printings. Lines stop where prices are missing. The index is 100 on {spec['baseline_text']}, the set’s English launch day.`
  :`{spec['count']} fixed printings. The index start date is {spec['baseline_text']}, the set’s English launch day. The index stays at — until a complete launch-day set of guides is available.`;
 document.getElementById('{index}-chart').innerHTML=chart(points,chartValue,chartLabel)+
  `<p class="set-chart-note">${{chartNote}}</p>`;
}}

function rawPrice(point){{
 return `<div class="set-price-bars"><div><span>Raw USD</span><b>${{point?.[2]==='ok'?money(point[1]):'—'}}</b></div></div>`;
}}

function issueLabel(c){{
 const n=parseInt(c.number,10);
 {spec['issue']}
}}

function ebayBuys(c,detail){{
 const block=window.BTCommerce&&window.BTCommerce.ebayCardBlock;
 return block?block(c,window.BT_COMMERCE,{{placement:'db',detail:!!detail,stack:!detail,pill:true,note:detail?'card':false}}):'';
}}
function cardMarkup(c,group,rank){{
 const point=E.latest(data,c.key);
 const imageLabel=esc(c.name+' · '+c.number+' · '+c.set+' · English '+c.printing);
 return `<article class="set-card">
  <button class="set-card-art" data-set-card="${{c.key}}" aria-label="Open ${{esc(c.name.includes(c.number)?c.name:c.name+' '+c.number)}}"><img src="${{c.image}}" alt="${{imageLabel}}" loading="lazy" width="200" height="279"></button>
  <div class="set-card-info">
   <span class="set-issue">${{rank?'#'+rank+' · ':''}}${{esc(issueLabel(c))}} · ${{esc(c.rarity||c.printing)}}</span>
   <h3>${{esc(c.name.replace(/ - .*$/,''))}}</h3><p>English · ${{esc(c.printing)}}</p>
   ${{rawPrice(point)}}
   <small>${{point?date(point[0]):'No observations'}} · ${{point?.[2]==='ok'?'Raw guide':'Price unavailable'}}</small>
   ${{ebayBuys(c,false)}}
   <button class="set-open" data-set-card="${{c.key}}">Open card &amp; history ↗</button>
  </div>
 </article>`;
}}

function drawCards(){{
 if(!data)return;
 const focus=E.focus(data);
 const ranked=E.rankedRaw(data);focus.top20=ranked.slice(0,20);
 const selected=collection==='all'?['all']:[collection];
 const query=search.trim().toLowerCase();
 let count=0,total=0;
 const html=selected.map(group=>{{
  const cards=focus[group].filter(c=>!query||[c.name,c.number,c.set,c.rarity,c.printing].join(' ').toLowerCase().includes(query));
  total+=focus[group].length;
  count+=cards.length;
  if(!cards.length)return '';
  if(sort==='name')cards.sort((a,b)=>a.name.localeCompare(b.name,undefined,{{numeric:true}}));
  else if(sort==='price'||(sort==='default'&&group==='top20'))cards.sort((a,b)=>(E.latest(data,b.key)?.[1]||0)-(E.latest(data,a.key)?.[1]||0));
  else cards.sort((a,b)=>a.number.localeCompare(b.number,undefined,{{numeric:true}}));
  return `<h3 class="set-group-title">${{galleryLabels[group]}} <small>${{cards.length}} / ${{focus[group].length}}</small></h3>`+
   cards.map(c=>cardMarkup(c,group,group==='top20'?focus.top20.indexOf(c)+1:null)).join('');
 }}).join('');
 document.getElementById('set-count').textContent=`${{count}} of ${{total}} cards`;
 const note=document.getElementById('set-ranking-note');note.hidden=collection!=='top20';
 note.textContent=`Ranked by Raw USD from ${{ranked.length}} of ${{data.cards.length}} printings priced on ${{date(data.sourceDate)}}. Missing prices stay unranked.`;
 document.getElementById('set-grid').innerHTML=html||'<p class="set-status">No cards match that filter.</p>';
}}

function unavailable(message){{
 document.getElementById('{index}-summary').innerHTML=`<p class="set-status">${{esc(message)}} <button type="button" data-set-retry>Try again</button></p>`;
}}

function openCard(key,button){{
 const c=data?.cards.find(c=>c.key===key);if(!c)return;returnFocus=button;
 const rows=E.series(data,key),p=rows.at(-1);
 const product=c.image.match(/([0-9]+)\\.jpg$/)[1];
 document.getElementById('set-dialog-body').innerHTML=`<div class="set-dialog-card"><img src="${{c.image}}" alt="${{esc(c.name+' · '+c.number+' · English '+c.printing)}}"><div><span class="kicker">${{esc(c.number)}} / ENGLISH</span><h2>${{esc(c.name)}}</h2><p>${{esc(c.set)}} · ${{esc(c.printing)}} · ${{esc(c.rarity||'')}}</p>${{rawPrice(p)}}<p>Raw market guide, ${{p?date(p[0]):'unavailable'}}.</p><a href="https://www.tcgplayer.com/product/${{product}}" target="_blank" rel="noopener">Exact catalogue issue ↗</a>${{ebayBuys(c,true)}}</div></div><div class="set-popup-tabs" role="tablist" aria-label="Card details">${{[['overview','Overview'],['evidence','Prices & sources'],['method','Method']].map(([id,label])=>`<button role="tab" id="set-tab-${{id}}" aria-controls="set-panel-${{id}}" aria-selected="${{id==='overview'}}" tabindex="${{id==='overview'?0:-1}}" data-set-tab="${{id}}">${{label}}</button>`).join('')}}</div><section id="set-panel-overview" role="tabpanel" aria-labelledby="set-tab-overview"><div class="set-dialog-chart">${{chart(rows.map(p=>({{date:p[0],usd:p[2]==='ok'?p[1]:null}})),p=>p.usd,'Dated Raw market guide in USD')}}</div></section><section id="set-panel-evidence" role="tabpanel" aria-labelledby="set-tab-evidence" hidden><details class="set-observations" open><summary>All prices, dates and sources</summary><div><table><thead><tr><th>Date</th><th>Raw USD</th><th>Source / status</th></tr></thead><tbody>${{[...rows].reverse().map(p=>`<tr><td>${{date(p[0])}}</td><td>${{p[2]==='ok'?money(p[1]):'—'}}</td><td>${{esc(p[2]==='ok'?'TCGCSV market guide':p[2].replaceAll('_',' '))}}${{data.sources.filter(s=>s.day===p[0]).map(s=>` <a href="${{esc(s.url)}}" target="_blank" rel="noopener">Source ↗</a>`).join('')}}</td></tr>`).join('')}}</tbody></table></div></details></section><section id="set-panel-method" role="tabpanel" aria-labelledby="set-tab-method" hidden><h3>One printing. One price series.</h3><p>English · ${{esc(c.set)}} · ${{esc(c.number)}} · ${{esc(c.printing)}}. Raw observations are TCGplayer mixed-condition market guides supplied by TCGCSV. They are separate from Near Mint guides and completed-sale prices.</p><p>Missing values stay unpriced. These figures describe this printing; they are not a condition assessment, a grading outcome or a guaranteed resale price.</p><p class="set-credit">${{CREDIT}}</p></section>`;
 document.getElementById('set-dialog').showModal();
}}

function stampSnapshot(value){{
 const generated=new Date();
 const copy={{...value,generatedAt:generated.toISOString(),expiresAt:new Date(generated.getTime()+9*60*1000).toISOString()}};
 return copy;
}}

async function loadDaily(signal){{
 const [cacheRes,snapRes]=await Promise.all([
  fetch('data/market-cache/'+E.spec.index+'-current.json',{{cache:'no-store',signal}}),
  fetch('{index}-market-snapshot.json',{{cache:'no-store',signal}})
 ]);
 if(!cacheRes.ok||!snapRes.ok)throw Error();
 const value=E.validate(stampSnapshot(Factory.adaptDailyCache(await snapRes.json(),await cacheRes.json())));
 if(!value)throw Error();
 return value;
}}

async function loadRoster(signal){{
 if(chaseRoster)return chaseRoster;
 const res=await fetch('data/market-rosters/'+E.spec.index+'.json',{{cache:'no-store',signal}});
 if(!res.ok)throw Error();
 chaseRoster=await res.json();
 return chaseRoster;
}}
function drawChase(){{
 const slot=document.getElementById('chase-slot');
 if(!slot)return;
 slot.innerHTML=data&&chaseRoster?Factory.chaseHtml(chaseRoster,data,E.latest,{{esc,money,date}}):'';
}}
async function load(){{
 const token=++epoch;
 controller?.abort();
 controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),8000);
 let value=null;
 try{{
  const res=await fetch('market-config.json',{{cache:'no-store',signal:controller.signal}});
  if(!res.ok)throw Error();
  const config=await res.json();
  if(!config.enabled||!config.endpoint)throw Error();
  value=await loadDaily(controller.signal);
 }}catch(e){{
  value=null;
 }}
 try{{
  if(!value)value=await loadDaily(controller.signal);
  if(!active||token!==epoch)return;
  data=value;
  try{{await loadRoster(controller.signal);}}catch(err){{}}
  if(!active||token!==epoch)return;
  drawChase();
  draw();
  drawCards();
  clearTimeout(expiry);
  expiry=setTimeout(()=>{{if(active){{unavailable('Refreshing the shared market data…');load();}}}},Math.max(0,Date.parse(data.expiresAt)-Date.now()));
 }}catch(e){{
  if(active&&token===epoch)unavailable('The shared market data could not be checked.');
 }}finally{{
  clearTimeout(timeout);
 }}
}}

function mount(){{
 active=true;
 const host=document.querySelector('.thirtieth-market');
 if(!host)return;
 document.getElementById('set-search').oninput=e=>{{search=e.target.value;drawCards();}};
 document.getElementById('set-collection').value=collection;
 document.getElementById('set-collection').onchange=e=>{{collection=e.target.value;drawCards();}};
 document.getElementById('set-sort').onchange=e=>{{sort=e.target.value;drawCards();}};
 const root=document.getElementById('main');
 root.onclick=e=>{{
  if(e.target.closest('.ebay-bar a'))return;
  const tab=e.target.closest('[data-set-tab]');
  if(tab){{
   root.querySelectorAll('[data-set-tab]').forEach(b=>{{const on=b===tab;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;document.getElementById('set-panel-'+b.dataset.setTab).hidden=!on;}});
   return;
  }}
  const p=e.target.closest('[data-set-period]'),card=e.target.closest('[data-set-card]');
  if(p){{period=p.dataset.setPeriod;root.querySelectorAll('[data-set-period]').forEach(b=>b.setAttribute('aria-pressed',String(b===p)));draw();}}
  else if(card)openCard(card.dataset.setCard,card);
  else if(e.target.closest('[data-set-retry]'))load();
  else if(e.target.closest('[data-set-scroll]')){{e.preventDefault();document.getElementById('{index}-cards').scrollIntoView({{block:'start'}});}}
 }};
 const dialog=document.getElementById('set-dialog');
 dialog.querySelector('.set-dialog-close').onclick=()=>dialog.close();
 dialog.addEventListener('close',()=>returnFocus?.focus());
 dialog.addEventListener('keydown',e=>{{
  const tab=e.target.closest('[data-set-tab]');
  if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
  e.preventDefault();
  const tabs=[...dialog.querySelectorAll('[data-set-tab]')],i=tabs.indexOf(tab),next=e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3;
  tabs[next].click();tabs[next].focus();
 }});
 load();
 timer=setInterval(load,300000);
}}

function unmount(){{epoch++;active=false;controller?.abort();clearInterval(timer);clearTimeout(expiry);data=null;returnFocus=null;const main=document.getElementById('main');if(main)main.onclick=null;}}
window.BT{spec['window']}={{page,mount,unmount}};
}})();
"""


def py_source(spec):
    index = spec['index']
    ident = index.replace('-', '_')
    secret_line = ''
    if spec['secret_over']:
        secret_line = f"    secrets = sum(1 for card in cards if int(card['number'].split('/', 1)[0]) > {spec['secret_over']})\n    "
    else:
        secret_line = "    secrets = sum(1 for card in cards if card['number'].startswith('GG'))\n    "
    intro = spec['price_intro']
    return f'''"""Public raw-price page for the English Pokémon {spec['full']} set.

Refresh: the daily job rewrites data/prices/{index}.json from the daily cache.
Rows, the card count and the as-of date all come from that file.
"""
from __future__ import annotations

from pathlib import Path

import raw_price_page as engine

SNAPSHOT = Path('data/prices/{index}.json')
PAGE_REL = Path('prices/{index}/index.html')
PRICE_PAGE_URL = 'https://buytrigger.cards/prices/{index}/'
CAMPAIGN = '{index}-prices'
SOURCE_NAME = engine.SOURCE_NAME
SET_LABEL = '{spec['full']}'


def accept_set(set_name):
    if not isinstance(set_name, str) or not set_name.strip():
        raise ValueError('Card rarity missing')
    return set_name.strip()


def accept_image(product_id, image_path):
    expected = f'assets/{index}/{{product_id}}.jpg'
    if image_path != expected:
        raise ValueError('Unexpected image path for ' + product_id)
    return image_path


def intro(cards):
    count = len(cards)
{secret_line}return f'{intro}'


def description(cards, date_text):
    count = len(cards)
    return (
        f'Raw (ungraded) market guide prices in USD for all {{count}} English Pokémon {{SET_LABEL}} cards. '
        f'{{SOURCE_NAME}} as of {{date_text}}. US-market references, not offers.'
    )


SPEC = {{
    'snapshot': SNAPSHOT,
    'roster': Path('data/market-rosters/{index}.json'),
    'page_rel': PAGE_REL,
    'url': PRICE_PAGE_URL,
    'campaign': CAMPAIGN,
    'form_id': '{index}-prices',
    'data_page': '{index}-prices',
    'footer_href': 'prices/{index}/',
    'footer_label': '{spec['footer']}',
    'title': '{spec['page_title']}',
    'kicker': 'ENGLISH / RAW PRICE REFERENCE',
    'heading': '{spec['heading']}',
    'source_lead': 'Raw (ungraded) market guide prices, source: {{source}}, as of {{date}}',
    'source_note': 'US-market references in USD, not offers. These figures follow the daily market-guide release.',
    'price_header': 'Raw price',
    'group_header': 'Rarity',
    'group_attr': 'rarity',
    'group_class': 'price-rarity',
    'number_sort': True,
    'group_sort': False,
    'filter_placeholder': 'Name, number or rarity',
    'region_label': '{spec['full']} raw prices',
    'caption': 'English Pokémon {spec['full']} raw prices in USD',
    'search_set': '{spec['search_set']}',
    'accept_set': accept_set,
    'accept_image': accept_image,
    'intro': intro,
    'description': description,
    'image_credit': '{CREDIT}',
    'sort_options': [
        ('price-desc', 'Price, high to low', True),
        ('price-asc', 'Price, low to high', False),
        ('name-asc', 'Name, A to Z', False),
        ('name-desc', 'Name, Z to A', False),
        ('number-asc', 'Number, low to high', False),
        ('number-desc', 'Number, high to low', False),
    ],
}}


def load_snapshot(path: Path) -> dict:
    return engine.load_snapshot(path)


def prepare_cards(snapshot: dict, root: Path):
    return engine.prepare_cards(snapshot, root, SPEC)


def render_page(root: Path, snapshot: dict | None = None) -> str:
    return engine.render_page(root, SPEC, snapshot)


def publish_price_page(root: Path, dist: Path):
    engine.publish_price_page(root, dist, SPEC)


def source_date(root: Path) -> str:
    return engine.read_source_date(root, SNAPSHOT)


def format_source_date(iso_date: str) -> str:
    return engine.format_source_date(iso_date)
'''


def test_source(spec):
    index = spec['index']
    extra = ''
    if index == 'paldean-fates':
        extra = '''
    def test_shiny_vault_and_secrets(self):
        shiny = [card for card in self.cards if 92 <= int(card['number'].split('/', 1)[0]) <= 226]
        secrets = [card for card in self.cards if int(card['number'].split('/', 1)[0]) > 226]
        self.assertEqual(len(shiny), 135)
        self.assertEqual(len(secrets), 19)
        self.assertIn('Shiny Vault', self.html)
'''
    elif index == 'crown-zenith':
        extra = '''
    def test_both_groups_and_all_seventy_gallery_cards(self):
        gallery = [card for card in self.cards if card['number'].startswith('GG')]
        main = [card for card in self.cards if not card['number'].startswith('GG')]
        self.assertEqual(len(gallery), 70)
        self.assertEqual(len(main), 160)
        numbers = {card['number'] for card in gallery}
        self.assertEqual(numbers, {f'GG{i:02d}/GG70' for i in range(1, 71)})
        self.assertIn('17688', (ROOT / 'crown-zenith.js').read_text())
        self.assertIn('17689', (ROOT / 'crown-zenith.js').read_text())
        self.assertTrue(any(card['number'] == '160/159' for card in main))
        self.assertTrue(any(card['number'] == 'GG70/GG70' for card in gallery))
'''
    elif index == 'fusion-strike':
        extra = '''
    def test_gengar_vmax_alternate_art_is_271(self):
        card = next(card for card in self.cards if card['product_id'] == '253266')
        self.assertEqual(card['number'], '271/264')
        self.assertIn('Gengar VMAX', card['name'])
        secrets = [card for card in self.cards if int(card['number'].split('/', 1)[0]) > 264]
        self.assertEqual(len(secrets), 20)
'''
    return f'''"""Public {spec['full']} raw-price page."""
from __future__ import annotations

from pathlib import Path
import json
import re
import sys
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digest_signup
import {index.replace('-', '_')}_prices as prices
import raw_price_page

ROOT = Path(__file__).resolve().parents[1]


def release_date():
    return json.loads((ROOT / 'refresh-status.json').read_text())['sourceDate']


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = prices.load_snapshot(ROOT / prices.SNAPSHOT)
        self.cards = prices.prepare_cards(self.snapshot, ROOT)
        self.html = prices.render_page(ROOT)

    def test_snapshot_is_the_full_english_set(self):
        self.assertEqual(len(self.cards), {spec['count']})
        self.assertEqual(self.snapshot['source_date'], release_date())
        self.assertEqual(self.snapshot['set_slug'], '{index}')
        self.assertTrue(all(card['image'] and (ROOT / card['image']).is_file() for card in self.cards))
        self.assertTrue(all(card['price'] and card['price'] > 0 for card in self.cards))
        self.assertTrue(all(card['image'].startswith('assets/{index}/') for card in self.cards))

    def test_default_order_is_raw_price_high_to_low(self):
        ordered = [card['price'] for card in self.cards]
        self.assertEqual(ordered, sorted(ordered, reverse=True))
{extra}

class PageTests(unittest.TestCase):
    def setUp(self):
        self.html = prices.render_page(ROOT)
        self.page = BeautifulSoup(self.html, 'html.parser')

    def test_page_lists_every_card_without_graded_or_trading_language(self):
        rows = self.page.select('#price-table tbody tr')
        self.assertEqual(len(rows), {spec['count']})
        editorial = raw_price_page.without_ebay_buttons(self.html)
        self.assertNotIn('PSA', editorial)
        self.assertIsNone(re.search(r'(?<!un)graded', self.html, re.I))
        text = BeautifulSoup(editorial, 'html.parser').get_text(' ')
        date = prices.format_source_date(prices.load_snapshot(ROOT / prices.SNAPSHOT)['source_date'])
        self.assertIn(f'Raw (ungraded) market guide prices, source: TCGCSV market price, as of {{date}}', text)
        self.assertIn('US-market references in USD, not offers.', text)
        self.assertIn('These figures follow the daily market-guide release.', text)
        self.assertIn('Card image: The Pokémon Company / pokemon.com', text)
        self.assertIsNone(re.search(r'\\b(buy|sell|accumulate|invest)\\b', text, re.I))
        self.assertIsNone(re.search(r'index level|index change|since launch|performance', text, re.I))
        bare = re.sub(r'BuyTrigger\\.Cards', '', text, flags=re.I)
        bare = re.sub(r'BUYTRIGGER\\.CARDS', '', bare)
        self.assertNotIn('BuyTrigger', bare)
        self.assertNotIn('BUYTRIGGER', bare)

    def test_metadata_canonical_and_footer(self):
        self.assertEqual(self.page.title.get_text(), '{spec['page_title']}')
        self.assertIn('all {spec['count']} English', self.page.select_one('meta[name=description]')['content'])
        self.assertEqual(self.page.select_one('link[rel=canonical]')['href'], prices.PRICE_PAGE_URL)
        self.assertEqual(self.page.select_one('footer a[href="/prices/{index}/"]').get('aria-current'), 'page')
        self.assertEqual(self.page.select_one('footer a[href="/prices/{index}/"]').get_text(), '{spec['footer']}')

    def test_rows_use_local_images_and_plain_tcgplayer_links(self):
        images = self.page.select('#price-table .price-card img')
        self.assertEqual(len(images), {spec['count']})
        self.assertTrue(all(img['src'].startswith('assets/{index}/') and img['src'].endswith('.jpg') for img in images))
        links = self.page.select('#price-table a.price-check')
        self.assertEqual(len(links), {spec['count']})

    def test_reuses_the_shared_digest_band(self):
        block = self.page.select_one('.digest-signup')
        self.assertIsNotNone(block)
        self.assertEqual(block.select_one('form.digest-form')['action'], 'https://buytriggercards.substack.com/subscribe')

    def test_sort_controls_are_present(self):
        self.assertEqual(self.page.select_one('#price-sort option[selected]')['value'], 'price-desc')
        self.assertIsNotNone(self.page.select_one('#price-filter'))


if __name__ == '__main__':
    unittest.main()
'''


WINDOWS = {
    'paldean-fates': 'PaldeanFates',
    'crown-zenith': 'CrownZenith',
    'fusion-strike': 'FusionStrike',
}


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')


def build_thirtieth_files():
    catalogue = json.loads((ROOT / 'thirtieth-catalogue.json').read_text())
    chase_ids = [714372, 714386, 716210, 717605, 717610, 716198, 712954, 696688, 717603, 712953, 716231, 716232, 696687]
    rank = {str(product_id): index for index, product_id in enumerate(chase_ids, 1)}
    cards = []
    snap_cards = []
    for card in sorted(catalogue['cards'], key=lambda item: number_key(str(item['number']))):
        product_id = str(card['productId'])
        row = {
            'productId': product_id,
            'groupId': str(card['groupId']),
            'name': card['name'],
            'set': card['set'],
            'number': card['number'],
            'language': 'English',
            'printing': 'Holofoil',
            'image': card['image'],
        }
        if product_id in rank:
            row['chase_rank'] = rank[product_id]
        cards.append(row)
        snap_cards.append({
            'key': card['key'],
            'name': card['name'],
            'set': card['set'],
            'number': card['number'],
            'language': 'English',
            'printing': 'Holofoil',
            'image': card['image'],
        })
    if len(cards) != 195 or len(rank) != 13 or sum('chase_rank' in card for card in cards) != 13:
        raise SystemExit('30th roster did not keep 195 cards and 13 chases')
    source_version = sha256('\n'.join(card['key'] for card in snap_cards).encode()).hexdigest()
    write_json(ROOT / 'data/market-rosters/thirtieth-anniversary.json', {
        'schemaVersion': 1,
        'index': 'thirtieth-anniversary',
        'chase_source': 'thirtieth-engine chase ids, 13 published focus cards',
        'sourceList': 'thirtieth-catalogue.json, 195 English cards. Chase order is the existing thirtieth-engine list. The daily cache is not rewritten.',
        'cards': cards,
    })
    write_json(ROOT / 'thirtieth-market-snapshot.json', {
        'schemaVersion': 2,
        'available': True,
        'index': 'thirtieth-anniversary',
        'sourceSystem': 'shared-cards-market',
        'grade': 'Raw',
        'currency': 'USD',
        'measure': 'tcgcsv_market',
        'cards': snap_cards,
        'sourceDate': RELEASE,
        'source': 'https://tcgcsv.com/faq',
        'sources': [],
        'baseline': {'date': '2026-10-08', 'usd': None, 'proposed': False},
        'preview': True,
        'previewNote': 'Card list for the 195-card page. Prices are read from data/market-cache/thirtieth-current.json and are not rewritten here. The whole-set index stays at — until a complete 195-card guide for 8 October 2026 is in that public history.',
        'sourceVersion': source_version,
    })


def main():
    jobs = []
    built = []
    for spec in SPECS:
        cards = []
        sealed = 0
        digests = {}
        for group_id, set_name, api_set in spec['groups']:
            chosen, sealed_count, digest = choose(group_id, set_name)
            sealed += sealed_count
            digests[str(group_id)] = digest
            for card in chosen:
                card['api_set'] = api_set
                card['image_dir'] = f"assets/{spec['index']}"
            cards.extend(chosen)
        cards.sort(key=lambda card: number_key(card['number']))
        if len(cards) != spec['count']:
            raise SystemExit(f"{spec['index']} has {len(cards)} cards, expected {spec['count']}")
        if len({card['productId'] for card in cards}) != len(cards):
            raise SystemExit(f"{spec['index']} has a duplicate product")
        if spec['index'] == 'fusion-strike':
            gengar = next(card for card in cards if card['productId'] == '253266')
            if gengar['number'] != '271/264':
                raise SystemExit('Gengar VMAX is not 271/264')
        if spec['index'] == 'crown-zenith':
            gallery = [card for card in cards if card['number'].startswith('GG')]
            if len(gallery) != 70:
                raise SystemExit('Crown Zenith is missing Galarian Gallery cards')
        spec['_cards'] = cards
        spec['_sealed'] = sealed
        spec['_digests'] = digests
        built.append(spec)
        for card in cards:
            jobs.append((spec['index'], card))

    print(f'downloading {len(jobs)} official images', flush=True)
    provenance = {spec['index']: [] for spec in built}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {}
        for index, card in jobs:
            folder = ROOT / 'assets' / index
            folder.mkdir(parents=True, exist_ok=True)
            futures[pool.submit(download_one, card, folder)] = index
        done = 0
        for future in as_completed(futures):
            record = future.result()
            provenance[futures[future]].append(record)
            done += 1
            if done % 50 == 0 or done == len(jobs):
                print(f'  {done}/{len(jobs)}', flush=True)

    for spec in built:
        index = spec['index']
        cards = spec['_cards']
        by_id = {card['productId']: card for card in cards}
        records = sorted(provenance[index], key=lambda row: number_key(by_id[row['productId']]['number']))
        write_json(ROOT / 'assets' / index / 'provenance.json', {
            'purpose': f'Official {spec["full"]} card images for the buytrigger.cards set tracker.',
            'credit': CREDIT,
            'rights': 'Card artwork © The Pokémon Company / Nintendo / Creatures / GAME FREAK. Images retrieved from images.pokemontcg.io.',
            'processed': 'Downloaded the official scan and resized it to 200px wide JPEG. No artwork was redrawn or generated.',
            'release': RELEASE,
            'cards': records,
        })
        roster_cards = []
        snap_cards = []
        price_cards = []
        cache_cards = []
        rank = {product_id: position for position, product_id in enumerate(spec['chase'], 1)}
        for card in cards:
            image = f"assets/{index}/{card['productId']}.jpg"
            printing_key = card['printing'].lower()
            roster = {
                'productId': card['productId'],
                'groupId': card['groupId'],
                'name': card['name'],
                'set': card['set'],
                'number': card['number'],
                'language': 'English',
                'printing': card['printing'],
                'image': image,
            }
            if card['productId'] in rank:
                roster['chase_rank'] = rank[card['productId']]
            roster_cards.append(roster)
            snap_cards.append({
                'key': f"en-{index}-{card['productId']}-{printing_key}",
                'name': card['name'],
                'set': card['set'],
                'number': card['number'],
                'language': 'English',
                'printing': card['printing'],
                'image': image,
                'rarity': card['rarity'],
            })
            price_cards.append({
                'name': card['name'],
                'number': card['number'],
                'set_name': card['rarity'],
                'rarity': card['rarity'],
                'raw_price_usd': card['usd'],
                'tcgplayer_product_id': card['productId'],
                'tcgplayer_product_url': card['url'].split('?', 1)[0],
                'image_url': None,
                'image_path': image,
            })
            cache_cards.append({
                'productId': card['productId'],
                'groupId': card['groupId'],
                'name': card['name'],
                'set': card['set'],
                'number': card['number'],
                'language': 'English',
                'printing': card['printing'],
                'image': image,
                'points': [{
                    'day': RELEASE,
                    'usd': card['usd'],
                    'status': 'ok',
                    'source': f"https://tcgcsv.com/tcgplayer/3/{card['groupId']}/prices",
                    'sourceSha256': spec['_digests'][card['groupId']],
                }],
            })
        price_cards.sort(key=lambda card: (-card['raw_price_usd'], card['name'].casefold(), number_key(card['number'])))
        source_version = sha256('\n'.join(card['key'] for card in snap_cards).encode()).hexdigest()
        groups = ', '.join(f'{group_id} {name}' for group_id, name, _api in spec['groups'])
        write_json(ROOT / 'data/market-rosters' / f'{index}.json', {
            'schemaVersion': 1,
            'index': index,
            'chase_source': 'set-trackers brief 22 Nov 2026, the three named heroes',
            'sourceList': f'TCGCSV {groups}. English base printing only (Holofoil, or Normal where that card has no Holofoil). Reverse Holofoil and {spec["_sealed"]} sealed products with no collector number are left out. Guides are the 21 Nov 2026 TCGCSV prices file. No launch-day archive was backfilled.',
            'cards': roster_cards,
        })
        write_json(ROOT / f'{index}-market-snapshot.json', {
            'schemaVersion': 2,
            'available': True,
            'index': index,
            'sourceSystem': 'shared-cards-market',
            'grade': 'Raw',
            'currency': 'USD',
            'measure': 'tcgcsv_market',
            'cards': snap_cards,
            'sourceDate': RELEASE,
            'source': 'https://tcgcsv.com/faq',
            'sources': [{
                'day': RELEASE,
                'url': f"https://tcgcsv.com/tcgplayer/3/{spec['groups'][0][0]}/prices",
            }],
            'baseline': {'date': spec['baseline'], 'usd': None, 'proposed': False},
            'preview': True,
            'previewNote': f"One current Raw guide per card, dated {RELEASE}. The index start date is {spec['baseline_text']}. That launch-day set of guides is not in this file, so the index stays at — . No launch-day price was invented.",
            'sourceVersion': source_version,
        })
        write_json(ROOT / 'data/prices' / f'{index}.json', {
            'set_name': spec['full'],
            'set_slug': index,
            'source': 'TCGCSV marketPrice',
            'source_date': RELEASE,
            'generated_at': BUILT_AT,
            'cards': price_cards,
        })
        write_json(ROOT / 'data/market-cache' / f'{index}-current.json', {
            'schemaVersion': 1,
            'index': index,
            'sourceSystem': 'shared-cards-market-cache',
            'grade': 'Raw',
            'currency': 'USD',
            'measure': 'tcgcsv_market',
            'sourceDate': RELEASE,
            'sourceBuildAt': BUILT_AT,
            'expiresAt': EXPIRES_AT,
            'cards': cache_cards,
        })
        spec['window'] = WINDOWS[index]
        (ROOT / f'{index}.js').write_text(js_source(spec))
        (ROOT / 'scripts' / f'{index.replace("-", "_")}_prices.py').write_text(py_source(spec))
        (ROOT / 'scripts' / f'test_{index.replace("-", "_")}_prices.py').write_text(test_source(spec))
        print(index, len(cards), 'sealed excluded', spec['_sealed'], flush=True)
    build_thirtieth_files()
    print('wrote trackers', flush=True)


if __name__ == '__main__':
    main()
