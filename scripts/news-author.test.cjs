const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../site.js'),'utf8');
const esc=source.match(/^const esc=.+;$/m)?.[0];
const render=source.match(/^function newsAuthor\(w\)\{.+\}$/m)?.[0];
assert.ok(esc&&render,'News byline renderer must remain testable');
const newsAuthor=vm.runInNewContext(esc+'\n'+render+'\nnewsAuthor');
test('recorded correspondent names use the owner-approved plain public byline',()=>{
 for(const name of ['Elliot Reed','Hana Mori','Theo Brooks','Zara Chen']){
  const html=newsAuthor({author:{type:'named_ai_correspondent',name}});
  assert.ok(html.includes(name));
  assert.doesNotMatch(html,/AI correspondent/);
 }
});
test('unsigned news does not acquire a fictional author and names remain escaped',()=>{
 assert.match(newsAuthor({}),/BuyTrigger\.Cards.*Newsroom/);
 assert.doesNotMatch(newsAuthor({}),/AI correspondent/);
 const html=newsAuthor({author:{type:'named_ai_correspondent',name:'<script>bad</script>'}});
 assert.doesNotMatch(html,/<script>/);
 assert.match(html,/&lt;script&gt;/);
});
