const test=require('node:test'),assert=require('node:assert/strict');
const{createPlacementTracker}=require('../commerce.js');
function fixture(){
 const events=[];let allowed=false;
 const el={dataset:{commercialCampaign:'ebay-5339239680',commercialSlot:'DROPS-01',commercialCreative:'ebay-search-v1',commercialDestination:'cards-drops'},isConnected:true,querySelector:()=>({}),getBoundingClientRect:()=>({left:0,top:0,right:100,bottom:100,width:100,height:100})};
 const win={location:{pathname:'/',hash:'#drops'},innerWidth:100,innerHeight:100,document:{visibilityState:'visible',querySelectorAll:()=>[el]},BTAnalytics:{allowed:()=>allowed,track:(event,props)=>{events.push({event,props});return true;}}};
 return{events,el,win,tracker:createPlacementTracker(win),allow:v=>allowed=v};
}
test('no commercial tracking before consent; one served, qualified impression and click per placement/page',()=>{
 const f=fixture();f.tracker.tick(0);f.tracker.tick(1001);assert.equal(f.events.length,0);f.allow(true);f.tracker.tick(2000);f.tracker.tick(2999);assert.deepEqual(f.events.map(x=>x.event),['ad_served']);f.tracker.tick(3000);f.tracker.tick(4000);
 const event={target:{closest:()=>({closest:()=>f.el})}};f.tracker.click(event);f.tracker.click(event);assert.deepEqual(f.events.map(x=>x.event),['ad_served','ad_impression','ad_click']);f.win.location.hash='#home';f.tracker.tick(5000);assert.equal(f.events.at(-1).event,'ad_served');
});
test('visibility must remain continuous; hidden, offscreen, expired, detached and revoked placements cannot count',()=>{
 const f=fixture();f.allow(true);f.tracker.tick(0);f.win.document.visibilityState='hidden';f.tracker.hidden();f.tracker.tick(2000);f.win.document.visibilityState='visible';f.tracker.tick(3000);f.tracker.tick(3999);assert.equal(f.events.length,1);f.allow(false);f.tracker.tick(4000);f.allow(true);f.tracker.tick(5000);assert.equal(f.events.length,1);f.el.dataset.offerExpires='2020-01-01T00:00:00Z';f.tracker.tick(6000);f.tracker.click({target:{closest:()=>({closest:()=>f.el})}});assert.equal(f.events.length,1);
});
