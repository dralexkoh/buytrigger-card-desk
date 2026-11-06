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

const wireRenderer=source.slice(source.indexOf('function wire(w)'),source.indexOf('function homeWire('));
const wire=vm.runInNewContext(esc+'\n'+wireRenderer+'\nwire',{URL});

test('Newsroom briefs omit source lines and external reading links while retaining attribution',()=>{
 const html=wire({
  id:'photo-brief',category:'Auctions',date:'2026-11-05',displayDate:'5 Nov',kind:'Auction',
  title:'Test brief',summary:'Reported by the original publisher.',
  url:'https://publisher.example/lot',sourceLabel:'Publisher',
  ctaUrl:'https://catalogue.example/card',ctaLabel:'See the card',
  image:'assets/card.webp',imageAlt:'Exact auction card',imageCredit:'Photo: Original publisher.',
  imageSourceUrl:'https://publisher.example/photo',
  author:{type:'named_ai_correspondent',name:'Elliot Reed'},
 });
 assert.doesNotMatch(html,/Source:|Image source|publisher\.example|catalogue\.example|See the card/);
 assert.match(html,/Elliot Reed/);
 assert.match(html,/Photo: Original publisher\./);
});

test('Newsroom briefs keep internal reading links and a playable footage preview',()=>{
 const html=wire({
  id:'video-brief',category:'News',date:'2026-11-05',displayDate:'5 Nov',visual:'linked-video',
  ctaUrl:'#journal',ctaLabel:'More collecting stories',
  image:'https://i.ytimg.com/vi/uIMCHihZxdw/mqdefault.jpg',imageAlt:'Surveillance preview',
  imageSourceUrl:'https://www.youtube.com/watch?v=uIMCHihZxdw',imageCredit:'Surveillance footage.',
 });
 assert.match(html,/href="#journal"/);
 assert.equal((html.match(/href="https:\/\/www\.youtube\.com/g)||[]).length,1);
 assert.match(html,/aria-label="Watch footage"/);
});

test('release roundups keep readable paragraphs and only embed the reviewed YouTube format',()=>{
 const brief={id:'launch',date:'2026-11-06',displayDate:'6 Nov',title:'The launch',summary:'First <scene>.\n\nSecond scene.',
  visual:'editorial-ink',visualMark:'youtube-player',image:'assets/hunt.webp',url:'https://www.youtube.com/watch?v=MF1-zIXcKIQ'};
 const html=wire(brief);
 assert.match(html,/<p>First &lt;scene&gt;\.<\/p><p>Second scene\.<\/p>/);
 assert.match(html,/src="https:\/\/www\.youtube\.com\/embed\/MF1-zIXcKIQ"/);
 assert.doesNotMatch(wire({...brief,url:'https://www.youtube.com.example/watch?v=MF1-zIXcKIQ'}),/<iframe/);
 assert.doesNotMatch(wire({...brief,visualMark:null}),/<iframe/);
});
