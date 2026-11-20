const fs = require('node:fs');
const path = require('node:path');
const {ebayCardBlock, ebayPageNote} = require('../commerce.js');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'commerce.json'), 'utf8'));
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const options = input.options || {};
const rows = (input.cards || []).map(card => ({
  id: card.id,
  html: ebayCardBlock({name: card.name, number: card.number, set: card.set}, config, options) || '',
}));
process.stdout.write(JSON.stringify({rows, pageNote: ebayPageNote()}));
