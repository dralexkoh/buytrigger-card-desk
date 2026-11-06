/* Public, reviewed card projections only. Never load an owner export here. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.BTPublicTargets=api;})(typeof window==='undefined'?globalThis:window,function(){
'use strict';
const APPROVED_ENDPOINT='https://ukblxmvsqihnnyysvxes.supabase.co/functions/v1/public-card-targets';
const REFRESH_SECONDS=300;
const MAX_EVIDENCE_AGE=7*86400_000;
const SOURCE_URLS={
 rawUrl:/^https:\/\/(?:www\.ebay\.co\.uk\/itm\/[0-9]{12}|(?:elite-tcg\.co\.uk|lockett-labs\.com|magicmadhouse\.co\.uk|totalcards\.net|tradezardz\.co\.uk|www\.nmdcollectables\.co\.uk)\/[a-zA-Z0-9/_.-]+(?:\?sku=[A-Za-z0-9-]{1,48})?)$/,
 gradingUrl:/^https:\/\/thesubcenter\.co\.uk\/product\/psa-(value|standard)\/$/,
 saleUrl:/^https:\/\/www\.ebay\.co\.uk\/itm\/[0-9]{12}(?:\?nordt=true)?$/,
 imageSourceUrl:/^https:\/\/(?:assets\.pokemon\.com|assets\.tcgdex\.net|www\.pokemon-card\.com)\/[a-zA-Z0-9/_.-]+\.(?:jpg|png|webp)$/
};
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>n===null?'—':new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',maximumFractionDigits:n%100?2:0}).format(n/100);
const date=x=>new Date(x).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
const object=x=>x&&typeof x==='object'&&!Array.isArray(x);
const exactKeys=(x,keys)=>object(x)&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
const calendarDay=x=>typeof x==='string'&&/^\d{4}-\d\d-\d\d$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const timestamp=x=>typeof x==='string'&&/^\d{4}-\d\d-\d\dT(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(Z|[+-]\d\d:\d\d)$/.test(x)&&calendarDay(x.slice(0,10))&&Number.isFinite(Date.parse(x));
const printingKey=c=>JSON.stringify([c.set,c.number,c.printing].map(value=>value.trim().toLowerCase()));
function validateConfig(c){
 const fields=['schemaVersion','enabled','endpoint'];if(c?.review!==undefined)fields.push('review');
 if(!exactKeys(c,fields)||c.schemaVersion!==1||typeof c.enabled!=='boolean'||(c.enabled?c.endpoint!==APPROVED_ENDPOINT:c.endpoint!==null))throw Error('Invalid public feed setup');
 if(c.review!==undefined){
  const r=c.review,d=r?.checkedAt;
  const keys=['checkedAt','listingsChecked'];
  if(r?.findings!==undefined)keys.push('findings');
  if(r?.psaUpside!==undefined)keys.push('psaUpside');
  if(!exactKeys(r,keys)||!calendarDay(d)||Date.parse(d)>Date.now()||!exactKeys(r.listingsChecked,['en','ja'])||Object.values(r.listingsChecked).some(n=>!Number.isSafeInteger(n)||n<1||n>500))throw Error('Invalid dated review');
  if(r.findings!==undefined&&(!exactKeys(r.findings,['en','ja'])||Object.values(r.findings).some(lines=>
   !Array.isArray(lines)||lines.length<1||lines.length>3||lines.some(line=>typeof line!=='string'||!line.trim()||line.length>280)
  )))throw Error('Invalid review findings');
  if(r.psaUpside!==undefined&&(!Array.isArray(r.psaUpside)||r.psaUpside.length>100||
   !r.psaUpside.every(c=>validUpside(c,d))||new Set(r.psaUpside.map(c=>c.id)).size!==r.psaUpside.length
  ))throw Error('Invalid PSA upside examples');
 }
 return c;
}
function validUpside(c,reviewDay,now=Date.now()){
 const live=reviewDay===null;
 const fields=['id','name','set','number','printing','language','image','rawMinor','gradingMinor','psa10Minor','returnPostageFromMinor','soldOn','rawUrl','gradingUrl','saleUrl','imageSourceUrl'];
 if(live||c?.gradingTier!==undefined)fields.push('gradingTier');
 if(live||c?.checkedAt!==undefined)fields.push('checkedAt');
 if(live)fields.push('validUntil');
 if(!exactKeys(c,fields)||!['en','ja'].includes(c.language)||typeof c.id!=='string'||!/^[a-z0-9-]{1,100}$/.test(c.id))return false;
 if(c.gradingTier!==undefined&&!['Value','Standard'].includes(c.gradingTier))return false;
 if(!['name','set','number','printing'].every(k=>typeof c[k]==='string'&&c[k].trim()&&c[k].length<=120))return false;
 if(typeof c.image!=='string'||!/^assets\/public-targets\/[a-z0-9_-]+\.(jpg|png|webp)$/.test(c.image))return false;
 if(!['rawMinor','gradingMinor','psa10Minor','returnPostageFromMinor'].every(k=>Number.isSafeInteger(c[k])&&c[k]>0&&c[k]<=100_000_000)||c.psa10Minor<=c.rawMinor+c.gradingMinor)return false;
 const checkedAt=c.checkedAt===undefined?reviewDay:c.checkedAt;
 if(live){
  const checked=Date.parse(checkedAt),expires=Date.parse(c.validUntil);
  if(!timestamp(checkedAt)||!timestamp(c.validUntil)||checked>now||expires<=now||expires-checked>MAX_EVIDENCE_AGE)return false;
 }else if(!calendarDay(checkedAt)||Date.parse(checkedAt)>now)return false;
 const checkedDay=new Date(checkedAt).toISOString().slice(0,10);
 if(!calendarDay(c.soldOn)||c.soldOn>checkedDay)return false;
 if(!Object.entries(SOURCE_URLS).every(([key,pattern])=>typeof c[key]==='string'&&c[key].length<=500&&pattern.test(c[key])))return false;
 return c.gradingUrl.endsWith('/psa-'+(c.gradingTier??'Value').toLowerCase()+'/')&&c.rawUrl!==c.saleUrl.split('?')[0];
}
function upsideCard(c,checkedAt){
 const cost=c.rawMinor+c.gradingMinor;
 const margin=c.psa10Minor-cost;
 const tier=c.gradingTier??'Value';
 const artCredit=c.imageSourceUrl.startsWith('https://assets.tcgdex.net/')?'Card artwork via TCGdex':'Official Pokémon card artwork';
 const rows=[['Raw delivered',c.rawMinor],['PSA '+tier+' grading',c.gradingMinor],['Card + grading',cost],['UK PSA 10 sale',c.psa10Minor],['Profit if PSA 10',margin]];
 const postage=c.returnPostageFromMinor;
 let postageNote='';
 if(postage>=margin)postageNote=' The dealer’s minimum return postage of '+money(postage)+' wipes out this margin.';
 else if(margin<=2*postage)postageNote=' After the dealer’s minimum '+money(postage)+' return postage, '+money(margin-postage)+' remains before other costs.';
 const figures=rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${money(value)}</dd></div>`).join('');
 return `<article class="public-target" id="pick-${esc(c.id)}">
  <button type="button" class="target-picture" data-target-art="${esc(c.id)}" aria-label="Enlarge ${esc(c.name)} card artwork"><img src="${esc(c.image)}" alt="${esc(c.name+' · '+c.set+' · '+c.number)}"><span>View artwork ↗</span></button>
  <div class="target-copy"><span class="kicker">PSA 10 UPSIDE · ${c.language==='ja'?'JAPANESE':'ENGLISH'}</span><h3>${esc(c.name)}</h3><p class="target-printing">${esc(c.set+' · '+c.number+' · '+c.printing)}</p><p class="target-summary">Profit shown if this card earns PSA 10. The seller lists the card as Raw. Its grade and the condition of the copy are unknown.</p><p class="target-date">Entry and grading checked ${date(checkedAt)}</p></div>
  <div class="target-outcomes"><dl class="target-upside-figures">${figures}</dl><p class="target-context">PSA 10 sale on ${date(c.soldOn)}, excluding the buyer fee. Profit excludes grading postage and selling costs.${postageNote}</p><details><summary>Prices &amp; sources</summary><ul><li><a href="${esc(c.rawUrl)}">Raw listing</a></li><li><a href="${esc(c.gradingUrl)}">PSA ${tier} fee and return postage</a></li><li><a href="${esc(c.saleUrl)}">UK PSA 10 sold listing</a></li><li><a href="${esc(c.imageSourceUrl)}">${artCredit}</a></li></ul></details></div>
 </article>`;
}
function validateFeed(data,language,now=Date.now()){
 if(!['en','ja'].includes(language)||!exactKeys(data,['schemaVersion','generatedAt','refreshAfterSeconds','cards'])||data.schemaVersion!==2||data.refreshAfterSeconds!==REFRESH_SECONDS||!timestamp(data.generatedAt)||Date.parse(data.generatedAt)>now+30000||now-Date.parse(data.generatedAt)>=REFRESH_SECONDS*1000||!Array.isArray(data.cards)||data.cards.length>500)throw Error('Unavailable public edition');
 const ids=new Set(),printings=new Set();
 for(const c of data.cards){
  if(!validUpside(c,null,now)||c.language!==language||ids.has(c.id))throw Error('Invalid public card');
  const issue=printingKey(c);
  if(printings.has(issue))throw Error('Duplicate public printing');
  ids.add(c.id);
  printings.add(issue);
 }
 return data.cards;
}
let cleanup=()=>{};
function unmount(){cleanup();cleanup=()=>{};}
function mount(language){
 unmount();const host=document.querySelector('[data-public-target-list]'),status=document.querySelector('[data-public-target-status]');if(!host||!status)return;
 let active=true,busy=false,timer,expiryTimer,controller,config,items=[],returnFocus;
 const dialog=document.createElement('dialog');dialog.className='target-art-dialog';dialog.setAttribute('aria-label','Card artwork');dialog.innerHTML='<button type="button" aria-label="Close card artwork">Close ×</button><img alt="">';document.body.append(dialog);
 const close=()=>dialog.close();dialog.querySelector('button').onclick=close;dialog.addEventListener('close',()=>{document.documentElement.classList.remove('target-art-open');returnFocus?.focus();});
 function click(e){const b=e.target.closest('[data-target-art]');if(b){const c=items.find(x=>x.id===b.dataset.targetArt);if(!c)return;returnFocus=b;const img=dialog.querySelector('img');img.src=c.image;img.alt=c.name+' · '+c.set+' · '+c.number;dialog.showModal();document.documentElement.classList.add('target-art-open');return;}if(e.target.closest('[data-target-retry]'))refresh();}
 host.addEventListener('click',click);
 function pictureErrors(){
  host.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{
   const button=img.closest('button');
   button.disabled=true;
   button.innerHTML='<span>Picture temporarily unavailable</span>';
  },{once:true}));
 }
 function earlierExamples(current=[]){
  const ids=new Set(current.map(c=>c.id)),printings=new Set(current.map(printingKey));
  return config?.review?.psaUpside?.filter(c=>c.language===language&&!ids.has(c.id)&&!printings.has(printingKey(c)))??[];
 }
 function earlierCards(examples){
  return examples.map(c=>upsideCard(c,c.checkedAt??config.review.checkedAt)).join('');
 }
 function datedReview(message='',retry=false){
  clearTimeout(expiryTimer);
  const review=config?.review;
  const examples=earlierExamples();
  const retryButton=retry?'<button type="button" class="btn red" data-target-retry>Try again</button>':'';
  items=examples;
  if(!examples.length){
   status.textContent='No current reviewed picks';
   host.innerHTML=`<div class="opportunity-empty"><h3>No current reviewed picks</h3><p>${esc(message||'The next reviewed cards will appear here.')}</p>${retryButton}</div>`;
   return;
  }
  status.textContent=`${examples.length} dated PSA 10 scenario${examples.length===1?'':'s'}`;
  const findings=review.findings?.[language]??[];
  const notice=message?`<div class="opportunity-empty"><p>${esc(message)}</p>${retryButton}</div>`:'';
  host.innerHTML=notice+earlierCards(examples)+
   `<details class="target-review-history"><summary>Earlier downside review · ${date(review.checkedAt)}</summary><p>${review.listingsChecked[language]} listings checked. None passed the PSA 9 cost recovery and other checks.</p><ul>${findings.map(line=>`<li>${esc(line)}</li>`).join('')}</ul></details>`;
  pictureErrors();
 }
 function later(delay=REFRESH_SECONDS*1000){clearTimeout(timer);timer=setTimeout(refresh,delay);}
 async function json(url){const res=await fetch(url,{credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store',redirect:'error',signal:controller.signal});if(!res.ok)throw Error('Unavailable');const text=await res.text();if(text.length>2_000_000)throw Error('Oversized response');return JSON.parse(text);}
 async function refresh(){
  if(!active||busy)return;busy=true;clearTimeout(timer);controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),12000);
  try{
   if(!config)config=validateConfig(await json('public-targets-config.json'));
   if(!active)return;
   if(!config.enabled){
    datedReview();
    return;
   }
   if(!items.length)datedReview('Checking the current shortlist.');
   const url=new URL(config.endpoint);
   url.searchParams.set('language',language);
   const data=await json(url.href),cards=validateFeed(data,language);
   if(!active)return;
   if(cards.length){
    const examples=earlierExamples(cards);
    items=[...cards,...examples];
    status.textContent=`${cards.length} current reviewed card${cards.length===1?'':'s'}`;
    const earlier=examples.length?'<header><h3>Earlier PSA 10 scenarios</h3><p class="target-context">Raw and grading prices were checked on the dates shown.</p></header>'+earlierCards(examples):'';
    host.innerHTML=cards.map(c=>upsideCard(c,c.checkedAt)).join('')+earlier;
    pictureErrors();
    const expires=Math.min(Date.parse(data.generatedAt)+REFRESH_SECONDS*1000,...cards.map(c=>Date.parse(c.validUntil)));
    clearTimeout(expiryTimer);
    expiryTimer=setTimeout(()=>{
     datedReview('The current shortlist is being rechecked.');
     refresh();
    },expires-Date.now());
   }else datedReview('There are no current reviewed picks in this language.');
   later();
  }catch{if(active){datedReview('The current shortlist is temporarily unavailable.',true);later(60000);}}
  finally{clearTimeout(timeout);busy=false;}
 }
 const visible=()=>{if(document.visibilityState==='visible')refresh();};document.addEventListener('visibilitychange',visible);
 cleanup=()=>{active=false;controller?.abort();clearTimeout(timer);clearTimeout(expiryTimer);host.removeEventListener('click',click);document.removeEventListener('visibilitychange',visible);dialog.remove();document.documentElement.classList.remove('target-art-open');};
 refresh();
}
return {validateConfig,validateFeed,upsideCard,mount,unmount};
});
