const { test } = require('node:test');
const assert = require('node:assert/strict');
const { calculate, parseAmount } = require('../grading-calculator.js');

const initial = {
  mode: 'buy', unit: 100, entry: 1900, grading: 4999, fee: 1500,
  fixed: 0, fall: 0, target: 0, raw: 1800, eight: null, nine: 5000, ten: 10000
};
const run = changes => calculate({ ...initial, ...changes });
const profits = result => ['raw', 'nine', 'ten'].map(key => result.rows[key].result);

test('delivered entry, sale costs and grading cost apply to the correct outcomes', () => {
  assert.deepEqual(profits(run()), [-370, -2649, 1601]);
  assert.deepEqual(profits(run({ fixed: 500 })), [-870, -3149, 1101]);
  assert.deepEqual(profits(run({ fall: 1000 })), [-523, -3074, 751]);
});

test('missing grades and grading cost leave independent Raw and graded results usable', () => {
  assert.deepEqual(profits(run({ nine: null })), [-370, null, 1601]);
  assert.deepEqual(profits(run({ grading: null })), [-370, null, null]);
  assert.equal(run({ entry: null, target: 1000 }).rows.ten.maxEntry, 2501);
  assert.equal(run({ fixed: null }).rows.raw.result, null);
  assert.equal(run({ raw: 0 }).rows.raw.result, -1900);
});

test('already owned compares cash from today and includes the optional lower grade', () => {
  const result = run({ mode: 'own', entry: null, grading: 3000, fee: 1000, fixed: 300, raw: 5500, eight: 4800, nine: 8000, ten: 14000 });
  assert.deepEqual(profits(result), [4650, 3900, 9300]);
  assert.equal(result.rows.eight.result, 1020);
  assert.equal(result.rows.eight.vsRaw, -3630);
  assert.equal(result.rows.nine.vsRaw, -750);
  assert.equal(result.rows.ten.maxEntry, null);
});

test('break-even thresholds are the first payable price with the same fee rounding and stress', () => {
  const values = { fall: 1000, fixed: 300 };
  const result = run(values);
  assert.ok(run({ ...values, ten: result.breakEven }).rows.ten.result >= 0);
  assert.ok(run({ ...values, ten: result.breakEven - 1 }).rows.ten.result < 0);
  assert.ok(run({ ...values, ten: result.beatRaw }).rows.ten.vsRaw > 0);
  assert.ok(run({ ...values, ten: result.beatRaw - 1 }).rows.ten.vsRaw <= 0);
  assert.equal(run({ fee: 10000 }).breakEven, null);
  assert.equal(run({ fee: 10000 }).beatRaw, null);
});

test('blank, explicit zero, invalid amounts and whole-yen inputs remain distinct', () => {
  assert.deepEqual(parseAmount(''), { amount: null, invalid: false });
  assert.deepEqual(parseAmount('0'), { amount: 0, invalid: false });
  assert.equal(parseAmount('-5').invalid, true);
  assert.equal(parseAmount('101', 100, 100).invalid, true);
  assert.equal(parseAmount('12.99').amount, 1299);
  assert.equal(parseAmount('12.99', 1).invalid, true);
  assert.equal(parseAmount('3900', 1).amount, 3900);
});
