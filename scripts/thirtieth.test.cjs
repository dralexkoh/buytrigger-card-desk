const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),zlib=require('node:zlib'),path=require('node:path');
const E=require('../thirtieth-engine.js');
const snapshot=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(__dirname,'fixtures/thirtieth-public-replay.json.gz'))));
const now=Date.parse(snapshot.generatedAt)+1000,fixture=()=>structuredClone(snapshot);
test('real shared PostgreSQL projection retains all 191 exact singles and the fixed Raw baseline',()=>{
 const data=E.validate(fixture(),now),b=E.basket(data),last=b.points.at(-1);
 assert.equal(data.cards.length,191);assert.equal(Object.values(data.points).reduce((n,a)=>n+a.length,0),9550);
 assert.equal(b.baseDate,'2026-10-08');assert.ok(Math.abs(b.points.find(p=>p.date===b.baseDate).value-100)<1e-9);
 assert.ok(Math.abs(last.usd-13427.44)<1e-7);assert.ok(Math.abs(last.value-103.6789)<.0001);
 assert.equal(b.points.find(p=>p.date==='2026-10-07').value,null);
});
test('shortening the history window cannot silently reset the index to 100',()=>{
 const data=fixture();for(const key of Object.keys(data.points))data.points[key]=data.points[key].filter(p=>p[0]>='2026-11-01');
 assert.ok(Math.abs(E.basket(E.validate(data,now)).points.at(-1).value-103.6789)<.0001);
});
test('an unavailable member leaves the full fixed basket unpriced and cannot be dropped',()=>{
 const data=fixture();data.points[data.cards[0].key].at(-1)[1]=null;data.points[data.cards[0].key].at(-1)[2]='no_price';
 const last=E.basket(E.validate(data,now)).points.at(-1);assert.equal(last.count,190);assert.equal(last.usd,null);assert.equal(last.value,null);
 data.cards.pop();assert.throws(()=>E.validate(data,now));
});
test('exact grades, dates, source privacy and expiry fail closed',()=>{
 for(const mutate of[d=>d.grade='PSA 10',d=>d.cards[0].language='Japanese',d=>d.cards[0].printing='Reverse Holofoil',d=>d.owner_id='private',d=>d.cards[0].notes='private',d=>d.sources[0].url+='?token=private',d=>d.expiresAt=new Date(now-1).toISOString(),d=>d.points[d.cards[0].key].at(-1)[0]='2099-01-01',d=>d.baseline.date='2026-11-01']){const data=fixture();mutate(data);assert.throws(()=>E.validate(data,now));}
});
test('the known Mew Blue $5 anomaly is null and charts stop at missing dates',()=>{
 const data=E.validate(fixture(),now),c=data.cards.find(c=>c.number==='B/RGB');assert.equal(E.series(data,c.key).find(p=>p[0]==='2026-10-07')[1],null);
 const points=E.basket(data).points.filter(p=>p.date!=='2026-11-03');assert.equal(E.segments(points).length,2);
});
