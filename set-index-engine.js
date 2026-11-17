(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.BTSetIndexEngine=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const positive=n=>typeof n==='number'&&Number.isFinite(n)&&n>0;
const day=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s+'T12:00:00Z'))&&new Date(s+'T12:00:00Z').toISOString().slice(0,10)===s;
const keys=(v,allowed)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).every(k=>allowed.includes(k));

function createEngine(spec){
 const imageRe=new RegExp('^'+spec.imagePattern+'$');
 const keyRe=new RegExp('^'+spec.keyPattern+'$');
 const sourceRe=new RegExp('^'+spec.sourcePattern+'$');
 const allowedSets=new Set(spec.allowedSets);
 const allowedPrintings=new Set(spec.allowedPrintings);
 const cardKeys=spec.cardKeys||['key','name','set','number','language','printing','image','rarity'];
 const topKeys=spec.topKeys||['schemaVersion','available','index','sourceSystem','grade','currency','measure','cards','points','sourceDate','source','sources','baseline','generatedAt','expiresAt','sourceVersion','preview','previewNote'];
 const baselineKeys=spec.baselineKeys||['date','usd','proposed'];

 function focus(v){
  const all=[...v.cards];
  const groups={all};
  for(const [id,test] of Object.entries(spec.gallery||{})){
   groups[id]=all.filter(c=>test(c));
  }
  if(groups.all.length!==spec.cardCount)throw Error('Set coverage changed');
  return groups;
 }

 function validate(v,now=Date.now()){
  if(!keys(v,topKeys)||v.schemaVersion!==2||typeof v.available!=='boolean')throw Error('Invalid market response');
  if(!v.available)return null;
  if(v.index!==spec.index||v.sourceSystem!=='shared-cards-market'||v.grade!=='Raw'||v.currency!=='USD'||v.measure!=='tcgcsv_market'||v.source!=='https://tcgcsv.com/faq')throw Error('Market benchmark changed');
  if(!day(v.sourceDate)||v.sourceDate>new Date(now).toISOString().slice(0,10)||!/^[a-f0-9]{64}$/.test(v.sourceVersion||'')||!Array.isArray(v.cards)||v.cards.length!==spec.cardCount)throw Error('Incomplete set');
  const generated=Date.parse(v.generatedAt),expiry=Date.parse(v.expiresAt);
  if(!Number.isFinite(generated)||!Number.isFinite(expiry)||generated>now+300000||expiry<=now||expiry-generated>600000||generated<now-600000)throw Error('Market response expired');
  const identities=new Set(),ids=new Set();
  for(const c of v.cards){
   if(!keys(c,cardKeys)||!keyRe.test(c.key||'')||![c.name,c.number].every(s=>typeof s==='string'&&s.trim())||c.language!=='English'||!allowedPrintings.has(c.printing)||!allowedSets.has(c.set)||!imageRe.test(c.image||''))throw Error('Unreviewed printing');
   const identity=[c.set,c.number,c.language,c.printing].join('|');
   if(identities.has(identity)||ids.has(c.key))throw Error('Duplicate card');
   identities.add(identity);ids.add(c.key);
  }
  if(!keys(v.points,[...ids])||Object.keys(v.points).length!==v.cards.length)throw Error('Set coverage changed');
  focus(v);
  if(!keys(v.baseline,baselineKeys)||v.baseline.date!==spec.baselineDate||v.baseline.usd!==null&&!positive(v.baseline.usd))throw Error('Fixed baseline changed');
  for(const [key,rows] of Object.entries(v.points)){
   if(!ids.has(key)||!Array.isArray(rows)||rows.length>366)throw Error('Invalid history');
   let previous='';
   for(const p of rows){
    if(!Array.isArray(p)||p.length!==3||!day(p[0])||p[0]<=previous||p[0]>v.sourceDate||!['ok','no_price','source_anomaly','conflict'].includes(p[2])||(p[2]==='ok')!==positive(p[1])||(p[2]!=='ok'&&p[1]!==null))throw Error('Invalid observation');
    previous=p[0];
   }
  }
  if(!Array.isArray(v.sources)||v.sources.length>800||v.sources.some(s=>!keys(s,['day','url'])||!day(s.day)||!sourceRe.test(s.url||'')))throw Error('Invalid provenance');
  return v;
 }

 function series(v,key){return v?.points?.[key]||[];}
 function latest(v,key){return series(v,key).at(-1)||null;}
 function rankedRaw(v){
  return v.cards.filter(c=>{const p=latest(v,c.key);return p?.[0]===v.sourceDate&&p[2]==='ok'&&positive(p[1]);})
   .sort((a,b)=>latest(v,b.key)[1]-latest(v,a.key)[1]||a.key.localeCompare(b.key));
 }
 function basket(v,cards=v.cards){
  const byCard=cards.map(c=>new Map(series(v,c.key).map(p=>[p[0],p])));
  const dates=[...new Set(byCard.flatMap(rows=>[...rows.keys()]))].sort();
  const rows=dates.map(date=>{
   let total=0,count=0;
   for(const history of byCard){
    const p=history.get(date);
    if(p?.[2]==='ok'&&positive(p[1])){total+=p[1];count++;}
   }
   return {date,usd:count===cards.length?total:null,count};
  });
  const baseDate=v.baseline.date;
  const fromSeries=rows.find(p=>p.date===baseDate)?.usd;
  const baseUsd=positive(v.baseline.usd)&&cards===v.cards?v.baseline.usd:fromSeries;
  return {baseDate,points:rows.map(p=>({...p,value:positive(baseUsd)&&positive(p.usd)&&p.date>=baseDate?p.usd/baseUsd*100:null}))};
 }
 function segments(points,value=p=>p.value,date=p=>p.date){
  let all=[],part=[],last=null;
  for(const p of points){
   const time=Date.parse(date(p));
   if(!positive(value(p))||last!==null&&time-last!==86400000){if(part.length)all.push(part);part=[];}
   if(positive(value(p)))part.push(p);
   last=time;
  }
  if(part.length)all.push(part);
  return all;
 }
 return {positive,day,validate,series,latest,focus,rankedRaw,basket,segments,spec};
}

function chaseEntries(roster){
 if(!roster||!Array.isArray(roster.cards))return [];
 return roster.cards.filter(card=>Number.isInteger(card.chase_rank)&&card.chase_rank>0).map(card=>({
  chase_rank:card.chase_rank,
  productId:String(card.productId||''),
  name:typeof card.name==='string'?card.name:'',
  number:typeof card.number==='string'?card.number:'',
  image:typeof card.image==='string'?card.image:''
 })).filter(card=>card.productId).sort((a,b)=>a.chase_rank-b.chase_rank||a.productId.localeCompare(b.productId));
}

function chaseHtml(roster,data,latest,helpers){
 const esc=helpers.esc,money=helpers.money,date=helpers.date;
 const byId=new Map((data.cards||[]).map(card=>{
  const match=String(card.image||'').match(/(\d+)\.jpg$/);
  return [match?match[1]:'',card];
 }));
 const tiles=[];
 for(const entry of chaseEntries(roster)){
  const card=byId.get(entry.productId);
  if(!card)continue;
  const point=latest(data,card.key);
  const priced=point&&point[2]==='ok';
  const name=String(card.name||'').replace(/ - .*$/,'');
  const label=name+' '+card.number;
  const eager=tiles.length<4;
  const art=card.image?`<img src="${esc(card.image)}" alt="${esc(label)}" width="200" height="279" decoding="async" loading="${eager?'eager':'lazy'}" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'chase-fallback',textContent:this.alt||'Card image unavailable'}))">`:`<span class="chase-fallback">${esc(name||'Card image unavailable')}</span>`;
  tiles.push(`<button type="button" class="chase-tile" data-set-card="${esc(card.key)}" aria-label="Open ${esc(label)}"><span class="chase-art">${art}</span><strong>${esc(name)}</strong><span class="chase-number">${esc(card.number)}</span><span class="chase-price"><span>Raw guide</span><b>${priced?money(point[1]):'—'}</b></span><small>${point?esc(date(point[0])):'No observations'} · Raw guide</small></button>`);
 }
 if(!tiles.length)return '';
 const note=`TCGplayer market guides via TCGCSV, as of ${esc(date(data.sourceDate))}. Guide prices, not verified sales or offers.`;
 return `<section class="chase-band" aria-labelledby="chase-title"><div class="chase-head"><h2 id="chase-title">Chase cards</h2><p>${note}</p></div><div class="chase-strip">${tiles.join('')}</div></section>`;
}

return {positive,day,keys,createEngine,chaseEntries,chaseHtml};
});
