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
  const {chaseEntries} = require('../set-index-engine.js');
  const expected = {
    'delta-reign': ['728061', '728062', '726574', '726567', '726576', '728060', '727592', '726565', '726575', '726563'],
    'sv-151': ['517045', '517046', '517044', '502556', '502549', '517048', '517018', '517047', '516997', '513721'],
    'prismatic-evolutions': ['610516', '610511', '610499', '610510', '610505', '610504', '610501', '610508', '610522', '610517'],
  };
  for (const [slug, ids] of Object.entries(expected)) {
    const roster = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data/market-rosters', slug + '.json'), 'utf8'));
    assert.equal(roster.chase_source, 'keeper-2026-11-17');
    const entries = chaseEntries(roster);
    assert.deepEqual(entries.map((card) => card.productId), ids);
    assert.deepEqual(entries.map((card) => card.chase_rank), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  }
  const swapped = {cards: [{productId: '2', chase_rank: 2, name: 'B', number: '2'}, {productId: '1', chase_rank: 1, name: 'A', number: '1'}, {productId: '9', name: 'Skip'}]};
  assert.deepEqual(chaseEntries(swapped).map((card) => card.productId), ['1', '2']);
});
