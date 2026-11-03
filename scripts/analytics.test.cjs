const test = require('node:test');
const assert = require('node:assert/strict');
const {randomUUID} = require('node:crypto');
const A = require('../analytics.js');
const config = {...require('../analytics-config.json'),enabled:true,privacyReviewed:true};
const base = 'https://dralexkoh.github.io/buytrigger-card-desk/';
function storage() { const items=new Map(); return {writes:0,getItem:k=>items.get(k)||null,setItem(k,v){this.writes++;items.set(k,v);}}; }
function windowAt(path='index.html') {
  return {location:new URL(path,base),document:{body:{dataset:{}},referrer:'https://www.google.com/search?q=SECRET'},crypto:{randomUUID},navigator:{},innerWidth:390,localStorage:storage(),sessionStorage:storage(),BT_EDITORIAL:{articles:[{slug:'welcome',sources:[{url:'https://www.psacard.com/services'}]}]},MODERN_PREVIEW_DATA:{cards:[{id:1}]},BT_TOP50:{cards:[{id:2}]}};
}
function controller(path) {const win=windowAt(path),out=[];return {win,out,controller:A.createController(win,config,p=>out.push(p))};}
test('inactive or unreviewed config and other products cannot collect',()=>{
  assert.equal(A.validConfig({...config,enabled:false},base),false);
  assert.equal(A.validConfig({...config,privacyReviewed:false},base),false);
  for(const href of ['https://cards.alexkoh.me/','http://127.0.0.1:8000/','https://dralexkoh.github.io/another-repo/','https://dralexkoh.github.io/buytrigger-card-desk-evil/']) assert.equal(A.validConfig(config,href),false);
  assert.equal(A.validConfig({...config,collectorEndpoint:'https://bad.example/functions/v1/cards-traffic-ingest'},base),false);
});
test('no events or storage writes before choice; decline stays silent',()=>{
  const {win,out,controller:c}=controller(); c.routeRendered(); c.track('cta_click',{destination:'modern'});
  assert.equal(out.length,0); assert.equal(win.localStorage.writes,0); assert.equal(win.sessionStorage.writes,0);
  c.choose('denied');c.routeRendered();assert.equal(out.length,0);assert.equal(win.localStorage.writes,1);
});
test('one page view per real hash route; back navigation counts; no query leakage',()=>{
  const {win,out,controller:c}=controller('index.html?email=SECRET&gclid=PRIVATE#home');
  c.choose('granted');c.routeRendered();c.routeRendered();assert.equal(out.length,1);
  win.location=new URL('index.html#journal',base);c.routeRendered();c.routeRendered();
  win.location=new URL('index.html#home',base);c.routeRendered();
  assert.deepEqual(out.map(x=>x.page),['/','/journal','/']);
  assert.ok(!JSON.stringify(out).includes('SECRET'));assert.ok(!JSON.stringify(out).includes('PRIVATE'));
  assert.ok(out.every(x=>x.referrer_channel==='google'));
});
test('index anchors do not create duplicate views; exactly one index_open',()=>{
  const {win,out,controller:c}=controller('tcg-modern-index.html#performance');c.choose('granted');c.routeRendered();
  win.location=new URL('tcg-modern-index.html#cards',base);c.routeRendered();
  assert.deepEqual(out.map(x=>x.event),['page_view','index_open']);
});
test('direct story and hash story normalize to one catalogue-backed page',()=>{
  const {win,out,controller:c}=controller('stories/welcome/');c.choose('granted');c.routeRendered();
  win.location=new URL('index.html#read/welcome',base);c.routeRendered();assert.equal(out.length,1);assert.equal(out[0].page,'/stories/welcome/');
  win.location=new URL('index.html#read/my-email-secret',base);c.routeRendered();assert.equal(out.at(-1).page,'/story-not-found');
  assert.ok(!JSON.stringify(out).includes('my-email-secret'));
});
test('only reviewed campaigns survive; arbitrary query data and click IDs never pass',()=>{
  const {out,controller:c}=controller('index.html?utm_source=x&utm_medium=social&utm_campaign=launch_2026_11&utm_content=welcome&email=SECRET&fbclid=SECRET');
  c.choose('granted');c.routeRendered();assert.equal(out[0].utm_content,'welcome');assert.ok(!JSON.stringify(out).includes('SECRET'));
  const d=controller('index.html?utm_source=my_email&utm_medium=social&utm_campaign=launch_2026_11');d.controller.choose('granted');d.controller.routeRendered();assert.equal(d.out[0].utm_source,undefined);
});
test('event properties are controlled; calculator values and user identity cannot pass',()=>{
  const {out,controller:c}=controller('tcg-modern-index.html');c.choose('granted');c.routeRendered();
  assert.equal(c.track('card_research_open',{index:'modern',card:'secret'}),false);
  assert.equal(c.track('card_research_open',{index:'modern',card:'1',email:'SECRET',price:500}),true);
  assert.deepEqual(out.at(-1).props,{index:'modern',card:'1'});
  assert.equal(c.track('login',{user_id:'SECRET'}),false);assert.equal(c.track('source_outbound',{source:'private.example'}),false);
  assert.equal(c.track('source_outbound',{source:'www.psacard.com',url:'secret'}),true);
  assert.ok(!JSON.stringify(out).includes('SECRET'));
});
test('approved campaign and QA labels follow public journeys, never private or outbound links',()=>{
  const current=base+'index.html?utm_source=x&utm_medium=social&utm_campaign=launch_2026_11&email=SECRET&bt_analytics=qa';
  const data={articles:[{slug:'welcome'}],modern:[],top50:[]};
  const target=new URL(A.taggedDestination('tcg-modern-index.html',current,config,data));
  assert.equal(target.searchParams.get('utm_source'),'x');assert.equal(target.searchParams.get('bt_analytics'),'qa');assert.equal(target.searchParams.get('email'),null);
  assert.equal(A.taggedDestination('https://cards.alexkoh.me/',current,config,data),'https://cards.alexkoh.me/');
  assert.equal(A.taggedDestination('https://www.psacard.com/',current,config,data),'https://www.psacard.com/');
});
test('revoking consent stops new events immediately; blocked storage uses memory',()=>{
  const {win,out,controller:c}=controller();c.choose('granted');c.routeRendered();c.choose('denied');
  win.location=new URL('index.html#journal',base);c.routeRendered();assert.equal(out.length,1);
  const blocked=windowAt();Object.defineProperty(blocked,'localStorage',{get(){throw new Error('blocked')}});
  const cc=A.createController(blocked,config,()=>{});cc.choose('granted');assert.doesNotThrow(()=>cc.routeRendered());
});
test('DNT, global privacy control, local exclusion and QA labels remain explicit',()=>{
  for(const mode of ['dnt','gpc','local','query']){
    const w=windowAt(mode==='query'?'index.html?bt_analytics=off':'index.html');
    if(mode==='dnt')w.navigator.doNotTrack='1';if(mode==='gpc')w.navigator.globalPrivacyControl=true;if(mode==='local')w.localStorage.setItem(A.EXCLUSION_KEY,'1');
    const out=[],c=A.createController(w,config,x=>out.push(x));c.choose('granted');c.routeRendered();assert.equal(out.length,0);
  }
  const {out,controller:c}=controller('index.html?bt_analytics=qa');c.choose('granted');c.routeRendered();assert.equal(out[0].qa,true);
});
test('calculator counts a useful action once per route, never its input values',()=>{
  const {out,controller:c}=controller('index.html#targets');c.choose('granted');c.routeRendered();
  c.track('calculator_used',{amount:300},'calculator_used');c.track('calculator_used',{},'calculator_used');
  assert.deepEqual(out.map(x=>x.event),['page_view','calculator_used']);assert.equal(out[1].props,undefined);
});
test('bootstrap before opt-in only fetches same-origin config, inserts no external script',async()=>{
  const win=windowAt(),calls=[],elements=[];
  const element=tag=>({tag,children:[],listeners:{},append(...children){this.children.push(...children);},setAttribute(){},addEventListener(event,fn){this.listeners[event]=fn;},showModal(){this.open=true;},close(){this.open=false;}});
  const doc=win.document;doc.currentScript={src:base+'analytics.js'};doc.head=element('head');doc.body=Object.assign(element('body'),{dataset:{}});doc.createElement=tag=>{const e=element(tag);elements.push(e);return e;};doc.querySelector=()=>null;doc.addEventListener=()=>{};
  win.addEventListener=()=>{};win.setInterval=()=>{};win.fetch=async(url,opts)=>{calls.push({url,opts});return {ok:true,json:async()=>config};};
  A.boot(win);await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls.length,1);assert.equal(calls[0].url,base+'analytics-config.json');assert.equal(win.localStorage.writes,0);assert.equal(elements.filter(x=>x.tag==='script').length,0);
  const accept=elements.find(x=>x.textContent==='Allow statistics');assert.ok(accept);accept.listeners.click();
  assert.equal(calls.length,2);assert.equal(calls[1].opts.credentials,'omit');assert.equal(calls[1].opts.referrerPolicy,'no-referrer');
  assert.equal(JSON.parse(calls[1].opts.body).event,'page_view');
});
