const test=require('node:test');
const assert=require('node:assert/strict');
const authors=require('../article-authors.js');
const article={slug:'new-feature',publishedAt:'2026-11-04',sourcePublishedAt:'2026-11-02',author:{type:'person',id:'alex-koh',name:'Alex Koh',bio:'Collector and creator of BuyTrigger.Cards.'}};
test('new Features have the approved portrait, named author and actual publication date',()=>{
 const byline=authors.byline(article,true);
 assert.match(byline,/By <a[^>]+rel="author">Alex Koh/);
 assert.match(byline,/assets\/family.png/);
 assert.match(byline,/First published 4 November 2026/);
 assert.match(byline,/Story date · 2 November 2026/);
 assert.match(byline,/data-section="author-alex-koh"/);
 assert.match(authors.byline(article),/stories\/new-feature\/#author-alex-koh/);
 assert.match(authors.profile(article),/ABOUT THE AUTHOR/);
});
test('older organization stories acquire no personal authorship',()=>{
 assert.equal(authors.byline({slug:'old-story'}),'');
 assert.equal(authors.profile({slug:'old-story'}),'');
});
test('registered identities cannot be replaced by injected display text',()=>{
 const copy={...article,author:{...article.author,name:'<img onerror="bad">',bio:'A & B <script>'}};
 assert.doesNotMatch(authors.byline(copy),/<img onerror/);
 assert.doesNotMatch(authors.profile(copy),/<script>|A &amp; B/);
 assert.match(authors.profile(copy),/Alex Koh/);
});
test('Oscar has his own portrait and direct profile link',()=>{
 const oscar={...article,author:{type:'person',id:'oscar',name:'Oscar'}};
 assert.equal(authors.label(oscar),'Oscar');
 assert.match(authors.byline(oscar,true),/data-section="author-oscar"/);
 assert.match(authors.profile(oscar),/id="author-oscar"/);
 assert.doesNotMatch(authors.profile(oscar),/id="author-alex-koh"/);
});
test('family bylines expose two profiles and preserve actual publication/update dates',()=>{
 const family={...article,publishedAt:'2026-11-03',updatedAt:'2026-11-04',author:{type:'family',members:['alex-koh','oscar']}};
 assert.deepEqual(authors.people(family).map(p=>p.id),['alex-koh','oscar']);
 assert.equal(authors.label(family),'Alex Koh & Oscar');
 assert.match(authors.byline(family),/First published 3 November 2026 · Updated 4 November 2026/);
 assert.match(authors.profile(family),/author-heading-oscar/);
 assert.match(authors.profile(family),/author-heading-alex-koh/);
});
