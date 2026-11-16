const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const rootDir = path.join(__dirname, '..');
const fixed = new Date('2026-11-16T15:00:00Z');
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

function boot(mutate) {
  const page = harness();
  const context = vm.createContext({
    console, URL, setTimeout, clearTimeout, Intl, Date: MockDate,
    document: page.document, window: page.window,
  });
  page.window.window = page.window;
  vm.runInContext(fs.readFileSync(path.join(rootDir, 'market-engine.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(rootDir, 'catalogue.js'), 'utf8'), context);
  if (mutate) mutate(page.window.MODERN_PREVIEW_DATA);
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
  const gallery = page.get('#card-gallery').innerHTML;
  const cells = psaCells(gallery);
  assert.ok(cells.length >= 1);
  assert.ok(cells.some(cell => cell.includes('Pending')));
  assert.ok(cells.some(cell => cell.includes('$')));
  for (const cell of cells) assert.equal(cell.includes('—'), false);
  assert.match(page.get('#coverage-bars').innerHTML, /50 \/ 100 priced/);
  const credit = page.get('#psa-credit').innerHTML;
  assert.match(credit, /CardZ Marketcap, <a href="https:\/\/cardzmarketcap\.com"/);
  assert.match(credit, /data as of 2026-11-16/);
  assert.match(credit, /CC BY 4\.0 \(<a href="https:\/\/creativecommons\.org\/licenses\/by\/4\.0\/"/);

  page.click(page.grades[1]);
  assert.equal(page.get('#series-label').textContent, 'PSA 10 · LAST SALE · 50 OF 100 CARDS');
  assert.equal(page.get('#priced-only-hint').hidden, false);
  assert.equal(page.get('#priced-only').disabled, false);
  page.get('#card-search').listeners.input({ target: { value: 'Latias' } });
  assert.match(page.get('#card-gallery').innerHTML, /Latias &amp; Latios GX/);
  assert.match(psaCells(page.get('#card-gallery').innerHTML)[0], /Pending/);
  page.get('#card-search').listeners.input({ target: { value: 'Mewtwo GX' } });
  const mewtwo = page.get('#card-gallery').innerHTML;
  assert.match(mewtwo, /\$7,052/);
  assert.match(mewtwo, /https:\/\/cardzmarketcap\.com\/card\/cmc_735ae8ccb34ac2b25af3ef5e/);
  assert.match(mewtwo, /PSA 10 · last sale \(CardZ\)/);

  page.click({ dataset: { card: '24' }, closest(sel) { return sel === '[data-card]' ? this : null; } });
  const dialog = page.get('#dialog-content').innerHTML;
  assert.match(dialog, /\$7,052/);
  assert.match(dialog, /PSA 10: CardZ last sale · 16 Nov 2026 · confidence medium/);
  assert.match(dialog, /PSA 9 not tracked/);
  assert.match(dialog, /href="https:\/\/cardzmarketcap\.com\/card\/cmc_735ae8ccb34ac2b25af3ef5e"/);
  assert.match(dialog, /rel="noopener noreferrer"/);
  assert.match(dialog, /data as of 2026-11-16/);
  page.click({ dataset: { card: '1' }, closest(sel) { return sel === '[data-card]' ? this : null; } });
  const held = page.get('#dialog-content').innerHTML;
  assert.match(held, /Latias &amp; Latios GX/);
  assert.match(held, /PSA 10: Pending review/);
  assert.equal(held.includes('—</b>'), false);

  page.get('#card-search').listeners.input({ target: { value: '' } });
  page.click(page.views[1]);
  const table = page.get('#card-table').innerHTML;
  assert.match(table, /<th>PSA 10 · last sale \(CardZ\)<\/th>/);
  assert.equal(table.includes('<th>PSA 9</th>'), false);
  assert.match(table, /\$7,052/);
  assert.match(table, /cmc_735ae8ccb34ac2b25af3ef5e/);
  const psaColumn = [...table.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].slice(1).map(row => [...row[1].matchAll(/<td>([\s\S]*?)<\/td>/g)][2][1]);
  assert.ok(psaColumn.some(cell => cell.includes('$7,052')));
  assert.ok(psaColumn.some(cell => cell.includes('price-pending">Pending')));
  for (const cell of psaColumn) assert.equal(cell.includes('—'), false);
});

test('a five-day PSA 10 sale says last priced and a 31-day sale is Pending', () => {
  const page = boot(data => {
    const umbreon = data.cards.find(card => card.id === 6);
    umbreon.quotes['PSA 10'].as_of = umbreon.quotes['PSA 10'].date = '2026-11-11';
    const magikarp = data.cards.find(card => card.id === 89);
    magikarp.quotes['PSA 10'].as_of = magikarp.quotes['PSA 10'].date = '2026-10-16';
    magikarp.quotes['PSA 10'].status = 'ok';
  });
  assert.match(page.get('#coverage-bars').innerHTML, /49 \/ 100 priced/);
  page.get('#card-search').listeners.input({ target: { value: 'Umbreon VMAX' } });
  assert.match(page.get('#card-gallery').innerHTML, /last priced 11 Nov 2026/);
  page.get('#card-search').listeners.input({ target: { value: '203/193' } });
  const cells = psaCells(page.get('#card-gallery').innerHTML);
  assert.equal(cells.length, 1);
  assert.match(cells[0], /Pending/);
  assert.equal(cells[0].includes('$'), false);
});
