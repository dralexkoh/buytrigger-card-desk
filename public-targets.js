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
function money(minor,currency='GBP'){
 if(minor===null)return '—';
 if(currency==='JPY')return new Intl.NumberFormat('ja-JP',{style:'currency',currency:'JPY',minimumFractionDigits:0,maximumFractionDigits:0}).format(minor).replaceAll('￥','¥');
 if(currency==='USD')return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:minor%100?2:0}).format(minor/100).replace('$','US$');
 return new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',maximumFractionDigits:minor%100?2:0}).format(minor/100);
}
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
function validLegacyUpside(c,reviewDay,now=Date.now()){
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
const EXT_KEYS=['kind','currency','market','grading','liquidity'];
const DENIED=/(pokeinvest|pokemonpricetracker|pokemon price tracker|pokemon-price-tracker)/i;
const HTTPS_URL=/^https:\/\/[A-Za-z0-9.-]+\/[^\s"<>]*$/;
const PSA_URL=/^https:\/\/www\.psacard\.com\/[A-Za-z0-9/_.?=&%-]+$/;
const MARKET_KEYS=['rawGuide','rawAsk','psa10Guide','psa10Median30d'];
const GRADING_KEYS=['gemRatePct','psa10Pop','totalGraded'];
const LIQUIDITY_KEYS=['rawSold30d','psa10Sold30d'];
function sourceAllowed(s){return typeof s==='string'&&!DENIED.test(s);}
function sourceText(s){return sourceAllowed(s)&&s.trim().length>=1&&s.trim().length<=160;}
function positiveMinor(n){return Number.isSafeInteger(n)&&n>=1&&n<=999999999;}
function wholeDigits(n,max){return Number.isSafeInteger(n)&&n>=0&&String(n).length<=max;}
function allowedKeys(x,keys){return object(x)&&Object.keys(x).every(k=>keys.includes(k));}
function evidenceOk(v,block,checkedDay){
 if(!object(v))return false;
 if(block==='market'){
  if(!exactKeys(v,['amountMinor','currency','type','source','sourceUrl','observedOn','confidence']))return false;
  if(!positiveMinor(v.amountMinor)||!['GBP','USD','JPY'].includes(v.currency)||!['guide','ask','bid','sale','median'].includes(v.type)||!['high','medium','low'].includes(v.confidence))return false;
 }else if(block==='grading'){
  if(!exactKeys(v,['value','source','sourceUrl','observedOn']))return false;
  if(typeof v.value!=='number'||!Number.isFinite(v.value)||v.value<0||typeof v.sourceUrl!=='string'||!PSA_URL.test(v.sourceUrl))return false;
 }else if(block==='liquidity'){
  if(!exactKeys(v,['value','source','observedOn','floor']))return false;
  if(!wholeDigits(v.value,7)||typeof v.floor!=='boolean')return false;
 }else return false;
 if(!sourceText(v.source))return false;
 if(Object.hasOwn(v,'sourceUrl')&&(typeof v.sourceUrl!=='string'||v.sourceUrl.length>500||!HTTPS_URL.test(v.sourceUrl)||!sourceAllowed(v.sourceUrl)))return false;
 return calendarDay(v.observedOn)&&v.observedOn<=checkedDay;
}
function blocksOk(d,checkedDay){
 if(Object.hasOwn(d,'market')){
  const market=d.market;
  if(!object(market)||!Object.keys(market).length||!allowedKeys(market,MARKET_KEYS))return false;
  for(const value of Object.values(market)) if(!evidenceOk(value,'market',checkedDay))return false;
 }
 if(Object.hasOwn(d,'grading')){
  const grading=d.grading;
  if(!object(grading)||!allowedKeys(grading,GRADING_KEYS))return false;
  for(const [key,value] of Object.entries(grading)){
   if(value===null)continue;
   if(!evidenceOk(value,'grading',checkedDay))return false;
   if(key==='gemRatePct'&&value.value>100)return false;
   if((key==='psa10Pop'||key==='totalGraded')&&!wholeDigits(value.value,9))return false;
  }
 }
 if(Object.hasOwn(d,'liquidity')){
  const liquidity=d.liquidity;
  if(!object(liquidity)||!allowedKeys(liquidity,LIQUIDITY_KEYS))return false;
  for(const value of Object.values(liquidity)){
   if(value===null)continue;
   if(!evidenceOk(value,'liquidity',checkedDay))return false;
  }
 }
 return true;
}
function blockCheckedDay(c,reviewDay){
 const value=c.checkedAt===undefined?reviewDay:c.checkedAt;
 if(timestamp(value))return new Date(value).toISOString().slice(0,10);
 if(reviewDay!==null&&calendarDay(value))return value;
 return null;
}
function validUpside(c,reviewDay,now=Date.now()){
 if(!object(c)||!EXT_KEYS.some(k=>Object.hasOwn(c,k)))return validLegacyUpside(c,reviewDay,now);
 if(Object.hasOwn(c,'kind')&&typeof c.kind!=='string')return false;
 if(Object.hasOwn(c,'currency')&&c.currency!=null&&!['GBP','USD','JPY'].includes(c.currency))return false;
 const kind=typeof c.kind==='string'?c.kind:'upside';
 if(kind==='upside'){
  if((c.currency??'GBP')!=='GBP')return false;
  if(['market','grading','liquidity'].some(k=>Object.hasOwn(c,k))){
   const day=blockCheckedDay(c,reviewDay);
   if(!day||!blocksOk(c,day))return false;
  }
  const legacy={};
  for(const [key,value] of Object.entries(c)) if(!EXT_KEYS.includes(key))legacy[key]=value;
  return validLegacyUpside(legacy,reviewDay,now);
 }
 return kind==='watch'&&validWatch(c,reviewDay,now);
}
function validWatch(c,reviewDay,now){
 const live=reviewDay===null;
 const fields=['id','name','set','number','printing','language','image','imageSourceUrl','checkedAt','kind','market'];
 if(live)fields.push('validUntil');
 for(const key of ['currency','grading','liquidity']) if(Object.hasOwn(c,key))fields.push(key);
 if(!exactKeys(c,fields)||c.kind!=='watch'||!['en','ja'].includes(c.language)||typeof c.id!=='string'||!/^[a-z0-9-]{1,100}$/.test(c.id))return false;
 if(!['name','set','number','printing'].every(k=>typeof c[k]==='string'&&c[k].trim()&&c[k].length<=120))return false;
 if(typeof c.image!=='string'||!/^assets\/public-targets\/[a-z0-9_-]+\.(jpg|png|webp)$/.test(c.image))return false;
 if(c.currency!=null&&!['GBP','USD','JPY'].includes(c.currency))return false;
 if(typeof c.imageSourceUrl!=='string'||c.imageSourceUrl.length>500||!SOURCE_URLS.imageSourceUrl.test(c.imageSourceUrl))return false;
 let checkedDay;
 if(live){
  const checked=Date.parse(c.checkedAt),expires=Date.parse(c.validUntil);
  if(!timestamp(c.checkedAt)||!timestamp(c.validUntil)||checked>now||expires<=now||expires-checked>MAX_EVIDENCE_AGE)return false;
  checkedDay=new Date(c.checkedAt).toISOString().slice(0,10);
 }else if(!calendarDay(c.checkedAt)||Date.parse(c.checkedAt)>now)return false;
 else checkedDay=c.checkedAt;
 if(!blocksOk(c,checkedDay))return false;
 const market=c.market;
 return object(market)&&(Object.hasOwn(market,'rawGuide')||Object.hasOwn(market,'rawAsk'))&&(Object.hasOwn(market,'psa10Guide')||Object.hasOwn(market,'psa10Median30d'));
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
  <div class="target-outcomes"><dl class="target-upside-figures">${figures}</dl><p class="target-context">PSA 10 sale on ${date(c.soldOn)}, excluding the buyer fee. Profit excludes grading postage and selling costs.${postageNote}</p>${moreEvidence(c)}<details><summary>Prices &amp; sources</summary><ul><li><a href="${esc(c.rawUrl)}">Raw listing</a></li><li><a href="${esc(c.gradingUrl)}">PSA ${tier} fee and return postage</a></li><li><a href="${esc(c.saleUrl)}">UK PSA 10 sold listing</a></li><li><a href="${esc(c.imageSourceUrl)}">${artCredit}</a></li></ul></details></div>
 </article>`;
}
const MARKET_LABELS=[['rawGuide','Raw guide'],['rawAsk','Raw ask'],['psa10Guide','PSA 10 guide'],['psa10Median30d','PSA 10 30-day median']];
const GRADING_LABELS=[['gemRatePct','Gem rate'],['psa10Pop','PSA 10 pop'],['totalGraded','Total graded']];
const LIQUIDITY_LABELS=[['rawSold30d','Raw'],['psa10Sold30d','PSA 10']];
function marketRows(market){
 if(!object(market))return '';
 return MARKET_LABELS.filter(([key])=>object(market[key])).map(([key,label])=>{
  const value=market[key];
  return `<div><dt>${label}</dt><dd><span class="evidence-amount">${money(value.amountMinor,value.currency)}</span><a class="evidence-line" href="${esc(value.sourceUrl)}">${esc(value.source)} · ${date(value.observedOn)} · ${esc(value.type)} · ${esc(value.confidence)}</a></dd></div>`;
 }).join('');
}
function statRow(label,key,entry){
 if(entry==null)return `<div><dt>${label}</dt><dd>Unavailable</dd></div>`;
 const shown=key==='gemRatePct'?(Number.isInteger(entry.value)?String(entry.value):String(entry.value))+'%':new Intl.NumberFormat('en-GB').format(entry.value);
 return `<div><dt>${label}</dt><dd><span class="evidence-amount">${shown}</span><span class="evidence-line">PSA, ${date(entry.observedOn)}</span></dd></div>`;
}
function liquidityLines(block){
 if(!object(block))return '';
 return LIQUIDITY_LABELS.map(([key,label])=>{
  const value=block[key];
  if(!object(value))return '';
  return `<p class="evidence-liquidity">${label} · ${value.floor?'≥':''}${value.value} sold in 30 days<span class="evidence-line">${esc(value.source)} · ${date(value.observedOn)}</span></p>`;
 }).join('');
}
function moreEvidence(c){
 const chunks=[];
 const market=marketRows(c.market);
 if(market)chunks.push(`<dl class="target-evidence">${market}</dl>`);
 if(object(c.grading)){
  const rows=GRADING_LABELS.filter(([key])=>Object.hasOwn(c.grading,key)).map(([key,label])=>statRow(label,key,c.grading[key])).join('');
  if(rows)chunks.push(`<dl class="target-evidence">${rows}</dl>`);
 }
 const sold=liquidityLines(c.liquidity);
 if(sold)chunks.push(sold);
 return chunks.length?`<h4>More evidence</h4>${chunks.join('')}`:'';
}
function watchCard(c,checkedAt){
 const artCredit=c.imageSourceUrl.startsWith('https://assets.tcgdex.net/')?'Card artwork via TCGdex':'Official Pokémon card artwork';
 const grading=GRADING_LABELS.map(([key,label])=>statRow(label,key,c.grading?.[key]??null)).join('');
 return `<article class="public-target" id="pick-${esc(c.id)}">
  <button type="button" class="target-picture" data-target-art="${esc(c.id)}" aria-label="Enlarge ${esc(c.name)} card artwork"><img src="${esc(c.image)}" alt="${esc(c.name+' · '+c.set+' · '+c.number)}"><span>View artwork ↗</span></button>
  <div class="target-copy"><span class="kicker target-badge-watch">WATCH · ${c.language==='ja'?'JAPANESE':'ENGLISH'}</span><h3>${esc(c.name)}</h3><p class="target-printing">${esc(c.set+' · '+c.number+' · '+c.printing)}</p><p class="target-summary">Watch entry: dated market evidence, not a buy signal. Prices are in the currency shown; no conversions.</p><p class="target-date">Checked ${date(checkedAt)}</p></div>
  <div class="target-outcomes"><dl class="target-evidence">${marketRows(c.market)}</dl><h4>Grading</h4><dl class="target-evidence">${grading}</dl>${liquidityLines(c.liquidity)}<details><summary>Prices &amp; sources</summary><ul><li><a href="${esc(c.imageSourceUrl)}">${artCredit}</a></li></ul></details></div>
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
 function renderCard(c,checkedAt){return c.kind==='watch'?watchCard(c,checkedAt):upsideCard(c,checkedAt);}
 function earlierCards(examples){
  return examples.map(c=>renderCard(c,c.checkedAt??config.review.checkedAt)).join('');
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
  const watch=examples.some(c=>c.kind==='watch');
  status.textContent=watch?`${examples.length} dated entr${examples.length===1?'y':'ies'}`:`${examples.length} dated PSA 10 scenario${examples.length===1?'':'s'}`;
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
    const mixed=examples.some(c=>c.kind==='watch');
    const earlier=examples.length?'<header><h3>'+(mixed?'Earlier dated entries':'Earlier PSA 10 scenarios')+'</h3><p class="target-context">'+(mixed?'Dates show when each figure was checked. Watch entries are not buy signals.':'Raw and grading prices were checked on the dates shown.')+'</p></header>'+earlierCards(examples):'';
    host.innerHTML=cards.map(c=>renderCard(c,c.checkedAt)).join('')+earlier;
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
return {validateConfig,validateFeed,upsideCard,watchCard,mount,unmount};
});
