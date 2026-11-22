const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const source=fs.readFileSync(path.join(__dirname,'../site.js'),'utf8');

function extract(name){
  const match=source.match(new RegExp(String.raw`^function ${name}\([^)]*\)\{.*\}$`,'m'));
  assert.ok(match, `${name}() must remain a single testable function`);
  return match[0];
}

const helpers=[
  extract('deskFeatureSlug'),
  extract('publishStamp'),
  extract('weekStart'),
  extract('weekLabel'),
  extract('moreFeatures'),
  extract('archiveWeeks'),
  extract('inWeek'),
].join('\n');

assert.match(source,/\$\{moreFeatures\(\)\.map\(post\)\.join\(''\)\}/);
assert.match(source,/\$\{archiveWeeks\(\)\.map/);
assert.doesNotMatch(source,/\['how-the-index-works','psa10-is-not-profit','japanese-card-research'\]/);
assert.doesNotMatch(source,/\['2026-10-13','13–19 Oct'\]/);

function run(editorial){
  const context={E:editorial};
  vm.runInNewContext(helpers+'\nthis.api={moreFeatures,archiveWeeks,inWeek,weekLabel,weekStart,publishStamp,deskFeatureSlug};',context);
  const api=JSON.parse(JSON.stringify(context.api,(_,value)=>typeof value==='function'?undefined:value));
  // functions don't survive JSON; bind them from the context
  return context.api;
}

function select(editorial){
  const api=run(editorial);
  return {
    more:JSON.parse(JSON.stringify(api.moreFeatures())),
    weeks:JSON.parse(JSON.stringify(api.archiveWeeks())),
    inWeek:(article,week)=>api.inWeek(article,week),
    weekLabel:start=>api.weekLabel(start),
    desk:api.deskFeatureSlug(),
  };
}

test('More features rail uses newest published Features and skips the homepage and desk slots',()=>{
  const featured='featured-slug';
  const desk='psa-value-returns';
  const api=select({
    featuredArticle:featured,
    articles:[
      {slug:'older',status:'published',publishedAt:'2026-11-10',title:'Older'},
      {slug:featured,status:'published',publishedAt:'2026-11-21',title:'Homepage feature'},
      {slug:desk,status:'published',publishedAt:'2026-11-22',title:'Desk slot'},
      {slug:'newest',status:'published',publishedAt:'2026-11-20',title:'Newest'},
      {slug:'draft',status:'draft',publishedAt:'2026-11-21',title:'Draft'},
      {slug:'middle',status:'published',publishedAt:'2026-11-15',title:'Middle'},
      {slug:'undated',status:'published',title:'No date'},
      {slug:'bad-date',status:'published',publishedAt:'20 November 2026',title:'Bad date'},
    ],
  });
  assert.equal(api.desk,desk);
  assert.deepEqual(api.more.map(a=>a.slug),['newest','middle','older']);
});

test('archive weeks are Monday–Sunday publish-date buckets and grow when a new week appears',()=>{
  const editorial={
    featuredArticle:'featured-slug',
    articles:[
      {slug:'a',status:'published',publishedAt:'2026-11-03',title:'A'},
      {slug:'b',status:'published',publishedAt:'2026-11-08',title:'B'},
      {slug:'c',status:'published',publishedAt:'2026-11-09',title:'C'},
      {slug:'draft',status:'draft',publishedAt:'2026-11-30',title:'Draft stays out'},
    ],
  };
  const before=select(editorial);
  assert.deepEqual(before.weeks,[
    ['all','All dates'],
    ['2026-11-02','2–8 Nov'],
    ['2026-11-09','9–15 Nov'],
  ]);
  assert.equal(before.inWeek(editorial.articles[0],'2026-11-02'),true);
  assert.equal(before.inWeek(editorial.articles[1],'2026-11-02'),true);
  assert.equal(before.inWeek(editorial.articles[2],'2026-11-02'),false);
  assert.equal(before.inWeek(editorial.articles[2],'2026-11-09'),true);
  assert.equal(before.inWeek(editorial.articles[0],'all'),true);

  editorial.articles.push({slug:'later',status:'published',publishedAt:'2026-11-23',title:'New week'});
  const after=select(editorial);
  assert.deepEqual(after.weeks,[
    ['all','All dates'],
    ['2026-11-02','2–8 Nov'],
    ['2026-11-09','9–15 Nov'],
    ['2026-11-23','23–29 Nov'],
  ]);
  assert.equal(after.weekLabel('2026-10-27'),'27 Oct–2 Nov');
  assert.equal(after.weekLabel('2026-12-29'),'29 Dec 2026–4 Jan 2027');
});

test('current edition more-features rail and week filters follow live editorial data',()=>{
  const editorial=JSON.parse(fs.readFileSync(path.join(__dirname,'../editorial.json'),'utf8'));
  assert.equal(editorial.featuredArticle,'next-1000-dollar-pokemon-card-bubble-mew-test');
  const api=select(editorial);
  assert.equal(api.desk,'psa-value-returns');
  assert.deepEqual(api.more.map(a=>a.slug),[
    'modern-card-prices-is-it-just-bad-copies',
    'delta-reign-top-10-chase-raikou-beats-rayquaza',
    'thirtieth-celebration-psa10-prices-halve',
  ]);
  assert.ok(api.more.every(a=>a.slug!==editorial.featuredArticle&&a.slug!==api.desk&&a.status==='published'));
  assert.deepEqual(api.weeks,[
    ['all','All dates'],
    ['2026-11-02','2–8 Nov'],
    ['2026-11-09','9–15 Nov'],
    ['2026-11-16','16–22 Nov'],
  ]);
});
