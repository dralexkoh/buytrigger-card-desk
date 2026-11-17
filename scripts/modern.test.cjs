const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const rootDir = path.join(__dirname, '..');
// Saved CardZ quotes. Rendering stays on this clock so a newer feed does not change the result.
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/modern-psa10-render.json'), 'utf8'));
const fixed = new Date(fixture.clock);
class MockDate extends Date {
  constructor(...args) { super(...(args.length ? args : [fixed.getTime()])); }
  static now() { return fixed.getTime(); }
}

function harness() {
  const nodes = new Map();
  function make(selector) {
    const node = {
      selector, id: selector.startsWith('#') ? selector.slice(1) : '',
      hidden: false, textContent: '', innerHTML: '', value: '', checked: false, disabled: false,
      open: false, tabIndex: 0, dataset: {}, attrs: {}, className: '', listeners: {},
      classList: { toggle() {}, add() {}, remove() {} },
      setAttribute(key, value) { this.attrs[key] = String(value); },
      getAttribute(key) { return Object.prototype.hasOwnProperty.call(this.attrs, key) ? this.attrs[key] : null; },
      removeAttribute(key) { delete this.attrs[key]; },
      addEventListener(type, fn) { this.listeners[type] = fn; },
      focus() {}, showModal() { this.open = true; }, close() { this.open = false; },
      closest(sel) { return matches(this, sel) ? this : null; },
      querySelector(sel) { return queryAll(sel)[0] || null; },
      querySelectorAll(sel) { return queryAll(sel); },
      get clientWidth() { return 900; }, get clientHeight() { return 420; },
    };
    node.previousElementSibling = { textContent: '' };
    return node;
  }
  function matches(node, sel) {
    if (sel.startsWith('[data-') && sel.endsWith(']')) {
      const key = sel.slice(6, -1).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      return node.dataset[key] != null;
    }
    return node.selector === sel;
  }
  function queryAll(sel) {
    if (sel === '[data-grade]') return grades;
    if (sel === '[data-period]') return periods;
    if (sel === '[data-cohort]') return cohorts;
    if (sel === '[data-view]') return views;
    if (sel === '[data-brand]' || sel === 'img' || sel === '[data-card-tab]') return [];
    return [get(sel)];
  }
  function get(sel) {
    if (!nodes.has(sel)) nodes.set(sel, make(sel));
    return nodes.get(sel);
  }
  const root = make('#modern-preview');
  root.querySelector = sel => (sel.startsWith('[') ? queryAll(sel)[0] || null : get(sel));
  root.querySelectorAll = queryAll;
  const button = dataset => { const node = make('button'); node.dataset = dataset; return node; };
  const grades = [button({ grade: 'Raw' }), button({ grade: 'PSA 10' })];
  const periods = [button({ period: 'YTD' })];
  const cohorts = [button({ cohort: 'january' }), button({ cohort: 'current' })];
  const views = [button({ view: 'gallery' }), button({ view: 'table' })];
  const document = { getElementById: id => (id === 'modern-preview' ? root : get('#' + id)) };
  const window = {
    document, addEventListener() {},
    MODERN_PREVIEW_DATA: null, BT_HISTORY: null, BTMarket: null,
  };
  return { root, window, document, grades, views, get };
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function usd(amount) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}

function gbDate(iso) {
  return new Date(iso + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

function shiftDay(iso, days) {
  const date = new Date(iso + 'T00:00:00Z');
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function saleQuote() {
  return { ...fixture.quote, as_of: fixture.effectiveDay, date: fixture.effectiveDay };
}

function applyPsaFixture(data) {
  if (fixed.toISOString().slice(0, 10) !== fixture.effectiveDay) {
    throw new Error('fixture clock and effectiveDay must be the same UTC day');
  }
  const priced = new Set(fixture.pricedIds);
  for (const card of [fixture.fresh, fixture.fiveDay, fixture.agedOut]) {
    if (!priced.has(card.id)) throw new Error(`fixture card ${card.id} must be priced`);
  }
  if (priced.has(fixture.pending.id)) throw new Error('pending card is priced in the fixture');
  const present = new Set(data.cards.map(card => card.id));
  for (const id of priced) {
    if (!present.has(id)) throw new Error(`fixture card ${id} is missing from the catalogue`);
  }
  if (!present.has(fixture.pending.id)) throw new Error('pending card is missing from the catalogue');
  data.release = data.release || {};
  for (const card of data.cards) {
    if (priced.has(card.id)) card.quotes['PSA 10'] = saleQuote();
    else delete card.quotes['PSA 10'];
  }
  data.release.psa10 = { ...(data.release.psa10), effectiveDay: fixture.effectiveDay };
}

function boot(mutate) {
  const page = harness();
  const context = vm.createContext({
    console, URL, setTimeout, clearTimeout, Intl, Date: MockDate,
    document: page.document, window: page.window,
  });
  page.window.window = page.window;
  vm.runInContext(fs.readFileSync(path.join(rootDir, 'market-engine.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(rootDir, 'catalogue.js'), 'utf8'), context);
  applyPsaFixture(page.window.MODERN_PREVIEW_DATA);
  if (mutate) mutate(page.window.MODERN_PREVIEW_DATA);
  page.data = page.window.MODERN_PREVIEW_DATA;
  vm.runInContext(fs.readFileSync(path.join(rootDir, 'market-history.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(rootDir, 'modern.js'), 'utf8'), context);
  page.click = node => page.root.listeners.click({ target: node });
  return page;
}

function psaCells(html) {
  return [...html.matchAll(/<span>PSA 10 · last sale \(CardZ\)<\/span><b>([\s\S]*?)<\/b>/g)].map(match => match[1]);
}

test('PSA 10 gallery, table and dialog show CardZ sales, Pending and the credit line', () => {
  const page = boot();
  const total = page.data.cards.length;
  const priced = fixture.pricedIds.length;
  const price = usd(fixture.quote.price);
  const saleDay = gbDate(fixture.effectiveDay);
  const gallery = page.get('#card-gallery').innerHTML;
  const cells = psaCells(gallery);
  assert.ok(cells.length >= 1);
  assert.ok(cells.some(cell => cell.includes('Pending')));
  assert.ok(cells.some(cell => cell.includes('$')));
  for (const cell of cells) assert.equal(cell.includes('—'), false);
  assert.match(page.get('#coverage-bars').innerHTML, new RegExp(`${priced} / ${total} priced`));
  const credit = page.get('#psa-credit').innerHTML;
  assert.match(credit, /CardZ Marketcap, <a href="https:\/\/cardzmarketcap\.com"/);
  assert.match(credit, new RegExp(`data as of ${escapeRegExp(fixture.effectiveDay)}`));
  assert.match(credit, /CC BY 4\.0 \(<a href="https:\/\/creativecommons\.org\/licenses\/by\/4\.0\/"/);

  page.click(page.grades[1]);
  assert.equal(page.get('#series-label').textContent, `PSA 10 · LAST SALE · ${priced} OF ${total} CARDS`);
  assert.equal(page.get('#priced-only-hint').hidden, false);
  assert.equal(page.get('#priced-only').disabled, false);
  page.get('#card-search').listeners.input({ target: { value: fixture.pending.name } });
  assert.match(page.get('#card-gallery').innerHTML, new RegExp(escapeRegExp(esc(fixture.pending.name))));
  assert.match(psaCells(page.get('#card-gallery').innerHTML)[0], /Pending/);
  page.get('#card-search').listeners.input({ target: { value: fixture.fresh.name } });
  const fresh = page.get('#card-gallery').innerHTML;
  assert.match(fresh, new RegExp(escapeRegExp(price)));
  assert.match(fresh, new RegExp(escapeRegExp(fixture.quote.url)));
  assert.match(fresh, /PSA 10 · last sale \(CardZ\)/);

  const open = id => page.click({ dataset: { card: String(id) }, closest(sel) { return sel === '[data-card]' ? this : null; } });
  open(fixture.fresh.id);
  const dialog = page.get('#dialog-content').innerHTML;
  assert.match(dialog, new RegExp(escapeRegExp(esc(fixture.fresh.name))));
  assert.match(dialog, new RegExp(escapeRegExp(price)));
  assert.match(dialog, new RegExp(`PSA 10: CardZ last sale · ${escapeRegExp(saleDay)} · confidence ${escapeRegExp(fixture.quote.confidence)}`));
  assert.match(dialog, /PSA 9 not tracked/);
  assert.match(dialog, new RegExp(`href="${escapeRegExp(fixture.quote.url)}"`));
  assert.match(dialog, /rel="noopener noreferrer"/);
  assert.match(dialog, new RegExp(`data as of ${escapeRegExp(fixture.effectiveDay)}`));
  open(fixture.pending.id);
  const held = page.get('#dialog-content').innerHTML;
  assert.match(held, new RegExp(escapeRegExp(esc(fixture.pending.name))));
  assert.match(held, /PSA 10: Pending review/);
  assert.equal(held.includes('—</b>'), false);

  page.get('#card-search').listeners.input({ target: { value: '' } });
  page.click(page.views[1]);
  const table = page.get('#card-table').innerHTML;
  assert.match(table, /<th>PSA 10 · last sale \(CardZ\)<\/th>/);
  assert.equal(table.includes('<th>PSA 9</th>'), false);
  assert.match(table, new RegExp(escapeRegExp(price)));
  assert.match(table, new RegExp(escapeRegExp(fixture.quote.url.split('/').pop())));
  const psaColumn = [...table.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].slice(1).map(row => [...row[1].matchAll(/<td>([\s\S]*?)<\/td>/g)][2][1]);
  assert.ok(psaColumn.some(cell => cell.includes(price)));
  assert.ok(psaColumn.some(cell => cell.includes('price-pending">Pending')));
  for (const cell of psaColumn) assert.equal(cell.includes('—'), false);
});

test('a five-day PSA 10 sale says last priced and a 31-day sale is Pending', () => {
  const fiveDay = shiftDay(fixture.effectiveDay, -5);
  const agedOut = shiftDay(fixture.effectiveDay, -31);
  const page = boot(data => {
    const recent = data.cards.find(card => card.id === fixture.fiveDay.id);
    recent.quotes['PSA 10'].as_of = recent.quotes['PSA 10'].date = fiveDay;
    const old = data.cards.find(card => card.id === fixture.agedOut.id);
    old.quotes['PSA 10'].as_of = old.quotes['PSA 10'].date = agedOut;
    old.quotes['PSA 10'].status = 'ok';
  });
  assert.match(page.get('#coverage-bars').innerHTML, new RegExp(`${fixture.pricedIds.length - 1} / ${page.data.cards.length} priced`));
  page.get('#card-search').listeners.input({ target: { value: fixture.fiveDay.name } });
  assert.match(page.get('#card-gallery').innerHTML, new RegExp(`last priced ${escapeRegExp(gbDate(fiveDay))}`));
  page.get('#card-search').listeners.input({ target: { value: fixture.agedOut.number } });
  const cells = psaCells(page.get('#card-gallery').innerHTML);
  assert.equal(cells.length, 1);
  assert.match(cells[0], /Pending/);
  assert.equal(cells[0].includes('$'), false);
});
