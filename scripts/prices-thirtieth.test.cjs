const test = require('node:test');
const assert = require('node:assert/strict');
const {compareNumber, compareRows} = require('../prices-table.js');

test('card numbers sort by the numeric parts, then the stored text', () => {
  const numbers = ['10/128', '2/128', '001/128', '107', 'B/RGB', '4/102', 'R/RGB'];
  numbers.sort(compareNumber);
  assert.deepEqual(numbers, ['001/128', '2/128', '4/102', '10/128', '107', 'B/RGB', 'R/RGB']);
});

test('default price order is high to low, with missing prices last', () => {
  const rows = [
    {name: 'Low', number: '002/128', price: 0.2, id: '2'},
    {name: 'Missing', number: '003/128', price: null, id: '3'},
    {name: 'High', number: '001/128', price: 10, id: '1'},
  ];
  rows.sort((a, b) => compareRows(a, b, 'price-desc'));
  assert.deepEqual(rows.map(row => row.name), ['High', 'Low', 'Missing']);
  rows.sort((a, b) => compareRows(a, b, 'price-asc'));
  assert.deepEqual(rows.map(row => row.name), ['Low', 'High', 'Missing']);
});

test('name and number sorts can reverse', () => {
  const rows = [
    {name: 'Volbeat', number: '10/128', price: 1, id: '1'},
    {name: 'Alolan Exeggutor', number: '2/128', price: 1, id: '2'},
  ];
  const byName = [...rows].sort((a, b) => compareRows(a, b, 'name-asc')).map(row => row.name);
  const byNumber = [...rows].sort((a, b) => compareRows(a, b, 'number-asc')).map(row => row.number);
  assert.deepEqual(byName, ['Alolan Exeggutor', 'Volbeat']);
  assert.deepEqual(byNumber, ['2/128', '10/128']);
});

test('set sort is alphabetical and reversible', () => {
  const rows = [
    {name: 'Lugia', number: '134/135', set: 'Plasma Storm', price: 1, id: '1'},
    {name: 'Gardevoir', number: '109/108', set: 'Dark Explorers', price: 9, id: '2'},
  ];
  const ascending = [...rows].sort((a, b) => compareRows(a, b, 'set-asc')).map(row => row.set);
  const descending = [...rows].sort((a, b) => compareRows(a, b, 'set-desc')).map(row => row.set);
  assert.deepEqual(ascending, ['Dark Explorers', 'Plasma Storm']);
  assert.deepEqual(descending, ['Plasma Storm', 'Dark Explorers']);
});
