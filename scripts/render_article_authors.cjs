const fs=require('node:fs');
const authors=require('../article-authors.js');
const articles=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(Object.fromEntries(articles.map(a=>[a.slug,{byline:authors.byline(a,true),profile:authors.profile(a)}]))));
