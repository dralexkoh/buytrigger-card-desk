const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createEngine} = require('../set-index-engine.js');

const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'delta-reign-market-snapshot.json'), 'utf8'));
const engine = createEngine({
  index: 'delta-reign',
  cardCount: 141,
  baselineDate: '2026-11-06',
  proposedBaseline: true,
  imagePattern: 'assets/delta-reign/[0-9]+\\.jpg',
  keyPattern: 'en-delta-reign-[0-9]+-(holofoil|normal)',
  sourcePattern: 'https://tcgcsv\\.com/(?:archive/tcgplayer/prices-\\d{4}-\\d{2}-\\d{2}\\.ppmd\\.7z|tcgplayer/3/24831/prices)',
  allowedSets: ['ME06: Delta Reign'],
  allowedPrintings: ['Holofoil', 'Normal'],
  gallery: { secret: (card) => parseInt(card.number, 10) > 103 },
});

function stamped() {
  const generated = new Date();
  return {
    ...snapshot,
    generatedAt: generated.toISOString(),
    expiresAt: new Date(generated.getTime() + 9 * 60 * 1000).toISOString(),
  };
}

test('Delta Reign snapshot validates and ranks the three most expensive cards first', () => {
  const data = engine.validate(stamped());
  assert.equal(data.cards.length, 141);
  assert.equal(engine.focus(data).all.length, 141);
  assert.equal(engine.focus(data).secret.length, 38);
  const ranked = engine.rankedRaw(data);
  assert.deepEqual(ranked.slice(0, 3).map((card) => card.name), [
    'Mega Rayquaza ex - 138/103',
    'Mega Rayquaza ex - 141/103',
    'Raikou ex',
  ]);
  const history = engine.basket(data, data.cards);
  assert.equal(history.baseDate, '2026-11-06');
  const latest = history.points.find((point) => point.date === data.sourceDate);
  assert.ok(latest.usd);
  assert.equal(Number(latest.usd.toFixed(2)), 962.23);
  assert.ok(latest.value < 100);
});

test('chase cards follow roster chase_rank, with 1 at the top', () => {
  const {chaseEntries, sortCards, chaseRankMap} = require('../set-index-engine.js');
  const expected = {
    'delta-reign': ['728061', '728062', '726574', '726567', '726576', '728060', '727592', '726565', '726575', '726563'],
    'sv-151': ['517045', '517046', '517044', '502556', '502549', '517048', '517018', '517047', '516997', '513721'],
    'prismatic-evolutions': ['610516', '610511', '610499', '610510', '610505', '610504', '610501', '610508', '610522', '610517'],
    'paldean-fates': ['534919', '535090', '535085', '534522', '534683', '535193', '535527', '534483', '535191', '535215'],
    'crown-zenith': ['478100', '477057', '478101', '478099', '478097', '477060', '478027', '478077', '477061', '478067'],
    'fusion-strike': ['253266', '253177', '253265', '253147', '253176', '253138', '253146', '253371', '253155', '253171'],
  };
  const keeperSource = new Set(['delta-reign', 'sv-151', 'prismatic-evolutions']);
  for (const [slug, ids] of Object.entries(expected)) {
    const roster = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data/market-rosters', slug + '.json'), 'utf8'));
    if (keeperSource.has(slug)) assert.equal(roster.chase_source, 'keeper-2026-11-17');
    const entries = chaseEntries(roster);
    assert.deepEqual(entries.map((card) => card.productId), ids);
    assert.deepEqual(entries.map((card) => card.chase_rank), ids.map((_, index) => index + 1));
  }
  const swapped = {cards: [{productId: '2', chase_rank: 2, name: 'B', number: '2'}, {productId: '1', chase_rank: 1, name: 'A', number: '1'}, {productId: '9', name: 'Skip'}]};
  assert.deepEqual(chaseEntries(swapped).map((card) => card.productId), ['1', '2']);
  const cards = [
    {key: 'c', name: 'C', number: '003/100', image: 'assets/example/30.jpg'},
    {key: 'a', name: 'A', number: '010/100', image: 'assets/example/10.jpg'},
    {key: 'b', name: 'B', number: '002/100', image: 'assets/example/20.jpg'},
  ];
  const ranks = chaseRankMap({cards: [{productId: '20', chase_rank: 1}, {productId: '10', chase_rank: 2}]});
  const latest = (key) => ({a: [0, 1, 'ok'], b: [0, 9, 'ok'], c: [0, 4, 'ok']}[key]);
  assert.deepEqual(sortCards(cards, 'default', 'all', latest, ranks).map((card) => card.key), ['b', 'a', 'c']);
  assert.deepEqual(sortCards(cards, 'number', 'all', latest, ranks).map((card) => card.key), ['b', 'c', 'a']);
  assert.deepEqual(sortCards(cards, 'name', 'all', latest, ranks).map((card) => card.key), ['a', 'b', 'c']);
  assert.deepEqual(sortCards(cards, 'price', 'all', latest, ranks).map((card) => card.key), ['b', 'c', 'a']);
  assert.deepEqual(sortCards(cards, 'default', 'top20', latest, ranks).map((card) => card.key), ['b', 'c', 'a']);
});

test('Prismatic index view stays at 180 while ball patterns stay out of the gallery', () => {
  const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'prismatic-evolutions-market-snapshot.json'), 'utf8'));
  const engine = createEngine({
    index: 'prismatic-evolutions',
    cardCount: 180,
    baselineDate: '2025-01-17',
    imagePattern: 'assets/prismatic-evolutions/[0-9]+\\.jpg',
    keyPattern: 'en-prismatic-evolutions-[0-9]+-(holofoil|normal)',
    sourcePattern: 'https://tcgcsv\\.com/(?:archive/tcgplayer/prices-\\d{4}-\\d{2}-\\d{2}\\.ppmd\\.7z|tcgplayer/3/23821/prices)',
    allowedSets: ['SV: Prismatic Evolutions'],
    allowedPrintings: ['Holofoil', 'Normal'],
    gallery: {
      secret: (card) => parseInt(card.number, 10) > 131,
      'special-illustration': (card) => card.rarity === 'Special Illustration Rare',
      'ace-spec': (card) => card.rarity === 'ACE SPEC Rare',
      hyper: (card) => card.rarity === 'Hyper Rare',
    },
  });
  const generated = new Date();
  const data = engine.validate({
    ...snapshot,
    generatedAt: generated.toISOString(),
    expiresAt: new Date(generated.getTime() + 9 * 60 * 1000).toISOString(),
  });
  const focus = engine.focus(data);
  assert.equal(data.cards.length, 180);
  assert.equal(focus.all.length, 180);
  assert.equal(data.baseline.date, '2025-01-17');
  assert.equal(data.baseline.usd, null);
  assert.equal(data.baseline.proposed, false);
  assert.equal(data.cards.some((card) => /ball pattern/i.test(card.name)), false);
  for (const group of Object.values(focus)) {
    assert.equal(group.some((card) => /ball pattern/i.test(card.name)), false);
  }
  const cache = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data/market-cache/prismatic-evolutions-current.json'), 'utf8'));
  assert.equal(cache.cards.length, 347);
  assert.equal(cache.index, 'prismatic-evolutions');
});

test('daily cache replaces the 16 Nov snapshot price for Kecleon and Raikou', () => {
  const {adaptDailyCache} = require('../set-index-engine.js');
  const cache = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data/market-cache/delta-reign-current.json'), 'utf8'));
  const generated = new Date();
  const value = engine.validate({
    ...adaptDailyCache(snapshot, cache),
    generatedAt: generated.toISOString(),
    expiresAt: new Date(generated.getTime() + 9 * 60 * 1000).toISOString(),
  });
  assert.equal(value.sourceDate, cache.sourceDate);
  const price = (id) => {
    const card = value.cards.find((row) => row.image.endsWith('/' + id + '.jpg'));
    const point = engine.latest(value, card.key);
    assert.equal(point[0], cache.sourceDate);
    assert.equal(point[2], 'ok');
    return point[1];
  };
  const kecleon = cache.cards.find((card) => String(card.productId) === '726567');
  const raikou = cache.cards.find((card) => String(card.productId) === '726574');
  const onRelease = (card) => card.points.find((point) => point.day === cache.sourceDate).usd;
  assert.equal(price('726567'), onRelease(kecleon));
  assert.equal(price('726574'), onRelease(raikou));
  assert.equal(value.cards.length, 141);
});
