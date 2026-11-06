const {test}=require('node:test');
const assert=require('node:assert/strict');
const {validateConfig,validateFeed,upsideCard}=require('../public-targets.js');
const datedConfig=require('../public-targets-config.json');

const now=Date.parse('2026-11-06T12:00:00Z');
const card={
 id:'synthetic-card',name:'Synthetic <script>card</script>',set:'Test set',number:'001',printing:'Holo',
 language:'en',image:'assets/public-targets/test.webp',gradingTier:'Value',
 rawMinor:2000,gradingMinor:4000,psa10Minor:6500,returnPostageFromMinor:500,
 checkedAt:'2026-11-06T11:00:00Z',validUntil:'2026-11-07T11:00:00Z',soldOn:'2026-11-05',
 rawUrl:'https://www.ebay.co.uk/itm/123456789012',saleUrl:'https://www.ebay.co.uk/itm/123456789013?nordt=true',
 gradingUrl:'https://thesubcenter.co.uk/product/psa-value/',imageSourceUrl:'https://assets.pokemon.com/test.webp'
};
const feed=(cards=[card])=>({schemaVersion:2,generatedAt:'2026-11-06T12:00:00.000001+00:00',refreshAfterSeconds:300,cards});

test('only the approved Cards endpoint may be configured',()=>{
 const endpoint='https://ukblxmvsqihnnyysvxes.supabase.co/functions/v1/public-card-targets';
 assert.equal(validateConfig({schemaVersion:1,enabled:true,endpoint}).endpoint,endpoint);
 assert.equal(validateConfig(datedConfig).review.psaUpside.length,25);
 for(const value of [endpoint+'?token=secret',endpoint+'#secret',endpoint.replace('ukblxmvsqihnnyysvxes','another-project'),endpoint.replace('https:','http:'),endpoint.replace('https://','https://user:secret@')]){
  assert.throws(()=>validateConfig({schemaVersion:1,enabled:true,endpoint:value}));
 }
 assert.throws(()=>validateConfig({schemaVersion:1,enabled:false,endpoint}));
});

test('both languages show the conditional PSA 10 margin and the break-even postage warning',()=>{
 assert.deepEqual(validateFeed(feed(),'en',now),[card]);
 const japanese={...card,language:'ja'};
 assert.deepEqual(validateFeed(feed([japanese]),'ja',now),[japanese]);
 const html=upsideCard(card,card.checkedAt);
 assert.match(html,/Profit if PSA 10<\/dt><dd>£5<\/dd>/);
 assert.match(html,/£5 wipes out this margin/);
 assert.match(html,/Entry and grading checked 6 Nov 2026/);
 assert.match(html,/PSA 10 sale on 5 Nov 2026/);
 assert.match(html,/Profit excludes grading postage and selling costs/);
 assert.match(html,/&lt;script&gt;/);
 assert.doesNotMatch(html,/<script>|PSA 9|CGC/);
 assert.throws(()=>validateFeed(feed([{...card,psa10Minor:6000}]),'en',now));
});

test('rejects the old feed, private fields, unverified URLs, invalid prices and dates',()=>{
 assert.throws(()=>validateFeed({...feed(),schemaVersion:1},'en',now));
 for(const [key,value] of [
  ['notes','PRIVATE'],['owner_id','SECRET'],['psa9Minor',1000],['rawMinor',0],['psa10Minor',true],
  ['image','assets/public-targets/../secret.jpg'],['imageSourceUrl','https://private.example/photo.jpg'],
  ['saleUrl',card.saleUrl+'&token=private'],['rawUrl',card.saleUrl.split('?')[0]],['gradingTier','Standard'],
  ['checkedAt','2026-11-06T13:00:00Z'],['checkedAt','2026-02-30T11:00:00Z'],['soldOn','2026-11-07'],
  ['validUntil','2026-11-06T12:00:00Z'],['validUntil','2026-11-13T11:00:01Z'],['language','ja']
 ]){
  assert.throws(()=>validateFeed(feed([{...card,[key]:value}]),'en',now),key);
 }
});

test('empty feed is valid and stale feeds or repeated exact printings are rejected',()=>{
 assert.deepEqual(validateFeed(feed([]),'en',now),[]);
 assert.throws(()=>validateFeed(feed(),'en',now+300000));
 assert.throws(()=>validateFeed(feed([card,card]),'en',now));
 assert.throws(()=>validateFeed(feed([card,{...card,id:'other-seller',printing:'holo'}]),'en',now));
});
