const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

test('route notification follows successful rendering and skips redirect-only routes',()=>{
  const src=fs.readFileSync('site.js','utf8');
  const code=src.slice(src.indexOf('function render(){'),src.indexOf("document.addEventListener('click'"));
  const nodes={'#main':{innerHTML:''},'#site-nav':{classList:{remove(){}}},'.mobile-menu':{setAttribute(){}}};
  const rendered=[],redirects=[],document={body:{dataset:{}},title:''},location={hash:'#home',replace:url=>redirects.push(url)};
  const window={scrollTo(){},BTAnalytics:{routeRendered(){rendered.push({html:nodes['#main'].innerHTML,title:document.title});}}};
  const context={window,document,location,$:s=>nodes[s],$$:()=>[],imageErrors(){},calculate(){},article:()=>null,read:()=>'',home:()=>'<h1>Rendered home</h1>'};
  for(const name of ['desk','journal','targets','japan','top50','method','funding','privacy'])context[name]=()=>name;
  vm.runInNewContext(code+';render();',context);
  assert.equal(rendered.length,1);assert.match(rendered[0].html,/Rendered home/);assert.match(rendered[0].title,/BuyTrigger.Cards/);
  location.hash='#top50';vm.runInNewContext('render();',context);assert.equal(rendered.length,1);assert.deepEqual(redirects,['top-50.html']);
});

function sharing(failClipboard=false,failAnalytics=false){
  const listeners={},sent=[],writes=[];
  const platforms=['x','threads','instagram'].map(platform=>({dataset:{sharePlatform:platform},setAttribute(){}}));
  const nodes={'#share-caption':{value:'',focus(){},select(){}},'#share-status':{textContent:''},'#share-caption-label':{},'#share-story-title':{},'#share-dialog':{querySelectorAll:()=>platforms,showModal(){this.open=true;},close(){this.open=false;}}};
  const document={querySelector:s=>nodes[s],addEventListener:(event,fn)=>listeners[event]=fn};
  const window={BT_EDITORIAL:{articles:[{slug:'welcome',title:'A public story',summary:'Public summary'}]},BTAnalytics:{track:(name,props)=>{if(failAnalytics)throw new Error('optional counter unavailable');sent.push({name,props});}}};
  const navigator={clipboard:{writeText:async text=>{if(failClipboard)throw new Error('clipboard refused');writes.push(text);}}};
  vm.runInNewContext(fs.readFileSync('social.js','utf8'),{document,window,navigator});
  const click=async(selector,node={})=>listeners.click({target:{closest:s=>s===selector?node:null}});
  return {nodes,sent,writes,click};
}
test('share-copy event follows clipboard success with exact story/platform, never caption',async()=>{
  const s=sharing();await s.click('[data-share-story]',{dataset:{shareStory:'welcome'}});await s.click('[data-share-platform]',{dataset:{sharePlatform:'threads'}});
  await s.click('#copy-caption');assert.equal(s.writes.length,1);assert.equal(s.sent.length,1);
  assert.equal(s.sent[0].name,'share_caption_copy');assert.equal(s.sent[0].props.article,'welcome');assert.equal(s.sent[0].props.platform,'threads');
  assert.deepEqual(Object.keys(s.sent[0].props).sort(),['article','platform']);
});
test('failed clipboard writes emit no success event; counter failure cannot misreport copy outcome',async()=>{
  const failed=sharing(true);await failed.click('[data-share-story]',{dataset:{shareStory:'welcome'}});await failed.click('#copy-caption');assert.equal(failed.sent.length,0);assert.match(failed.nodes['#share-status'].textContent,/Select and copy/);
  const optional=sharing(false,true);await optional.click('[data-share-story]',{dataset:{shareStory:'welcome'}});await optional.click('#copy-caption');assert.equal(optional.writes.length,1);assert.equal(optional.nodes['#share-status'].textContent,'Caption copied. Nothing has been posted.');
});
