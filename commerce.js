(function(root){'use strict';
const ROTATIONS={'www.ebay.co.uk':'710-53481-19255-0','www.ebay.com':'711-53200-19255-0'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function ebayLink(target,config,placement){
  if(!config?.ebay?.enabled||!/^\d{10}$/.test(config.ebay.campaignId))return null;
  try{const u=new URL(target);if(u.protocol!=='https:'||!ROTATIONS[u.host]||u.username||u.password||u.hash)return null;
    const listing=/^\/itm\/\d{9,15}$/.test(u.pathname),search=u.pathname==='/sch/i.html';
    if(!listing&&!search)return null;
    // Card searches add Buy It Now (LH_BIN) and UK item location (LH_PrefLoc). Listing URLs stay limited to var.
    const allowed=listing?['var']:['_nkw','LH_BIN','LH_PrefLoc'];
    if([...u.searchParams.keys()].some(k=>!allowed.includes(k)))return null;
    if(search){
      if(!u.searchParams.get('_nkw'))return null;
      for(const k of ['LH_BIN','LH_PrefLoc'])if(u.searchParams.has(k)&&u.searchParams.get(k)!=='1')return null;
    }
    for(const [k,v] of Object.entries({mkevt:'1',mkcid:'1',mkrid:ROTATIONS[u.host],campid:config.ebay.campaignId,toolid:'10001'}))u.searchParams.set(k,v);
    if(placement&&/^[a-zA-Z0-9_-]{1,64}$/.test(placement))u.searchParams.set('customid',placement);
    return u.href;
  }catch{return null;}
}
function isFresh(offer,now=Date.now()){
  const checked=Date.parse(offer.checkedAt),expires=Date.parse(offer.expiresAt);
  return Number.isFinite(checked)&&Number.isFinite(expires)&&checked<=now&&now<expires&&expires>checked&&expires-checked<=900000;
}
function activeOffers(data,config,now=Date.now(),region='All'){
  return (data?.items||[]).filter(o=>isFresh(o,now)&&['In stock','Preorder'].includes(o.availability)
    &&(region==='All'||o.region===region)&&o.affiliateProvider==='ebay'
    &&/^https:\/\/www\.ebay\.(?:co\.uk|com)\/itm\/\d{9,15}(?:\?|$)/.test(o.productUrl)
    &&ebayLink(o.productUrl,config,o.id)===o.affiliateUrl);
}
function disclosure(){return 'As an eBay Partner Network Affiliate, we earn from qualifying purchases.';}
function measurement(config,slot,creative,destination){return `data-commercial-campaign="ebay-${esc(config.ebay.campaignId)}" data-commercial-slot="${slot}" data-commercial-creative="${esc(creative)}" data-commercial-destination="${esc(destination)}"`;}
function affiliateCard(config,placement){
  const url=ebayLink('https://www.ebay.co.uk/sch/i.html?_nkw=Pokemon+TCG',config,placement);
  if(!url)return '';
  return `<aside class="affiliate-placement" aria-label="eBay affiliate advertisement" ${measurement(config,placement==='cards-home'?'HOME-01':'DROPS-01','ebay-search-v1',placement)}><small class="commerce-label">Ad · Affiliate link</small><div class="affiliate-placement-body"><div><span class="kicker">THE COLLECTOR’S MARKETPLACE</span><h2>Find it on eBay.</h2><p>Explore Pokémon cards and collecting supplies. Search results, seller prices and availability vary.</p></div><a class="btn black" href="${esc(url)}" target="_blank" rel="sponsored noopener noreferrer">Search Pokémon on eBay ↗</a></div><p class="affiliate-disclosure">${disclosure()}</p></aside>`;
}
function offerCard(o,config,home){const check=new Date(o.checkedAt).toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Europe/London'});
  const price=o.price?`${new Intl.NumberFormat('en-GB',{style:'currency',currency:o.price.currency}).format(o.price.amount)} · item price; delivery shown by seller`:'Check price and delivery on the seller’s page.';
  return `<article class="verified-offer" data-offer-expires="${esc(o.expiresAt)}" ${measurement(config,home?'HOME-01':'DROPS-01','ebay-offer-v1',o.id)}><small class="commerce-label">Ad · Affiliate link</small><div class="drop-meta"><span>${esc(o.country)}</span><span>${esc(o.language)}</span><span>${esc(o.event)}</span></div><h3>${esc(o.title)}</h3><p>${esc(o.summary)}</p><p class="offer-seller">Seller: ${esc(o.seller)} · ${esc(o.fulfilment)}</p><p class="offer-price">${esc(price)}</p><p class="offer-status"><strong>${esc(o.availability)} when checked</strong> · ${esc(check)} UK time</p><a class="btn red" data-offer-link href="${esc(o.affiliateUrl)}" target="_blank" rel="sponsored noopener noreferrer">View on eBay ↗</a></article>`;
}
// Internal measurement: one served/impression/click per placement and page visit.
// Consent, DNT, browser exclusion and QA are enforced by the existing counter.
function createPlacementTracker(win){
 let page='',sent=new Set(),timers=new WeakMap();
 const props=el=>({campaign_id:el.dataset.commercialCampaign,slot_id:el.dataset.commercialSlot,creative_id:el.dataset.commercialCreative,destination_id:el.dataset.commercialDestination});
 const key=(el,event)=>event+'|'+Object.values(props(el)).join('|');
 function resetPage(){const next=win.location.pathname+win.location.hash;if(next!==page){page=next;sent=new Set();timers=new WeakMap();}}
 function eligible(el){return !!win.BTAnalytics?.allowed?.()&&el.isConnected&&(!el.dataset.offerExpires||Date.now()<Date.parse(el.dataset.offerExpires))&&!!el.querySelector('a[href]');}
 function send(el,event){const k=key(el,event);if(sent.has(k))return true;if(win.BTAnalytics.track(event,props(el))){sent.add(k);return true;}return false;}
 function tick(now=Date.now()){
  resetPage();for(const el of win.document.querySelectorAll('[data-commercial-campaign]')){
   if(!eligible(el)){timers.delete(el);continue;}send(el,'ad_served');
   const r=el.getBoundingClientRect(),area=Math.max(0,r.width)*Math.max(0,r.height),visible=Math.max(0,Math.min(r.right,win.innerWidth)-Math.max(r.left,0))*Math.max(0,Math.min(r.bottom,win.innerHeight)-Math.max(r.top,0));
   if(win.document.visibilityState!=='visible'||!area||visible/area<.5){timers.delete(el);continue;}
   if(!timers.has(el))timers.set(el,now);
   if(now-timers.get(el)>=1000)send(el,'ad_impression');
  }
 }
 function click(event){resetPage();if(event.defaultPrevented)return;const link=event.target?.closest?.('a[href]'),el=link?.closest('[data-commercial-campaign]');if(!el||!eligible(el))return;send(el,'ad_served');send(el,'ad_click');}
 function hidden(){if(win.document.visibilityState!=='visible')timers=new WeakMap();}
 return{tick,click,hidden};
}
const NOT_A_SET=new Set(['Common','Uncommon','Rare','Double Rare','Ultra Rare','Illustration Rare','Special Illustration Rare','Hyper Rare','Mega Hyper Rare','ACE SPEC Rare','TCG Modern','30th Anniversary']);
const EBAY_WORDMARK='assets/ebay/ebay-wordmark-b4-trimmed.png';
const PRICE_NOTE='Each “Buy on eBay” control opens an eBay UK Buy It Now search for that card’s name, number and set, not a single listing. Search results, seller prices and availability vary. These are affiliate links: as an eBay Partner Network partner, we may earn from qualifying purchases.';
function cleanName(value){
  const name=String(value??'').replace(/\s+/g,' ').trim();
  if(name.length<2||name.length>80||!/[A-Za-z]/.test(name)||!/^[A-Za-z0-9][A-Za-z0-9 '&.,()[\]!:-]*$/.test(name))return null;
  return name;
}
function cleanNumber(value){
  const number=String(value??'').trim();
  if(/^\d{1,3}\/\d{1,3}$/.test(number)||/^[A-Z]{1,4}\d{1,3}\/[A-Z]{1,4}\d{1,3}$/.test(number)||/^[RGB]\/RGB$/.test(number)||/^\d{2,4}$/.test(number))return number;
  return null;
}
function cleanSet(value){
  let set=String(value??'').replace(/\s+/g,' ').trim().replace(/^[A-Z]{2,4}\d{0,3}:\s+/,'');
  if(set.length<2||set.length>80||NOT_A_SET.has(set)||!/[A-Za-z]/.test(set)||!/^[A-Za-z0-9][A-Za-z0-9 '&.,:+-]*$/.test(set))return null;
  return set;
}
function cleanCard(card){
  const number=cleanNumber(card?.number);
  if(!number)return null;
  let raw=String(card?.name??'').replace(/\s+/g,' ').trim();
  const needle=' - '+number;
  const at=raw.indexOf(needle);
  if(at>=0)raw=(raw.slice(0,at)+' '+raw.slice(at+needle.length)).replace(/\s+/g,' ').trim();
  const name=cleanName(raw),set=cleanSet(card?.set);
  return name&&set?{name,number,set}:null;
}
function placementId(prefix,grade){
  const id=String(prefix||'')+'-'+(grade==='psa10'?'psa10':'raw');
  return /^[a-zA-Z0-9_-]{1,64}$/.test(id)?id:null;
}
function cardSearchUrl(card,config,placement,grade){
  const id=cleanCard(card),custom=placementId(placement,grade==='psa10'?'psa10':'raw');
  if(!id||!custom||(grade!=='raw'&&grade!=='psa10'))return null;
  const words=[id.name,id.number,id.set];
  if(grade==='psa10')words.push('PSA 10');
  const u=new URL('https://www.ebay.co.uk/sch/i.html');
  u.searchParams.set('_nkw',words.join(' '));
  u.searchParams.set('LH_BIN','1');
  u.searchParams.set('LH_PrefLoc','1');
  return ebayLink(u.href,config,custom);
}
function ebayBar(card,raw,psa,line){
  const rel='rel="nofollow sponsored noopener" target="_blank"';
  const who=esc(card.name+' '+card.number);
  return `<div class="ebay-bar ${line?'ebay-bar-line':'ebay-bar-grey'}" role="group" aria-label="Buy on eBay"><a class="ebay-brand" href="${esc(raw)}" ${rel}><span>Buy on</span><img class="ebay-logo" src="${EBAY_WORDMARK}" alt="eBay" width="783" height="324"><span class="visually-hidden">, raw, UK Buy It Now search for ${who}</span></a><a class="ebay-seg" href="${esc(raw)}" ${rel}>RAW<span class="visually-hidden">, ${who}</span></a><a class="ebay-seg" href="${esc(psa)}" ${rel}>PSA 10<span class="visually-hidden">, ${who}</span></a></div>`;
}
function shopLabel(id){
  return [id.name,id.number,id.set].filter(Boolean).join(' · ');
}
function ebayShop(card,raw,psa,id){
  const label=shopLabel(id);
  const line=`Opens an eBay UK Buy It Now search for ${label}. Search results, seller prices and availability vary.`;
  return `<aside class="shop-strip" aria-label="Shop this card on eBay"><div class="shop-strip-head"><span class="kicker red-text">Shop this card</span><p class="shop-id">${esc(label)}</p><span class="shop-affil">Affiliate link</span></div><p class="shop-explain">${esc(line)}</p>${ebayBar(id,raw,psa,true)}</aside>`;
}
function ebayCardBlock(card,config,options={}){
  const id=cleanCard(card);
  const raw=cardSearchUrl(card,config,options.placement,'raw');
  const psa=cardSearchUrl(card,config,options.placement,'psa10');
  if(!id||!raw||!psa)return '';
  if(options.variant==='shop'||options.detail)return ebayShop(card,raw,psa,id);
  return ebayBar(id,raw,psa,false);
}
function ebayPageNote(){return `<div class="ebay-footnote"><p><strong>About the eBay links.</strong> ${PRICE_NOTE} “Check price” is a separate affiliate link.</p></div>`;}
function ebayListNote(){return `<div class="ebay-footnote"><p><strong>About the eBay links.</strong> ${PRICE_NOTE}</p></div>`;}
const api={ebayLink,isFresh,activeOffers,affiliateCard,disclosure,createPlacementTracker,cleanCard,cardSearchUrl,ebayCardBlock,ebayPageNote,ebayListNote};
if(typeof module==='object'&&module.exports)module.exports=api;
if(root)root.BTCommerce=api;
if(!root?.document)return;
const doc=root.document;
function offersMarkup(items,home){return `<div class="section-heading"><div><span class="kicker red-text">CHECKED AT THE SELLER</span><h2>${home?'Latest verified offers':'Verified product offers'}</h2></div>${home?'<a class="text-link" href="drops.html">See Drops →</a>':''}</div><p class="offers-note">Availability changes quickly. Each offer is checked separately from the release calendar.</p><div class="verified-offer-grid">${items.map(o=>offerCard(o,root.BT_COMMERCE,home)).join('')}</div><p class="affiliate-disclosure">${disclosure()}</p>`;}
function expireVisible(){for(const card of doc.querySelectorAll('[data-offer-expires]')){
  if(Date.now()<Date.parse(card.dataset.offerExpires))continue;
  const status=card.querySelector('.offer-status');if(status)status.textContent='Availability needs rechecking. This offer has expired.';
  const price=card.querySelector('.offer-price');if(price)price.textContent='Current price and availability are unverified.';
  const link=card.querySelector('[data-offer-link]');if(link){const disabled=doc.createElement('span');disabled.className='btn offer-expired';disabled.setAttribute('aria-disabled','true');disabled.textContent='Check needed';link.replaceWith(disabled);}
}}
function renderOffers(region='All'){
  const host=doc.querySelector('#verified-offers');if(!host)return;
  const home=doc.body.dataset.page==='home',items=activeOffers(root.BT_DROPS_OFFERS,root.BT_COMMERCE,Date.now(),region).slice(0,home?3:12);
  host.innerHTML=items.length?offersMarkup(items,home):(home?'':'<h2>Verified product offers</h2><p class="offers-note">No fresh verified offers for this region right now. Confirmed release dates are listed below.</p>');
  host.hidden=home&&!items.length;
}
function mountPlacement(page){
  const main=doc.querySelector('#main');if(!main||doc.querySelector('#affiliate-placement'))return;
  const node=doc.createElement('div');node.id='affiliate-placement';node.className='commerce-wrap';node.innerHTML=affiliateCard(root.BT_COMMERCE,page==='home'?'cards-home':'cards-drops');
  if(page==='home')main.querySelector('#verified-offers')?.before(node);
  else{const cards=[...main.querySelectorAll('#drop-list > .drop-card')],anchor=cards[Math.min(2,cards.length-1)];if(anchor)anchor.after(node);else main.append(node);}
}
function mount(){
  const main=doc.querySelector('#main'),page=doc.body.dataset.page;if(!main||!['home','drops'].includes(page))return;
  const config=root.BT_COMMERCE;if(!config||config.placements?.[page]!==true)return;
  if(!doc.querySelector('#verified-offers')){
    const section=doc.createElement('section');section.id='verified-offers';section.className='verified-offers section';section.setAttribute('aria-label','Verified product offers');
    if(page==='drops')main.querySelector('.drops-wrap')?.before(section);
    else main.querySelector('.feature-story')?.closest('section')?.before(section);
  }
  renderOffers();
  mountPlacement(page);
}
function mountCardSlots(){
  const config=root.BT_COMMERCE;if(!config)return;
  for(const el of doc.querySelectorAll('[data-ebay-card]')){
    if(el.dataset.ebayReady)continue;
    el.innerHTML=ebayCardBlock({
      name:el.getAttribute('data-ebay-name'),
      number:el.getAttribute('data-ebay-number'),
      set:el.getAttribute('data-ebay-set')
    },config,{
      placement:el.getAttribute('data-ebay-placement')||'',
      variant:el.getAttribute('data-ebay-detail')==='tile'?'row':'shop'
    });
    el.dataset.ebayReady='1';
  }
  const grid=doc.querySelector('#set-grid');
  if(grid&&!grid.parentElement.querySelector(':scope > .ebay-footnote'))grid.insertAdjacentHTML('afterend',ebayListNote());
}
doc.addEventListener('click',e=>{
  const link=e.target.closest('[data-offer-link]');
  if(link&&Date.now()>=Date.parse(link.closest('[data-offer-expires]').dataset.offerExpires)){e.preventDefault();e.stopImmediatePropagation();expireVisible();return;}
},true);
doc.addEventListener('click',e=>{const filter=e.target.closest('[data-drop-region]');if(filter){renderOffers(filter.dataset.dropRegion);mountPlacement('drops');}});
root.addEventListener('hashchange',()=>{mount();mountCardSlots();});doc.addEventListener('visibilitychange',expireVisible);root.setInterval(expireVisible,10000);mount();mountCardSlots();
const measurementTracker=createPlacementTracker(root);root.setInterval(()=>measurementTracker.tick(),250);doc.addEventListener('click',measurementTracker.click);doc.addEventListener('auxclick',e=>{if(e.button===1)measurementTracker.click(e);});doc.addEventListener('visibilitychange',measurementTracker.hidden);
})(typeof window!=='undefined'?window:null);
