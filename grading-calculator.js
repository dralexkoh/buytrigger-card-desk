(function (root, factory) {
  const calculator = factory();
  if (typeof module === 'object' && module.exports) module.exports = calculator;
  else root.BTGradingCalculator = calculator;
})(typeof globalThis === 'undefined' ? window : globalThis, function () {
  'use strict';

  const SCALE = 10000;
  const MAX_PRICE = 10_000_000;
  const CURRENCIES = { GBP: '£', USD: 'US$', EUR: '€', JPY: '¥' };
  const OUTCOMES = [ ['raw', 'Raw'], ['nine', 'PSA 9'], ['ten', 'PSA 10'] ];
  const PRICES = ['entry', 'grading', 'raw', 'nine', 'ten', 'eight', 'fixed', 'target'];

  function parseAmount(text, unit = 100, max = MAX_PRICE) {
    const value = String(text).trim();
    if (!value) return { amount: null, invalid: false };
    const decimal = unit === 1 ? /^\d+$/ : /^(?:\d+(?:\.\d{0,2})?|\.\d{1,2})$/;
    if (!decimal.test(value) || Number(value) > max) return { amount: null, invalid: true };
    return { amount: Math.round(Number(value) * unit), invalid: false };
  }

  function netSale(sale, fee, fixed, fall) {
    const adjusted = Math.floor(sale * (SCALE - fall) / SCALE);
    const commission = Math.floor((adjusted * fee + SCALE / 2) / SCALE);
    return { adjusted, proceeds: adjusted - commission - fixed };
  }

  // The displayed threshold must still work after the same rounding and stress
  // used for an entered sale. Net proceeds are monotonic in the gross price.
  function minimumSale(needed, fee, fixed, fall, maximum) {
    if (netSale(maximum, fee, fixed, fall).proceeds < needed) return null;
    let low = 0;
    let high = maximum;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (netSale(middle, fee, fixed, fall).proceeds >= needed) high = middle;
      else low = middle + 1;
    }
    return low;
  }

  function calculate(values) {
    const { mode, entry, grading, fee, fixed, fall, target, unit } = values;
    const feesKnown = fee !== null && fixed !== null;
    const buying = mode === 'buy';
    const paid = buying ? entry : 0;
    const maximum = MAX_PRICE * unit;
    const rows = {};
    for (const key of ['raw', 'eight', 'nine', 'ten']) {
      const gross = values[key];
      const gradingCost = key === 'raw' ? 0 : grading;
      const sale = gross !== null && feesKnown ? netSale(gross, fee, fixed, fall) : null;
      const takeHome = sale && gradingCost !== null ? sale.proceeds - gradingCost : null;
      rows[key] = {
        gross,
        adjusted: gross === null ? null : Math.floor(gross * (SCALE - fall) / SCALE),
        takeHome,
        result: paid === null || takeHome === null ? null : takeHome - paid,
        maxEntry: buying && takeHome !== null && target !== null ? takeHome - target : null
      };
    }
    const raw = rows.raw.takeHome;
    const canCompare = raw !== null && grading !== null;
    const canBreakEven = buying && entry !== null && grading !== null && feesKnown;
    for (const key of ['eight', 'nine', 'ten']) {
      rows[key].vsRaw = rows[key].takeHome !== null && raw !== null ? rows[key].takeHome - raw : null;
    }
    return {
      rows,
      canCompare,
      beatRaw: canCompare ? minimumSale(raw + grading + 1, fee, fixed, fall, maximum) : null,
      canBreakEven,
      breakEven: canBreakEven ? minimumSale(entry + grading, fee, fixed, fall, maximum) : null
    };
  }

  function moneyField(key, label, hint = '') {
    const description = hint ? ` aria-describedby="gc-${key}-hint"` : '';
    return `<div class="gc-field"${key === 'entry' || key === 'target' ? ' data-buy-only' : ''}>
      <label for="gc-${key}">${label}</label>
      <div class="gc-input"><span data-currency-symbol aria-hidden="true">£</span>
        <input id="gc-${key}" name="${key}" type="number" inputmode="decimal" min="0" step="0.01" max="${MAX_PRICE}"${description}>
      </div>
      ${hint ? `<small id="gc-${key}-hint">${hint}</small>` : ''}
    </div>`;
  }

  function outcomeCard(key, label) {
    return `<article class="gc-outcome" data-outcome="${key}">
      <div class="gc-outcome-line"><h3>${label}</h3><p data-outcome-value>—</p></div>
      <div class="gc-bar" aria-hidden="true"><i></i></div>
      <p class="gc-gross" data-outcome-gross>Enter a sale price</p>
      <p class="gc-comparison" data-outcome-compare hidden></p>
      <p class="gc-limit" data-outcome-limit hidden></p>
    </article>`;
  }

  function page() {
    return `<section class="grading-tool" aria-labelledby="grading-title">
      <header class="gc-intro">
        <span class="kicker red-text">GRADING CALCULATOR</span>
        <h1 id="grading-title">Is it worth grading<span class="red-text">?</span></h1>
        <p>Compare selling raw with grading. See what you keep after costs and what changes if prices fall.</p>
      </header>
      <div class="gc-layout">
        <form class="gc-form" novalidate>
          <div class="gc-setup">
            <fieldset class="gc-mode">
              <legend>What are you deciding?</legend>
              <div class="gc-toggle">
                <label><input type="radio" name="mode" value="buy" checked><span>I’m buying</span></label>
                <label><input type="radio" name="mode" value="own"><span>I own it</span></label>
              </div>
            </fieldset>
            <div class="gc-field gc-currency"><label for="gc-currency">Currency</label>
              <select id="gc-currency" name="currency" aria-describedby="gc-currency-hint">
                <option value="GBP">GBP £</option><option value="USD">USD $</option>
                <option value="EUR">EUR €</option><option value="JPY">JPY ¥</option>
              </select>
              <small id="gc-currency-hint">Changing currency changes the units. Enter all prices in that currency.</small>
            </div>
          </div>
          <div class="gc-fields gc-costs">
            ${moneyField('entry', 'Delivered buy price', 'Include postage and any buyer fees.')}
            ${moneyField('grading', 'Total grading cost', 'Include the fee, shipping both ways, tax and any upcharge.')}
          </div>
          <fieldset class="gc-sale-fields">
            <legend>What could it sell for?</legend>
            <p>Use recent sales of the exact printing. Start with any one price.</p>
            <div class="gc-fields">
              ${moneyField('raw', 'Raw sale price')}
              ${moneyField('nine', 'PSA 9 sale price')}
              ${moneyField('ten', 'PSA 10 sale price')}
            </div>
            <p class="gc-raw-source" data-raw-source hidden></p>
          </fieldset>
          <details class="gc-details gc-reference" data-reference hidden>
            <summary>Use a Raw guide from the Modern Index</summary>
            <div class="gc-reference-body">
              <label for="gc-card">Choose a printing</label>
              <select id="gc-card"><option value="">Choose a card</option></select>
              <div class="gc-reference-card" data-reference-card hidden>
                <img width="52" height="73" alt=""><div>
                  <p data-guide-identity></p><p data-guide-price></p>
                  <a data-guide-source target="_blank" rel="noopener noreferrer">View price source ↗</a>
                </div>
              </div>
              <p data-guide-hint hidden></p>
              <button type="button" class="gc-secondary" data-gc-action="use-guide" hidden>Use as Raw sale price</button>
            </div>
          </details>
          <details class="gc-details">
            <summary>Selling costs and downside <span data-cost-summary>0% + £0 per sale</span></summary>
            <div class="gc-fields gc-extra-fields">
              <div class="gc-field"><label for="gc-fee">Selling fee %</label>
                <input id="gc-fee" name="fee" type="number" inputmode="decimal" min="0" max="100" step="0.01" value="0">
              </div>
              ${moneyField('fixed', 'Fixed cost per sale', 'Postage, packing and any fixed fee.')}
              ${moneyField('target', 'Profit target', 'Used to calculate your maximum buy price.')}
              ${moneyField('eight', 'PSA 8 sale price', 'Optional lower-grade outcome.')}
            </div>
          </details>
          <p data-form-error class="gc-error" role="status" hidden></p>
          <div class="gc-actions">
            <button type="button" class="gc-secondary" data-gc-action="example">Try an example</button>
            <button type="button" class="gc-secondary" data-gc-action="clear">Clear</button>
            <button type="button" class="gc-jump" data-gc-action="results">See results ↓</button>
          </div>
          <p data-example-note class="gc-example-note" hidden>Illustrative prices and fees. Replace them with your own numbers.</p>
        </form>
        <section class="gc-results" aria-labelledby="grading-results" tabindex="-1">
          <div class="gc-result-head">
            <div><span class="kicker">YOUR SCENARIO</span><h2 id="grading-results">What you keep</h2></div>
            <div class="gc-field gc-stress"><label for="gc-stress">If sale prices fall</label>
              <select id="gc-stress"><option value="0">No fall</option><option value="10">10% lower</option><option value="20">20% lower</option></select>
            </div>
          </div>
          <p class="gc-verdict" data-verdict aria-live="polite"></p>
          <div class="gc-outcomes">${OUTCOMES.map(([key, label]) => outcomeCard(key, label)).join('')}</div>
          <p class="gc-lower-grade" data-lower-grade hidden></p>
          <div class="gc-thresholds" data-thresholds hidden>
            <p data-break-even hidden></p><p data-beat-raw hidden></p>
          </div>
          <p class="gc-result-note" data-result-note></p>
          <div class="gc-copy" data-copy hidden>
            <button type="button" class="gc-secondary" data-gc-action="copy">Copy calculation</button>
            <span role="status" data-copy-status></span>
          </div>
        </section>
      </div>
    </section>`;
  }

  function newDraft(currency = 'GBP', mode = 'buy') {
    return { currency, mode, fee: '0', fixed: '0', target: '0', fall: '0', guide: null, selected: '', example: false };
  }

  let draft = newDraft();

  function currentGuides(catalogue) {
    const latest = catalogue?.release?.sourceDate;
    return (catalogue?.cards || []).filter(card => {
      const quote = card.quotes?.Raw;
      return card.rawRefresh?.status === 'current' && card.rawRefresh.sourceDate === latest &&
        quote?.date === latest && /^\d{4}-\d{2}-\d{2}$/.test(latest) &&
        Object.hasOwn(CURRENCIES, quote.currency) && Number.isFinite(quote.price) &&
        quote.price > 0 && quote.price <= MAX_PRICE && Number.isInteger(card.productId);
    }).sort((a, b) => a.name.localeCompare(b.name) || a.set.localeCompare(b.set));
  }

  function mount(container, catalogue) {
    const tool = container.querySelector('.grading-tool');
    if (!tool) return;
    const find = selector => tool.querySelector(selector);
    const form = find('.gc-form');
    const resultPanel = find('.gc-results');
    const stress = find('#gc-stress');
    const cardSelect = find('#gc-card');
    const guides = new Map(currentGuides(catalogue).map(card => [String(card.productId), card]));
    const fields = Object.fromEntries([...PRICES, 'fee'].map(key => [key, find(`#gc-${key}`)]));
    const hide = (node, hidden) => { node.hidden = hidden; };
    const showText = (node, value) => { node.textContent = value; hide(node, !value); };
    const currency = find('#gc-currency');
    const dateLabel = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' });

    for (const [id, card] of guides) {
      cardSelect.add(new Option(`${card.name} · ${card.set} ${card.number} · ${card.printing}`, id));
    }
    hide(find('[data-reference]'), !guides.size);

    function setInputs() {
      currency.value = draft.currency;
      stress.value = draft.fall;
      find(`input[name="mode"][value="${draft.mode}"]`).checked = true;
      cardSelect.value = draft.selected;
      for (const [key, field] of Object.entries(fields)) field.value = draft[key] ?? '';
    }

    function hasEnteredPrices() {
      return PRICES.some(key => fields[key].value !== '' && Number(fields[key].value) !== 0);
    }

    function updateReference(money, unit) {
      const selected = guides.get(cardSelect.value);
      const preview = find('[data-reference-card]');
      const use = find('[data-gc-action="use-guide"]');
      hide(preview, !selected);
      hide(use, !selected);
      if (selected) {
        const quote = selected.quotes.Raw;
        const guideMoney = new Intl.NumberFormat('en-GB', { style: 'currency', currency: quote.currency });
        const label = `${selected.name} · ${selected.set} ${selected.number} · ${selected.language} ${selected.printing}`;
        preview.querySelector('img').src = selected.image;
        preview.querySelector('img').alt = `${selected.name}, ${selected.set} ${selected.number}`;
        find('[data-guide-identity]').textContent = label;
        find('[data-guide-price]').textContent = `${guideMoney.format(quote.price)} · ${dateLabel.format(new Date(quote.date))} Raw market guide`;
        find('[data-guide-source]').href = `https://www.tcgplayer.com/product/${selected.productId}`;
        const otherCurrency = quote.currency !== draft.currency;
        use.disabled = otherCurrency && hasEnteredPrices();
        use.textContent = otherCurrency && !use.disabled ? `Use Raw guide in ${quote.currency}` : 'Use as Raw sale price';
        showText(find('[data-guide-hint]'), use.disabled
          ? `Choose ${quote.currency} to use this guide. Prices are kept in their source currency.`
          : 'Combined-condition market guide. Use your own sale estimate if condition or local prices differ.');
      } else hide(find('[data-guide-hint]'), true);
      const applied = guides.get(draft.guide);
      if (applied) {
        const quote = applied.quotes.Raw;
        showText(find('[data-raw-source]'), `${applied.name} · ${applied.set} ${applied.number} · ${money(Math.round(quote.price * unit))} guide dated ${dateLabel.format(new Date(quote.date))}`);
      } else hide(find('[data-raw-source]'), true);
    }

    let lastCalculation;
    function render(fromUser = false) {
      const unit = draft.currency === 'JPY' ? 1 : 100;
      const formatter = new Intl.NumberFormat('en-GB', { style: 'currency', currency: draft.currency });
      const money = amount => formatter.format(amount / unit);
      const buying = draft.mode === 'buy';
      const resultLabel = buying ? 'profit' : 'after costs';
      const renderResult = value => value < 0
        ? `${money(-value)} ${buying ? 'loss' : 'out of pocket'}`
        : `${money(value)} ${resultLabel}`;
      const difference = value => value === 0 ? 'Same as selling raw' : `${money(Math.abs(value))} ${value > 0 ? 'more' : 'less'} than selling raw`;
      const values = { mode: draft.mode, unit, fall: Number(stress.value) * 100 };
      let invalid = false;
      for (const [key, field] of Object.entries(fields)) {
        const isFee = key === 'fee';
        if (!isFee) field.step = unit === 1 ? '1' : '0.01';
        const parsed = parseAmount(field.value, isFee ? 100 : unit, isFee ? 100 : MAX_PRICE);
        const relevant = buying || (key !== 'entry' && key !== 'target');
        const error = relevant && (parsed.invalid || field.validity.badInput);
        if (error) field.setAttribute('aria-invalid', 'true');
        else field.removeAttribute('aria-invalid');
        invalid ||= error;
        values[key] = error ? null : parsed.amount;
      }
      tool.querySelectorAll('[data-currency-symbol]').forEach(node => { node.textContent = CURRENCIES[draft.currency]; });
      tool.querySelectorAll('[data-buy-only]').forEach(node => hide(node, !buying));
      showText(find('[data-form-error]'), invalid ? `Enter non-negative ${draft.currency} amounts in the shown units and fees from 0 to 100%.` : '');
      showText(find('[data-cost-summary]'), values.fee === null || values.fixed === null ? 'Enter costs' : `${values.fee / 100}% + ${money(values.fixed)} per sale`);
      hide(find('[data-example-note]'), !draft.example);
      updateReference(money, unit);

      const result = calculate(values);
      const { rows } = result;
      const largest = Math.max(1, ...OUTCOMES.map(([key]) => rows[key].adjusted ?? 0));
      for (const [key] of OUTCOMES) {
        const row = rows[key];
        const card = find(`[data-outcome="${key}"]`);
        const value = card.querySelector('[data-outcome-value]');
        value.textContent = row.result === null ? '—' : renderResult(row.result);
        value.classList.toggle('gc-loss', row.result !== null && row.result < 0);
        card.querySelector('.gc-bar i').style.width = `${(row.adjusted ?? 0) / largest * 100}%`;
        card.querySelector('[data-outcome-gross]').textContent = row.adjusted === null ? 'Enter a sale price' : `${money(row.adjusted)} sale${values.fall ? ' after the fall' : ''}`;
        showText(card.querySelector('[data-outcome-compare]'), row.vsRaw == null ? '' : difference(row.vsRaw));
        const cap = row.maxEntry;
        const limitLabel = values.target > 0 ? `Max buy for ${money(values.target)} profit` : 'Break-even buy price';
        showText(card.querySelector('[data-outcome-limit]'), cap === null ? '' : cap < 0
          ? `${limitLabel} · ${money(-cap)} short even at ${money(0)}`
          : `${limitLabel} · ${money(cap)}`);
      }

      const downside = rows.eight;
      showText(find('[data-lower-grade]'), downside.gross === null ? '' : downside.result === null
        ? 'PSA 8 · Add the applicable costs to see this outcome.'
        : `PSA 8 · ${renderResult(downside.result)}${downside.vsRaw === null ? '' : ` · ${difference(downside.vsRaw)}`}`);
      const fallSuffix = values.fall ? ' before the price fall' : '';
      const breakEven = result.canBreakEven ? (result.breakEven === null
        ? 'Graded break-even is outside the sale price range.'
        : `Graded sale to break even · ${money(result.breakEven)}${fallSuffix}`) : '';
      const beatRaw = result.canCompare ? (result.beatRaw === null
        ? 'Grading cannot beat the Raw result within the sale price range.'
        : `Graded sale to beat Raw · ${money(result.beatRaw)}${fallSuffix}`) : '';
      showText(find('[data-break-even]'), breakEven);
      showText(find('[data-beat-raw]'), beatRaw);
      hide(find('[data-thresholds]'), !breakEven && !beatRaw);

      let verdict = 'Enter a sale price and the costs that apply to it.';
      if (values.fee === null || values.fixed === null) verdict = 'Add the percentage fee and fixed cost for each sale.';
      else if (buying && values.entry === null && OUTCOMES.some(([key]) => rows[key].maxEntry !== null)) {
        verdict = 'Your buy limits are ready. Add the delivered price to see profit or loss.';
      } else if (rows.nine.result !== null) {
        verdict = rows.nine.vsRaw === null
          ? `PSA 9 · ${renderResult(rows.nine.result)}. Add a Raw sale price to compare.`
          : `At PSA 9, you keep ${rows.nine.vsRaw === 0 ? 'the same as selling raw' : difference(rows.nine.vsRaw)}.`;
      } else if (rows.ten.result !== null) {
        verdict = `PSA 10 · ${renderResult(rows.ten.result)}. Add a PSA 9 price to see the lower outcome.`;
      } else if (rows.raw.result !== null) {
        verdict = `Selling raw · ${renderResult(rows.raw.result)}. Add a grading cost and graded sale price to compare.`;
      } else if (values.grading === null && [rows.eight, rows.nine, rows.ten].some(row => row.gross !== null)) {
        verdict = 'Add the total grading cost to see what you keep at that grade.';
      }
      const verdictNode = find('[data-verdict]');
      if (verdictNode.textContent !== verdict) verdictNode.textContent = verdict;
      find('[data-result-note]').textContent = buying
        ? 'Profit deducts the delivered price, selling costs and any grading cost. Bars compare sale prices.'
        : 'Take-home deducts selling costs and any new grading cost. Compare the cash each option adds from today. Bars compare sale prices.';

      const hasResult = OUTCOMES.some(([key]) => rows[key].result !== null || rows[key].maxEntry !== null) || result.canCompare || downside.result !== null;
      hide(find('[data-copy]'), !hasResult);
      find('[data-copy-status]').textContent = '';
      lastCalculation = [
        `BuyTrigger.Cards grading calculator · ${draft.currency} · ${buying ? 'Buying' : 'Already owned'}`,
        ...(draft.example ? ['Illustrative example'] : []),
        ...(buying && values.entry !== null ? [`Delivered buy price ${money(values.entry)}`] : []),
        ...(values.grading !== null ? [`Total grading cost ${money(values.grading)}`] : []),
        values.fee !== null && values.fixed !== null ? `Selling cost ${values.fee / 100}% + ${money(values.fixed)}` : 'Selling costs unknown',
        `Sale-price fall ${values.fall / 100}%`,
        ...OUTCOMES.filter(([key]) => rows[key].gross !== null).map(([key, label]) => {
          const row = rows[key];
          const net = row.result === null ? 'result incomplete' : renderResult(row.result);
          const cap = row.maxEntry === null ? '' : row.maxEntry < 0 ? ' · no viable buy price at this target' : ` · max buy ${money(row.maxEntry)}`;
          return `${label} ${money(row.adjusted)} sale · ${net}${cap}`;
        }),
        ...(downside.result === null ? [] : [`PSA 8 ${money(downside.adjusted)} sale · ${renderResult(downside.result)}`]),
        ...(buying && values.target > 0 ? [`Profit target for buy limits ${money(values.target)}`] : []),
        ...(breakEven ? [breakEven] : []), ...(beatRaw ? [beatRaw] : [])
      ].join('\n');
      if (fromUser && hasResult) tool.dispatchEvent(new Event('bt:calculator-result', { bubbles: true }));
    }

    setInputs();
    render();
    form.addEventListener('submit', event => event.preventDefault());
    form.addEventListener('input', event => {
      const key = event.target.name;
      if (!Object.hasOwn(fields, key)) return;
      draft[key] = event.target.value;
      if (key === 'raw') draft.guide = null;
      render(true);
    });
    form.addEventListener('change', event => {
      if (event.target === cardSelect) draft.selected = cardSelect.value;
      else if (event.target === currency) {
        draft.currency = currency.value;
        if (draft.guide) {
          draft.guide = null;
          draft.raw = '';
          fields.raw.value = '';
        }
      } else if (event.target.name === 'mode') draft.mode = event.target.value;
      else return;
      render(true);
    });
    stress.addEventListener('change', () => { draft.fall = stress.value; render(true); });
    tool.addEventListener('click', async event => {
      const button = event.target.closest('[data-gc-action]');
      if (!button) return;
      switch (button.dataset.gcAction) {
        case 'example': {
          const yen = draft.currency === 'JPY' ? 100 : 1;
          const numbers = { entry: 45, grading: 30, raw: 55, nine: 80, ten: 140, fixed: 3, eight: 48 };
          draft = newDraft(draft.currency, draft.mode);
          for (const [key, value] of Object.entries(numbers)) draft[key] = String(value * yen);
          draft.fee = '10';
          draft.example = true;
          setInputs();
          render(true);
          break;
        }
        case 'clear':
          draft = newDraft(draft.currency, draft.mode);
          setInputs();
          render();
          break;
        case 'use-guide': {
          const card = guides.get(cardSelect.value);
          if (!card || (card.quotes.Raw.currency !== draft.currency && hasEnteredPrices())) return;
          draft.currency = card.quotes.Raw.currency;
          currency.value = draft.currency;
          const digits = draft.currency === 'JPY' ? 0 : 2;
          draft.raw = card.quotes.Raw.price.toFixed(digits);
          draft.guide = cardSelect.value;
          fields.raw.value = draft.raw;
          render(true);
          break;
        }
        case 'results':
          resultPanel.focus({ preventScroll: true });
          resultPanel.scrollIntoView({ block: 'start' });
          break;
        case 'copy':
          try {
            await navigator.clipboard.writeText(lastCalculation);
            find('[data-copy-status]').textContent = 'Calculation copied.';
          } catch {
            find('[data-copy-status]').textContent = 'Clipboard unavailable in this browser.';
          }
          break;
      }
    });
  }

  return { page, mount, calculate, parseAmount };
});
