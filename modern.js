(()=>{
'use strict';
const root=document.getElementById('modern-preview'), data=window.MODERN_PREVIEW_DATA, cards=data.cards;
const $=s=>root.querySelector(s), $$=s=>[...root.querySelectorAll(s)];
const grades=['Raw','PSA 9','PSA 10'];
const state={mode:'snapshot',grade:'Raw',period:'YTD',view:'gallery',query:'',set:'all',sort:'rank',priced:false,limit:12,inspect:305};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>n==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
const exactMoney=n=>n==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);
const signed=(n,d=2)=>(n>=0?'+':'−')+Math.abs(n).toFixed(d);
const byId=id=>cards.find(c=>c.id===Number(id));
const dates=Array.from({length:306},(_,d)=>new Date(Date.UTC(2026,0,1+d)));
const dateLabel=d=>dates[d].toLocaleDateString('en-GB',{day:'numeric',month:'short',timeZone:'UTC'});
const fullDate=s=>new Date(s+'T00:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
function image(c,extra=''){extra=extra.replace('loading="lazy"','loading="eager"');return `<img src="${esc(c.image)}" alt="${esc(c.name+' · '+c.set+' · '+c.number)}" ${extra}>`;}
function wireImageFallback(scope=root){scope.querySelectorAll('img').forEach(img=>{if(img.dataset.fallbackBound)return;img.dataset.fallbackBound='yes';img.addEventListener('error',()=>{img.dataset.failed='true';img.style.display='none';const label=document.createElement('span');label.className='image-failed';label.textContent='Artwork unavailable';img.after(label);});});}
$$('[data-brand]').forEach(img=>img.src=data[img.dataset.brand]);
$('#card-fan').innerHTML=[10,20,6,14,1].map(id=>image(byId(id),'class="fan-card"')).join('');
const setCounts=Object.entries(cards.reduce((acc,c)=>(acc[c.set]=(acc[c.set]||0)+1,acc),{})).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
$('#set-filter').innerHTML+=[...setCounts].sort((a,b)=>a[0].localeCompare(b[0])).map(([s])=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');
$('#set-bars').innerHTML=setCounts.slice(0,5).map(([s,n])=>`<div class="data-bar-row"><span>${esc(s)}</span><div class="bar-track"><span style="width:${n/7*100}%"></span></div><b>${n} / 90</b></div>`).join('')+`<div class="data-bar-row"><span>All other sets</span><div></div><b>${90-setCounts.slice(0,5).reduce((a,x)=>a+x[1],0)} / 90</b></div>`;
$('#coverage-bars').innerHTML=grades.map(g=>`<div class="data-bar-row"><span>${g}</span><div class="bar-track"><span style="width:${data.coverage[g]/90*100}%"></span></div><b>${data.coverage[g]}/90</b></div>`).join('');
$('#entrant-slots').innerHTML=Array.from({length:10},(_,i)=>`<div class="entrant-slot"><span>POSITION</span><b>${91+i}</b><small>To research</small></div>`).join('');
$('#sale-examples').innerHTML='<p class="scenario-note">Public sale-count and price-distribution evidence is being prepared. Exact card source links are available in each research file.</p>';


function press(selector,key,value){$$(selector).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset[key]===value)));}
function renderChart(){
 const host=$('#chart'),w=Math.max(240,host.clientWidth),h=host.clientHeight,left=65,right=w-38,max=90;
 const rows=[['Raw',data.coverage.Raw,'#df242b'],['PSA 9',0,'#171719'],['PSA 10',0,'#e3b92e']];
 host.innerHTML=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Public research coverage: ${data.coverage.Raw} dated Raw references of 90 cards. PSA 9 and PSA 10 data awaiting public-use clearance. No index returns.">${rows.map(([g,n,color],i)=>{const y=58+i*64;return `<text x="10" y="${y+18}" font-size="13">${g}</text><rect x="${left}" y="${y}" width="${right-left}" height="26" rx="5" fill="#eeeae4"/><rect x="${left}" y="${y}" width="${n/max*(right-left)}" height="26" rx="5" fill="${color}"/><text x="${right}" y="${y-8}" text-anchor="end" font-size="12">${n?n+' / 90':'Pending public data'}</text>`;}).join('')}<text x="${left}" y="${h-15}" font-size="12">Dated coverage · not performance</text></svg>`;
 host.setAttribute('aria-label','Research coverage, not index performance');
}
function renderMetrics(){
 press('[data-grade]','grade',state.grade);
 $('#mode-note').innerHTML='<b>Research beta.</b> Browse 90 exact card identities and dated Raw guide references. PSA 9, PSA 10 and full index history need cleared public data. Card artwork opens at the original source; the graphics here identify each research file.';
 $('#series-label').textContent='PUBLIC RESEARCH COVERAGE / '+state.grade.toUpperCase();
 $('#index-level').textContent=state.grade==='Raw'?'87 / 90':'Pending';
 $('#index-return').textContent=state.grade==='Raw'?'Dated Raw references':'Public-use clearance';
 $('#hero-series').textContent='TCG MODERN INDEX / RESEARCH IN PROGRESS';$('#hero-level').textContent='90 identities';$('#hero-return').textContent='+10 to select';
 $('#period-description').textContent='What is available in this public edition';
 $('#metric-high').textContent='1–2 Nov';$('#metric-high').previousElementSibling.textContent='Reference capture';
 $('#metric-drawdown').textContent='100';$('#metric-drawdown').previousElementSibling.textContent='Intended basket';
 $('#metric-breadth').textContent='In progress';$('#metric-breadth').previousElementSibling.textContent='Index history';
 $('#chart-footnote').textContent='Bars count published references. No performance curve or return is implied.';
 const coverage=data.coverage[state.grade];$('#selected-coverage').textContent=`${coverage} / 90`;$('#coverage-fill').style.width=coverage/90*100+'%';
 $('#coverage-description').textContent=state.grade==='Raw'?'Dated TCGplayer market guides via TCGCSV. Conditions combined.':'Public graded data is pending. Open an exact card for its original source links.';
 $('#grade-overview').innerHTML=grades.map(g=>`<article class="grade-card ${state.grade===g?'selected':''}"><span>${g}</span><small>PUBLIC REFERENCE COVERAGE</small><strong>${data.coverage[g]?data.coverage[g]+' / 90':'Pending'}</strong><b>${g==='Raw'?'Source dates on every card':'Public data in progress'}</b><p>${g==='Raw'?'Guides, not completed sales':'No substitution or invented values'}</p></article>`).join('');
 $('#return-matrix').innerHTML='<div class="matrix-heading"><h3>The path to a complete index.</h3><span>Research status</span></div><div class="matrix-scroll"><table><thead><tr><th>Research area</th><th>Current position</th><th>Next evidence</th></tr></thead><tbody><tr><th>Starting catalogue</th><td>90 exact identities</td><td>Ten exact additions</td></tr><tr><th>January 2026 history</th><td>Not validated</td><td>Issue-by-issue coverage</td></tr><tr><th>100-card returns & attribution</th><td>Not available</td><td>Final selection + cleared data</td></tr></tbody></table></div>';
 renderChart();renderMovers();
}
function renderMovers(){
 $('#mover-period').textContent='Source guides · 2 Nov capture';$('#mover-intro').textContent='Five research files from the original catalogue. Open each card for exact identity and sources.';
 $('#movers-grid').innerHTML=[6,10,14,20,1].map(id=>{const c=byId(id);return `<button type="button" class="mover" data-card="${c.id}" aria-label="Open ${esc(c.name)} source research"><span class="mover-image"><span class="mover-number">CATALOGUE SPOTLIGHT</span>${image(c,'loading="lazy"')}</span><span class="mover-copy"><h3>${esc(c.name)}</h3><span>${esc(c.set)}</span><strong>${money(c.quotes[state.grade]?.price)}</strong><small>${state.grade} source guide</small><small>${c.quotes[state.grade]?fullDate(c.quotes[state.grade].date):'Exact-grade evidence needed'}</small></span></button>`;}).join('');
 $('#attribution-summary').innerHTML='<span>Individual guide values are not index returns. Open a card for all three scenarios and source evidence.</span>';wireImageFallback($('#movers-grid'));
}
function filteredCards(){let results=cards.filter(c=>(state.set==='all'||c.set===state.set)&&(!state.priced||c.quotes[state.grade])&&(`${c.name} ${c.set} ${c.number}`.toLowerCase().includes(state.query.toLowerCase())));if(state.sort==='price')results.sort((a,b)=>(b.quotes[state.grade]?.price??-1)-(a.quotes[state.grade]?.price??-1));if(state.sort==='name')results.sort((a,b)=>a.name.localeCompare(b.name));return results;}
function tablePerformance(){return '<td>—</td><td>—</td><td>—</td>';}
function renderCards(){
 const filtered=filteredCards(),shown=state.view==='table'?filtered:filtered.slice(0,state.limit);
 $('#card-count').textContent=`${shown.length} of ${filtered.length} matching cards · 90 original + 10 positions to research`;
 press('[data-view]','view',state.view);$('#card-gallery').hidden=state.view!=='gallery';$('#card-table').hidden=state.view!=='table';$('#table-context').hidden=state.view!=='table';$('#table-context').textContent=state.mode==='demo'?'Price columns are dated source guides. Movement, weight and contribution are illustrative '+state.period+' design figures.':'Dated Raw references. TCG Modern Index performance, weights and contribution are not established.';
 $('#show-more').hidden=state.view!=='gallery'||shown.length>=filtered.length;$('#show-all').hidden=state.view!=='gallery'||shown.length>=filtered.length;
 $('#show-more').textContent=`Show ${Math.min(12,filtered.length-shown.length)} more cards ↓`;
 if(state.view==='gallery'){
  $('#card-gallery').innerHTML=shown.length?shown.map(c=>`<article class="catalog-card"><button class="catalog-art" type="button" data-card="${c.id}" aria-label="Open ${esc(c.name)} card research"><span class="catalog-rank">#${String(c.id).padStart(2,'0')} ORIGINAL LIST</span>${image(c,'loading="lazy"')}<span class="catalog-flag">ENGLISH</span></button><div class="catalog-body"><h3>${esc(c.name)}</h3><p class="catalog-meta">${esc(c.set)}<br>${esc(c.number)}</p><div class="price-triplet">${grades.map(g=>`<div class="${g===state.grade?'selected':''}"><span>${g}</span><b>${money(c.quotes[g]?.price)}</b></div>`).join('')}</div><div class="catalog-footer"><span>${state.grade} · ${c.quotes[state.grade]?fullDate(c.quotes[state.grade].date):'Not published'}</span><button type="button" data-card="${c.id}">Evidence ↗</button></div></div></article>`).join(''):'<div class="empty-state"><h3>No matching cards.</h3><p>Try another name, set or price-coverage filter.</p><button type="button" class="text-link" id="reset-filters">Clear filters</button></div>';
 }else{
  $('#card-table').innerHTML=`<table class="card-data-table"><thead><tr><th>Card / original rank</th><th>Raw</th><th>PSA 9</th><th>PSA 10</th><th>${esc(state.grade)} source date</th><th>100-card period return</th><th>Final weight</th><th>Contribution</th><th>Entry status</th></tr></thead><tbody>${shown.map(c=>`<tr><td><button class="table-card" data-card="${c.id}" type="button">${image(c,'loading="lazy"')}<span><b>#${c.id} · ${esc(c.name)}</b><small>${esc(c.set)} · ${esc(c.number)}</small></span></button></td>${grades.map(g=>`<td class="${g===state.grade?'selected':''}">${money(c.quotes[g]?.price)}</td>`).join('')}<td>${c.quotes[state.grade]?fullDate(c.quotes[state.grade].date):'Evidence needed'}</td>${tablePerformance(c)}<td>Original 90</td></tr>`).join('')||'<tr><td colspan="9">No matching cards. Change or clear the filters above.</td></tr>'}</tbody></table>`;
 }
 wireImageFallback(state.view==='gallery'?$('#card-gallery'):$('#card-table'));
}
function showCard(id){
 const c=byId(id);if(!c)return;
 const max=Math.max(1,...grades.map(g=>c.quotes[g]?.price??0));
 $('#dialog-content').innerHTML=`<div class="dialog-layout"><div class="dialog-image">${image(c)}</div><div class="dialog-main"><span class="eyebrow">EXACT CARD / ORIGINAL CATALOGUE #${c.id}</span><h2 id="dialog-title">${esc(c.name)}</h2><p class="dialog-meta">${esc(c.set)} · ${esc(c.number)} · English<br>Public research · Raw source capture 1–2 November 2026</p><div class="dialog-tabs" role="tablist" aria-label="Card research"><button type="button" role="tab" id="tab-overview" data-card-tab="overview" aria-selected="true" aria-controls="card-overview">Overview</button><button type="button" role="tab" id="tab-evidence" data-card-tab="evidence" aria-selected="false" aria-controls="card-evidence">Evidence</button><button type="button" role="tab" id="tab-method" data-card-tab="method" aria-selected="false" aria-controls="card-method">Method</button></div><section id="card-overview" role="tabpanel" aria-labelledby="tab-overview"><span class="kicker">THREE OUTCOMES / PUBLIC USD REFERENCES</span><div class="three-bars">${grades.map(g=>`<div class="scenario-row"><span>${g}</span><div class="scenario-track"><span style="width:${(c.quotes[g]?.price??0)/max*100}%"></span></div><b>${money(c.quotes[g]?.price)}</b></div>`).join('')}</div><p class="scenario-note">Alternative scenarios, never added together. Raw is a dated combined-condition guide; PSA 9 and PSA 10 are pending public data, not zero. A guide is not a completed sale or net profit.</p><div class="source-item"><strong>Selected view: ${state.grade}</strong><p>${c.quotes[state.grade]?`Source effective ${fullDate(c.quotes[state.grade].date)} · ${c.quotes[state.grade].count==null?'Provider guide':c.quotes[state.grade].count+' accepted source reports'}`:'Public graded data is pending. The original source links are available below.'}</p><div class="direct-source-links">${Object.entries(c.sources).map(([g,url])=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(g)} original ↗</a>`).join(' · ')}</div></div></section><section id="card-evidence" role="tabpanel" aria-labelledby="tab-evidence" hidden>${grades.map(g=>{const q=c.quotes[g];return `<article class="source-item"><strong>${g} · ${exactMoney(q?.price)}</strong>${q?`<p>${esc(q.provider)}</p><p>Source date ${fullDate(q.date)}${q.count!=null?' · '+q.count+' reports in a rolling 30-day sample':''}</p><a href="${esc(q.source)}" target="_blank" rel="noreferrer">Open ${g} source ↗</a>`:`<p>Value not published in this edition.</p>${c.sources[g]?`<a href="${esc(c.sources[g])}" target="_blank" rel="noopener noreferrer">Open original ${g} evidence ↗</a>`:'<p>Exact source not yet mapped.</p>'}`}</article>`;}).join('')}<p class="scenario-note">Source links may have changed since this saved capture. These are provider guides and aggregator reports, not independently verified UK completed sales.</p></section><section class="dialog-method" id="card-method" role="tabpanel" aria-labelledby="tab-method" hidden><h3>What these values represent</h3><p>Raw: TCGplayer USD market guide via TCGCSV, combining conditions. It is not a Near Mint-only sale or available listing.</p><p>PSA 9 / PSA 10: public numeric data is pending a cleared publication source. Original evidence links are provided where mapped; no graded values are substituted or invented.</p><p>Catalogue order is inherited from the original 90. It is not a current index weight, fresh value ranking or purchase recommendation.</p><p>TCG Modern Index basket composition and public source permissions remain under review. Public research does not expose personal purchase costs or holdings.</p></section></div></div>`;
 wireImageFallback($('#dialog-content'));$('#card-dialog').showModal();
}
const info={targets:['Targets are a separate research lane.','Index basket composition does not make a card undervalued. The approved target research and three-outcome maths remain separate; this page focuses on the TCG Modern Index detail page.'],japan:['The Japan desk stays separate.','The original modern catalogue is English. Japanese issues keep their own identity, sources and price history. This preview does not change the Japan research.'],login:['Your collection stays private.','This public edition is separate from the owner database. Open cards.alexkoh.me in your existing owner tab to use the private tracker. There is no public account signup here.']};
root.addEventListener('click',e=>{
 const card=e.target.closest('[data-card]');if(card){showCard(card.dataset.card);return;}
 const grade=e.target.closest('[data-grade]');if(grade){state.grade=grade.dataset.grade;renderMetrics();renderCards();return;}
 
 
 const view=e.target.closest('[data-view]');if(view){state.view=view.dataset.view;renderCards();return;}
 const tab=e.target.closest('[data-card-tab]');if(tab){const target=tab.dataset.cardTab;$$('[role="tab"][data-card-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.cardTab===target)));['overview','evidence','method'].forEach(t=>$('#card-'+t).hidden=t!==target);return;}
 const nav=e.target.closest('[data-info]');if(nav){const [title,body]=info[nav.dataset.info];$('#info-title').textContent=title;$('#info-body').textContent=body;$('#info-dialog').showModal();return;}
 if(e.target.closest('.dialog-close,.dialog-dismiss')){e.target.closest('dialog').close();return;}
 if(e.target.closest('#show-more')){state.limit+=12;renderCards();return;}
 if(e.target.closest('#show-all')){state.limit=90;renderCards();return;}
 if(e.target.closest('#reset-filters')){state.query='';state.set='all';state.priced=false;$('#card-search').value='';$('#set-filter').value='all';$('#priced-only').checked=false;renderCards();return;}
 if(e.target.closest('#math-toggle')){const b=$('#math-toggle'),open=b.getAttribute('aria-expanded')==='true';b.setAttribute('aria-expanded',String(!open));b.textContent=open?'Show the worked example +':'Hide the worked example −';$('#math-detail').hidden=open;}
});
$('#card-search').addEventListener('input',e=>{state.query=e.target.value;state.limit=12;renderCards();});
$('#set-filter').addEventListener('change',e=>{state.set=e.target.value;state.limit=12;renderCards();});
$('#card-sort').addEventListener('change',e=>{state.sort=e.target.value;renderCards();});
$('#priced-only').addEventListener('change',e=>{state.priced=e.target.checked;state.limit=12;renderCards();});
$('#chart-scrub').addEventListener('input',e=>{state.inspect=Number(e.target.value);renderChart();});
new ResizeObserver(()=>renderChart()).observe($('#chart'));
renderMetrics();renderCards();wireImageFallback();
})();

document.querySelector('.mobile-menu').addEventListener('click',e=>{const open=document.querySelector('#site-nav').classList.toggle('open');e.currentTarget.setAttribute('aria-expanded',String(open));});
