/* An artwork viewer shared by both public indices. Catalogue scans stay unchanged. */
(()=>{
  'use strict';
  const dialog=document.createElement('dialog');
  dialog.id='artwork-dialog';
  dialog.setAttribute('aria-labelledby','artwork-title');
  dialog.innerHTML='<header class="artwork-toolbar"><div><span>THE ARTWORK</span><h2 id="artwork-title"></h2></div><div><button type="button" data-art-zoom aria-pressed="false">Original size</button><button type="button" data-art-close aria-label="Close artwork">Close ×</button></div></header><div class="artwork-stage"><img alt=""></div><p class="artwork-caption">Catalogue reference · original scan resolution</p>';
  document.body.append(dialog);
  const img=dialog.querySelector('img'),stage=dialog.querySelector('.artwork-stage'),zoom=dialog.querySelector('[data-art-zoom]');
  let opener=null;
  function fit(){stage.classList.remove('original-size');zoom.setAttribute('aria-pressed','false');zoom.textContent='Original size';stage.scrollTop=stage.scrollLeft=0;}
  document.addEventListener('click',e=>{
    const button=e.target.closest('.artwork-open');
    if(!button)return;
    const source=button.querySelector('img');
    if(!source||source.hidden)return;
    opener=button;img.src=source.currentSrc||source.src;img.alt=source.alt;
    dialog.querySelector('#artwork-title').textContent=document.querySelector('#dialog-title')?.textContent||'Card artwork';
    fit();dialog.showModal();
  });
  dialog.addEventListener('click',e=>{
    if(e.target.closest('[data-art-close]')){dialog.close();return;}
    if(e.target.closest('[data-art-zoom]')){
      const original=stage.classList.toggle('original-size');
      zoom.setAttribute('aria-pressed',String(original));zoom.textContent=original?'Fit to screen':'Original size';
    }
  });
  dialog.addEventListener('close',()=>{fit();opener?.focus();});
})();
