(function(root,factory){
 const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.BT_ARTICLE_AUTHORS=api;
})(typeof globalThis==='object'?globalThis:this,function(){
 'use strict';
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const registry={'alex-koh':{id:'alex-koh',name:'Alex Koh',bio:'Collector and creator of BuyTrigger.Cards.'},oscar:{id:'oscar',name:'Oscar',bio:'Part of the father-and-son team behind BuyTrigger.Cards, with a focus on card artwork and collecting.'}};
 const date=v=>new Date(v+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
 function people(article){const a=article?.author;const ids=a?.type==='family'?a.members:a?.type==='person'?[a.id]:[];return [...new Set(ids||[])].filter(id=>registry[id]).map(id=>registry[id]);}
 const label=a=>people(a).map(p=>p.name).join(' & ');
 const portrait=p=>'<span class="author-portrait" data-author="'+p.id+'"><img src="assets/family.png" alt="'+p.name+'’s cartoon portrait from the BuyTrigger.Cards family artwork."></span>';
 function byline(article,insideArticle=false){
  const ps=people(article);if(!ps.length)return '';
  const names=ps.map(p=>'<a href="stories/'+encodeURIComponent(article.slug)+'/#author-'+p.id+'"'+(insideArticle?' data-section="author-'+p.id+'"':'')+' rel="author">'+p.name+'</a>').join(' &amp; ');
  const art=ps.length===1?portrait(ps[0]):'<span class="author-portrait-pair">'+ps.map(portrait).join('')+'</span>';
  return '<div class="byline person-byline">'+art+'<span><strong>By '+names+' · BuyTrigger.Cards</strong>First published '+esc(date(article.publishedAt))+(article.updatedAt&&article.updatedAt!==article.publishedAt?' · Updated '+esc(date(article.updatedAt)):'')+'<small class="story-date">'+(article.sourcePublishedAt?'Story date · '+esc(date(article.sourcePublishedAt)):'Evergreen collecting guide')+(article.eventDate&&article.eventDate!==article.sourcePublishedAt?' · Event '+esc(date(article.eventDate)):'')+'</small></span></div>';
 }
 function profile(article){return people(article).map(p=>'<section class="author-profile" id="author-'+p.id+'" aria-labelledby="author-heading-'+p.id+'">'+portrait(p)+'<div><span class="kicker">ABOUT THE AUTHOR</span><h2 id="author-heading-'+p.id+'">'+p.name+'</h2><p>'+p.bio+'</p><p class="author-art-credit">Portrait from the BuyTrigger.Cards family illustration.</p></div></section>').join('');}
 return {byline,profile,people,label};
});
