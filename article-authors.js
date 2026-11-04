(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.BT_ARTICLE_AUTHORS=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const person=article=>article?.author?.type==='person'&&article.author.id==='alex-koh';
  const date=value=>new Date(value+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
  const portrait=()=>'<span class="author-portrait"><img src="assets/family.png" alt="Alex Koh’s cartoon portrait, cropped from the approved family artwork."></span>';
  function byline(article,insideArticle=false){
    if(!person(article))return '';
    const a=article.author;
    const url=insideArticle?'#author-alex-koh':'stories/'+encodeURIComponent(article.slug)+'/#author-alex-koh';
    return '<div class="byline person-byline">'+portrait()+'<span><strong>By <a href="'+url+'"'+(insideArticle?' data-section="author-alex-koh"':'')+' rel="author">'+esc(a.name)+'</a> · BuyTrigger.Cards</strong>Published '+esc(date(article.publishedAt))+'<small class="story-date">'+(article.sourcePublishedAt?'Source story · '+esc(date(article.sourcePublishedAt)):'')+(article.eventDate&&article.eventDate!==article.sourcePublishedAt?' · Event '+esc(date(article.eventDate)):'')+'</small></span></div>';
  }
  function profile(article){
    if(!person(article))return '';
    return '<section class="author-profile" id="author-alex-koh" aria-labelledby="author-heading">'+portrait()+'<div><span class="kicker">ABOUT THE AUTHOR</span><h2 id="author-heading">'+esc(article.author.name)+'</h2><p>'+esc(article.author.bio)+'</p><p class="author-art-credit">Cartoon portrait from the original BuyTrigger.Cards family illustration.</p></div></section>';
  }
  return {byline,profile};
});
