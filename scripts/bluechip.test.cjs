const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const B=require('../bluechip-engine.js');
const root=path.resolve(__dirname,'..');
// Synthetic evidence exercises publication safety; these are not market observations.
function fixture(){const cards=Array.from({length:50},(_,i)=>{
 const c={name:'Synthetic '+i,language:'English',set:'Test set',number:String(i),printing:'Holofoil',scope:'traded-card',image:'assets/test-'+i+'.jpg',imageExactPrinting:true,imageSource:'https://catalogue.example/card/'+i};
 c.imageIdentity=B.identity(c);c.quotes={'PSA 10':{price:i+1,currency:'USD',grader:'PSA',grade:'10',identity:B.identity(c),date:'2026-11-04',reviewedAt:'2026-11-05',validUntil:'2026-11-12',source:'https://evidence.example/sale/'+i,evidenceState:'verified',publicDisplayApproved:true,measure:'completed-sales-benchmark',method:'same-window-median'}};return c;
});return {status:'released',sourceSystem:'shared-cards-market',asOf:'2026-11-05',rankingGrade:'PSA 10',rankingBasis:'comparable-market-value',constituentCount:50,selectionReview:{widerUniverseChecked:true,unresolvedAtOrAboveCutoff:0},cards};}
const check=d=>B.review(d,'2026-11-05');
test('rank uses PSA 10 alone, in descending order, without mutating source order',()=>{
 const d=fixture();d.cards[0].quotes.Raw={price:9999999};const r=check(d);assert.equal(r.published,true);assert.equal(r.cards[0].name,'Synthetic 49');assert.equal(r.cards[49].name,'Synthetic 0');assert.equal(d.cards[0].rank,undefined);
});
test('one missing PSA 10 price holds the whole replacement; Raw cannot fill it',()=>{const d=fixture();delete d.cards[3].quotes['PSA 10'];d.cards[3].quotes.Raw={price:50000};assert.equal(check(d).published,false);assert.deepEqual(check(d).cards,[]);});
test('PSA 9, another grader and edition mismatch cannot enter PSA 10 rank',()=>{for(const edit of [q=>q.grade='9',q=>q.grader='BGS',q=>q.identity=q.identity.replace('Holofoil','Reverse Holofoil')]){const d=fixture();edit(d.cards[2].quotes['PSA 10']);assert.equal(check(d).published,false);}});
test('a wrong printing, unverified image or duplicate identity holds the release',()=>{for(const edit of [d=>d.cards[0].imageExactPrinting=false,d=>d.cards[0].imageIdentity='different printing',d=>d.cards[1]={...d.cards[0]}]){const d=fixture();edit(d);assert.equal(check(d).published,false);}});
test('the wider cutoff, exact count and scope must pass before publishing fifty',()=>{for(const edit of [d=>d.cards.pop(),d=>d.selectionReview.unresolvedAtOrAboveCutoff=1,d=>d.selectionReview.widerUniverseChecked=false,d=>d.cards[0].scope='trophy']){const d=fixture();edit(d);assert.equal(check(d).published,false);}});
test('undated guides, invalid dates, future prices and expired reviews stay held',()=>{for(const edit of [q=>q.measure='undated-guide',q=>q.date=null,q=>q.date='2026-13-01',q=>q.date='2026-11-06',q=>q.validUntil='2026-11-04']){const d=fixture();edit(d.cards[0].quotes['PSA 10']);assert.equal(check(d).published,false);}});
test('research-only or non-permitted evidence cannot publish; benchmark methods cannot mix',()=>{for(const edit of [q=>q.publicDisplayApproved=false,q=>q.evidenceState='research-only',q=>q.method='historical-record-high']){const d=fixture();edit(d.cards[0].quotes['PSA 10']);assert.equal(check(d).published,false);}});
test('the curated Raw page and earlier archive have separate payloads while PSA 10 stays held',()=>{
 const d=JSON.parse(fs.readFileSync(path.join(root,'bluechip-release.json')));assert.equal(d.rankingGrade,'PSA 10');assert.equal(check(d).published,false);assert.equal(d.cards.length,0);
 const page=fs.readFileSync(path.join(root,'top-50.html'),'utf8');assert.match(page,/id="card-gallery"/);assert.match(page,/src="bluechip-collection-data\.js"/);assert.match(page,/id="era-filter"/);
 const archive=fs.readFileSync(path.join(root,'bluechip-raw-archive.html'),'utf8');assert.match(archive,/src="top50-data\.js/);assert.match(archive,/id="card-gallery"/);
 const script=fs.readFileSync(path.join(root,'top50.js'),'utf8');assert.match(script,/c\.imageExactPrinting===true/);assert.match(script,/Exact-printing picture pending/);
});
test('legacy Raw importer cannot silently overwrite the PSA 10 publication path',()=>{const s=fs.readFileSync(path.join(root,'scripts/import-reviewed-top50.py'),'utf8');assert.match(s,/--legacy-raw-archive/);assert.match(s,/cannot publish a PSA 10/);});
test('private or undeclared fields cannot travel with a released price projection',()=>{for(const edit of [d=>d.owner_id='private',d=>d.cards[0].notes='private',d=>d.cards[0].quotes['PSA 10'].acquired_cost=100]){const d=fixture();edit(d);assert.equal(check(d).published,false);}});
test('malformed constituents fail closed rather than leaving a partially rendered list',()=>{const d=fixture();d.cards[0]=null;assert.equal(check(d).published,false);assert.deepEqual(check(d).cards,[]);});
test('the published collection is 40 classics and 10 modern, ranked on TCGCSV guides',()=>{
 const data=JSON.parse(fs.readFileSync(path.join(root,'bluechip-collection-data.js'),'utf8').split('=').slice(1).join('=').replace(/;\s*$/,''));
 const page=fs.readFileSync(path.join(root,'top-50.html'),'utf8');
 const home=fs.readFileSync(path.join(root,'site.js'),'utf8');
 assert.equal(data.cards.length,50);
 assert.deepEqual(data.cards.slice(0,40).map(c=>c.era),Array(40).fill('classic'));
 assert.deepEqual(data.cards.slice(40).map(c=>c.era),Array(10).fill('modern'));
 assert.ok(data.cards.slice(0,40).every(c=>c.releaseDate<'2011-04-01'));
 assert.ok(data.cards.slice(40).every(c=>c.releaseDate>='2011-04-01'));
 assert.equal(data.cards.some(c=>c.productId===85668),false);
 assert.equal(data.cards.find(c=>c.productId===84186).printing,'Reverse Holofoil');
 assert.deepEqual(data.history.cohorts.history.members,[8,22,42,43,44]);
 const held=new Set(data.history.exclusions.filter(e=>data.history.cohorts.history.members.includes(e.cardId)).map(e=>e.cardId+e.date));
 for(const id of data.history.cohorts.history.members){
  const values=data.history.prices[String(id)];
  assert.equal(values.length,data.history.dates.length);
  assert.ok(data.history.dates.every((day,i)=>typeof values[i]==='number'&&values[i]>0&&!held.has(id+day)));
 }
 assert.equal(/pricecharting/i.test(JSON.stringify(data.cards)),false);
 assert.match(page,/50 CARDS · 40 CLASSICS \+ 10 MODERN/);
 assert.match(page,/<option value="classic">Classics<\/option>/);
 assert.match(page,/<option value="modern">Modern<\/option>/);
 const filters=fs.readFileSync(path.join(root,'top50.js'),'utf8');
 assert.match(filters,/classic\.textContent='Classics · '\+count\('classic'\)/);
 assert.match(filters,/modern\.textContent='Modern · '\+count\('modern'\)/);
 assert.match(home,/50 CARDS · 40 CLASSICS \+ 10 MODERN/);
 assert.match(home,/Top 100 Modern Cards\./);
 assert.equal(/pricecharting/i.test(page),false);
});
