/* Public collector receipt. Source dates and check dates describe different events. */
(()=>{
 'use strict';
 const mount=document.querySelector('[data-refresh-status]');
 if(!mount)return;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const date=(value,withTime=false)=>{
  if(!value)return 'Unavailable';
  const stamp=new Date(/^\d{4}-\d{2}-\d{2}$/.test(value)?value+'T12:00:00Z':value);
  if(!Number.isFinite(stamp.getTime()))return 'Unavailable';
  return stamp.toLocaleString('en-GB',{day:'numeric',month:'short',year:'numeric',...(withTime?{hour:'2-digit',minute:'2-digit'}:{}),timeZone:'UTC'})+(withTime?' UTC':'');
 };
 const count=value=>Number.isInteger(value)&&value>=0?value:null;
 const coverage=(name,value)=>{
  if(!value)return name+' coverage unavailable';
  const priced=count(value.priced),total=count(value.total);
  const currencies=name==='Modern'&&count(value.usd)!==null?` · ${value.usd} USD${count(value.eur)?' + '+value.eur+' EUR':''}`:'';
  return name+' '+(priced===null?'—':priced)+'/'+(total===null?'—':total)+' priced'+currencies;
 };
 function show(receipt){
  if(receipt.schemaVersion!==1||!['current','partial','delayed','failed'].includes(receipt.status))throw new Error('Unsupported receipt');
  const checked=Date.parse(receipt.checkedAt),overdue=Number.isFinite(checked)&&Date.now()-checked>36*60*60*1000;
  const state=overdue&&receipt.status==='current'?'delayed':receipt.status;
  const label={current:'Latest source checked',partial:'Partial source coverage',delayed:overdue?'Source check overdue':'Source update delayed',failed:'Latest source check failed'}[state];
  const schedule=receipt.automaticRefreshActive===true?'Daily checks active':receipt.schedulerEnabled===true?'Scheduled · first automatic check pending':'Manual source checks';
  const gaps=count(receipt.missingCount),held=count(receipt.heldCount),changed=count(receipt.changedCount);
  const detail=[changed===null?'':changed+' changed prices in this check',gaps?gaps+' missing quotes':'',held?held+' held observations':'',receipt.lastError?'Last check needs attention; existing dated observations are retained.':'',receipt.status==='failed'&&receipt.lastSuccessfulCheck?'Last successful check '+date(receipt.lastSuccessfulCheck,true):''].filter(Boolean).join(' · ');
  mount.dataset.state=state;
  mount.innerHTML=`<span class="refresh-state">${esc(label)}</span><span><strong>Source</strong> ${esc(date(receipt.sourceDate))}</span><span><strong>Checked</strong> ${esc(date(receipt.checkedAt,true))}</span><span class="refresh-coverage">${esc(coverage('Modern',receipt.coverage?.modern))} · ${esc(coverage('Top 50',receipt.coverage?.top50))}</span><span>${esc(schedule)}</span><a href="refresh-status.json">Update receipt ↗</a><p class="refresh-detail">${esc(detail)}</p>`;
  document.querySelectorAll('[data-refresh-schedule]').forEach(el=>el.textContent=schedule);
  window.BT_REFRESH_STATUS=receipt;
 }
 fetch(new URL('refresh-status.json',document.baseURI),{cache:'no-store'})
  .then(response=>{if(!response.ok)throw new Error('Receipt unavailable');return response.json();})
  .then(show)
  .catch(()=>{
   mount.dataset.state='failed';
   mount.innerHTML='<span class="refresh-state">Update receipt unavailable</span><span>Each card retains its dated source. Reload to check for a newer receipt.</span>';
   document.querySelectorAll('[data-refresh-schedule]').forEach(el=>el.textContent='Update receipt unavailable');
  });
})();
