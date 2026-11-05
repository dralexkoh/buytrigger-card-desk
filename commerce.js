(function(root){'use strict';
const ROTATIONS={'www.ebay.co.uk':'710-53481-19255-0','www.ebay.com':'711-53200-19255-0'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function ebayLink(target,config,placement){
  if(!config?.ebay?.enabled||!/^\d{10}$/.test(config.ebay.campaignId))return null;
  try{const u=new URL(target);if(u.protocol!=='https:'||!ROTATIONS[u.host]||u.username||u.password||u.hash)return null;
    const listing=/^\/itm\/\d{9,15}$/.test(u.pathname),search=u.pathname==='/sch/i.html';
    if(!listing&&!search)return null;
    const allowed=listing?['var']:['_nkw'];if([...u.searchParams.keys()].some(k=>!allowed.includes(k)))return null;
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
const api={ebayLink,isFresh,activeOffers,affiliateCard,disclosure,createPlacementTracker};
if(typeof module==='object'&&module.exports)module.exports=api;
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
doc.addEventListener('click',e=>{
  const link=e.target.closest('[data-offer-link]');
  if(link&&Date.now()>=Date.parse(link.closest('[data-offer-expires]').dataset.offerExpires)){e.preventDefault();e.stopImmediatePropagation();expireVisible();return;}
},true);
doc.addEventListener('click',e=>{const filter=e.target.closest('[data-drop-region]');if(filter){renderOffers(filter.dataset.dropRegion);mountPlacement('drops');}});
root.addEventListener('hashchange',mount);doc.addEventListener('visibilitychange',expireVisible);root.setInterval(expireVisible,10000);mount();
const measurementTracker=createPlacementTracker(root);root.setInterval(()=>measurementTracker.tick(),250);doc.addEventListener('click',measurementTracker.click);doc.addEventListener('visibilitychange',measurementTracker.hidden);
})(typeof window!=='undefined'?window:null);
