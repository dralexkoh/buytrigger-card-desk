const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const M=require('../market-engine.js');
const zlib=require('node:zlib');
const root=path.resolve(__dirname,'..');
const text=fs.readFileSync(path.join(root,'top50-data.js'),'utf8');
const data=JSON.parse(text.slice(text.indexOf('=')+1).trim().replace(/;$/,''));

const frozenFiles=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(root,'scripts/fixtures/public-baseline-2026-11-02.json.gz')))).files;
const parseJS=text=>JSON.parse(text.slice(text.indexOf('=')+1).trim().replace(/;$/,''));
const baseline=parseJS(frozenFiles['top50-data.js']);

test('Top 50 preserves 50 exact printings and frozen selection while guides update',()=>{
 assert.equal(data.cards.length,50);
 assert.equal(new Set(data.cards.map(c=>`${c.productId}|${c.printing}`)).size,50);
 data.cards.forEach((c,i)=>{
  assert.equal(c.rank,i+1);assert.equal(c.id,i+1);
  assert.equal(c.language,'English');assert.ok(c.number&&c.set&&c.printing);
  assert.deepEqual(Object.keys(c.quotes),['Raw']);
  assert.equal(c.quotes.Raw.currency,'USD');
  assert.equal(c.productId,baseline.cards[i].productId);assert.equal(c.printing,baseline.cards[i].printing);
  assert.ok(c.quotes.Raw.date<=data.release.sourceDate);
  assert.ok(M.positive(c.quotes.Raw.price));
  if(i)assert.ok(baseline.cards[i-1].quotes.Raw.price>=baseline.cards[i].quotes.Raw.price);
  if(!c.rawRefresh||c.rawRefresh.status==='current'){
   assert.equal(c.quotes.Raw.date,data.release.sourceDate);
   assert.equal(M.price(data,c.id,data.release.sourceDate),c.quotes.Raw.price);
  }else{assert.equal(M.price(data,c.id,data.release.sourceDate),null);assert.equal(c.quotes.Raw.date,c.rawRefresh.lastValidDate);}
 });
});

test('Historical guides preserve missing prices, exact dates and pre-release limits',()=>{
 const dates=data.history.dates;
 assert.equal(dates[0],'2024-02-08');assert.equal(dates.at(-1),data.release.sourceDate);
 assert.deepEqual(dates,[...new Set(dates)].sort());
 assert.equal(dates.filter(d=>d.startsWith('2024-01')).length,0);
 for(const c of data.cards){
  const values=data.history.prices[c.id];assert.equal(values.length,dates.length);
  values.forEach((v,i)=>{
   assert.ok(v===null||M.positive(v));
   if(c.releaseDate&&dates[i]<c.releaseDate)assert.equal(v,null);
  });
 }
 for(const date of data.release.incompleteArchiveDates){assert.ok(dates.includes(date));for(const c of data.cards)assert.equal(M.price(data,c.id,date),null);}
});

test('Fixed historical basket never silently drops an unpriced component',()=>{
 const s=M.cohort(data,'history');
 assert.ok(s.ids.length>0&&s.ids.length<50);
 assert.equal(s.points[0].value,100);
 assert.equal(s.baseDate,data.history.dates[0]);
 for(const p of s.points){if(p.count===s.ids.length)assert.ok(M.positive(p.value));else assert.equal(p.value,null);}
 const current=M.cohort(data,'current');assert.equal(current.ids.length,50);
 for(const p of current.points){if(p.count!==50)assert.equal(p.value,null);}
 const observed=s.points.filter(p=>M.positive(p.value));
 const attribution=M.attribution(data,s,observed),first=observed[0],last=observed.at(-1);
 assert.ok(Math.abs(attribution.reduce((n,r)=>n+r.contribution,0)-M.change(first.value,last.value))<1e-8);
});

test('Artwork and source notes exist for all 50; auction lots stay outside prices',()=>{
 for(const c of data.cards){
  assert.ok(fs.existsSync(path.join(root,c.image)));assert.ok(fs.existsSync(path.join(root,c.imageLarge)));
  assert.ok(c.imageNote&&c.imageSource&&c.imageProvider);
  assert.equal(typeof c.imageExactPrinting,'boolean');
  assert.match(c.quotes.Raw.source,/^https:\/\//);
 }
 assert.equal(data.auctions.length,3);
 for(const a of data.auctions){assert.equal(a.priceBasis.includes('premium'),true);assert.equal(a.hammerPrice,null);assert.match(a.originalAuctionUrl,/https:\/\/comics\.ha\.com\//);}
});


test('Reviewed holds retain reported values but cannot become chart prices',()=>{
 assert.ok(data.history.exclusions.length>=baseline.history.exclusions.length);
 for(const e of baseline.history.exclusions)assert.deepEqual(data.history.exclusions.find(x=>x.cardId===e.cardId&&x.date===e.date),e);
 let usable=0;for(const c of data.cards)for(const date of data.history.dates)if(M.positive(M.price(data,c.id,date)))usable++;
 assert.equal(data.release.historyObservations,usable);
 for(const e of data.history.exclusions){
  assert.equal(data.history.prices[e.cardId][data.history.dates.indexOf(e.date)],e.reportedValue);
  assert.equal(M.price(data,e.cardId,e.date),null);
 }
 assert.equal(M.cohort(data,'history').ids.length,14);
 assert.equal(M.cohort(data,'current').baseDate,'2026-11-02');
 for(const c of data.cards){baseline.history.dates.forEach((date,i)=>assert.equal(data.history.prices[c.id][data.history.dates.indexOf(date)],baseline.history.prices[c.id][i]));}
 assert.deepEqual(data.history.cohorts,baseline.history.cohorts);
});

test('Shared Modern cards retain the same current exact-printing Raw guide',()=>{
 const t=fs.readFileSync(path.join(root,'catalogue.js'),'utf8');
 const modern=JSON.parse(t.slice(t.indexOf('=')+1).trim().replace(/;$/,''));
 let compared=0;
 for(const c of data.cards){
  const other=modern.cards.find(m=>m.productId===c.productId&&m.printing===c.printing&&m.quotes.Raw?.currency==='USD');
  if(other){assert.equal(c.quotes.Raw.price,other.quotes.Raw.price);assert.equal(c.quotes.Raw.date,other.quotes.Raw.date);compared++;}
 }
 assert.ok(compared>=10);
});
