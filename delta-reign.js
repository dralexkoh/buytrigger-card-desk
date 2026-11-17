(()=>{'use strict';
const Factory=window.BTSetIndexEngine;
const E=Factory.createEngine({
 index:'delta-reign',
 cardCount:141,
 baselineDate:'2026-11-06',
 proposedBaseline:false,
 imagePattern:'assets/delta-reign/[0-9]+\\.jpg',
 keyPattern:'en-delta-reign-[0-9]+-(holofoil|normal)',
 sourcePattern:'https://tcgcsv\\.com/(?:archive/tcgplayer/prices-\\d{4}-\\d{2}-\\d{2}\\.ppmd\\.7z|tcgplayer/3/24831/prices)',
 allowedSets:['ME06: Delta Reign'],
 allowedPrintings:['Holofoil','Normal'],
 gallery:{
  secret:c=>parseInt(c.number,10)>103,
  'special-illustration':c=>c.rarity==='Special Illustration Rare',
  'illustration':c=>c.rarity==='Illustration Rare',
  'mega-hyper':c=>c.rarity==='Mega Hyper Rare'
 }
});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);
const date=s=>new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
let epoch=0,data=null,controller=null,timer=null,expiry=null,active=false,search='',collection='all',period='All',sort='default',returnFocus=null;
const CREDIT='Card image: The Pokémon Company / pokemon.com';
const heroes=[[728061,'Mega Rayquaza ex 138/103'],[728062,'Mega Rayquaza ex 141/103'],[726574,'Raikou ex 136/103']];
const galleryLabels={all:'All 141 cards',top20:'Top 20 by Raw',secret:'Secret rares', 'special-illustration':'Special Illustration Rares',illustration:'Illustration Rares','mega-hyper':'Mega Hyper Rare'};

function page(){
 return `
 <section class="page-intro thirtieth-intro">
  <a class="back-link" href="market.html">← All markets</a>
  <div class="thirtieth-hero">
   <div>
    <span class="kicker red-text">ENGLISH / RAW MARKET GUIDES</span>
    <h1>Delta Reign <em>Index.</em></h1>
    <p>All 141 English cards from ME06: Delta Reign, one of each base printing. Open any card for its dated Raw market guides. Prices are dated 16 November 2026 and will stay on that date until the daily refresh for this set is switched on. The index starts at 100 on 6 November 2026, the set’s launch day.</p>
    <a class="btn red" href="#delta-reign-cards" data-set-scroll>Explore the cards ↓</a>
   </div>
   <div class="thirtieth-fan" aria-label="English Delta Reign cards">${heroes.map(([id,label])=>`<img src="assets/delta-reign/${id}.jpg" alt="${label} · English ME06: Delta Reign official card image">`).join('')}</div>
  </div>
 </section>
 <section class="thirtieth-market" aria-label="Delta Reign market tracker">
  <div class="set-chart-head">
   <div><span class="kicker">RAW GUIDE INDEX</span><h2 id="set-index-title">All 141 cards.</h2></div>
  </div>
  <div id="delta-reign-summary" aria-live="polite"><p class="set-status">Loading the latest Raw guides…</p></div>
  <div class="shared-periods" role="group" aria-label="History window">${['7D','30D','All'].map(p=>`<button data-set-period="${p}" aria-pressed="${p===period}">${p==='All'?'All history':p}</button>`).join('')}</div>
  <div id="delta-reign-chart"></div>
  <details class="set-method">
   <summary>How the chart works</summary>
   <p>The index adds the Raw market guide for one of each of the 141 English base printings and sets that total to 100 on 6 November 2026, the set’s launch day. A day needs every price in the set. Missing dates stay as gaps.</p>
   <p>Prices are TCGplayer mixed-condition market guides via <a href="https://tcgcsv.com/faq" target="_blank" rel="noopener">TCGCSV</a>, in USD. This snapshot currently shows the launch-day guides and the 16 November 2026 guides from a verified handoff. Daily points will fill in once the regular refresh for this set is switched on. These are guide prices, not verified sales or offers.</p>
  </details>
 </section>
 <section class="thirtieth-catalogue" id="delta-reign-cards">
  <header class="set-list-head"><div><span class="kicker">EXACT ENGLISH PRINTINGS</span><h2>Find your card.</h2></div><span id="set-count" aria-live="polite"></span></header>
  <div class="set-tools">
   <label>Find a card<input type="search" id="set-search" placeholder="Name or card number" autocomplete="off"></label>
   <label>Collection<select id="set-collection"><option value="all">All 141 cards</option><option value="top20">Top 20 by Raw</option><option value="secret">Secret rares</option><option value="special-illustration">Special Illustration Rares</option><option value="illustration">Illustration Rares</option><option value="mega-hyper">Mega Hyper Rare</option></select></label>
   <label>Sort<select id="set-sort"><option value="default">Card number</option><option value="price">Raw price: high to low</option><option value="number">Card number</option><option value="name">Name</option></select></label>
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
 const cards=E.focus(data).all;
 const history=E.basket(data,cards);
 const latest=history.points.find(p=>p.date===data.sourceDate);
 document.getElementById('delta-reign-summary').innerHTML=`<div class="set-stats">
  <div><span>Raw guide total</span><strong>${latest?.usd?money(latest.usd):'—'}</strong><small>141 singles · USD</small></div>
  <div><span>Raw index</span><strong>${latest?.value?latest.value.toFixed(2):'—'}</strong><small>100 on ${date(history.baseDate)}</small></div>
  <div><span>Since the start date</span><strong class="${latest?.value>=100?'positive':''}">${latest?.value?(latest.value>=100?'+':'')+(latest.value-100).toFixed(2)+'%':'—'}</strong><small>All 141 cards</small></div>
  <div><span>Source date</span><strong class="set-source-day">${date(data.sourceDate)}</strong><small>${latest?.count??0} / ${cards.length} Raw guides</small></div>
 </div>`;
 const cutoff=period==='All'?'':new Date(Date.parse(data.sourceDate+'T12:00:00Z')-(period==='7D'?6:29)*86400000).toISOString().slice(0,10);
 const points=history.points.filter(p=>!cutoff||p.date>=cutoff);
 document.getElementById('delta-reign-chart').innerHTML=chart(points,p=>p.value,'Delta Reign Raw market-guide index')+
  `<p class="set-chart-note">141 fixed printings. Lines stop where prices are missing. The index is 100 on 6 November 2026, the set’s launch day.</p>`;
}

function rawPrice(point){
 return `<div class="set-price-bars"><div><span>Raw USD</span><b>${point?.[2]==='ok'?money(point[1]):'—'}</b></div></div>`;
}

function issueLabel(c){
 const n=parseInt(c.number,10);
 if(n>103)return 'Secret rare · '+c.number;
 return c.number;
}

function cardMarkup(c,group,rank){
 const point=E.latest(data,c.key);
 const imageLabel=esc(c.name+' · '+c.number+' · '+c.set+' · English '+c.printing);
 return `<article class="set-card">
  <button class="set-card-art" data-set-card="${c.key}" aria-label="Open ${esc(c.name.includes(c.number)?c.name:c.name+' '+c.number)}"><img src="${c.image}" alt="${imageLabel}" loading="lazy" width="200" height="279"></button>
  <div class="set-card-info">
   <span class="set-issue">${rank?'#'+rank+' · ':''}${esc(issueLabel(c))} · ${esc(c.rarity||c.printing)}</span>
   <h3>${esc(c.name.replace(/ - .*$/,''))}</h3><p>English · ${esc(c.printing)}</p>
   ${rawPrice(point)}
   <small>${point?date(point[0]):'No observations'} · ${point?.[2]==='ok'?'Raw guide':'Price unavailable'}</small>
   <button class="set-open" data-set-card="${c.key}">Open card &amp; history ↗</button>
  </div>
 </article>`;
}

function drawCards(){
 if(!data)return;
 const focus=E.focus(data);
 const ranked=E.rankedRaw(data);focus.top20=ranked.slice(0,20);
 const selected=collection==='all'?['all']:[collection];
 const query=search.trim().toLowerCase();
 let count=0,total=0;
 const html=selected.map(group=>{
  const cards=focus[group].filter(c=>!query||[c.name,c.number,c.set,c.rarity,c.printing].join(' ').toLowerCase().includes(query));
  total+=focus[group].length;
  count+=cards.length;
  if(!cards.length)return '';
  if(sort==='name')cards.sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true}));
  else if(sort==='price'||(sort==='default'&&group==='top20'))cards.sort((a,b)=>(E.latest(data,b.key)?.[1]||0)-(E.latest(data,a.key)?.[1]||0));
  else cards.sort((a,b)=>a.number.localeCompare(b.number,undefined,{numeric:true}));
  return `<h3 class="set-group-title">${galleryLabels[group]} <small>${cards.length} / ${focus[group].length}</small></h3>`+
   cards.map(c=>cardMarkup(c,group,group==='top20'?focus.top20.indexOf(c)+1:null)).join('');
 }).join('');
 document.getElementById('set-count').textContent=`${count} of ${total} cards`;
 const note=document.getElementById('set-ranking-note');note.hidden=collection!=='top20';
 note.textContent=`Ranked by Raw USD from ${ranked.length} of ${data.cards.length} printings priced on ${date(data.sourceDate)}. Missing prices stay unranked.`;
 document.getElementById('set-grid').innerHTML=html||'<p class="set-status">No matching cards. Try another name or number.</p>';
}

function unavailable(message){
 document.getElementById('delta-reign-summary').innerHTML=`<p class="set-status">${esc(message)} <button type="button" data-set-retry>Try again</button></p>`;
}

function openCard(key,button){
 const c=data?.cards.find(c=>c.key===key);if(!c)return;returnFocus=button;
 const rows=E.series(data,key),p=rows.at(-1);
 const product=c.image.match(/([0-9]+)\.jpg$/)[1];
 document.getElementById('set-dialog-body').innerHTML=`<div class="set-dialog-card"><img src="${c.image}" alt="${esc(c.name+' · '+c.number+' · English '+c.printing)}"><div><span class="kicker">${esc(c.number)} / ENGLISH</span><h2>${esc(c.name)}</h2><p>${esc(c.set)} · ${esc(c.printing)} · ${esc(c.rarity||'')}</p>${rawPrice(p)}<p>Raw market guide, ${p?date(p[0]):'unavailable'}.</p><a href="https://www.tcgplayer.com/product/${product}" target="_blank" rel="noopener">Exact catalogue issue ↗</a></div></div><div class="set-popup-tabs" role="tablist" aria-label="Card details">${[['overview','Overview'],['evidence','Prices & sources'],['method','Method']].map(([id,label])=>`<button role="tab" id="set-tab-${id}" aria-controls="set-panel-${id}" aria-selected="${id==='overview'}" tabindex="${id==='overview'?0:-1}" data-set-tab="${id}">${label}</button>`).join('')}</div><section id="set-panel-overview" role="tabpanel" aria-labelledby="set-tab-overview"><div class="set-dialog-chart">${chart(rows.map(p=>({date:p[0],usd:p[2]==='ok'?p[1]:null})),p=>p.usd,'Dated Raw market guide in USD')}</div></section><section id="set-panel-evidence" role="tabpanel" aria-labelledby="set-tab-evidence" hidden><details class="set-observations" open><summary>All prices, dates and sources</summary><div><table><thead><tr><th>Date</th><th>Raw USD</th><th>Source / status</th></tr></thead><tbody>${[...rows].reverse().map(p=>`<tr><td>${date(p[0])}</td><td>${p[2]==='ok'?money(p[1]):'—'}</td><td>${esc(p[2]==='ok'?'TCGCSV market guide':p[2].replaceAll('_',' '))}${data.sources.filter(s=>s.day===p[0]).map(s=>` <a href="${esc(s.url)}" target="_blank" rel="noopener">Source ↗</a>`).join('')}</td></tr>`).join('')}</tbody></table></div></details></section><section id="set-panel-method" role="tabpanel" aria-labelledby="set-tab-method" hidden><h3>One printing. One price series.</h3><p>English · ${esc(c.set)} · ${esc(c.number)} · ${esc(c.printing)}. Raw observations are TCGplayer mixed-condition market guides supplied by TCGCSV. They are separate from Near Mint guides and completed-sale prices.</p><p>Missing values stay unpriced. These figures describe this printing; they are not a condition assessment, a grading outcome or a guaranteed resale price.</p><p class="set-credit">${CREDIT}</p></section>`;
 document.getElementById('set-dialog').showModal();
}

function stampSnapshot(value){
 const generated=new Date();
 const copy={...value,generatedAt:generated.toISOString(),expiresAt:new Date(generated.getTime()+9*60*1000).toISOString()};
 return copy;
}

async function loadSnapshot(signal){
 const res=await fetch('delta-reign-market-snapshot.json',{cache:'no-store',signal});
 if(!res.ok)throw Error();
 const value=E.validate(stampSnapshot(await res.json()));
 if(!value)throw Error();
 return value;
}

async function load(){
 if(!active)return;
 const token=++epoch;
 controller?.abort();
 controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),12000);
 if(data&&Date.parse(data.expiresAt)<=Date.now())unavailable('Refreshing the shared market data…');
 let value=null;
 try{
  const res=await fetch('shared-market-config.json',{cache:'no-store',signal:controller.signal});
  if(res.ok){
   const config=await res.json();
   if(config.enabled&&config.endpoint){
    const url=new URL(config.endpoint,location.href);
    if(url.protocol==='https:'||(location.hostname==='127.0.0.1'&&url.origin===location.origin)){
     url.search=new URLSearchParams({index:'delta-reign',days:'366'});
     const r=await fetch(url,{credentials:'omit',cache:'no-store',signal:controller.signal});
     if(r.ok){
      const text=await r.text();
      if(text.length<=3000000){
       const parsed=JSON.parse(text);
       if(parsed&&parsed.available!==false)value=E.validate(parsed);
      }
     }
    }
   }
  }
 }catch(e){
  value=null;
 }
 try{
  if(!value)value=await loadSnapshot();
  if(!active||token!==epoch)return;
  data=value;
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
  const tab=e.target.closest('[data-set-tab]');
  if(tab){
   root.querySelectorAll('[data-set-tab]').forEach(b=>{const on=b===tab;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;document.getElementById('set-panel-'+b.dataset.setTab).hidden=!on;});
   return;
  }
  const p=e.target.closest('[data-set-period]'),card=e.target.closest('[data-set-card]');
  if(p){period=p.dataset.setPeriod;root.querySelectorAll('[data-set-period]').forEach(b=>b.setAttribute('aria-pressed',String(b===p)));draw();}
  else if(card)openCard(card.dataset.setCard,card);
  else if(e.target.closest('[data-set-retry]'))load();
  else if(e.target.closest('[data-set-scroll]')){e.preventDefault();document.getElementById('delta-reign-cards').scrollIntoView({block:'start'});}
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
window.BTDeltaReign={page,mount,unmount};
})();
