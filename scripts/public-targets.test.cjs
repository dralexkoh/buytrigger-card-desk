const {test}=require('node:test');
const assert=require('node:assert/strict');
const {validateConfig,validateFeed,upsideCard,watchCard}=require('../public-targets.js');
const datedConfig=require('../public-targets-config.json');
const legacyConfig=require('./fixtures/public-targets/config-main-2026-11-18.json');
const legacyHtml=require('./fixtures/public-targets/legacy-upside-html.json');
const feedEn=require('./fixtures/public-targets/feed-watch-en.json');
const feedJa=require('./fixtures/public-targets/feed-watch-ja.json');
const packets=require('./fixtures/public-targets/db-packet-cases.json');

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
 assert.equal(validateConfig(datedConfig).review.psaUpside.length,39);
 assert.equal(datedConfig.review.psaUpside.filter(c=>c.kind==='watch').length,14);
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

function withClock(frozen,run){
 const real=Date.now;
 Date.now=()=>frozen;
 try{return run();}
 finally{Date.now=real;}
}
function packetFeed(entry){
 const at=Date.parse(entry.checkedAt)+1000;
 return [{schemaVersion:2,generatedAt:new Date(at).toISOString(),refreshAfterSeconds:300,cards:[entry]},at];
}

test('saved main config still validates and every legacy card renders byte-for-byte',()=>{
 withClock(Date.parse('2026-11-20T00:00:00Z'),()=>{
  assert.equal(validateConfig(legacyConfig).review.psaUpside.length,25);
 });
 for(const entry of legacyConfig.review.psaUpside){
  const html=upsideCard(entry,entry.checkedAt??legacyConfig.review.checkedAt);
  assert.equal(html,legacyHtml[entry.id],entry.id);
  assert.doesNotMatch(html,/target-badge-watch|More evidence|US\$|¥/);
 }
});

test('widened config keeps the 25 legacy cards and renders 14 watch cards from saved figures',()=>{
 withClock(Date.parse('2026-11-20T00:00:00Z'),()=>{
  assert.equal(validateConfig(datedConfig).review.psaUpside.length,39);
 });
 const watch=datedConfig.review.psaUpside.filter(entry=>entry.kind==='watch');
 const legacy=datedConfig.review.psaUpside.filter(entry=>entry.kind!=='watch');
 assert.equal(watch.length,14);
 assert.equal(watch.filter(entry=>entry.language==='en').length,7);
 assert.equal(watch.filter(entry=>entry.language==='ja').length,7);
 for(const entry of legacy){
  assert.equal(upsideCard(entry,entry.checkedAt??datedConfig.review.checkedAt),legacyHtml[entry.id],entry.id);
 }
 const english=watchCard(watch.find(entry=>entry.id==='vaporeon-swsh9tg-tg02-en'),'2026-11-18');
 const japanese=watchCard(watch.find(entry=>entry.id==='flareon-s8b-188-ja'),'2026-11-18');
 assert.match(english,/<span class="kicker">WATCH · ENGLISH<\/span>/);
 assert.match(english,/Raw delivered<\/dt><dd>US\$18\.51<\/dd>/);
 assert.match(english,/UK PSA 10 sale<\/dt><dd>US\$615<\/dd>/);
 assert.match(english,/PSA Value grading<\/dt><dd>—<\/dd>/);
 assert.match(english,/Card \+ grading<\/dt><dd>—<\/dd>/);
 assert.match(english,/Profit if PSA 10<\/dt><dd>—<\/dd>/);
 assert.match(japanese,/<span class="kicker">WATCH · JAPANESE<\/span>/);
 assert.match(japanese,/Raw delivered<\/dt><dd>¥1,480<\/dd>/);
 assert.match(japanese,/UK PSA 10 sale<\/dt><dd>—<\/dd>/);
 assert.doesNotMatch(japanese,/US\$/);
 for(const entry of watch){
  const one=watchCard(entry,entry.checkedAt);
  const legacyShape=upsideCard(legacy[0],legacy[0].checkedAt??datedConfig.review.checkedAt);
  assert.equal((one.match(/<div><dt>/g)||[]).length,5);
  assert.equal((one.match(/class="public-target"|class="target-picture"|class="target-copy"|class="target-printing"|class="target-summary"|class="target-date"|class="target-outcomes"|class="target-upside-figures"|class="target-context"/g)||[]).length,(legacyShape.match(/class="public-target"|class="target-picture"|class="target-copy"|class="target-printing"|class="target-summary"|class="target-date"|class="target-outcomes"|class="target-upside-figures"|class="target-context"/g)||[]).length);
  assert.match(one,entry.language==='ja'?/>WATCH · JAPANESE</:/>WATCH · ENGLISH</);
  assert.doesNotMatch(one,/evidence-line|target-evidence|target-badge-watch|Unavailable|More evidence|Gem rate|sold in 30 days/);
  if(entry.language==='ja')assert.doesNotMatch(one,/US\$|£/);
  else assert.doesNotMatch(one,/¥|£/);
 }
});

test('saved watch feeds pass for their own language and expire at the frozen clock',()=>{
 const fresh=Date.parse('2026-11-18T21:36:00Z');
 assert.equal(validateFeed(feedEn,'en',fresh).length,7);
 assert.throws(()=>validateFeed(feedEn,'ja',fresh));
 assert.equal(validateFeed(feedJa,'ja',fresh).length,7);
 assert.throws(()=>validateFeed(feedJa,'en',fresh));
 withClock(Date.parse('2026-11-20T00:00:00Z'),()=>{
  assert.throws(()=>validateFeed(feedEn,'en'));
  assert.throws(()=>validateFeed(feedJa,'ja'));
 });
 const upside={...card,id:'synthetic-beside-watch',checkedAt:'2026-11-18T21:30:00Z',validUntil:'2026-11-19T21:30:00Z',soldOn:'2026-11-18'};
 const mixed={schemaVersion:2,generatedAt:'2026-11-18T21:36:00.000Z',refreshAfterSeconds:300,cards:[upside,feedEn.cards[0]]};
 assert.equal(validateFeed(mixed,'en',fresh).length,2);
 const broken={...feedEn.cards[0],notes:'rejected'};
 assert.throws(()=>validateFeed({...mixed,cards:[feedEn.cards[0],broken]},'en',fresh));
});

test('saved database packet cases match the public validator',()=>{
 for(const [name,packet] of Object.entries(packets.bad)){
  const [data,at]=packetFeed(packet.public);
  if(name==='watch_wrong_gates'){
   assert.equal(validateFeed(data,packet.public.language,at).length,1);
   continue;
  }
  assert.throws(()=>validateFeed(data,packet.public.language,at),name);
 }
 for(const [name,packet] of Object.entries(packets.good)){
  const [data,at]=packetFeed(packet.public);
  assert.equal(validateFeed(data,packet.public.language,at).length,1,name);
 }
 const upside=upsideCard(packets.good.upside_gbp_with_usd_market_block.public,'2026-11-06T12:00:00Z');
 assert.match(upside,/Profit if PSA 10<\/dt><dd>£/);
 assert.doesNotMatch(upside,/More evidence|US\$|evidence-line/);
 const populated=watchCard(packets.good.watch_with_psa_direct_pop.public,'2026-11-18T21:30:00Z');
 assert.match(populated,/Raw delivered<\/dt><dd>US\$18\.51<\/dd>/);
 assert.doesNotMatch(populated,/1,234|Unavailable|Gem rate|evidence-line/);
});
