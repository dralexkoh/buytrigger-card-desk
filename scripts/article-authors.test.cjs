const test=require('node:test');
const assert=require('node:assert/strict');
const authors=require('../article-authors.js');
const article={slug:'new-feature',publishedAt:'2026-11-04',sourcePublishedAt:'2026-11-02',author:{type:'person',id:'alex-koh',name:'Alex Koh',bio:'Collector and creator of BuyTrigger.Cards.'}};
test('new Features have the approved portrait, named author and actual publication date',()=>{
 const byline=authors.byline(article,true);
 assert.match(byline,/By <a[^>]+rel="author">Alex Koh/);
 assert.match(byline,/assets\/family.png/);
 assert.match(byline,/Published 4 November 2026/);
 assert.match(byline,/Source story · 2 November 2026/);
 assert.match(byline,/data-section="author-alex-koh"/);
 assert.match(authors.byline(article),/stories\/new-feature\/#author-alex-koh/);
 assert.match(authors.profile(article),/ABOUT THE AUTHOR/);
});
test('older organization stories acquire no personal authorship',()=>{
 assert.equal(authors.byline({slug:'old-story'}),'');
 assert.equal(authors.profile({slug:'old-story'}),'');
});
test('author display text is escaped',()=>{
 const copy={...article,author:{...article.author,name:'<img onerror="bad">',bio:'A & B <script>'}};
 assert.doesNotMatch(authors.byline(copy),/<img onerror/);
 assert.match(authors.profile(copy),/A &amp; B &lt;script&gt;/);
});
