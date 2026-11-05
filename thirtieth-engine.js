(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.BTThirtiethEngine=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const positive=n=>typeof n==='number'&&Number.isFinite(n)&&n>0;
const day=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s+'T12:00:00Z'))&&new Date(s+'T12:00:00Z').toISOString().slice(0,10)===s;
const keys=(v,allowed)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).every(k=>allowed.includes(k));
function validate(v,now=Date.now()){
 if(!keys(v,['schemaVersion','available','index','sourceSystem','grade','currency','measure','cards','points','sourceDate','source','sources','baseline','generatedAt','expiresAt','sourceVersion'])||v.schemaVersion!==2||typeof v.available!=='boolean')throw Error('Invalid market response');
 if(!v.available)return null;
 if(v.index!=='thirtieth-anniversary'||v.sourceSystem!=='shared-cards-market'||v.grade!=='Raw'||v.currency!=='USD'||v.measure!=='tcgcsv_market'||v.source!=='https://tcgcsv.com/faq')throw Error('Market benchmark changed');
 if(!day(v.sourceDate)||v.sourceDate>new Date(now).toISOString().slice(0,10)||!/^[a-f0-9]{64}$/.test(v.sourceVersion||'')||!Array.isArray(v.cards)||v.cards.length!==191)throw Error('Incomplete set');
 const generated=Date.parse(v.generatedAt),expiry=Date.parse(v.expiresAt);
 if(!Number.isFinite(generated)||!Number.isFinite(expiry)||generated>now+300000||expiry<=now||expiry-generated>600000||generated<now-600000)throw Error('Market response expired');
 const identities=new Set(),ids=new Set();let classic=0;
 for(const c of v.cards){
  if(!keys(c,['key','name','set','number','language','printing','image'])||!/^en-30th-[a-z0-9-]+$/.test(c.key||'')||![c.name,c.number].every(s=>typeof s==='string'&&s.trim())||c.language!=='English'||c.printing!=='Holofoil'||!['ME: 30th Celebration','ME: 30th Celebration Classic Collection'].includes(c.set)||!/^assets\/thirtieth\/[0-9]+\.jpg$/.test(c.image||''))throw Error('Unreviewed printing');
  const identity=[c.set,c.number,c.language,c.printing].join('|');if(identities.has(identity)||ids.has(c.key))throw Error('Duplicate card');identities.add(identity);ids.add(c.key);if(c.set.endsWith('Classic Collection'))classic++;
 }
 if(classic!==30||!keys(v.points,[...ids])||Object.keys(v.points).length!==191)throw Error('Set coverage changed');
 if(!keys(v.baseline,['date','usd'])||v.baseline.date!=='2026-10-08'||v.baseline.usd!==null&&!positive(v.baseline.usd))throw Error('Fixed baseline changed');
 for(const [key,rows]of Object.entries(v.points)){
  if(!ids.has(key)||!Array.isArray(rows)||rows.length>366)throw Error('Invalid history');let previous='';
  for(const p of rows){if(!Array.isArray(p)||p.length!==3||!day(p[0])||p[0]<=previous||p[0]>v.sourceDate||!['ok','no_price','source_anomaly','conflict'].includes(p[2])||(p[2]==='ok')!==positive(p[1])||(p[2]!=='ok'&&p[1]!==null))throw Error('Invalid observation');previous=p[0];}
 }
 if(!Array.isArray(v.sources)||v.sources.length>800||v.sources.some(s=>!keys(s,['day','url'])||!day(s.day)||!/^https:\/\/tcgcsv\.com\/(?:archive\/tcgplayer\/prices-\d{4}-\d{2}-\d{2}\.ppmd\.7z|tcgplayer\/3\/(?:24722|24837)\/prices)$/.test(s.url||'')))throw Error('Invalid provenance');
 return v;
}
function series(v,key){return v?.points?.[key]||[];}
function latest(v,key){return series(v,key).at(-1)||null;}
function basket(v){
 const dates=[...new Set(Object.values(v.points).flatMap(a=>a.map(p=>p[0])))].sort();
 const maps=new Map(v.cards.map(c=>[c.key,new Map(series(v,c.key).map(p=>[p[0],p]))]));
 const rows=dates.map(date=>{let total=0,count=0;for(const c of v.cards){const p=maps.get(c.key).get(date);if(p?.[2]==='ok'&&positive(p[1])){total+=p[1];count++;}}return {date,usd:count===191?total:null,count};});
 const base=v.baseline;return {baseDate:base.date,points:rows.map(p=>({...p,value:positive(base.usd)&&positive(p.usd)&&p.date>=base.date?p.usd/base.usd*100:null}))};
}
function segments(points,value=p=>p.value,date=p=>p.date){let all=[],part=[],last=null;for(const p of points){const time=Date.parse(date(p));if(!positive(value(p))||last!==null&&time-last!==86400000){if(part.length)all.push(part);part=[];}if(positive(value(p)))part.push(p);last=time;}if(part.length)all.push(part);return all;}
return {positive,day,validate,series,latest,basket,segments};
});
