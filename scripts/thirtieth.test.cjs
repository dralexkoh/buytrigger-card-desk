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
test('the public focus has 13 chases, every numbered Pikachu and the three RGB Mews',()=>{
 const data=E.validate(fixture(),now),{chases,pikachu,rgb}=E.focus(data);
 assert.deepEqual(chases.map(c=>c.number),['4/102','149/147','203/193','152/128','154/128','94/102','150/128','158/128','151/128','149/128','153/128','155/128','157/128']);
 assert.deepEqual(pikachu.map(c=>c.number).sort(),Array.from({length:30},(_,i)=>String(i+23).padStart(3,'0')+'/128'));
 assert.deepEqual(rgb.map(c=>c.number),['R/RGB','G/RGB','B/RGB']);
 const bad=fixture();
 const first=bad.cards.find(c=>c.number==='023/128');
 first.image=bad.cards.find(c=>c.number==='024/128').image;
 assert.throws(()=>E.validate(bad,now),/focus printings changed/);
});
test('focused Raw charts share the fixed baseline and keep gaps within their own basket',()=>{
 const data=fixture(),{chases,pikachu,rgb}=E.focus(data);
 for(const cards of [chases,pikachu,rgb]){
  const history=E.basket(data,cards);
  assert.equal(history.baseDate,'2026-10-08');
  assert.equal(history.points.find(p=>p.date===history.baseDate).value,100);
  assert.equal(history.points.at(-1).count,cards.length);
 }
 assert.equal(E.basket(data,chases).points.at(-1).usd.toFixed(2),'804.83');
 assert.equal(E.basket(data,pikachu).points.at(-1).usd.toFixed(2),'21.69');
 const point=data.points[rgb[0].key].at(-1);
 point[1]=null;point[2]='no_price';
 assert.equal(E.basket(data,rgb).points.at(-1).value,null);
 assert.equal(E.basket(data,chases).points.at(-1).usd.toFixed(2),'804.83');
});
