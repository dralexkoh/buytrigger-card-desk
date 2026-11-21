const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const source=fs.readFileSync(path.join(__dirname,'../site.js'),'utf8');
const render=source.match(/^function missedStories\(\)\{.+\}$/m)?.[0];
assert.ok(render,'missedStories() must remain a single testable function');
assert.match(source,/\$\{missedStories\(\)\.map\(post\)\.join\(''\)\}/);
assert.doesNotMatch(source,/psa-backlog-november-2026-collector-guide','pokemon-santa-cruz-card-art','psa10-is-not-profit'/);

function select(editorial){
  const cards=vm.runInNewContext(render+'\nmissedStories',{E:editorial})();
  return JSON.parse(JSON.stringify(cards));
}

test('missed-stories rail uses the newest published Features and skips the featured article',()=>{
  const featured='featured-slug';
  const cards=select({
    featuredArticle:featured,
    articles:[
      {slug:'older',status:'published',publishedAt:'2026-11-10',title:'Older'},
      {slug:featured,status:'published',publishedAt:'2026-11-21',title:'Featured'},
      {slug:'newest',status:'published',publishedAt:'2026-11-20',title:'Newest'},
      {slug:'draft',status:'draft',publishedAt:'2026-11-21',title:'Draft'},
      {slug:'middle',status:'published',publishedAt:'2026-11-15',title:'Middle'},
      {slug:'undated',status:'published',title:'No date'},
      {slug:'bad-date',status:'published',publishedAt:'20 November 2026',title:'Bad date'},
    ],
  });
  assert.deepEqual(cards.map(a=>a.slug),['newest','middle','older']);
});

test('current edition rail is the three newest published Features after Bubble Mew',()=>{
  const editorial=JSON.parse(fs.readFileSync(path.join(__dirname,'../editorial.json'),'utf8'));
  assert.equal(editorial.featuredArticle,'next-1000-dollar-pokemon-card-bubble-mew-test');
  const cards=select(editorial);
  assert.equal(cards.length,3);
  assert.deepEqual(cards.map(a=>a.slug),[
    'delta-reign-top-10-chase-raikou-beats-rayquaza',
    'thirtieth-celebration-psa10-prices-halve',
    'mega-charizard-x-ex-sir-one-year-prices',
  ]);
  assert.ok(cards.every(a=>a.slug!==editorial.featuredArticle&&a.status==='published'));
  const stamps=cards.map(a=>a.publishedAt);
  assert.deepEqual(stamps,[...stamps].sort().reverse());
});
