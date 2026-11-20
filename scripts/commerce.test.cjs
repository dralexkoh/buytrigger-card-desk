const test=require('node:test');
const assert=require('node:assert/strict');
const {ebayLink,isFresh,activeOffers,affiliateCard,cardSearchUrl,ebayCardBlock,cleanCard}=require('../commerce.js');
const config={schemaVersion:1,placements:{home:false,drops:true},ebay:{enabled:true,campaignId:'5339239680'},amazonUk:{enabled:false,trackingId:'buytrigger-21'}};
const now=Date.parse('2026-11-04T17:00:00Z');
const offer={id:'ebay-123456789012',region:'UK',affiliateProvider:'ebay',productUrl:'https://www.ebay.co.uk/itm/123456789012',checkedAt:'2026-11-04T16:59:00Z',expiresAt:'2026-11-04T17:14:00Z',availability:'In stock'};
offer.affiliateUrl=ebayLink(offer.productUrl,config,offer.id);
test('own campaign, marketplace rotation and exact item are retained',()=>{
 const u=new URL(offer.affiliateUrl);assert.equal(u.pathname,'/itm/123456789012');assert.equal(u.searchParams.get('campid'),'5339239680');assert.equal(u.searchParams.get('mkrid'),'710-53481-19255-0');
 assert.equal(new URL(ebayLink('https://www.ebay.com/itm/123456789012',config)).searchParams.get('mkrid'),'711-53200-19255-0');
});
test('disabled programme, foreign affiliate tags and misleading hosts are rejected',()=>{
 for(const url of ['https://www.ebay.co.uk.evil.test/itm/123456789012','http://www.ebay.co.uk/itm/123456789012','https://user@www.ebay.co.uk/itm/123456789012','https://www.ebay.co.uk/itm/123456789012?campid=5330000000','https://www.amazon.co.uk/dp/B012345678'])assert.equal(ebayLink(url,config),null);
 assert.equal(ebayLink(offer.productUrl,{ebay:{enabled:false,campaignId:'5339239680'}}),null);
});
test('expiry works exactly at deadline, for future checks and oversized windows',()=>{
 assert.equal(isFresh(offer,now),true);assert.equal(isFresh(offer,Date.parse(offer.expiresAt)),false);
 assert.equal(isFresh(offer,Date.parse(offer.checkedAt)-1),false);assert.equal(isFresh({...offer,expiresAt:'2026-11-04T18:00:00Z'},now),false);
});
test('search advertisements do not masquerade as verified product offers',()=>{
 const search=ebayLink('https://www.ebay.co.uk/sch/i.html?_nkw=Pokemon+TCG',config,'cards-home');
 assert.match(search,/_nkw=Pokemon\+TCG/);assert.match(affiliateCard(config,'cards-home'),/Ad · Affiliate link/);assert.match(affiliateCard(config,'cards-home'),/Search results, seller prices and availability vary/);
 const productUrl='https://www.ebay.co.uk/sch/i.html?_nkw=Pokemon';
 assert.deepEqual(activeOffers({items:[{...offer,productUrl,affiliateUrl:ebayLink(productUrl,config,offer.id)}]},config,now),[]);
});
test('card search keeps the campaign from commerce config and the approved URL shape',()=>{
 const card={name:'Mega Rayquaza ex - 138/103',number:'138/103',set:'ME06: Delta Reign'};
 const raw=cardSearchUrl(card,config,'price','raw');
 assert.equal(raw,'https://www.ebay.co.uk/sch/i.html?_nkw=Mega+Rayquaza+ex+138%2F103+Delta+Reign&LH_BIN=1&LH_PrefLoc=1&mkevt=1&mkcid=1&mkrid=710-53481-19255-0&campid=5339239680&toolid=10001&customid=price-raw');
 const psa=new URL(cardSearchUrl(card,config,'price','psa10'));
 assert.equal(psa.searchParams.get('_nkw'),'Mega Rayquaza ex 138/103 Delta Reign PSA 10');
 assert.equal(psa.searchParams.get('customid'),'price-psa10');
 assert.equal(psa.searchParams.get('campid'),config.ebay.campaignId);
 const other={...config,ebay:{...config.ebay,campaignId:'5330000001'}};
 assert.equal(new URL(cardSearchUrl(card,other,'db','raw')).searchParams.get('campid'),'5330000001');
});
test('Buy It Now filters are allowed only as 1, and a card without a clean set is skipped',()=>{
 assert.equal(ebayLink('https://www.ebay.co.uk/sch/i.html?_nkw=Pikachu&LH_BIN=1&LH_PrefLoc=1',config,'price-raw')!==null,true);
 assert.equal(ebayLink('https://www.ebay.co.uk/sch/i.html?_nkw=Pikachu&LH_BIN=0',config),null);
 assert.equal(ebayLink('https://www.ebay.co.uk/sch/i.html?_nkw=Pikachu&_odkw=1',config),null);
 assert.equal(ebayLink('https://www.ebay.co.uk/itm/123456789012?LH_BIN=1',config),null);
 assert.equal(cardSearchUrl({name:'Heracross',number:'001/103',set:'Common'},config,'price'),null);
 assert.equal(cleanCard({name:'',number:'001/103',set:'Delta Reign'}),null);
 const html=ebayCardBlock({name:'Mega Rayquaza ex',number:'138/103',set:'Delta Reign'},config,{placement:'db',detail:true,stack:false,pill:true,note:'card'});
 assert.match(html,/Buy on eBay/);
 assert.match(html,/rel="nofollow sponsored noopener"/);
 assert.match(html,/target="_blank"/);
 assert.match(html,/customid=db-raw/);
 assert.match(html,/customid=db-psa10/);
 assert.match(html,/Affiliate link/);
 assert.match(html,/eBay Partner Network affiliate/);
 assert.doesNotMatch(html,/<img|logo/i);
});
test('only fresh available exact offers with our campaign enter each region',()=>{
 assert.equal(activeOffers({items:[offer]},config,now,'UK').length,1);
 for(const bad of [{...offer,availability:'Sold out'},{...offer,availability:'Invitation'},{...offer,affiliateUrl:offer.affiliateUrl.replace('5339239680','5330000000')},{...offer,affiliateProvider:'amazonUk'}])assert.equal(activeOffers({items:[bad]},config,now).length,0);
 assert.equal(activeOffers({items:[offer]},config,now,'US').length,0);
});
