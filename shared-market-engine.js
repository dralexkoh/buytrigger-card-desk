(function(host){'use strict';
const measures={Raw:['daily_nm_guide','archive_nm_period'],'PSA 9':['daily_psa_7d_median','archive_psa_sale_day'],'PSA 10':['daily_psa_7d_median','archive_psa_sale_day']};
const positive=n=>typeof n==='number'&&Number.isFinite(n)&&n>0;
const day=n=>new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/London',year:'numeric',month:'2-digit',day:'2-digit'}).format(n);
const validDay=s=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&!isNaN(Date.parse(s))&&new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;
function allowedKeys(o,keys){return o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).every(k=>keys.includes(k));}
function source(url){try{const u=new URL(url);return u.protocol==='https:'&&!u.username&&!u.password&&['www.pokemonpricetracker.com','infinite-api.tcgplayer.com','valuemycard.com'].includes(u.hostname)&&![...u.searchParams.keys()].some(k=>/key|token|secret|auth/i.test(k));}catch{return false;}}
function validate(v,request,now=Date.now()){
 if(!allowedKeys(v,['schemaVersion','available','status','identity','grade','currency','measure','observations','generatedAt','expiresAt','sourceVersion'])||v.schemaVersion!==1||typeof v.available!=='boolean')throw Error('Market response unavailable');
 if(!v.available){if(Object.keys(v).some(k=>!['schemaVersion','available','status'].includes(k)))throw Error('Unexpected held data');return v;}
 if(!allowedKeys(v.identity,['key','name','set','number','language','printing','edition'])||v.identity.key!==request.key||!Object.values(v.identity).every(x=>typeof x==='string'&&x.length>0&&x.length<=180)||v.grade!==request.grade||v.measure!==request.measure||!measures[v.grade]?.includes(v.measure)||v.currency!=='USD')throw Error('Exact series mismatch');
 if(!/^[a-f0-9]{64}$/.test(v.sourceVersion)||!Number.isFinite(Date.parse(v.generatedAt))||!Number.isFinite(Date.parse(v.expiresAt))||Date.parse(v.generatedAt)>now+60000||Date.parse(v.expiresAt)<=now||Date.parse(v.expiresAt)-Date.parse(v.generatedAt)>300000)throw Error('Market response expired');
 if(!Array.isArray(v.observations)||v.observations.length>366)throw Error('Invalid history');
 let prior='';for(const p of v.observations){
 if(!allowedKeys(p,['day','usd','status','provider','capturedAt','providerUpdatedAt','lastSaleAt','lifetimeSalesCount','dailyVolume7d','transactions','units','methods','sources'])||!validDay(p.day)||p.day>day(now)||p.day<=prior||typeof p.status!=='string'||(p.status==='ok'?!positive(p.usd):p.usd!==null)||p.provider!==(v.grade==='Raw'?'TCGplayer':'PokemonPriceTracker')||!Array.isArray(p.methods)||!p.methods.every(x=>typeof x==='string')||!Array.isArray(p.sources)||!p.sources.every(source))throw Error('Invalid observation');
 prior=p.day;
 }return v;
}
function windowed(v,period,now=Date.now()){
 const start=new Date(day(now)+'T00:00:00Z');if(period!=='All')start.setUTCDate(start.getUTCDate()-(period==='7D'?6:29));
 return v.observations.filter(p=>period==='All'||p.day>=start.toISOString().slice(0,10));
}
function summary(points,today){const good=points.filter(p=>p.status==='ok'&&positive(p.usd));const first=good[0],last=good.at(-1),latest=points.at(-1);return {first,last,current:latest?.day===today&&latest.status==='ok',change:first&&last&&first.day!==last.day?(last.usd/first.usd-1)*100:null};}
function segments(points,measure){if(!measure.startsWith('daily_'))return points.filter(p=>p.status==='ok').map(p=>[p]);const groups=[];for(const p of points){if(p.status!=='ok')continue;const prev=groups.at(-1)?.at(-1);if(!prev||Date.parse(p.day)-Date.parse(prev.day)!==86400000)groups.push([]);groups.at(-1).push(p);}return groups;}
const api={measures,positive,day,validate,windowed,summary,segments};if(typeof module!=='undefined'&&module.exports)module.exports=api;else host.BTSharedMarketData=api;
})(typeof window!=='undefined'?window:globalThis);
