(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.BTBlueChipEngine=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const positive=n=>typeof n==='number'&&Number.isFinite(n)&&n>0;
const date=s=>{if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;const d=new Date(s+'T00:00:00Z');return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===s;};
const https=s=>typeof s==='string'&&/^https:\/\/[^\s<>]+$/.test(s);
const identity=c=>[c?.language,c?.set,c?.number,c?.printing].join('|');
function review(data,asOf=new Date().toISOString().slice(0,10)){
 const issues=[];
 if(data?.status!=='released')return {published:false,cards:[],issues:['PSA 10 ranking not published']};
 const keys=(o,allowed,label)=>{if(Object.keys(o||{}).some(k=>!allowed.includes(k)))issues.push('Unapproved public field in '+label);};
 keys(data,['status','asOf','sourceSystem','sourceRelease','constituentCount','rankingGrade','rankingBasis','weightingMethod','performanceStatus','selectionReview','cards'],'release');
 keys(data.selectionReview,['widerUniverseChecked','unresolvedAtOrAboveCutoff','reviewedAt','candidateCount','source'],'selection review');
 if(data.sourceSystem!=='shared-cards-market')issues.push('Use the existing shared Cards market source');
 if(!date(asOf)||!date(data.asOf)||data.asOf>asOf)issues.push('Invalid release date');
 if(data.rankingGrade!=='PSA 10'||data.rankingBasis!=='comparable-market-value')issues.push('PSA 10 market-value ranking required');
 if(data.constituentCount!==50||!Array.isArray(data.cards)||data.cards.length!==50)issues.push('Exactly 50 constituents required');
 const cards=Array.isArray(data.cards)?data.cards:[];
 if(cards.some(c=>!c||typeof c!=='object'||Array.isArray(c)))return {published:false,cards:[],issues:[...issues,'Invalid constituent record']};
 if(new Set(cards.map(identity)).size!==cards.length)issues.push('Duplicate printing');
 if(data.selectionReview?.widerUniverseChecked!==true||data.selectionReview?.unresolvedAtOrAboveCutoff!==0)issues.push('Wider candidate universe and cutoff not cleared');
 const methods=new Set();
 for(const c of cards){
  const id=identity(c),q=c.quotes?.['PSA 10'];
  keys(c,['name','language','set','number','printing','scope','image','imageExactPrinting','imageIdentity','imageSource','quotes'],'card');
  keys(c.quotes,['Raw','PSA 9','PSA 10'],'quotes');
  for(const quote of Object.values(c.quotes||{}))keys(quote,['price','currency','grader','grade','identity','date','reviewedAt','validUntil','source','evidenceState','publicDisplayApproved','measure','method','sampleCount'],'quote');
  if(c.language!=='English'||![c.set,c.number,c.printing,c.name].every(x=>typeof x==='string'&&x.trim()))issues.push('Incomplete English identity: '+id);
  if(c.scope!=='traded-card')issues.push('Trophy, record-only or unreviewed issue: '+id);
  if(c.imageExactPrinting!==true||c.imageIdentity!==id||!/^assets\/[\w/-]+\.(?:jpg|png|webp)$/.test(c.image||'')||!https(c.imageSource))issues.push('Exact-printing artwork not cleared: '+id);
  if(!q||q.grader!=='PSA'||q.grade!=='10'||q.currency!=='USD'||!positive(q.price))issues.push('Missing exact PSA 10 quote: '+id);
  if(q){
   if(q.identity!==id||q.evidenceState!=='verified'||q.publicDisplayApproved!==true||!https(q.source))issues.push('Quote identity, evidence or display permission not cleared: '+id);
   if(!date(q.date)||q.date>data.asOf||!date(q.reviewedAt)||q.reviewedAt>data.asOf)issues.push('Quote date not cleared: '+id);
   if(!date(q.validUntil)||q.validUntil<asOf)issues.push('Quote review expired: '+id);
   if(!['completed-sales-benchmark','licensed-market-aggregate'].includes(q.measure)||!q.method)issues.push('Comparable market benchmark required: '+id);
   methods.add(q.method);
  }
 }
 if(methods.size!==1)issues.push('Comparable benchmark method required across all 50');
 if(issues.length)return {published:false,cards:[],issues};
 const ordered=[...cards].sort((a,b)=>b.quotes['PSA 10'].price-a.quotes['PSA 10'].price||identity(a).localeCompare(identity(b)));
 return {published:true,cards:ordered.map((c,i)=>({...c,rank:i+1})),issues:[]};
}
return {identity,review};
});
