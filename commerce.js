(function(root){'use strict';
const ROTATIONS={'www.ebay.co.uk':'710-53481-19255-0','www.ebay.com':'711-53200-19255-0'};
// US zones only. Other America/* zones (Toronto, Mexico City, Sao Paulo) are not a US signal.
const US_ZONES=new Set(['America/New_York','America/Detroit','America/Kentucky/Louisville','America/Kentucky/Monticello','America/Indiana/Indianapolis','America/Indiana/Vincennes','America/Indiana/Winamac','America/Indiana/Marengo','America/Indiana/Petersburg','America/Indiana/Vevay','America/Indiana/Tell_City','America/Indiana/Knox','America/Chicago','America/Menominee','America/North_Dakota/Center','America/North_Dakota/New_Salem','America/North_Dakota/Beulah','America/Denver','America/Boise','America/Phoenix','America/Los_Angeles','America/Anchorage','America/Juneau','America/Sitka','America/Metlakatla','America/Yakutat','America/Nome','America/Adak','America/Puerto_Rico','America/Virgin','America/Indianapolis','America/Louisville','America/Knox_IN','America/Fort_Wayne','America/Atka','America/Shiprock','Pacific/Honolulu','Pacific/Guam','Pacific/Pago_Pago','Pacific/Midway','Pacific/Wake','US/Eastern','US/Central','US/Mountain','US/Pacific','US/Alaska','US/Aleutian','US/Arizona','US/Hawaii','US/East-Indiana','US/Indiana-Starke','US/Michigan','US/Samoa']);
const POST_TYPES={deal:'d_',news:'n_',feature:'f_',reply:'r_'};
const POST_TYPE_KEY='buytrigger.cards.commerce.post-type.v1';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function postTypePrefix(win){
  try{const type=win?.sessionStorage?.getItem(POST_TYPE_KEY);return Object.hasOwn(POST_TYPES,type)?POST_TYPES[type]:'';}catch(_){return '';}
}
function capturePostType(win){
  try{
    const value=new URL(win.location.href).searchParams.get('utm_content');
    if(value==null)return;
    const type=String(value).toLowerCase();
    if(!Object.hasOwn(POST_TYPES,type))return;
    win.sessionStorage.setItem(POST_TYPE_KEY,type);
  }catch(_){}
}
function customId(placement,win){
  if(!placement||!/^[a-zA-Z0-9_-]{1,64}$/.test(placement))return '';
  const id=(postTypePrefix(win)+placement).slice(0,64);
  return /^[a-zA-Z0-9_-]{1,64}$/.test(id)?id:'';
}
function attributeUrl(url,win){
  try{
    const prefix=postTypePrefix(win);
    if(!prefix)return url;
    const u=new URL(url,win?.location?.href);
    if(u.protocol!=='https:'||!ROTATIONS[u.host])return url;
    const id=u.searchParams.get('customid');
    if(!id||id.startsWith(prefix))return url;
    const next=customId(id,win);
    if(!next||next===id)return url;
    u.searchParams.set('customid',next);
    return u.href;
  }catch(_){return url;}
}
function stampEbayCustomIds(doc,win){
  if(!postTypePrefix(win))return;
  let links;try{links=doc.querySelectorAll('a[href*="customid="]');}catch(_){return;}
  for(const link of links){
    try{
      const raw=link.getAttribute('href');
      const next=attributeUrl(raw,win);
      if(next&&next!==raw)link.setAttribute('href',next);
    }catch(_){}
  }
}
function languageTags(nav){
  const tags=[];
  const push=value=>{const tag=String(value??'').trim().toLowerCase().replace(/_/g,'-');if(tag&&!tags.includes(tag))tags.push(tag);};
  try{push(nav&&nav.language);}catch(_){}
  try{const list=nav&&nav.languages;if(list&&typeof list.length==='number')for(let i=0;i<list.length;i++)push(list[i]);}catch(_){}
  return tags;
}
function readTimeZone(win){
  try{const tz=win?.Intl?.DateTimeFormat?.().resolvedOptions?.().timeZone;if(typeof tz==='string'&&tz)return tz;}catch(_){}
  if(win&&win===root){try{const tz=Intl.DateTimeFormat().resolvedOptions().timeZone;if(typeof tz==='string'&&tz)return tz;}catch(_){}}
  return '';
}
// Language plus time zone only. No IP lookup, storage or network.
function visitorMarket(win){
  const tags=languageTags(win?.navigator),tz=readTimeZone(win);
  if(tags.some(tag=>tag==='en-gb'||tag.startsWith('en-gb-'))||tz==='Europe/London')return 'uk';
  const usLanguage=tags.some(tag=>tag==='en-us'||tag.startsWith('en-us-'));
  const usZone=US_ZONES.has(tz);
  if((usLanguage&&tz.startsWith('America/')&&usZone)||usZone)return 'us';
  return 'other';
}
function isEbayHost(host){
  return /^(?:[a-z0-9-]+\.)*ebay\.(?:com|co\.uk|ca|de|fr|it|es|nl|ie|at|ch|be|pl|ph|com\.au|com\.sg|com\.hk)$/.test(String(host||'').toLowerCase());
}
function rewriteEbayHref(href,market){
  let u;
  try{u=new URL(href);}catch(_){return href;}
  if(u.protocol!=='https:'||u.username||u.password||!isEbayHost(u.hostname)||u.pathname!=='/sch/i.html')return href;
  // Sold-listing citations stay on the marketplace that recorded the sales.
  if(u.searchParams.has('LH_Sold')||u.searchParams.has('LH_Complete'))return href;
  const uk=market==='uk';
  const nextHost=uk?'www.ebay.co.uk':'www.ebay.com';
  const bin=u.searchParams.get('LH_BIN')==='1';
  const hadLoc=[...u.searchParams.keys()].includes('LH_PrefLoc');
  const params=[...u.searchParams.entries()].filter(([key])=>key!=='LH_PrefLoc'&&key!=='mkrid');
  const rebuilt=[];
  let placedMkrid=false,placedLoc=false;
  for(const pair of params){
    if(pair[0]==='LH_BIN'&&uk&&(bin||hadLoc)){rebuilt.push(pair,['LH_PrefLoc','1']);placedLoc=true;continue;}
    if(pair[0]==='campid'&&!placedMkrid){rebuilt.push(['mkrid',ROTATIONS[nextHost]]);placedMkrid=true;}
    rebuilt.push(pair);
  }
  if(uk&&(bin||hadLoc)&&!placedLoc)rebuilt.push(['LH_PrefLoc','1']);
  if(!placedMkrid)rebuilt.push(['mkrid',ROTATIONS[nextHost]]);
  const out=new URL('https://'+nextHost+u.pathname);
  for(const [key,value] of rebuilt)out.searchParams.append(key,value);
  if(u.hash)out.hash=u.hash;
  return out.href;
}
function forVisitor(href,win){
  if(!href)return href;
  const scope=win||root;
  if(!scope||!scope.document)return href;
  return rewriteEbayHref(href,visitorMarket(scope));
}
function rewriteEbayHrefs(scope,win){
  const market=visitorMarket(win||root);
  const node=scope||win?.document||root?.document;
  if(!node)return;
  const links=[];
  try{if(node.nodeType===1&&String(node.tagName).toLowerCase()==='a'&&node.getAttribute('href'))links.push(node);}catch(_){}
  try{if(node.querySelectorAll)links.push(...node.querySelectorAll('a[href*="ebay."]'));}catch(_){return;}
  for(const link of links){
    try{
      const raw=link.getAttribute('href');
      const next=rewriteEbayHref(raw,market);
      if(next&&next!==raw)link.setAttribute('href',next);
    }catch(_){}
  }
}
function watchEbayHrefs(doc,win){
  const Observer=win?.MutationObserver;
  if(typeof Observer!=='function'||!doc?.documentElement)return;
  try{
    const observer=new Observer(records=>{
      for(const record of records)for(const added of record.addedNodes||[])if(added&&added.nodeType===1)rewriteEbayHrefs(added,win);
    });
    observer.observe(doc.documentElement,{childList:true,subtree:true});
  }catch(_){}
}
function ebayLink(target,config,placement,win){
  if(!config?.ebay?.enabled||!/^\d{10}$/.test(config.ebay.campaignId))return null;
  try{const u=new URL(target);if(u.protocol!=='https:'||!ROTATIONS[u.host]||u.username||u.password||u.hash)return null;
    const listing=/^\/itm\/\d{9,15}$/.test(u.pathname),search=u.pathname==='/sch/i.html';
    if(!listing&&!search)return null;
    // Card searches may add Buy It Now (LH_BIN). UK visitors also get LH_PrefLoc. Listing URLs stay limited to var.
    const allowed=listing?['var']:['_nkw','LH_BIN','LH_PrefLoc'];
    if([...u.searchParams.keys()].some(k=>!allowed.includes(k)))return null;
    if(search){
      if(!u.searchParams.get('_nkw'))return null;
      for(const k of ['LH_BIN','LH_PrefLoc'])if(u.searchParams.has(k)&&u.searchParams.get(k)!=='1')return null;
    }
    for(const [k,v] of Object.entries({mkevt:'1',mkcid:'1',mkrid:ROTATIONS[u.host],campid:config.ebay.campaignId,toolid:'10001'}))u.searchParams.set(k,v);
    const custom=customId(placement,arguments.length>3?win:root);
    if(custom)u.searchParams.set('customid',custom);
    return u.href;
  }catch{return null;}
}
function citePlacement(win){
  const path=String(win?.location?.pathname||'');
  const hash=String(win?.location?.hash||'').replace(/^#/,'');
  const route=String(win?.document?.body?.dataset?.route||'');
  const story=path.match(/\/stories\/([a-z0-9]+(?:-[a-z0-9]+)*)\/?$/)||hash.match(/^read\/([a-z0-9-]+)/)||route.match(/^read\/([a-z0-9-]+)/);
  if(story)return 'story-'+story[1]+'-cite';
  const news=path.match(/\/news\/([a-z0-9-]+)\/?$/)||hash.match(/^news\/([a-z0-9-]+)/)||route.match(/^news\/([a-z0-9-]+)/);
  if(news)return 'story-'+news[1].slice(0,45).replace(/-+$/,'')+'-cite';
  if(path.endsWith('undervalued-japanese.html')||hash==='japan'||route==='japan')return 'uvjp-cite';
  if(path.endsWith('undervalued.html')||hash==='targets'||route==='targets')return 'uv-cite';
  return '';
}
function mergeRel(value){
  const tokens=[];
  for(const token of String(value||'').split(/\s+/)) if(token&&!tokens.includes(token))tokens.push(token);
  for(const token of ['sponsored','nofollow','noopener']) if(!tokens.includes(token))tokens.push(token);
  return tokens.join(' ');
}
function tagCitations(doc,win){
  const config=win?.BT_COMMERCE,placement=citePlacement(win);
  if(!doc||!config?.ebay?.enabled)return;
  for(const link of doc.querySelectorAll('a[href]')){
    let href=link.getAttribute('href');
    if(!href||!/https:\/\/[^/]*ebay\./.test(href))continue;
    if(!href.includes('campid=')){
      if(!placement)continue;
      const next=citeHref(href,config,placement);
      if(!next||next===href)continue;
      link.setAttribute('href',next);
      href=next;
      if(!link.nextElementSibling?.classList?.contains('ebay-cite')){
        const label=doc.createElement('span');
        label.className='ebay-cite';
        label.textContent='Affiliate link';
        link.after(label);
      }
    }
    if(!String(link.getAttribute('href')||'').includes('campid='))continue;
    const rel=mergeRel(link.getAttribute('rel'));
    if(link.getAttribute('rel')!==rel)link.setAttribute('rel',rel);
  }
}
function citeHref(target,config,placement){
  try{
    const u=new URL(target);
    const host=u.hostname.toLowerCase();
    const mkrid=ROTATIONS[host]||(host.includes('ebay.')?ROTATIONS['www.ebay.co.uk']:null);
    if(u.protocol!=='https:'||!mkrid||u.searchParams.get('campid'))return target;
    const custom=customId(placement,root);
    if(!custom)return target;
    for(const [k,v] of Object.entries({mkevt:'1',mkcid:'1',mkrid,campid:config.ebay.campaignId,toolid:'10001',customid:custom})){
      if(!u.searchParams.has(k))u.searchParams.set(k,v);
    }
    return u.href;
  }catch{return target;}
}
function isFresh(offer,now=Date.now()){
  const checked=Date.parse(offer.checkedAt),expires=Date.parse(offer.expiresAt);
  return Number.isFinite(checked)&&Number.isFinite(expires)&&checked<=now&&now<expires&&expires>checked&&expires-checked<=900000;
}
function activeOffers(data,config,now=Date.now(),region='All'){
  return (data?.items||[]).filter(o=>isFresh(o,now)&&['In stock','Preorder'].includes(o.availability)
    &&(region==='All'||o.region===region)&&o.affiliateProvider==='ebay'
    &&/^https:\/\/www\.ebay\.(?:co\.uk|com)\/itm\/\d{9,15}(?:\?|$)/.test(o.productUrl)
    &&ebayLink(o.productUrl,config,o.id,null)===o.affiliateUrl);
}
function disclosure(){return 'As an eBay Partner Network Affiliate, we earn from qualifying purchases.';}
function measurement(config,slot,creative,destination){return `data-commercial-campaign="ebay-${esc(config.ebay.campaignId)}" data-commercial-slot="${slot}" data-commercial-creative="${esc(creative)}" data-commercial-destination="${esc(destination)}"`;}
function affiliateCard(config,placement){
  const url=forVisitor(ebayLink('https://www.ebay.co.uk/sch/i.html?_nkw=Pokemon+TCG',config,placement));
  if(!url)return '';
  return `<aside class="affiliate-placement" aria-label="eBay affiliate advertisement" ${measurement(config,placement==='cards-home'?'HOME-01':'DROPS-01','ebay-search-v1',placement)}><small class="commerce-label">Ad · Affiliate link</small><div class="affiliate-placement-body"><div><span class="kicker">THE COLLECTOR’S MARKETPLACE</span><h2>Find it on eBay.</h2><p>Explore Pokémon cards and collecting supplies. Search results, seller prices and availability vary.</p></div><a class="btn black" href="${esc(url)}" target="_blank" rel="sponsored nofollow noopener noreferrer">Search Pokémon on eBay ↗</a></div><p class="affiliate-disclosure">${disclosure()}</p></aside>`;
}
function offerCard(o,config,home){const check=new Date(o.checkedAt).toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Europe/London'});
  const price=o.price?`${new Intl.NumberFormat('en-GB',{style:'currency',currency:o.price.currency}).format(o.price.amount)} · item price; delivery shown by seller`:'Check price and delivery on the seller’s page.';
  return `<article class="verified-offer" data-offer-expires="${esc(o.expiresAt)}" ${measurement(config,home?'HOME-01':'DROPS-01','ebay-offer-v1',o.id)}><small class="commerce-label">Ad · Affiliate link</small><div class="drop-meta"><span>${esc(o.country)}</span><span>${esc(o.language)}</span><span>${esc(o.event)}</span></div><h3>${esc(o.title)}</h3><p>${esc(o.summary)}</p><p class="offer-seller">Seller: ${esc(o.seller)} · ${esc(o.fulfilment)}</p><p class="offer-price">${esc(price)}</p><p class="offer-status"><strong>${esc(o.availability)} when checked</strong> · ${esc(check)} UK time</p><a class="btn red" data-offer-link href="${esc(attributeUrl(o.affiliateUrl,root))}" target="_blank" rel="sponsored nofollow noopener noreferrer">View on eBay ↗</a></article>`;
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
const PRICE_NOTE='Each “Buy on eBay” control opens an eBay search (UK or US site depending on your location) for that card’s name, number and set, not a single listing. Search results, seller prices and availability vary. These are affiliate links: as an eBay Partner Network partner, we may earn from qualifying purchases.';
function cleanName(value){
  const name=String(value??'').replace(/\s+/g,' ').trim();
  if(name.length<2||name.length>80||!/[A-Za-z]/.test(name)||!/^[A-Za-z0-9\u00C0-\u024F][A-Za-z0-9\u00C0-\u024F '&.,()[\]!:-]*$/.test(name))return null;
  return name;
}
function cleanNumber(value){
  const number=String(value??'').trim();
  if(/^\d{1,3}\/\d{1,3}$/.test(number)||/^[A-Z]{1,4}\d{1,3}\/[A-Z]{1,4}\d{1,3}$/.test(number)||/^[RGB]\/RGB$/.test(number)||/^\d{2,4}$/.test(number))return number;
  return null;
}
function cleanSet(value){
  let set=String(value??'').replace(/\s+/g,' ').trim().replace(/^[A-Z]{2,4}\d{0,3}:\s+/,'');
  if(set.length<2||set.length>80||NOT_A_SET.has(set)||!/[A-Za-z]/.test(set)||!/^[A-Za-z0-9\u00C0-\u024F][A-Za-z0-9\u00C0-\u024F '&.,:+-]*$/.test(set))return null;
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
  if(card?.language==='Japanese'||card?.language==='ja')words.push('Japanese');
  if(grade==='psa10')words.push('PSA 10');
  const u=new URL('https://www.ebay.co.uk/sch/i.html');
  u.searchParams.set('_nkw',words.join(' '));
  u.searchParams.set('LH_BIN','1');
  return ebayLink(u.href,config,custom);
}
function ebayBar(card,raw,psa,line){
  const rel='rel="nofollow sponsored noopener" target="_blank"';
  const who=esc(card.name+' '+card.number);
  return `<div class="ebay-bar ${line?'ebay-bar-line':'ebay-bar-grey'}" role="group" aria-label="Buy on eBay"><a class="ebay-brand" href="${esc(raw)}" ${rel}><span>Buy on</span><img class="ebay-logo" src="${EBAY_WORDMARK}" alt="eBay" width="783" height="324"><span class="visually-hidden">, raw, Buy It Now search for ${who}</span></a><a class="ebay-seg" href="${esc(raw)}" ${rel}>RAW<span class="visually-hidden">, ${who}</span></a><a class="ebay-seg" href="${esc(psa)}" ${rel}>PSA 10<span class="visually-hidden">, ${who}</span></a></div>`;
}
function shopLabel(id){
  return [id.name,id.number,id.set].filter(Boolean).join(' · ');
}
function ebayShop(card,raw,psa,id){
  const label=shopLabel(id);
  const line='eBay search (UK or US site depending on your location). Results, seller prices and availability vary.';
  return `<aside class="shop-strip shop-inline" aria-label="Buy on eBay"><p class="shop-id">${esc(label)}</p>${ebayBar(id,raw,psa,false)}<p class="shop-meta"><span class="shop-affil">Affiliate link</span><span class="shop-explain">${esc(line)}</span></p></aside>`;
}
function ebayCardBlock(card,config,options={}){
  const id=cleanCard(card);
  const raw=forVisitor(cardSearchUrl(card,config,options.placement,'raw'));
  const psa=forVisitor(cardSearchUrl(card,config,options.placement,'psa10'));
  if(!id||!raw||!psa)return '';
  if(options.variant==='shop'||options.detail)return ebayShop(card,raw,psa,id);
  return ebayBar(id,raw,psa,false);
}
function ebayPageNote(){return `<div class="ebay-footnote"><p><strong>About the eBay links.</strong> ${PRICE_NOTE} “Check price” is a separate affiliate link.</p></div>`;}
function ebayListNote(){return `<div class="ebay-footnote"><p><strong>About the eBay links.</strong> ${PRICE_NOTE}</p></div>`;}
// Official logo path. Leave empty for the generic bag icon. One swap: set this to the asset path.
const TCGPLAYER_LOGO='';
function tcgplayerMark(){
  const src=String(TCGPLAYER_LOGO||'').trim();
  if(src)return `<img class="tcgplayer-mark" src="${esc(src)}" alt="" width="20" height="20">`;
  return `<svg class="tcgplayer-mark" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M6 8h12l-1.2 12H7.2L6 8zM9 8V6.8a3 3 0 0 1 6 0V8"/></svg>`;
}
function tcgplayerHref(config){
  const raw=String(config?.tcgplayerImpactUrl??'').trim();
  if(!raw)return '';
  let u;
  try{u=new URL(raw);}catch(_){return '';}
  if(u.protocol!=='https:'||!u.host||u.username||u.password)return '';
  u.searchParams.set('subId1','banner');
  u.searchParams.set('subId2','home');
  return u.href;
}
function tcgplayerBanner(config){
  const url=tcgplayerHref(config);
  if(!url)return '';
  return `<aside class="tcgplayer-banner" aria-label="TCGplayer affiliate advertisement"><p class="tcgplayer-banner-label">Advertisement · affiliate link</p><div class="tcgplayer-banner-body"><p class="tcgplayer-brand">${tcgplayerMark()}<span>TCGplayer</span></p><div class="tcgplayer-banner-copy"><h2>Find your next Pokémon single.</h2><p>Explore the TCGplayer marketplace.</p></div><a class="btn black" href="${esc(url)}" target="_blank" rel="sponsored nofollow noopener">Shop Pokémon on TCGplayer</a></div><p class="tcgplayer-banner-disclosure">We may earn a commission from a purchase through this link.</p></aside>`;
}
const api={ebayLink,citeHref,tagCitations,isFresh,activeOffers,affiliateCard,disclosure,createPlacementTracker,cleanCard,cardSearchUrl,ebayCardBlock,ebayPageNote,ebayListNote,capturePostType,stampEbayCustomIds,visitorMarket,rewriteEbayHref,rewriteEbayHrefs,tcgplayerHref,tcgplayerBanner};
if(typeof module==='object'&&module.exports)module.exports=api;
if(root)root.BTCommerce=api;
if(!root?.document)return;
const doc=root.document;
capturePostType(root);
stampEbayCustomIds(doc,root);
rewriteEbayHrefs(doc,root);
watchEbayHrefs(doc,root);
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
function mountTcgplayerBanner(){
  if(doc.body?.dataset?.page!=='home'||doc.getElementById('tcgplayer-home-banner'))return;
  const html=tcgplayerBanner(root.BT_COMMERCE);
  if(!html)return;
  const main=doc.querySelector('#main');if(!main)return;
  const node=doc.createElement('div');node.id='tcgplayer-home-banner';node.className='section tcgplayer-banner-wrap';node.innerHTML=html;
  main.append(node);
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
if(!['home','drops'].includes(doc.body?.dataset?.page)&&!root.BT_COMMERCE&&!doc.querySelector('[data-ebay-card]'))return;
doc.addEventListener('click',e=>{
  const link=e.target.closest('[data-offer-link]');
  if(link&&Date.now()>=Date.parse(link.closest('[data-offer-expires]').dataset.offerExpires)){e.preventDefault();e.stopImmediatePropagation();expireVisible();return;}
},true);
doc.addEventListener('click',e=>{const filter=e.target.closest('[data-drop-region]');if(filter){renderOffers(filter.dataset.dropRegion);mountPlacement('drops');}});
root.addEventListener('hashchange',()=>{mount();mountTcgplayerBanner();mountCardSlots();tagCitations(doc,root);});tagCitations(doc,root);doc.addEventListener('visibilitychange',expireVisible);root.setInterval(expireVisible,10000);mount();mountTcgplayerBanner();mountCardSlots();
const measurementTracker=createPlacementTracker(root);root.setInterval(()=>measurementTracker.tick(),250);doc.addEventListener('click',measurementTracker.click);doc.addEventListener('auxclick',e=>{if(e.button===1)measurementTracker.click(e);});doc.addEventListener('visibilitychange',measurementTracker.hidden);
})(typeof window!=='undefined'?window:null);
