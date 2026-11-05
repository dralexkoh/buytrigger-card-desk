/* Public, reviewed card projections only. Never load an owner export here. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.BTPublicTargets=api;})(typeof window==='undefined'?globalThis:window,function(){
'use strict';
const APPROVED_ENDPOINT='https://ukblxmvsqihnnyysvxes.supabase.co/functions/v1/public-card-targets';
const FIELDS=['id','name','set','number','parallel','language','image','currency','deliveredEntryMinor','rawMinor','psa9Minor','psa10Minor','checkedAt','validUntil','summary','evidence'];
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>n===null?'—':new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',maximumFractionDigits:n%100?2:0}).format(n/100);
const date=x=>new Date(x).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
const object=x=>x&&typeof x==='object'&&!Array.isArray(x);
const exactKeys=(x,keys)=>object(x)&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
const timestamp=x=>typeof x==='string'&&/(Z|[+-]\d\d:\d\d)$/.test(x)&&Number.isFinite(Date.parse(x));
function validateConfig(c){
 const fields=['schemaVersion','enabled','endpoint'];if(c?.review!==undefined)fields.push('review');
 if(!exactKeys(c,fields)||c.schemaVersion!==1||typeof c.enabled!=='boolean'||(c.enabled?c.endpoint!==APPROVED_ENDPOINT:c.endpoint!==null))throw Error('Invalid public feed setup');
 if(c.review!==undefined){
  const r=c.review,d=r?.checkedAt,ms=Date.parse(d);
  const keys=['checkedAt','listingsChecked'];
  if(r?.findings!==undefined)keys.push('findings');
  if(r?.psaUpside!==undefined)keys.push('psaUpside');
  if(!exactKeys(r,keys)||typeof d!=='string'||!/^\d{4}-\d\d-\d\d$/.test(d)||!Number.isFinite(ms)||new Date(ms).toISOString().slice(0,10)!==d||ms>Date.now()||!exactKeys(r.listingsChecked,['en','ja'])||Object.values(r.listingsChecked).some(n=>!Number.isSafeInteger(n)||n<1||n>500))throw Error('Invalid dated review');
  if(r.findings!==undefined&&(!exactKeys(r.findings,['en','ja'])||Object.values(r.findings).some(lines=>
   !Array.isArray(lines)||lines.length<1||lines.length>3||lines.some(line=>typeof line!=='string'||!line.trim()||line.length>280)
  )))throw Error('Invalid review findings');
  if(r.psaUpside!==undefined&&(!Array.isArray(r.psaUpside)||r.psaUpside.length>20||
   !r.psaUpside.every(c=>validUpside(c,d))||new Set(r.psaUpside.map(c=>c.id)).size!==r.psaUpside.length
  ))throw Error('Invalid PSA upside examples');
 }
 return c;
}
function validUpside(c,checkedAt){
 const fields=['id','name','set','number','printing','language','image','rawMinor','gradingMinor','psa10Minor','returnPostageFromMinor','soldOn','rawUrl','gradingUrl','saleUrl','imageSourceUrl'];
 if(c?.gradingTier!==undefined)fields.push('gradingTier');
 if(!exactKeys(c,fields)||!['en','ja'].includes(c.language)||typeof c.id!=='string'||!/^[a-z0-9-]{1,100}$/.test(c.id))return false;
 if(c.gradingTier!==undefined&&!['Value','Standard'].includes(c.gradingTier))return false;
 if(!['name','set','number','printing'].every(k=>typeof c[k]==='string'&&c[k].trim()&&c[k].length<=120))return false;
 if(typeof c.image!=='string'||!/^assets\/public-targets\/[a-z0-9_-]+\.(jpg|png|webp)$/.test(c.image))return false;
 if(!['rawMinor','gradingMinor','psa10Minor','returnPostageFromMinor'].every(k=>Number.isSafeInteger(c[k])&&c[k]>0&&c[k]<=100_000_000)||c.psa10Minor<=c.rawMinor+c.gradingMinor)return false;
 if(typeof c.soldOn!=='string'||!/^\d{4}-\d\d-\d\d$/.test(c.soldOn)||!Number.isFinite(Date.parse(c.soldOn))||new Date(c.soldOn).toISOString().slice(0,10)!==c.soldOn||c.soldOn>checkedAt)return false;
 return ['rawUrl','gradingUrl','saleUrl','imageSourceUrl'].every(k=>typeof c[k]==='string'&&/^https:\/\/[a-z0-9.-]+\/[^\s@#]+$/.test(c[k])&&c[k].length<=500);
}
function upsideCard(c,checkedAt){
 const cost=c.rawMinor+c.gradingMinor;
 const margin=c.psa10Minor-cost;
 const tier=c.gradingTier??'Value';
 const artCredit=c.imageSourceUrl.startsWith('https://assets.pokemon.com/')?'Official Pokémon card artwork':'Card artwork via TCGdex';
 const rows=[['Raw delivered',c.rawMinor],['PSA '+tier+' grading',c.gradingMinor],['Card + grading',cost],['UK PSA 10 sale',c.psa10Minor],['Profit if PSA 10',margin]];
 const postage=c.returnPostageFromMinor;
 let postageNote='';
 if(postage>margin)postageNote=' The dealer’s minimum return postage of '+money(postage)+' exceeds this margin.';
 else if(margin<=2*postage)postageNote=' After the dealer’s minimum '+money(postage)+' return postage, '+money(margin-postage)+' remains before other costs.';
 const figures=rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${money(value)}</dd></div>`).join('');
 return `<article class="public-target" id="pick-${esc(c.id)}">
  <button type="button" class="target-picture" data-target-art="${esc(c.id)}" aria-label="Enlarge ${esc(c.name)} card artwork"><img src="${esc(c.image)}" alt="${esc(c.name+' · '+c.set+' · '+c.number)}"><span>View artwork ↗</span></button>
  <div class="target-copy"><span class="kicker">PSA 10 UPSIDE · ${c.language==='ja'?'JAPANESE':'ENGLISH'}</span><h3>${esc(c.name)}</h3><p class="target-printing">${esc(c.set+' · '+c.number+' · '+c.printing)}</p><p class="target-summary">Profit shown if this card earns PSA 10. The seller lists the card as Raw. Its grade and the condition of the copy are unknown.</p><p class="target-date">Entry and grading checked ${date(checkedAt)}</p></div>
  <div class="target-outcomes"><dl class="target-upside-figures">${figures}</dl><p class="target-context">PSA 10 sale on ${date(c.soldOn)}, excluding the buyer fee. Profit excludes grading postage and selling costs.${postageNote}</p><details><summary>Prices &amp; sources</summary><ul><li><a href="${esc(c.rawUrl)}">Raw listing</a></li><li><a href="${esc(c.gradingUrl)}">PSA ${tier} fee and return postage</a></li><li><a href="${esc(c.saleUrl)}">UK PSA 10 sold listing</a></li><li><a href="${esc(c.imageSourceUrl)}">${artCredit}</a></li></ul></details></div>
 </article>`;
}
function validCard(c,now){
 if(!exactKeys(c,FIELDS))return false;
 if(!['id','name','set','number','parallel','language','image','currency','checkedAt','validUntil','summary'].every(k=>typeof c[k]==='string'&&c[k].length<=600))return false;
 if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(c.id)||c.id.length>160||!c.name||!c.set||!c.number||!c.summary)return false;
 if(!['en','ja'].includes(c.language)||c.currency!=='GBP'||!/^assets\/public-targets\/[a-z0-9_-]+\.(jpg|png|webp)$/.test(c.image))return false;
 if(!['deliveredEntryMinor','psa9Minor','psa10Minor'].every(k=>Number.isSafeInteger(c[k])&&c[k]>0)||(c.rawMinor!==null&&(!Number.isSafeInteger(c.rawMinor)||c.rawMinor<=0)))return false;
 if(!timestamp(c.checkedAt)||!timestamp(c.validUntil)||Date.parse(c.checkedAt)>now||Date.parse(c.validUntil)<=now||Date.parse(c.validUntil)-Date.parse(c.checkedAt)>7*86400_000)return false;
 if(!Array.isArray(c.evidence)||!c.evidence.length||c.evidence.length>30)return false;
 return c.evidence.every(s=>exactKeys(s,['url','label','date','measure','grade'])&&Object.values(s).every(v=>typeof v==='string')&&/^https:\/\/[a-z0-9.-]+\/[^?#\s@]*$/.test(s.url)&&s.url.length<=2048&&s.label.length>0&&s.label.length<=240&&/^\d{4}-\d{2}-\d{2}$/.test(s.date)&&Number.isFinite(Date.parse(s.date))&&s.date<=c.checkedAt.slice(0,10)&&['completed_sale','market_guide'].includes(s.measure)&&['Raw','PSA 9','PSA 10'].includes(s.grade));
}
function validateFeed(data,language,now=Date.now()){
 if(!exactKeys(data,['schemaVersion','generatedAt','refreshAfterSeconds','cards'])||data.schemaVersion!==1||data.refreshAfterSeconds!==300||!timestamp(data.generatedAt)||Date.parse(data.generatedAt)>now+30000||now-Date.parse(data.generatedAt)>300000||!Array.isArray(data.cards)||data.cards.length>500)throw Error('Unavailable public edition');
 const ids=new Set();for(const c of data.cards){if(!validCard(c,now)||c.language!==language||ids.has(c.id))throw Error('Invalid public card');ids.add(c.id);}
 return data.cards;
}
function card(c){
 const max=Math.max(c.rawMinor||0,c.psa9Minor,c.psa10Minor),gap=c.rawMinor===null?null:c.rawMinor-c.deliveredEntryMinor;
 const bars=[['Raw',c.rawMinor,'raw'],['PSA 9',c.psa9Minor,'nine'],['PSA 10',c.psa10Minor,'ten']].map(([label,v,type])=>`<div class="target-bar"><b>${label}</b><span class="target-track"><i class="${type}" style="width:${v===null?0:v/max*100}%"></i></span><strong>${money(v)}</strong></div>`).join('');
 const sources=c.evidence.map(s=>`<li><a href="${esc(s.url)}" rel="noopener noreferrer" target="_blank">${esc(s.label)} ↗</a><span>${esc(s.grade)} · ${s.measure==='completed_sale'?'Completed sale':'Price guide'} · ${date(s.date)}</span></li>`).join('');
 return `<article class="public-target" id="pick-${esc(c.id)}"><button type="button" class="target-picture" data-target-art="${esc(c.id)}" aria-label="Enlarge ${esc(c.name)} card artwork"><img src="${esc(c.image)}" alt="${esc(c.name+' · '+c.set+' · '+c.number)}" loading="lazy"><span>View artwork ↗</span></button><div class="target-copy"><span class="kicker">${c.language==='ja'?'JAPANESE':'ENGLISH'} · ${esc(c.set)}</span><h3>${esc(c.name)}</h3><p class="target-printing">#${esc(c.number)}${c.parallel?' · '+esc(c.parallel):''}</p><div class="target-entry"><div><span>Delivered entry</span><strong>${money(c.deliveredEntryMinor)}</strong></div><p>${gap===null?'Raw reference pending':`${money(Math.abs(gap))} ${gap>=0?'below':'above'} Raw reference`}</p></div><p class="target-summary">${esc(c.summary)}</p></div><div class="target-outcomes"><h4>Three possible outcomes</h4>${bars}<p class="target-context">Gross sale references, before grading and selling costs. Alternative outcomes; a PSA 10 is not guaranteed.</p><p class="target-date">Checked ${date(c.checkedAt)} · Review by ${date(c.validUntil)}</p><details><summary>Prices &amp; sources</summary><ul>${sources}</ul></details></div></article>`;
}
let cleanup=()=>{};
function unmount(){cleanup();cleanup=()=>{};}
function mount(language){
 unmount();const host=document.querySelector('[data-public-target-list]'),status=document.querySelector('[data-public-target-status]');if(!host||!status)return;
 let active=true,busy=false,timer,controller,config,items=[],feedExpiresAt=0,returnFocus;
 const dialog=document.createElement('dialog');dialog.className='target-art-dialog';dialog.setAttribute('aria-label','Card artwork');dialog.innerHTML='<button type="button" aria-label="Close card artwork">Close ×</button><img alt="">';document.body.append(dialog);
 const close=()=>dialog.close();dialog.querySelector('button').onclick=close;dialog.addEventListener('close',()=>{document.documentElement.classList.remove('target-art-open');returnFocus?.focus();});
 function click(e){const b=e.target.closest('[data-target-art]');if(b){const c=items.find(x=>x.id===b.dataset.targetArt)??config?.review?.psaUpside?.find(x=>x.id===b.dataset.targetArt&&x.language===language);if(!c)return;returnFocus=b;const img=dialog.querySelector('img');img.src=c.image;img.alt=c.name+' · '+c.set+' · '+c.number;dialog.showModal();document.documentElement.classList.add('target-art-open');return;}if(e.target.closest('[data-target-retry]'))refresh();}
 host.addEventListener('click',click);
 function state(title,message,retry=false){items=[];status.textContent=title;host.innerHTML=`<div class="opportunity-empty"><h3>${esc(title)}</h3><p>${esc(message)}</p>${retry?'<button type="button" class="btn red" data-target-retry>Try again</button>':''}</div>`;}
 function later(delay=300000){clearTimeout(timer);timer=setTimeout(refresh,delay);}
 async function json(url){const res=await fetch(url,{credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store',redirect:'error',signal:controller.signal});if(!res.ok)throw Error('Unavailable');const text=await res.text();if(text.length>2_000_000)throw Error('Oversized response');return JSON.parse(text);}
 async function refresh(){
  if(!active||busy)return;busy=true;clearTimeout(timer);controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),12000);
  if(items.length&&(Date.now()>=feedExpiresAt||items.some(c=>Date.parse(c.validUntil)<=Date.now())))state('Refreshing the shortlist','Checking the latest reviewed cards.');
  try{
   if(!config)config=validateConfig(await json('public-targets-config.json'));
   if(!active)return;
   if(!config.enabled){
    const review=config.review,label=language==='ja'?'Japanese':'English';
    const examples=review?.psaUpside?.filter(c=>c.language===language)??[];
    if(examples.length){
     status.textContent=examples.length===1?'1 PSA 10 scenario':examples.length+' PSA 10 scenarios';
     const findings=review.findings?.[language]??[];
     host.innerHTML=examples.map(c=>upsideCard(c,review.checkedAt)).join('')+
      `<details class="target-review-history"><summary>Earlier downside review · ${date(review.checkedAt)}</summary><p>${review.listingsChecked[language]} listings checked. None passed the PSA 9 cost recovery and other checks.</p><ul>${findings.map(line=>`<li>${esc(line)}</li>`).join('')}</ul></details>`;
     return;
    }
    state('No verified picks',review?`${review.listingsChecked[language]} listings checked on ${date(review.checkedAt)} for the ${label} shortlist. No card in this review passed every check.`:'No current reviewed cards in this language.');
    const findings=review?.findings?.[language];
    if(findings)host.querySelector('.opportunity-empty').insertAdjacentHTML('beforeend',
     `<ul class="target-review-findings" aria-label="What held the picks back">${findings.map(line=>`<li>${esc(line)}</li>`).join('')}</ul>`);
    return;
   }
   const url=new URL(config.endpoint);if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||!/^\/functions\/v1\/public-card-targets$/.test(url.pathname))throw Error('Invalid feed endpoint');url.searchParams.set('language',language);
   const data=await json(url.href),cards=validateFeed(data,language);if(!active)return;items=cards;feedExpiresAt=Date.parse(data.generatedAt)+300000;
   if(cards.length){status.textContent=cards.length+' reviewed card'+(cards.length===1?'':'s');host.innerHTML=cards.map(card).join('');host.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{const b=img.closest('button');b.disabled=true;b.innerHTML='<span>Picture temporarily unavailable</span>';},{once:true}));}
   else state('No current published picks','There are no reviewed cards available in this language right now. New picks appear after their prices and evidence are checked.');
   later(cards.length?Math.max(1000,Math.min(feedExpiresAt-Date.now(),300000,...cards.map(c=>Date.parse(c.validUntil)-Date.now()))):300000);
  }catch{if(active){config=null;state('Prices temporarily unavailable','We could not check the current shortlist. Please try again shortly.',true);later(60000);}}
  finally{clearTimeout(timeout);busy=false;}
 }
 const visible=()=>{if(document.visibilityState==='visible')refresh();};document.addEventListener('visibilitychange',visible);
 cleanup=()=>{active=false;controller?.abort();clearTimeout(timer);host.removeEventListener('click',click);document.removeEventListener('visibilitychange',visible);dialog.remove();document.documentElement.classList.remove('target-art-open');};
 state('Checking the shortlist','Looking for the latest reviewed cards.');refresh();
}
return {validateConfig,validateFeed,card,mount,unmount};
});
