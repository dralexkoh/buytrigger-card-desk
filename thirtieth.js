(()=>{'use strict';
const Factory=window.BTSetIndexEngine;
const T=window.BTThirtiethEngine;
const E=Factory.createEngine({
 index:'thirtieth-anniversary',
 cardCount:195,
 baselineDate:'2026-10-08',
 proposedBaseline:false,
 imagePattern:'assets/thirtieth/[0-9]+\\.jpg',
 keyPattern:'en-30th-[a-z0-9-]+',
 sourcePattern:'https://tcgcsv\\.com/(?:archive/tcgplayer/prices-\\d{4}-\\d{2}-\\d{2}\\.ppmd\\.7z|tcgplayer/3/(?:24722|24837|24451)/prices)',
 allowedSets:['ME: 30th Celebration','ME: 30th Celebration Classic Collection','ME: Mega Evolution Promo'],
 allowedPrintings:['Holofoil'],
 cardKeys:['key','name','set','number','language','printing','image'],
 gallery:{
  celebration:c=>c.set==='ME: 30th Celebration',
  classic:c=>c.set==='ME: 30th Celebration Classic Collection',
  promos:c=>c.set==='ME: Mega Evolution Promo'
 }
});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);
const date=s=>new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
let epoch=0,data=null,chaseRoster=null,controller=null,timer=null,expiry=null,active=false,search='',collection='all',period='All',basketMode='all',sort='default',returnFocus=null;
const baskets={all:'All 195 cards',chases:'Chase cards',pikachu:'The 30 Pikachu',rgb:'RGB Mew'};
const galleryLabels={all:'All 195 cards',top20:'Top 20 by Raw',chases:'Chase cards',pikachu:'The 30 Pikachu',rgb:'RGB Mew',promos:'Day & Night promos',celebration:'ME: 30th Celebration',classic:'Classic Collection'};
const CREDIT='Catalogue artwork: TCGplayer. Card names and artwork © Pokémon.';

function groupsOf(value){
 const focus=E.focus(value);
 const named=T.focus(value);
 focus.chases=named.chases;
 focus.pikachu=named.pikachu;
 focus.rgb=named.rgb;
 focus.promos=named.promos;
 focus.top20=E.rankedRaw(value).slice(0,20);
 return focus;
}

function page(){
 const heroes=[[714372,'Charizard 4/102 Classic Collection'],[712953,'Pikachu ex 149/128'],[712934,'Pikachu 023/128']];
 return `
 <div id="chase-slot"></div>
 <section class="page-intro thirtieth-intro">
  <a class="back-link" href="market.html">← All markets</a>
  <div class="thirtieth-hero">
   <div>
    <span class="kicker red-text">ENGLISH / RAW MARKET GUIDES</span>
    <h1>30th Anniversary <em>Index.</em></h1>
    <p>All 195 English cards: ME: 30th Celebration (161), Classic Collection (30) and Mega Evolution Promo (4). Open any card for its dated Raw market guides. Prices follow the daily Raw market-guide release. The source date is shown with the index. The index start date is 8 October 2026; the index stays at — until a complete 195-card set of guides for that day is available.</p>
    <a class="btn red" href="#thirtieth-cards" data-set-scroll>Explore the cards ↓</a>
   </div>
   <div class="thirtieth-fan" aria-label="English 30th Celebration cards">${heroes.map(([id,label])=>`<img src="assets/thirtieth/${id}.jpg" alt="${label} · English 30th Celebration catalogue artwork">`).join('')}</div>
  </div>
 </section>
 <section class="thirtieth-market" aria-label="30th market tracker">
  <div class="set-chart-head">
   <div><span class="kicker">RAW GUIDE INDEX</span><h2 id="set-index-title">${baskets[basketMode]}.</h2></div>
   <div class="shared-grades" role="group" aria-label="Index basket">${Object.entries(baskets).map(([id,label])=>`<button data-set-basket="${id}" aria-pressed="${id===basketMode}">${label}</button>`).join('')}</div>
  </div>
  <div id="thirtieth-summary" aria-live="polite"><p class="set-status">Loading the latest Raw guides…</p></div>
  <div class="shared-periods" role="group" aria-label="History window">${['7D','30D','All'].map(p=>`<button data-set-period="${p}" aria-pressed="${p===period}">${p==='All'?'All history':p}</button>`).join('')}</div>
  <div class="set-chart" id="thirtieth-chart"></div>
  <details class="set-method">
   <summary>How the chart works</summary>
   <p>The index adds the Raw market guide for one of each of the 195 English cards and sets that total to 100 on 8 October 2026. The index stays at — until a complete 195-card set of guides for 8 October 2026 is available, because the dated guides in this release do not include one. A day needs every price in the set. Missing dates stay as gaps.</p>
   <p>Chase cards (13), The 30 Pikachu and the RGB Mews keep their own charts. Each of those groups is also 100 on 8 October 2026 when that day’s guides are complete for the group.</p>
   <p>Prices are TCGplayer mixed-condition market guides via <a href="https://tcgcsv.com/faq" target="_blank" rel="noopener">TCGCSV</a>, in USD. Each figure is that printing’s guide on the daily release. These are guide prices, not verified sales or offers.</p>
  </details>
 </section>
 <section class="thirtieth-catalogue" id="thirtieth-cards">
  <header class="set-list-head"><div><span class="kicker">EXACT ENGLISH PRINTINGS</span><h2>Find your card.</h2></div><span id="set-count" aria-live="polite"></span></header>
  <div class="set-tools">
   <label>Find a card<input type="search" id="set-search" placeholder="Name or card number" autocomplete="off"></label>
   <label>Collection<select id="set-collection"><option value="all">All 195 cards</option><option value="top20">Top 20 by Raw</option><option value="chases">Chase cards</option><option value="pikachu">The 30 Pikachu</option><option value="rgb">RGB Mew</option><option value="promos">Day &amp; Night promos</option><option value="celebration">ME: 30th Celebration</option><option value="classic">Classic Collection</option></select></label>
   <label>Sort<select id="set-sort"><option value="default">Chase cards, then number</option><option value="price">Raw price: high to low</option><option value="number">Card number</option><option value="name">Name</option></select></label>
  </div>
  <p class="set-chart-note" id="set-ranking-note" hidden></p>
  <div class="set-grid" id="set-grid"></div>
  <p class="set-credit">${CREDIT}</p>
 </section>
 <dialog class="set-dialog" id="set-dialog"><button type="button" class="set-dialog-close" aria-label="Close card">×</button><div id="set-dialog-body"></div></dialog>`;
}

function chart(points,value,label){
 const good=points.filter(p=>E.positive(value(p)));
 if(!good.length)return '<p class="set-status">No supported observations for this view.</p>';
 const lo=Math.min(...good.map(value)),hi=Math.max(...good.map(value)),span=hi-lo||Math.max(1,hi*.1),start=Date.parse(points[0].date),end=Date.parse(points.at(-1).date),x=p=>55+(Date.parse(p.date)-start)/(end-start||86400000)*700,y=p=>215-(value(p)-lo+span*.1)/(span*1.2)*170;
 const lines=E.segments(points,value).filter(a=>a.length>1).map(a=>`<path d="${a.map((p,i)=>(i?'L':'M')+x(p).toFixed(2)+','+y(p).toFixed(2)).join(' ')}"/>`).join('');
 return `<svg viewBox="0 0 800 270" role="img" aria-label="${esc(label)}"><text x="7" y="31">${hi.toLocaleString('en-US',{maximumFractionDigits:1})}</text><text x="7" y="222">${lo.toLocaleString('en-US',{maximumFractionDigits:1})}</text><line x1="55" y1="230" x2="760" y2="230"/>${lines}${good.map(p=>`<circle cx="${x(p)}" cy="${y(p)}" r="3"><title>${date(p.date)} · ${value(p).toFixed(2)}</title></circle>`).join('')}<text x="55" y="258">${date(points[0].date)}</text><text x="755" y="258" text-anchor="end">${date(points.at(-1).date)}</text></svg>`;
}

function draw(){
 if(!data)return;
 const focus=groupsOf(data);
 const cards=basketMode==='all'?focus.all:focus[basketMode];
 const label=baskets[basketMode];
 const history=basketMode==='all'?E.basket(data,cards):T.basket(data,cards);
 const latest=history.points.find(p=>p.date===data.sourceDate);
 document.getElementById('set-index-title').textContent=label+'.';
 document.getElementById('thirtieth-summary').innerHTML=`<div class="set-stats">
  <div><span>Raw guide total</span><strong>${latest?.usd?money(latest.usd):'—'}</strong><small>${cards.length} singles · USD</small></div>
  <div><span>Raw index</span><strong>${latest?.value?latest.value.toFixed(2):'—'}</strong><small>100 on ${date(history.baseDate)}</small></div>
  <div><span>Since the start date</span><strong class="${latest?.value>=100?'positive':''}">${latest?.value?(latest.value>=100?'+':'')+(latest.value-100).toFixed(2)+'%':'—'}</strong><small>${label}</small></div>
  <div><span>Source date</span><strong class="set-source-day">${date(data.sourceDate)}</strong><small>${latest?.count??0} / ${cards.length} Raw guides</small></div>
 </div>`;
 const cutoff=period==='All'?'':new Date(Date.parse(data.sourceDate+'T12:00:00Z')-(period==='7D'?6:29)*86400000).toISOString().slice(0,10);
 const points=history.points.filter(p=>!cutoff||p.date>=cutoff);
 const indexReady=points.some(p=>E.positive(p.value));
 const chartValue=indexReady?(p=>p.value):(p=>p.usd);
 const chartLabel=indexReady?label+' Raw market-guide index':label+' Raw market-guide total in USD';
 const chartNote=basketMode==='all'
  ?(indexReady
    ?'195 fixed printings. Lines stop where prices are missing. The index is 100 on 8 October 2026.'
    :'195 fixed printings. The index start date is 8 October 2026. The index stays at — until a complete 195-card set of guides for that day is available.')
  :`${cards.length} fixed printings. This group is 100 on 8 October 2026 when that day’s guides are complete. Lines stop where prices are missing.`;
 document.getElementById('thirtieth-chart').innerHTML=chart(points,chartValue,chartLabel)+
  `<p class="set-chart-note">${chartNote}</p>`;
}

function rawPrice(point){
 return `<div class="set-price-bars"><div><span>Raw USD</span><b>${point?.[2]==='ok'?money(point[1]):'—'}</b></div></div>`;
}

function issueLabel(c){
 if(c.set==='ME: Mega Evolution Promo')return 'Day & Night promo · MEP'+c.number;
 if(c.set.endsWith('Classic Collection'))return 'Classic Collection · '+c.number;
 return c.number;
}

function ebayBuys(c,detail){
 const block=window.BTCommerce&&window.BTCommerce.ebayCardBlock;
 return block?block(c,window.BT_COMMERCE,{placement:'db',detail:!!detail,stack:!detail,pill:true,note:detail?'card':false}):'';
}

function cardMarkup(c,group,rank){
 const point=E.latest(data,c.key);
 const imageLabel=esc(c.name+' · '+c.number+' · '+c.set+' · English Holofoil');
 return `<article class="set-card">
  <button class="set-card-art" data-set-card="${c.key}" aria-label="Open ${esc(c.name.includes(c.number)?c.name:c.name+' '+c.number)}"><img src="${c.image}" alt="${imageLabel}" loading="lazy" width="200" height="280"></button>
  <div class="set-card-info">
   <span class="set-issue">${rank?'#'+rank+' · ':''}${esc(issueLabel(c))}</span>
   <h3>${esc(c.name.replace(/ - .*$/,''))}</h3><p>English · Holofoil</p>
   ${rawPrice(point)}
   <small>${point?date(point[0]):'No observations'} · ${point?.[2]==='ok'?'Raw guide':'Price unavailable'}</small>
   ${ebayBuys(c,false)}
   <button class="set-open" data-set-card="${c.key}">Open card &amp; history ↗</button>
  </div>
 </article>`;
}

function drawCards(){
 if(!data)return;
 const focus=groupsOf(data);
 const selected=collection==='all'?['all']:[collection];
 const query=search.trim().toLowerCase();
 let count=0,total=0;
 const html=selected.map(group=>{
  const cards=focus[group].filter(c=>!query||[c.name,c.number,c.set,c.set==='ME: Mega Evolution Promo'?'MEP'+c.number:''].join(' ').toLowerCase().includes(query));
  total+=focus[group].length;
  count+=cards.length;
  if(!cards.length)return '';
  const ordered=Factory.sortCards(cards,sort,group,key=>E.latest(data,key),Factory.chaseRankMap(chaseRoster));
  return `<h3 class="set-group-title">${galleryLabels[group]} <small>${ordered.length} / ${focus[group].length}</small></h3>`+
   ordered.map(c=>cardMarkup(c,group,group==='top20'?focus.top20.indexOf(c)+1:null)).join('');
 }).join('');
 document.getElementById('set-count').textContent=`${count} of ${total} cards`;
 const note=document.getElementById('set-ranking-note');note.hidden=collection!=='top20';
 note.textContent=`Ranked by Raw USD from ${focus.top20.length?E.rankedRaw(data).length:0} of ${data.cards.length} printings priced on ${date(data.sourceDate)}. Missing prices stay unranked.`;
 document.getElementById('set-grid').innerHTML=html||'<p class="set-status">No cards match that filter.</p>';
}

function unavailable(message){
 document.getElementById('thirtieth-summary').innerHTML=`<p class="set-status">${esc(message)} <button type="button" data-set-retry>Try again</button></p>`;
}

function openCard(key,button){
 const c=data?.cards.find(c=>c.key===key);if(!c)return;returnFocus=button;
 const rows=E.series(data,key),p=rows.at(-1);
 const product=c.image.match(/([0-9]+)\.jpg$/)[1];
 document.getElementById('set-dialog-body').innerHTML=`<div class="set-dialog-card"><img src="${c.image}" alt="${esc(c.name+' · '+c.number+' · English '+c.printing)}"><div><span class="kicker">${esc(c.number)} / ENGLISH</span><h2>${esc(c.name)}</h2><p>${esc(c.set)} · Holofoil</p>${rawPrice(p)}<p>Raw market guide, ${p?date(p[0]):'unavailable'}.</p><a href="https://www.tcgplayer.com/product/${product}" target="_blank" rel="noopener">Exact catalogue issue ↗</a>${ebayBuys(c,true)}</div></div><div class="set-popup-tabs" role="tablist" aria-label="Card details">${[['overview','Overview'],['evidence','Prices & sources'],['method','Method']].map(([id,label])=>`<button role="tab" id="set-tab-${id}" aria-controls="set-panel-${id}" aria-selected="${id==='overview'}" tabindex="${id==='overview'?0:-1}" data-set-tab="${id}">${label}</button>`).join('')}</div><section id="set-panel-overview" role="tabpanel" aria-labelledby="set-tab-overview"><div class="set-dialog-chart">${chart(rows.map(p=>({date:p[0],usd:p[2]==='ok'?p[1]:null})),p=>p.usd,'Dated Raw market guide in USD')}</div></section><section id="set-panel-evidence" role="tabpanel" aria-labelledby="set-tab-evidence" hidden><details class="set-observations" open><summary>All prices, dates and sources</summary><div><table><thead><tr><th>Date</th><th>Raw USD</th><th>Source / status</th></tr></thead><tbody>${[...rows].reverse().map(p=>`<tr><td>${date(p[0])}</td><td>${p[2]==='ok'?money(p[1]):'—'}</td><td>${esc(p[2]==='ok'?'TCGCSV market guide':p[2].replaceAll('_',' '))}${data.sources.filter(s=>s.day===p[0]).map(s=>` <a href="${esc(s.url)}" target="_blank" rel="noopener">Source ↗</a>`).join('')}</td></tr>`).join('')}</tbody></table></div></details></section><section id="set-panel-method" role="tabpanel" aria-labelledby="set-tab-method" hidden><h3>One printing. One price series.</h3><p>English · ${esc(c.set)} · ${esc(c.number)} · Holofoil. Raw observations are TCGplayer mixed-condition market guides supplied by TCGCSV. They are separate from Near Mint guides and completed-sale prices.</p><p>Missing values stay unpriced. These figures describe this printing; they are not a condition assessment, a grading outcome or a guaranteed resale price.</p><p class="set-credit">${CREDIT}</p></section>`;
 document.getElementById('set-dialog').showModal();
}

function stampSnapshot(value){
 const generated=new Date();
 return {...value,generatedAt:generated.toISOString(),expiresAt:new Date(generated.getTime()+9*60*1000).toISOString()};
}

async function loadDaily(signal){
 const [cacheRes,snapRes]=await Promise.all([
  fetch('data/market-cache/thirtieth-current.json',{cache:'no-store',signal}),
  fetch('thirtieth-market-snapshot.json',{cache:'no-store',signal})
 ]);
 if(!cacheRes.ok||!snapRes.ok)throw Error();
 const value=E.validate(stampSnapshot(Factory.adaptDailyCache(await snapRes.json(),await cacheRes.json())));
 if(!value)throw Error();
 return value;
}

async function loadRoster(signal){
 if(chaseRoster)return chaseRoster;
 const res=await fetch('data/market-rosters/'+E.spec.index+'.json',{cache:'no-store',signal});
 if(!res.ok)throw Error();
 chaseRoster=await res.json();
 return chaseRoster;
}

function drawChase(){
 const slot=document.getElementById('chase-slot');
 if(!slot)return;
 slot.innerHTML=data&&chaseRoster?Factory.chaseHtml(chaseRoster,data,E.latest,{esc,money,date}):'';
}

async function load(){
 const token=++epoch;
 controller?.abort();
 controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),8000);
 let value=null;
 try{
  value=await loadDaily(controller.signal);
  if(!active||token!==epoch)return;
  data=value;
  try{await loadRoster(controller.signal);}catch(err){}
  if(!active||token!==epoch)return;
  drawChase();
  draw();
  drawCards();
  clearTimeout(expiry);
  expiry=setTimeout(()=>{if(active){unavailable('Refreshing the shared market data…');load();}},Math.max(0,Date.parse(data.expiresAt)-Date.now()));
 }catch(e){
  if(active&&token===epoch)unavailable('The shared market data could not be checked.');
 }finally{
  clearTimeout(timeout);
 }
}

function mount(){
 active=true;
 const host=document.querySelector('.thirtieth-market');
 if(!host)return;
 document.getElementById('set-search').oninput=e=>{search=e.target.value;drawCards();};
 document.getElementById('set-collection').value=collection;
 document.getElementById('set-collection').onchange=e=>{collection=e.target.value;drawCards();};
 document.getElementById('set-sort').onchange=e=>{sort=e.target.value;drawCards();};
 const root=document.getElementById('main');
 root.onclick=e=>{
  if(e.target.closest('.ebay-bar a'))return;
  const tab=e.target.closest('[data-set-tab]');
  if(tab){
   root.querySelectorAll('[data-set-tab]').forEach(b=>{const on=b===tab;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;document.getElementById('set-panel-'+b.dataset.setTab).hidden=!on;});
   return;
  }
  const g=e.target.closest('[data-set-basket]'),p=e.target.closest('[data-set-period]'),card=e.target.closest('[data-set-card]');
  if(g){basketMode=g.dataset.setBasket;root.querySelectorAll('[data-set-basket]').forEach(b=>b.setAttribute('aria-pressed',String(b===g)));draw();}
  else if(p){period=p.dataset.setPeriod;root.querySelectorAll('[data-set-period]').forEach(b=>b.setAttribute('aria-pressed',String(b===p)));draw();}
  else if(card)openCard(card.dataset.setCard,card);
  else if(e.target.closest('[data-set-retry]'))load();
  else if(e.target.closest('[data-set-scroll]')){e.preventDefault();document.getElementById('thirtieth-cards').scrollIntoView({block:'start'});}
 };
 const dialog=document.getElementById('set-dialog');
 dialog.querySelector('.set-dialog-close').onclick=()=>dialog.close();
 dialog.addEventListener('close',()=>returnFocus?.focus());
 dialog.addEventListener('keydown',e=>{
  const tab=e.target.closest('[data-set-tab]');
  if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
  e.preventDefault();
  const tabs=[...dialog.querySelectorAll('[data-set-tab]')],i=tabs.indexOf(tab),next=e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3;
  tabs[next].click();tabs[next].focus();
 });
 load();
 timer=setInterval(load,300000);
}

function unmount(){epoch++;active=false;controller?.abort();clearInterval(timer);clearTimeout(expiry);data=null;returnFocus=null;const main=document.getElementById('main');if(main)main.onclick=null;}
window.BTThirtieth={page,mount,unmount};
})();
