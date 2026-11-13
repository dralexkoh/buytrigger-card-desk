const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),{randomUUID}=require('node:crypto');
const A=require('../analytics.js'),config=require('../analytics-config.json'),e=require('../editorial.json');
const manifest=JSON.parse(require('node:child_process').execFileSync('python3',['scripts/build_tracking_catalogue.py'],{encoding:'utf8'})),data={articles:e.articles,wire:e.wire,retailerLinks:manifest.retailerLinks,modern:[],top50:[],commerce:require('../commerce.json')};
test('every built Feature and individual Newsroom brief resolves to a unique approved route',()=>{
 const seen=new Set();for(const a of e.articles){const route=A.resolveRoute('https://buytrigger.cards/stories/'+a.slug+'/',config,data);assert.equal(route.article,a.slug);assert.ok(!seen.has(route.url));seen.add(route.url);assert.equal(A.resolveRoute('https://buytrigger.cards/index.html#read/'+a.slug,config,data).url,route.url);}
 for(const n of e.wire)assert.equal(A.resolveRoute('https://buytrigger.cards/#desk/'+n.id,config,data).url,'/news/'+n.id+'/');
 assert.equal(A.resolveRoute('https://buytrigger.cards/stories/welcome/#author-alex-koh',config,data,'read/welcome').article,'welcome');
});
test('all direct tools and index pages receive canonical identities; private routes stay excluded',()=>{
 for(const[file,route]of[['30th-anniversary-index.html','/thirtieth'],['market.html','/market'],['grading-calculator.html','/calculator'],['undervalued.html','/targets'],['undervalued-japanese.html','/japan']])assert.equal(A.resolveRoute('https://buytrigger.cards/'+file,config,data).url,route);
 assert.equal(A.resolveRoute('https://cards.alexkoh.me/',config,data),null);
});
test('Amazon product and review links match the exact published host/path/article and never send queries',()=>{
 const article='best-binder-for-pokemon-cards';for(const asin of ['B0BNW3DFYR','B071V91LGC','B08G8JKMJ1'])assert.ok(data.retailerLinks.some(l=>l.kind==='product'&&l.asin===asin));
 for(const l of data.retailerLinks){assert.ok(A.retailerLink('https://'+l.host+l.path+'?tag=example&email=PRIVATE',data,article));const clean=A.sanitizeEvent('retailer_click',{retailer:'amazon',link_id:l.id,secret:'PRIVATE'},{article},data,new Set());assert.deepEqual(Object.keys(clean.data).sort(),['link_id','retailer']);assert.ok(!JSON.stringify(clean).includes('PRIVATE'));}
 for(const href of ['https://www.amazon.co.uk.evil.com/dp/B0BNW3DFYR','https://evil@www.amazon.co.uk/dp/B0BNW3DFYR','http://www.amazon.co.uk/dp/B0BNW3DFYR','https://www.amazon.co.uk/dp/B000000000'])assert.equal(A.retailerLink(href,data,article),null);
 assert.equal(A.retailerLink('https://www.amazon.co.uk/dp/B0BNW3DFYR',data,'welcome'),null);
});
test('Vault X measurement is a narrowly identified house promotion; consent, QA and opt-out remain enforced',()=>{
 const memory=new Map(),out=[],win={location:new URL('https://buytrigger.cards/?bt_analytics=qa'),document:{body:{dataset:{}},referrer:''},crypto:{randomUUID},navigator:{},innerWidth:390,localStorage:{getItem:k=>memory.get(k),setItem:(k,v)=>memory.set(k,v)},BT_EDITORIAL:e,BT_TRAFFIC_CATALOGUE:manifest,BT_COMMERCE:data.commerce};
 const c=A.createController(win,config,p=>out.push(p)),props={campaign_id:'vaultx-house-review',slot_id:'HOME-01',creative_id:'vaultx-binder-v1',destination_id:'vaultx-review'};
 c.routeRendered();assert.equal(c.track('ad_click',props),false);c.choose('granted');c.routeRendered();assert.equal(c.track('ad_click',props),true);assert.ok(out.every(r=>r.qa));assert.equal(c.track('ad_click',{...props,destination_id:'fake'}),false);c.choose('denied');assert.equal(c.track('ad_click',props),false);
});

test('published affiliate CTAs preserve exact destinations and sponsorship on hydrated article links',()=>{
 const vm=require('node:vm'),src=fs.readFileSync('site.js','utf8');
 const readFunction=src.split('\n').find(line=>line.startsWith('function read('));
 const context={article:slug=>e.articles.find(a=>a.slug===slug),esc:value=>String(value??'').replace(/&/g,'&amp;').replace(/"/g,'&quot;'),href:slug=>'stories/'+slug+'/',byline:()=>'',art:()=>'',routeLink:value=>value,heading:()=>'',post:()=>'',window:{BT_ARTICLE_AUTHORS:{profile:()=>''}}};
 vm.createContext(context);vm.runInContext(readFunction,context);
 const rendered=vm.runInContext("read('best-binder-for-pokemon-cards')",context);
 const links=[...rendered.matchAll(/<a\b[^>]*href="([^"]+)"[^>]*>/g)].filter(m=>m[1].startsWith('https://www.amazon.co.uk/'));
 assert.equal(links.length,6);
 for(const m of links){assert.equal(new URL(m[1]).searchParams.get('tag'),'buytrigger-21');assert.match(m[0],/rel="sponsored noopener noreferrer"/);}
 const ordinary=vm.runInContext("read('welcome')",context);
 assert.ok(!ordinary.includes('rel="sponsored'));
 assert.equal(e.articles.filter(a=>a.cta?.sponsored===true).length,1);
});
