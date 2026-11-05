(()=>{'use strict';
const E=window.BTThirtiethEngine,esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n),date=s=>new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
let epoch=0,data=null,controller=null,timer=null,expiry=null,active=false,search='',collection='all',period='All',basketMode='chases',sort='default',returnFocus=null;
const groups={chases:'Chase cards',pikachu:'The 30 Pikachu',rgb:'RGB Mew'};
function page(){
 const heroes=[[714372,'Charizard 4/102 Classic Collection'],[712953,'Pikachu ex 149/128'],[712934,'Pikachu 023/128']];
 return `
 <section class="page-intro thirtieth-intro">
  <a class="back-link" href="market.html">← All markets</a>
  <div class="thirtieth-hero">
   <div>
    <span class="kicker red-text">ENGLISH / RAW MARKET GUIDES</span>
    <h1>30th Anniversary <em>Index.</em></h1>
    <p>Follow the anniversary chases, collect the 30 numbered Pikachu, and track the three RGB Mews. Open any card for its dated Raw prices.</p>
    <a class="btn red" href="#thirtieth-cards" data-set-scroll>Explore the cards ↓</a>
   </div>
   <div class="thirtieth-fan" aria-label="English 30th Celebration cards">${heroes.map(([id,label])=>`<img src="assets/thirtieth/${id}.jpg" alt="${label} · English 30th Celebration catalogue artwork">`).join('')}</div>
  </div>
 </section>
 <section class="thirtieth-market" aria-label="30th market tracker">
  <div class="set-chart-head">
   <div><span class="kicker">RAW GUIDE INDEX</span><h2 id="set-index-title">${groups[basketMode]}.</h2></div>
   <div class="shared-grades" role="group" aria-label="Index basket">${Object.entries(groups).map(([id,label])=>`<button data-set-basket="${id}" aria-pressed="${id===basketMode}">${label}</button>`).join('')}</div>
  </div>
  <div id="thirtieth-summary" aria-live="polite"><p class="set-status">Loading the latest Raw guides…</p></div>
  <div class="shared-periods" role="group" aria-label="History window">${['7D','30D','All'].map(p=>`<button data-set-period="${p}" aria-pressed="${p===period}">${p==='All'?'All history':p}</button>`).join('')}</div>
  <div id="thirtieth-chart"></div>
  <details class="set-method">
   <summary>How the charts work</summary>
   <p>Each chart tracks a fixed group: 13 chases, Pikachu 023/128 through 052/128, or the three RGB Mews. We add the Raw guides for one of each printing and set that total to 100 on 8 October 2026. A day needs every price in its group. Missing dates stay as gaps.</p>
   <p>Prices are TCGplayer mixed-condition market guides via <a href="https://tcgcsv.com/faq" target="_blank" rel="noopener">TCGCSV</a>. Card histories show each dated observation in USD.</p>
  </details>
 </section>
 <section class="thirtieth-catalogue" id="thirtieth-cards">
  <header class="set-list-head"><div><span class="kicker">EXACT ENGLISH PRINTINGS</span><h2>Find your card.</h2></div><span id="set-count" aria-live="polite"></span></header>
  <div class="set-tools">
   <label>Find a card<input type="search" id="set-search" placeholder="Name or card number" autocomplete="off"></label>
   <label>Collection<select id="set-collection"><option value="all">All selected cards</option>${Object.entries(groups).map(([id,label])=>`<option value="${id}">${label}</option>`).join('')}</select></label>
   <label>Sort<select id="set-sort"><option value="default">Collection order</option><option value="price">Raw price: high to low</option><option value="number">Card number</option><option value="name">Name</option></select></label>
  </div>
  <div class="set-grid" id="set-grid"></div>
  <p class="set-credit">Catalogue artwork: TCGplayer. Card names and artwork © Pokémon.</p>
 </section>
 <dialog class="set-dialog" id="set-dialog"><button type="button" class="set-dialog-close" aria-label="Close card">×</button><div id="set-dialog-body"></div></dialog>`;
}
function chart(points,value,label){const good=points.filter(p=>E.positive(value(p)));if(!good.length)return '<p class="set-status">No supported observations for this view.</p>';const lo=Math.min(...good.map(value)),hi=Math.max(...good.map(value)),span=hi-lo||Math.max(1,hi*.1),start=Date.parse(points[0].date),end=Date.parse(points.at(-1).date),x=p=>55+(Date.parse(p.date)-start)/(end-start||86400000)*700,y=p=>215-(value(p)-lo+span*.1)/(span*1.2)*170;const lines=E.segments(points,value).filter(a=>a.length>1).map(a=>`<path d="${a.map((p,i)=>(i?'L':'M')+x(p).toFixed(2)+','+y(p).toFixed(2)).join(' ')}"/>`).join('');return `<svg viewBox="0 0 800 270" role="img" aria-label="${esc(label)}"><text x="7" y="31">${hi.toLocaleString('en-US',{maximumFractionDigits:1})}</text><text x="7" y="222">${lo.toLocaleString('en-US',{maximumFractionDigits:1})}</text><line x1="55" y1="230" x2="760" y2="230"/>${lines}${good.map(p=>`<circle cx="${x(p)}" cy="${y(p)}" r="3"><title>${date(p.date)} · ${value(p).toFixed(2)}</title></circle>`).join('')}<text x="55" y="258">${date(points[0].date)}</text><text x="755" y="258" text-anchor="end">${date(points.at(-1).date)}</text></svg>`;}
function draw(){
 if(!data)return;
 const cards=E.focus(data)[basketMode];
 const label=groups[basketMode];
 const history=E.basket(data,cards);
 const latest=history.points.find(p=>p.date===data.sourceDate);
 document.getElementById('set-index-title').textContent=label+'.';
 document.getElementById('thirtieth-summary').innerHTML=`<div class="set-stats">
  <div><span>Raw guide total</span><strong>${latest?.usd?money(latest.usd):'—'}</strong><small>${cards.length} singles · USD</small></div>
  <div><span>Raw index</span><strong>${latest?.value?latest.value.toFixed(2):'—'}</strong><small>100 on ${date(history.baseDate)}</small></div>
  <div><span>Since the baseline</span><strong class="${latest?.value>=100?'positive':''}">${latest?.value?(latest.value>=100?'+':'')+(latest.value-100).toFixed(2)+'%':'—'}</strong><small>${label}</small></div>
  <div><span>Source date</span><strong class="set-source-day">${date(data.sourceDate)}</strong><small>${latest?.count??0} / ${cards.length} Raw guides</small></div>
 </div>`;
 const cutoff=period==='All'?'':new Date(Date.parse(data.sourceDate+'T12:00:00Z')-(period==='7D'?6:29)*86400000).toISOString().slice(0,10);
 const points=history.points.filter(p=>!cutoff||p.date>=cutoff);
 document.getElementById('thirtieth-chart').innerHTML=chart(points,p=>p.value,label+' Raw market-guide index')+
  `<p class="set-chart-note">${cards.length} fixed printings. Lines stop where prices are missing.</p>`;
}
function rawPrice(point){
 return `<div class="set-price-bars"><div><span>Raw USD</span><b>${point?.[2]==='ok'?money(point[1]):'—'}</b></div></div>`;
}
function cardMarkup(c,group){
 const point=E.latest(data,c.key);
 const issue=group==='pikachu'?'Pikachu '+(parseInt(c.number,10)-22)+' of 30':
  c.set.endsWith('Classic Collection')?'Classic Collection':'Main set';
 const imageLabel=esc(c.name+' · '+c.number+' · '+c.set+' · English Holofoil');
 return `<article class="set-card">
  <button class="set-card-art" data-set-card="${c.key}" aria-label="Open ${esc(c.name.includes(c.number)?c.name:c.name+' '+c.number)}"><img src="${c.image}" alt="${imageLabel}" loading="lazy" width="200" height="280"></button>
  <div class="set-card-info">
   <span class="set-issue">${issue} · ${esc(c.number)}</span>
   <h3>${esc(c.name.replace(/ - .*$/,''))}</h3><p>English · Holofoil</p>
   ${rawPrice(point)}
   <small>${point?date(point[0]):'No observations'} · ${point?.[2]==='ok'?'Raw guide':'Price unavailable'}</small>
   <button class="set-open" data-set-card="${c.key}">Open card &amp; history ↗</button>
  </div>
 </article>`;
}
function drawCards(){
 if(!data)return;
 const focus=E.focus(data);
 const selected=collection==='all'?Object.keys(groups):[collection];
 const query=search.trim().toLowerCase();
 let count=0,total=0;
 const html=selected.map(group=>{
  const cards=focus[group].filter(c=>!query||[c.name,c.number,c.set].join(' ').toLowerCase().includes(query));
  total+=focus[group].length;
  count+=cards.length;
  if(!cards.length)return '';
  if(sort==='name')cards.sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true}));
  else if(sort==='number'||sort==='default'&&group==='pikachu')cards.sort((a,b)=>a.number.localeCompare(b.number,undefined,{numeric:true}));
  else if(sort==='price'||sort==='default'&&group==='chases')cards.sort((a,b)=>(E.latest(data,b.key)?.[1]||0)-(E.latest(data,a.key)?.[1]||0));
  return `<h3 class="set-group-title">${groups[group]} <small>${cards.length} / ${focus[group].length}</small></h3>`+
   cards.map(c=>cardMarkup(c,group)).join('');
 }).join('');
 document.getElementById('set-count').textContent=`${count} of ${total} cards`;
 document.getElementById('set-grid').innerHTML=html||'<p class="set-status">No matching cards. Try another name or number.</p>';
}
function openCard(key,button){const c=data?.cards.find(c=>c.key===key);if(!c)return;returnFocus=button;const rows=E.series(data,key),p=rows.at(-1);document.getElementById('set-dialog-body').innerHTML=`<div class="set-dialog-card"><img src="${c.image}" alt="${esc(c.name+' · '+c.number+' · English '+c.printing)}"><div><span class="kicker">${esc(c.number)} / ENGLISH</span><h2>${esc(c.name)}</h2><p>${esc(c.set)} · Holofoil</p>${rawPrice(p)}<p>Raw market guide, ${p?date(p[0]):'unavailable'}.</p><a href="https://www.tcgplayer.com/product/${c.image.match(/([0-9]+)\.jpg$/)[1]}" target="_blank" rel="noopener">Exact catalogue issue ↗</a></div></div><div class="set-popup-tabs" role="tablist" aria-label="Card details">${[['overview','Overview'],['evidence','Prices & sources'],['method','Method']].map(([id,label])=>`<button role="tab" id="set-tab-${id}" aria-controls="set-panel-${id}" aria-selected="${id==='overview'}" tabindex="${id==='overview'?0:-1}" data-set-tab="${id}">${label}</button>`).join('')}</div><section id="set-panel-overview" role="tabpanel" aria-labelledby="set-tab-overview"><div class="set-dialog-chart">${chart(rows.map(p=>({date:p[0],usd:p[2]==='ok'?p[1]:null})),p=>p.usd,'Dated Raw market guide in USD')}</div></section><section id="set-panel-evidence" role="tabpanel" aria-labelledby="set-tab-evidence" hidden><details class="set-observations" open><summary>All prices, dates and sources</summary><div><table><thead><tr><th>Date</th><th>Raw USD</th><th>Source / status</th></tr></thead><tbody>${[...rows].reverse().map(p=>`<tr><td>${date(p[0])}</td><td>${p[2]==='ok'?money(p[1]):'—'}</td><td>${esc(p[2]==='ok'?'TCGCSV market guide':p[2].replaceAll('_',' '))}${data.sources.filter(s=>s.day===p[0]&&(s.url.includes('/archive/')||s.url.endsWith('/3/'+(c.set.endsWith('Classic Collection')?'24837':'24722')+'/prices'))).map(s=>` <a href="${esc(s.url)}" target="_blank" rel="noopener">Source ↗</a>`).join('')}</td></tr>`).join('')}</tbody></table></div></details></section><section id="set-panel-method" role="tabpanel" aria-labelledby="set-tab-method" hidden><h3>One printing. One price series.</h3><p>English · ${esc(c.set)} · ${esc(c.number)} · Holofoil. Raw observations are TCGplayer mixed-condition market guides supplied by TCGCSV. They are separate from Near Mint guides and completed-sale prices.</p><p>Missing values and reviewed anomalies are unpriced. Earlier source values describe this printing retrospectively; they are not a condition assessment, a grading outcome or a guaranteed resale price.</p><p class="set-credit">Catalogue reference: TCGplayer. Artwork © Pokémon.</p></section>`;document.getElementById('set-dialog').showModal();}
function unavailable(message){clearTimeout(expiry);data=null;document.getElementById('thirtieth-summary').innerHTML=`<p class="set-status">${esc(message)} <button data-set-retry>Try again</button></p>`;document.getElementById('thirtieth-chart').replaceChildren();document.getElementById('set-grid').replaceChildren();document.getElementById('set-count').textContent='';document.getElementById('set-dialog')?.close();}
async function load(){if(!active)return;const token=++epoch;controller?.abort();controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),12000);if(data&&Date.parse(data.expiresAt)<=Date.now())unavailable('Refreshing the shared market data…');try{const res=await fetch('shared-market-config.json',{cache:'no-store',signal:controller.signal});if(!res.ok)throw Error();const config=await res.json();if(!config.enabled||!config.endpoint)throw Error();const url=new URL(config.endpoint,location.href);if(url.protocol!=='https:'&&!(location.hostname==='127.0.0.1'&&url.origin===location.origin))throw Error();url.search=new URLSearchParams({index:'thirtieth-anniversary',days:'366'});const r=await fetch(url,{credentials:'omit',cache:'no-store',signal:controller.signal});if(!r.ok)throw Error();const text=await r.text();if(text.length>3000000)throw Error();const value=E.validate(JSON.parse(text));if(!active||token!==epoch)return;if(!value){unavailable('The set data is temporarily unavailable.');return;}data=value;draw();drawCards();clearTimeout(expiry);expiry=setTimeout(()=>{if(active){unavailable('Refreshing the shared market data…');load();}},Math.max(0,Date.parse(data.expiresAt)-Date.now()));}catch(e){if(active&&token===epoch)unavailable('The shared market data could not be checked.');}finally{clearTimeout(timeout);}}
function mount(){active=true;const host=document.querySelector('.thirtieth-market');if(!host)return;document.getElementById('set-search').oninput=e=>{search=e.target.value;drawCards();};document.getElementById('set-collection').onchange=e=>{collection=e.target.value;drawCards();};document.getElementById('set-sort').onchange=e=>{sort=e.target.value;drawCards();};const root=document.getElementById('main');root.onclick=e=>{const tab=e.target.closest('[data-set-tab]');if(tab){root.querySelectorAll('[data-set-tab]').forEach(b=>{const on=b===tab;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;document.getElementById('set-panel-'+b.dataset.setTab).hidden=!on;});return;}const g=e.target.closest('[data-set-basket]'),p=e.target.closest('[data-set-period]'),card=e.target.closest('[data-set-card]');if(g){basketMode=g.dataset.setBasket;root.querySelectorAll('[data-set-basket]').forEach(b=>b.setAttribute('aria-pressed',String(b===g)));draw();}else if(p){period=p.dataset.setPeriod;root.querySelectorAll('[data-set-period]').forEach(b=>b.setAttribute('aria-pressed',String(b===p)));draw();}else if(card)openCard(card.dataset.setCard,card);else if(e.target.closest('[data-set-retry]'))load();else if(e.target.closest('[data-set-scroll]')){e.preventDefault();document.getElementById('thirtieth-cards').scrollIntoView({block:'start'});}};const dialog=document.getElementById('set-dialog');dialog.querySelector('.set-dialog-close').onclick=()=>dialog.close();dialog.addEventListener('close',()=>returnFocus?.focus());dialog.addEventListener('keydown',e=>{const tab=e.target.closest('[data-set-tab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...dialog.querySelectorAll('[data-set-tab]')],i=tabs.indexOf(tab),next=e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3;tabs[next].click();tabs[next].focus();});load();timer=setInterval(load,300000);}
function unmount(){epoch++;active=false;controller?.abort();clearInterval(timer);clearTimeout(expiry);data=null;returnFocus=null;const main=document.getElementById('main');if(main)main.onclick=null;}
window.BTThirtieth={page,mount,unmount};
})();
