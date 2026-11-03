/* Pure calculations shared by the public page and its verification tests. */
(function (host) {
  'use strict';
  const positive = n => typeof n === 'number' && Number.isFinite(n) && n > 0;
  const exclusion=(data,id,date)=>data.history.exclusions?.find(x=>x.cardId===Number(id)&&x.date===date);
  const price = (data, id, date) => exclusion(data,id,date)?null:(data.history.prices[id]?.[data.history.dates.indexOf(date)] ?? null);
  function cohort(data, mode) {
    const dates = data.history.dates;
    const latest = dates.at(-1);
    const ids = data.history.cohorts?.[mode]?.members || data.cards.filter(c => mode === 'january'
      ? c.releaseDate <= dates[0] && positive(price(data,c.id,dates[0]))
      : c.quotes.Raw?.currency === 'USD' && positive(price(data,c.id,latest)))
      .map(c => c.id);
    const baseIndex = dates.findIndex(d => ids.length && ids.every(id => positive(price(data, id, d))));
    if (baseIndex < 0) return { ids, baseDate: null, points: [] };
    const baseDate = dates[baseIndex];
    const bases = Object.fromEntries(ids.map(id => [id, price(data, id, baseDate)]));
    const points = dates.slice(baseIndex).map(date => {
      const usable = ids.filter(id => positive(price(data, id, date)));
      return { date, count: usable.length, value: usable.length === ids.length
        ? 100 * ids.reduce((s,id) => s + price(data,id,date)/bases[id],0)/ids.length : null };
    });
    return { ids, baseDate, points };
  }
  function periodStart(end, period) {
    const d = new Date(end + 'T00:00:00Z');
    if (period === 'YTD') return end.slice(0,4) + '-01-01';
    if (period === 'All') return '0000-01-01';
    const days = { '7D':7, '1M':30, '3M':90 }[period] || 0;
    d.setUTCDate(d.getUTCDate()-days); return d.toISOString().slice(0,10);
  }
  function windowed(points, period) {
    if (!points.length) return [];
    const start = periodStart(points.at(-1).date, period);
    return points.filter(p => p.date >= start);
  }
  function change(a,b) { return positive(a)&&positive(b) ? (b/a-1)*100 : null; }
  function observedChange(first,last) { return first && last && first.date !== last.date ? change(first.value,last.value) : null; }
  function attribution(data, series, points) {
    const first=points.find(p=>positive(p.value)), last=[...points].reverse().find(p=>positive(p.value));
    if (!first || !last || first.date === last.date) return [];
    const denom=series.ids.reduce((s,id)=>s+price(data,id,first.date)/price(data,id,series.baseDate),0);
    return series.ids.map(id => {
      const start=price(data,id,first.date), end=price(data,id,last.date), base=price(data,id,series.baseDate);
      return { id, return:change(start,end), contribution:100*(end-start)/base/denom,
        weight:100*(end/base)/(series.ids.reduce((s,j)=>s+price(data,j,last.date)/price(data,j,series.baseDate),0)) };
    });
  }
  function historyFor(data,card) {
    return data.history.dates.map((date,i)=>({date,value:price(data,card.id,date),reportedValue:data.history.prices[card.id]?.[i]??null,excludedReason:exclusion(data,card.id,date)?.reason}))
      .filter(p=>p.date>=card.releaseDate);
  }
  function paths(points,x,y) {
    let pen=false; return points.map(p=>{if(!positive(p.value)){pen=false;return '';}
      const command=pen?'L':'M';pen=true;return command+x(p).toFixed(2)+' '+y(p.value).toFixed(2);}).join(' ');
  }
  const api={positive,price,cohort,periodStart,windowed,change,observedChange,attribution,historyFor,paths};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else host.BTMarket=api;
})(typeof window!=='undefined'?window:this);
