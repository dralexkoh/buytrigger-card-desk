(()=>{'use strict';
const dialog=document.querySelector('#share-dialog'),caption=document.querySelector('#share-caption'),status=document.querySelector('#share-status');
let activeArticle=null,activePlatform='x';
function selectPlatform(platform){
 if(!activeArticle)return;
 activePlatform=platform;
 dialog.querySelectorAll('[data-share-platform]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.sharePlatform===platform)));
 const signature='BuyTrigger.Cards · Alex & Oscar',tags=platform==='instagram'?'\n\n#PokemonTCG #CardCollecting #BuyTriggerCards':'';
 caption.value=activeArticle.title+(platform==='x'?'':'\n\n'+activeArticle.summary)+'\n\n'+'https://buytrigger.cards/stories/'+activeArticle.slug+'/'+'\n\n'+signature+tags;
 document.querySelector('#share-caption-label').textContent=(platform==='instagram'?'Instagram caption':platform==='threads'?'Threads post':'X post')+' · draft';
 status.textContent='';
}
document.addEventListener('click',async e=>{
 const share=e.target.closest('[data-share-story]');
 if(share){activeArticle=window.BT_EDITORIAL.articles.find(a=>a.slug===share.dataset.shareStory);if(!activeArticle)return;document.querySelector('#share-story-title').textContent=activeArticle.title;selectPlatform('x');dialog.showModal();return;}
 const platform=e.target.closest('[data-share-platform]');if(platform){selectPlatform(platform.dataset.sharePlatform);return;}
 if(e.target.closest('.share-close')){dialog.close();return;}
 if(e.target.closest('#copy-caption')){try{await navigator.clipboard.writeText(caption.value);status.textContent='Caption copied. Nothing has been posted.';if(activeArticle){try{window.BTAnalytics?.track('share_caption_copy',{article:activeArticle.slug,platform:activePlatform});}catch{}}}catch{caption.focus();caption.select();status.textContent='Select and copy the caption above. Nothing has been posted.';}}
});
})();
