/* Sort and filter for the public 30th Anniversary raw-price table. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) {
    const boot = () => api.mount(root.document);
    if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', boot);
    else boot();
  }
})(typeof globalThis === 'undefined' ? this : globalThis, function () {
  'use strict';

  function numberKey(value) {
    return String(value ?? '').split(/(\d+)/).filter(Boolean).map(part => (
      /^\d+$/.test(part) ? [0, Number(part)] : [1, part.toLowerCase()]
    ));
  }

  function compareNumber(a, b) {
    const left = numberKey(a);
    const right = numberKey(b);
    const length = Math.max(left.length, right.length);
    for (let i = 0; i < length; i += 1) {
      const x = left[i] || [0, 0];
      const y = right[i] || [0, 0];
      if (x[0] !== y[0]) return x[0] - y[0];
      if (x[1] < y[1]) return -1;
      if (x[1] > y[1]) return 1;
    }
    return 0;
  }

  function fields(row) {
    if (row && row.dataset) {
      const raw = row.dataset.price;
      const price = raw === '' || raw == null ? null : Number(raw);
      return {
        name: row.dataset.name || '',
        number: row.dataset.number || '',
        price: Number.isFinite(price) && price > 0 ? price : null,
        id: row.dataset.id || '',
        search: row.dataset.search || '',
      };
    }
    const price = row.price == null || row.price === '' ? null : Number(row.price);
    return {
      name: row.name || '',
      number: row.number || '',
      price: Number.isFinite(price) && price > 0 ? price : null,
      id: row.id || '',
      search: row.search || '',
    };
  }

  function tie(a, b) {
    const left = fields(a);
    const right = fields(b);
    const name = left.name.localeCompare(right.name, 'en', {sensitivity: 'base', numeric: true});
    if (name) return name;
    const number = compareNumber(left.number, right.number);
    if (number) return number;
    return left.id.localeCompare(right.id);
  }

  function compareRows(a, b, mode) {
    const left = fields(a);
    const right = fields(b);
    const [kind, direction] = String(mode || 'price-desc').split('-');
    if (kind === 'name') {
      const name = left.name.localeCompare(right.name, 'en', {sensitivity: 'base', numeric: true});
      return (direction === 'desc' ? -name : name) || tie(a, b);
    }
    if (kind === 'number') {
      const number = compareNumber(left.number, right.number);
      return (direction === 'desc' ? -number : number) || tie(a, b);
    }
    const missing = (left.price == null) - (right.price == null);
    if (missing) return missing;
    if (left.price == null && right.price == null) return tie(a, b);
    const diff = direction === 'asc' ? left.price - right.price : right.price - left.price;
    return diff || tie(a, b);
  }

  function mount(doc) {
    const menu = doc.querySelector('.mobile-menu');
    const nav = doc.querySelector('#site-nav');
    if (menu && nav && menu.dataset.bound !== 'true') {
      menu.dataset.bound = 'true';
      menu.addEventListener('click', () => {
        const open = nav.classList.toggle('open');
        menu.setAttribute('aria-expanded', String(open));
      });
      nav.addEventListener('click', event => {
        if (!event.target.closest('a')) return;
        nav.classList.remove('open');
        menu.setAttribute('aria-expanded', 'false');
      });
    }

    const table = doc.querySelector('#price-table');
    const filter = doc.querySelector('#price-filter');
    const sort = doc.querySelector('#price-sort');
    const count = doc.querySelector('#price-count');
    const empty = doc.querySelector('#price-empty');
    if (!table || !filter || !sort || !count) return;
    const body = table.tBodies[0];

    function apply() {
      const query = filter.value.trim().toLowerCase();
      const rows = [...body.rows];
      rows.sort((a, b) => compareRows(a, b, sort.value));
      let shown = 0;
      rows.forEach(row => {
        const info = fields(row);
        const match = !query || info.search.includes(query);
        row.hidden = !match;
        if (match) shown += 1;
        body.appendChild(row);
      });
      table.querySelectorAll('th[data-sort], th:has(button[data-sort])').forEach(header => {
        const button = header.querySelector('[data-sort]');
        if (!button) return;
        const selected = sort.value.startsWith(button.dataset.sort + '-');
        header.setAttribute('aria-sort', selected ? (sort.value.endsWith('asc') ? 'ascending' : 'descending') : 'none');
      });
      count.textContent = shown === rows.length ? `${rows.length} cards` : `Showing ${shown} of ${rows.length} cards`;
      if (empty) empty.hidden = shown !== 0;
    }

    filter.addEventListener('input', apply);
    sort.addEventListener('change', apply);
    table.addEventListener('click', event => {
      const button = event.target.closest('[data-sort]');
      if (!button) return;
      const kind = button.dataset.sort;
      const current = sort.value;
      if (kind === 'price') sort.value = current === 'price-desc' ? 'price-asc' : 'price-desc';
      else sort.value = current === `${kind}-asc` ? `${kind}-desc` : `${kind}-asc`;
      apply();
    });
    apply();
  }

  return {numberKey, compareNumber, compareRows, mount};
});
