const test=require('node:test');
const assert=require('node:assert/strict');
const {ebayLink,isFresh,activeOffers,affiliateCard}=require('../commerce.js');
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
test('only fresh available exact offers with our campaign enter each region',()=>{
 assert.equal(activeOffers({items:[offer]},config,now,'UK').length,1);
 for(const bad of [{...offer,availability:'Sold out'},{...offer,availability:'Invitation'},{...offer,affiliateUrl:offer.affiliateUrl.replace('5339239680','5330000000')},{...offer,affiliateProvider:'amazonUk'}])assert.equal(activeOffers({items:[bad]},config,now).length,0);
 assert.equal(activeOffers({items:[offer]},config,now,'US').length,0);
});
