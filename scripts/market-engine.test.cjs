const test=require('node:test'); const assert=require('node:assert/strict');
const M=require('../market-engine.js');
function fixture(){return {cards:[{id:1,releaseDate:'2025-01-01',quotes:{Raw:{currency:'USD'}}},{id:2,releaseDate:'2025-01-01',quotes:{Raw:{currency:'USD'}}}],history:{dates:['2026-01-01','2026-01-02','2026-01-03'],prices:{1:[100,110,120],2:[200,190,180]}}};}
test('equal starting weights give5percent, attribution reconciles and expensivecard doesnotdominate',()=>{const d=fixture(),s=M.cohort(d,'january');assert.equal(s.points.at(-1).value,105);const a=M.attribution(d,s,s.points);assert.ok(Math.abs(a.reduce((n,x)=>n+x.contribution,0)-5)<1e-10);assert.ok(Math.abs(a[0].weight-100*1.2/2.1)<1e-10);});
test('missingcomponent createsgap, neverchangesdenominator andresumesfromoriginalbase',()=>{const d=fixture();d.history.prices[2][1]=null;const s=M.cohort(d,'january');assert.equal(s.points[1].value,null);assert.equal(s.points[2].value,105);assert.equal(s.ids.length,2);});
test('lateentrant doesnotgetJanuarypriceorenterJanuarycohort',()=>{const d=fixture();d.cards.push({id:3,releaseDate:'2026-01-02',quotes:{Raw:{currency:'USD'}}});d.history.prices[3]=[null,1000,1000];assert.equal(M.cohort(d,'january').ids.length,2);const s=M.cohort(d,'current');assert.equal(s.ids.length,3);assert.equal(s.baseDate,'2026-01-02');assert.equal(s.points[0].value,100);});
test('EURreferenceisnotmixedintotheUSDbenchmark',()=>{const d=fixture();d.cards[1].quotes.Raw.currency='EUR';assert.deepEqual(M.cohort(d,'current').ids,[1]);});
test('SVGbreakslineatmissingobservations',()=>{const p=[{date:'a',value:1},{date:'b',value:null},{date:'c',value:3}];assert.equal((M.paths(p,()=>0,x=>x).match(/M/g)||[]).length,2);assert.equal(M.change(null,100),null);});
test('periodcalculationusesUTCanddisplaysactualsupportedwindow',()=>{assert.equal(M.periodStart('2026-11-02','7D'),'2026-10-26');assert.equal(M.periodStart('2026-11-02','YTD'),'2026-01-01');});

test("frozen public cohort keeps a missing latest component instead of silently dropping it",()=>{const d=fixture();d.history.cohorts={current:{members:[1,2]}};d.history.prices[2][2]=null;const s=M.cohort(d,"current");assert.deepEqual(s.ids,[1,2]);assert.equal(s.points.at(-1).value,null);});

test("one observed date has no return or ranked attribution",()=>{const d=fixture(),s=M.cohort(d,"january"),p=[s.points[0]];assert.equal(M.observedChange(p[0],p[0]),null);assert.deepEqual(M.attribution(d,s,p),[]);assert.ok(Math.abs(M.observedChange(s.points[0],s.points[2])-5)<1e-10);});

test("reviewed source anomalies retain their receipt but cannot create returns",()=>{const d=fixture();d.history.exclusions=[{cardId:1,date:"2026-01-01",reportedValue:100,reason:"test hold"}];assert.equal(M.price(d,1,"2026-01-01"),null);assert.equal(d.history.prices[1][0],100);const h=M.historyFor(d,d.cards[0]);assert.equal(h[0].value,null);assert.equal(h[0].reportedValue,100);assert.equal(h[0].excludedReason,"test hold");});
