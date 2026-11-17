const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const src = fs.readFileSync('site.js', 'utf8');
const chaseStrip = src.split('\n').find(line => line.startsWith('function chaseStrip('));
const esc = src.match(/^const esc=.+;$/m)[0];
const render = vm.runInNewContext(esc + '\n' + chaseStrip + '\nchaseStrip');
const editorial = require('../editorial.json');

test('a story without chase_cards renders no strip', () => {
  assert.equal(render({}), '');
  assert.equal(render({chase_cards: []}), '');
  const welcome = editorial.articles.find(article => article.slug === 'welcome');
  assert.equal(render(welcome), '');
});

test('the Delta Reign chase story renders a lazy credited strip', () => {
  const article = editorial.articles.find(item => item.slug === 'delta-reign-chase-card-prices-november-2026');
  const html = render(article);
  assert.equal(article.chase_cards.length, 5);
  assert.equal((html.match(/loading="lazy"/g) || []).length, 5);
  assert.match(html, /aria-label="Chase cards"/);
  assert.match(html, /Card image: TCGplayer\./);
  for (const card of article.chase_cards) {
    assert.ok(html.includes(card.image), card.image);
    assert.ok(html.includes(card.alt), card.name);
    assert.ok(html.includes(card.name), card.name);
  }
  assert.doesNotMatch(html, /<script>/);
});

test('card names and links are escaped', () => {
  const html = render({
    chase_cards_credit: 'Card image: TCGplayer.',
    chase_cards: [{
      name: 'A & B <script>',
      image: 'assets/card.jpg',
      alt: 'Safe "alt"',
      link: 'https://www.tcgplayer.com/product/1',
    }],
  });
  assert.match(html, /A &amp; B &lt;script&gt;/);
  assert.match(html, /alt="Safe &quot;alt&quot;"/);
  assert.match(html, /href="https:\/\/www\.tcgplayer\.com\/product\/1"/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.doesNotMatch(html, /<script>/);
});
