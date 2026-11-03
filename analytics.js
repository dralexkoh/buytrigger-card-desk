/* Public publication analytics only. No private portfolio or stock CRM data. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else if (root && root.document) api.boot(root);
})(typeof window === 'undefined' ? null : window, function () {
  'use strict';
  const PREFERENCE_KEY = 'buytrigger.cards.analytics.preference.v1';
  const EXCLUSION_KEY = 'buytrigger.cards.analytics.exclude.v1';
  const CONSENT_DAYS = 180;
  const COLLECTOR = 'https://brzawmbpwkdundruicca.supabase.co/functions/v1/cards-traffic-ingest';
  const PAGES = Object.freeze({home:'Home',desk:'Card Desk',journal:'Journal',targets:'Grading calculator',japan:'Japan Desk',method:'Sources and methods',funding:'Funding',privacy:'Privacy'});
  const SOURCES = Object.freeze({
    'google.com':'google', 'www.google.com':'google', 'www.google.co.uk':'google',
    'bing.com':'bing', 'www.bing.com':'bing', 'duckduckgo.com':'duckduckgo',
    'x.com':'x', 'www.x.com':'x', 't.co':'x', 'threads.net':'threads',
    'www.threads.net':'threads', 'threads.com':'threads', 'www.threads.com':'threads',
    'instagram.com':'instagram', 'www.instagram.com':'instagram', 'l.instagram.com':'instagram',
    'facebook.com':'facebook', 'www.facebook.com':'facebook', 'l.facebook.com':'facebook',
    'reddit.com':'reddit', 'www.reddit.com':'reddit', 'youtube.com':'youtube', 'www.youtube.com':'youtube'
  });
  const safeSlug = value => typeof value === 'string' && /^[a-z0-9][a-z0-9-]{0,99}$/.test(value);
  const listed = (items, value) => Array.isArray(items) && items.includes(value);
  function storageFor(win,kind) { try { return win[kind]; } catch (_) { return null; } }
  function read(storage, key) { try { return storage?.getItem(key); } catch (_) { return null; } }
  function write(storage, key, value) { try { storage?.setItem(key, value); } catch (_) { /* Memory preference remains effective. */ } }
  function permittedSite(config, href) {
    let url; try { url = new URL(href); } catch (_) { return null; }
    if (url.protocol !== 'https:' || !Array.isArray(config?.origins)) return null;
    return config.origins.find(site => site.origin === url.origin && typeof site.basePath === 'string' && /^\/(?:[a-z0-9-]+\/)*$/.test(site.basePath) && url.pathname.startsWith(site.basePath)) || null;
  }
  function validConfig(config, href) {
    return Boolean(config?.schemaVersion === 1 && config.enabled === true && config.provider === 'buytrigger-crm' &&
      config.privacyReviewed === true && config.collectorEndpoint === COLLECTOR &&
      /^\d{4}-\d{2}-\d{2}-v\d+$/.test(config.consentVersion || '') && permittedSite(config, href));
  }
  function catalogue(win) {
    const articles = (win.BT_EDITORIAL?.articles || []).filter(a => safeSlug(a.slug));
    return {articles, modern:win.MODERN_PREVIEW_DATA?.cards || [], top50:win.BT_TOP50?.cards || []};
  }
  function resolveRoute(href, config, data, bodyRoute = '') {
    const site = permittedSite(config, href); if (!site) return null;
    const url = new URL(href), path = url.pathname.slice(site.basePath.length);
    if (path === 'tcg-modern-index.html') return {id:'modern', url:'/tcg-modern-index', title:'TCG Modern Index', index:'modern'};
    if (path === 'top-50.html') return {id:'top50', url:'/top-50', title:'Top 50', index:'top50'};
    const storyPath = /^stories\/([a-z0-9-]+)\/(?:index\.html)?$/.exec(path);
    if (path !== '' && path !== 'index.html' && !storyPath) return null;
    const hash = url.hash.slice(1);
    // These pages render hashes before body.data-route; mirror that rule.
    const requested = hash || bodyRoute || (storyPath ? 'read/' + storyPath[1] : 'home');
    const parts = requested.split('/');
    if (parts[0] === 'top50') return null; // Renderer redirects; destination owns the view.
    if (parts[0] === 'read' || parts[0] === 'about') {
      const slug = parts[0] === 'about' ? 'welcome' : parts[1];
      const article = data.articles.find(a => a.slug === slug);
      return article ? {id:'article:' + slug, url:'/stories/' + slug + '/', title:'Story: ' + slug, article:slug} : {id:'story-not-found',url:'/story-not-found',title:'Story not found'};
    }
    const route = Object.hasOwn(PAGES, parts[0]) ? parts[0] : 'home';
    return {id:route, url:route === 'home' ? '/' : '/' + route, title:PAGES[route]};
  }
  function campaign(href, config, data) {
    const params = new URL(href).searchParams;
    const source = params.get('utm_source'), medium = params.get('utm_medium'), name = params.get('utm_campaign'), content = params.get('utm_content');
    if (!listed(config.campaignSources, source) || !listed(config.campaignMediums, medium) || !listed(config.campaigns, name)) return '';
    const clean = new URLSearchParams({utm_source:source,utm_medium:medium,utm_campaign:name});
    if (listed(config.campaignContent, content) || data.articles.some(a => a.slug === content)) clean.set('utm_content', content);
    return '?' + clean.toString();
  }
  function referrer(value, ownOrigin) {
    try {
      const url = new URL(value);
      if (url.origin === ownOrigin || !SOURCES[url.hostname]) return '';
      return 'https://' + url.hostname + '/';
    } catch (_) { return ''; }
  }
  function taggedDestination(href, currentHref, config, data) {
    let destination;
    try { destination = new URL(href,currentHref); } catch (_) { return href; }
    if (!resolveRoute(destination.href,config,data)) return destination.href;
    const current = new URL(currentHref);
    const tags = new URLSearchParams(campaign(currentHref,config,data).slice(1));
    if (!campaign(destination.href,config,data)) for (const [key,value] of tags) destination.searchParams.set(key,value);
    // Controlled QA journeys stay labelled across public pages; never tag outbound/private links.
    if (current.searchParams.get('bt_analytics') === 'qa') destination.searchParams.set('bt_analytics','qa');
    return destination.href;
  }
  function approvedSourceHosts(data) {
    const hosts = new Set();
    const add = value => { try { const u = new URL(value); if (u.protocol === 'https:' && /^[a-z0-9.-]+$/.test(u.hostname)) hosts.add(u.hostname); } catch (_) {} };
    data.articles.forEach(a => (a.sources || []).forEach(s => add(s.url)));
    [...data.modern, ...data.top50].forEach(c => { add(c.imageSource); add(c.quotes?.Raw?.source); add(c.sources?.Raw); });
    ['tcgcsv.com','www.tcgcsv.com','api.tcgdex.net','tcgdex.net','www.psacard.com','press.pokemon.com','www.pokemon.com','pokemon.com','www.cgccards.com','www.cgccomics.com','www.ha.com','comics.ha.com','www.tcgplayer.com'].forEach(host => hosts.add(host));
    return hosts;
  }
  function sanitizeEvent(name, props, route, data, hosts) {
    if (!route || !props || typeof props !== 'object') return null;
    const clean = {};
    switch (name) {
      case 'index_open': if (!['modern','top50'].includes(props.index)) return null; clean.index = props.index; break;
      case 'card_research_open': {
        if (!['modern','top50'].includes(props.index)) return null;
        const card = data[props.index].find(c => String(c.id) === String(props.card));
        if (!card || !Number.isSafeInteger(Number(card.id)) || Number(card.id) < 1) return null;
        clean.index = props.index; clean.card = String(card.id); break;
      }
      case 'calculator_used': if (route.id !== 'targets') return null; break;
      case 'source_outbound': if (!hosts.has(props.source)) return null; clean.source = props.source; break;
      case 'share_open': case 'share_caption_copy': case 'article_engaged':
        if (!data.articles.some(a => a.slug === props.article)) return null;
        clean.article = props.article;
        if (name === 'share_caption_copy') { if (!['x','threads','instagram'].includes(props.platform)) return null; clean.platform = props.platform; }
        break;
      case 'cta_click':
        if (!['modern','top50','targets','journal','desk','japan','private_collection'].includes(props.destination)) return null;
        clean.destination = props.destination; break;
      default: return null;
    }
    return {name, data:clean};
  }
  function createController(win, config, transport) {
    const data = catalogue(win), hosts = approvedSourceHosts(data), site = permittedSite(config, win.location.href);
    const enabled = validConfig(config, win.location.href);
    let consent = 'unset', current = null, lastView = null, once = new Set(), sent = 0;
    const prefs = read(storageFor(win,'localStorage'), PREFERENCE_KEY);
    try {
      const p = JSON.parse(prefs);
      if (p?.version === config.consentVersion && p.expires > Date.now() && ['granted','denied'].includes(p.choice)) consent = p.choice;
    } catch (_) {}
    function excluded() {
      return new URL(win.location.href).searchParams.get('bt_analytics') === 'off' || read(storageFor(win,'localStorage'), EXCLUSION_KEY) === '1' ||
        win.navigator?.globalPrivacyControl === true || win.navigator?.doNotTrack === '1';
    }
    function allowed() { return enabled && consent === 'granted' && !excluded() && Boolean(permittedSite(config, win.location.href)); }
    function payload(event) {
      const utm = new URLSearchParams(campaign(win.location.href,config,data).slice(1));
      const width = win.innerWidth || 0;
      const result = {version:1,event_id:win.crypto.randomUUID(),event:event?.name || 'page_view',page:current.url,
        referrer_channel:SOURCES[new URL(referrer(win.document.referrer,site.origin) || site.origin).hostname] || 'direct_unknown',
        device:width && width < 700 ? 'phone' : width && width < 1100 && win.navigator.maxTouchPoints > 1 ? 'tablet' : 'desktop',
        qa:new URL(win.location.href).searchParams.get('bt_analytics') === 'qa'};
      ['utm_source','utm_medium','utm_campaign','utm_content'].forEach(key => { if (utm.has(key)) result[key] = utm.get(key); });
      if (event && Object.keys(event.data).length) result.props = event.data;
      return result;
    }
    function send(event) {
      if (!allowed() || !current) return false;
      transport(payload(event)); sent++; return true;
    }
    function track(name, props = {}, dedupeKey = '') {
      const event = sanitizeEvent(name, props, current, data, hosts);
      if (!event || (dedupeKey && once.has(dedupeKey))) return false;
      if (!send(event)) return false;
      if (dedupeKey) once.add(dedupeKey);
      return true;
    }
    function routeRendered() {
      const next = resolveRoute(win.location.href, config, data, win.document.body?.dataset?.route);
      if (!next) { current = null; return false; }
      if (current?.id !== next.id) once = new Set();
      current = next;
      if (!allowed() || lastView === next.id) return false;
      if (!send()) return false;
      lastView = next.id;
      if (next.index) track('index_open',{index:next.index},'index_open');
      return true;
    }
    function choose(choice) {
      if (!['granted','denied'].includes(choice)) return;
      consent = choice;
      write(storageFor(win,'localStorage'),PREFERENCE_KEY,JSON.stringify({version:config.consentVersion,choice,expires:Date.now() + CONSENT_DAYS * 86400000}));
      if (choice === 'denied') { lastView = null; once.clear(); }
    }
    return {enabled, allowed, excluded, routeRendered, track, choose,
      get route() { return current; }, get consent() { return consent; }, get sent() { return sent; },
      excludeThisBrowser(value) { write(storageFor(win,'localStorage'),EXCLUSION_KEY,value ? '1' : '0'); }
    };
  }
  function boot(win) {
    if (win.BTAnalytics) return;
    const doc = win.document, source = doc.currentScript?.src;
    if (!source) return;
    let config, controller, openDialog;
    const api = {routeRendered:() => controller?.routeRendered(),track:(name,props) => controller?.track(name,props),
      openPreferences:() => openDialog?.(), excludeThisBrowser:value => controller?.excludeThisBrowser(value),
      status:() => ({enabled:Boolean(controller?.enabled),consent:controller?.consent || 'unset',excluded:Boolean(controller?.excluded()),collectorConfigured:Boolean(controller?.enabled)})};
    win.BTAnalytics = api;
    function transmit(payload) {
      if (!controller.allowed()) return;
      // No auth cookies, tokens, external libraries, or full Referrer header.
      try { win.fetch(config.collectorEndpoint,{method:'POST',body:JSON.stringify(payload),keepalive:true,
        mode:'cors',credentials:'omit',referrerPolicy:'no-referrer',headers:{'content-type':'text/plain'}}).catch(() => {}); } catch (_) {}
    }
    function preferences() {
      let banner = null, bannerSpace = null;
      const style = doc.createElement('style');
      style.textContent = '.bt-analytics-dialog{max-width:34rem;width:calc(100% - 2rem);padding:1.5rem;border:2px solid #111;border-radius:12px;background:#fff;color:#111;font:16px/1.5 system-ui,sans-serif}.bt-analytics-dialog::backdrop{background:#0008}.bt-analytics-dialog h2{margin:0 0 .8rem;font-size:1.5rem}.bt-analytics-dialog p{margin:.7rem 0}.bt-analytics-actions{display:flex;flex-wrap:wrap;gap:.6rem;margin-top:1rem}.bt-analytics-dialog button,.bt-analytics-settings{font:inherit;padding:.65rem 1rem;border:2px solid #111;border-radius:6px;background:#fff;color:#111;cursor:pointer}.bt-analytics-dialog button:focus-visible,.bt-analytics-settings:focus-visible{outline:3px solid #B70000;outline-offset:3px}.bt-analytics-settings{font-size:.8rem;margin:.8rem}.bt-analytics-banner{position:fixed;z-index:500;left:12px;right:12px;bottom:max(12px,env(safe-area-inset-bottom));box-sizing:border-box;max-width:52rem;margin:0 auto;padding:10px 14px;border:1px solid #111;border-top:3px solid #B70000;border-radius:8px;background:#fff;color:#111;box-shadow:0 3px 18px #0002;font:14px/1.35 system-ui,sans-serif;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 16px;max-height:40svh;overflow:auto}.bt-analytics-banner p{margin:0;align-self:center}.bt-analytics-banner-choices{display:flex;gap:8px;grid-column:2;grid-row:1 / span 2}.bt-analytics-banner button{font:inherit;min-height:44px;padding:8px 16px;border:1px solid #111;border-radius:5px;background:#fff;color:#111;cursor:pointer}.bt-analytics-banner button:focus-visible,.bt-analytics-banner a:focus-visible{outline:3px solid #B70000;outline-offset:3px}.bt-analytics-banner-choices button{min-width:84px;flex:1}.bt-analytics-banner-links{display:flex;gap:16px;align-items:center;font-size:12px}.bt-analytics-banner-links a,.bt-analytics-banner-links button{color:#111;text-decoration:underline}.bt-analytics-banner-links button{min-height:0;padding:0;border:0;border-radius:0;background:none}.bt-analytics-banner-space{height:104px}@media(max-width:560px){.bt-analytics-banner{grid-template-columns:minmax(0,1fr);gap:6px;padding:10px 12px}.bt-analytics-banner-choices{grid-column:1;grid-row:auto}.bt-analytics-banner-links{justify-content:center}.bt-analytics-banner-space{height:164px}}';
      doc.head.append(style);
      const dialog = doc.createElement('dialog'); dialog.className = 'bt-analytics-dialog'; dialog.setAttribute('aria-labelledby','bt-analytics-title');
      const h = doc.createElement('h2'); h.id = 'bt-analytics-title'; h.textContent = 'Optional visitor statistics'; dialog.append(h);
      const p = doc.createElement('p'); p.textContent = 'May we count which public pages and tools readers use, and which approved campaigns bring visits? Our own BuyTrigger counter uses a daily changing visitor estimate from connection and browser information, without advertising cookies. We send no names, search text, calculator amounts or private collection data.'; dialog.append(p);
      const retention = doc.createElement('p'); retention.textContent = 'Detailed analytics older than 180 days are removed in a daily cleanup. Your choice is remembered on this browser for six months. You can change it at any time. Declining leaves all site features available.'; dialog.append(retention);
      const link = doc.createElement('a'); link.href = new URL('index.html#privacy',source).href; link.textContent = 'Privacy details'; link.addEventListener('click',() => dialog.close()); dialog.append(link);
      const status = doc.createElement('p'); status.setAttribute('aria-live','polite'); dialog.append(status);
      const actions = doc.createElement('div'); actions.className = 'bt-analytics-actions';
      function choose(choice) {
        controller.choose(choice);
        if (banner) { banner.remove(); banner = null; }
        if (bannerSpace) { bannerSpace.remove(); bannerSpace = null; }
        dialog.close();
        if (choice === 'granted') controller.routeRendered();
      }
      [['Decline statistics','denied'],['Allow statistics','granted']].forEach(([label,choice]) => {
        const button = doc.createElement('button'); button.type = 'button'; button.textContent = label;
        button.addEventListener('click',() => choose(choice));
        actions.append(button);
      });
      const close = doc.createElement('button'); close.type = 'button'; close.textContent = 'Close'; close.addEventListener('click',() => dialog.close()); actions.append(close); dialog.append(actions); doc.body.append(dialog);
      const settings = doc.createElement('button'); settings.type = 'button'; settings.className = 'bt-analytics-settings'; settings.textContent = 'Visitor statistics preferences';
      openDialog = () => { status.textContent = controller.excluded() ? 'Statistics are excluded for this browser or by its privacy preference.' : controller.consent === 'unset' ? 'No analytics is sent unless you allow it.' : controller.consent === 'granted' ? 'Current choice: allowed.' : 'Current choice: declined.'; if (!dialog.open) dialog.showModal(); };
      settings.addEventListener('click',openDialog); (doc.querySelector('footer') || doc.body).append(settings);
      if (controller.consent === 'unset' && !controller.excluded()) {
        banner = doc.createElement('section'); banner.className = 'bt-analytics-banner';
        banner.setAttribute('role','region'); banner.setAttribute('aria-label','Optional visitor statistics');
        const message = doc.createElement('p'); message.textContent = 'Optional visitor statistics. Nothing is sent until you allow.'; banner.append(message);
        const choices = doc.createElement('div'); choices.className = 'bt-analytics-banner-choices';
        [['Decline','denied'],['Allow','granted']].forEach(([label,choice]) => {
          const button = doc.createElement('button'); button.type = 'button'; button.textContent = label;
          button.setAttribute('aria-label',label + ' statistics'); button.addEventListener('click',() => choose(choice)); choices.append(button);
        });
        banner.append(choices);
        const links = doc.createElement('div'); links.className = 'bt-analytics-banner-links';
        const privacy = doc.createElement('a'); privacy.href = link.href; privacy.textContent = 'Privacy details'; links.append(privacy);
        const preferences = doc.createElement('button'); preferences.type = 'button'; preferences.textContent = 'Preferences'; preferences.addEventListener('click',openDialog); links.append(preferences); banner.append(links);
        // A normal-flow spacer lets the final footer/CTA scroll clear of the small fixed banner.
        // No focus move, modal opening, backdrop, inert state or page-scroll lock on first visit.
        bannerSpace = doc.createElement('div'); bannerSpace.className = 'bt-analytics-banner-space'; bannerSpace.setAttribute('aria-hidden','true');
        doc.body.append(bannerSpace,banner);
      }
    }
    function bindEvents() {
      win.addEventListener('bt:route-rendered',api.routeRendered);
      // Existing render listeners execute first. A duplicate explicit hook is deduplicated.
      win.addEventListener('hashchange',() => win.requestAnimationFrame(api.routeRendered));
      win.addEventListener('pageshow',api.routeRendered);
      doc.addEventListener('click',event => {
        const target = event.target?.closest ? event.target : event.target?.parentElement; if (!target) return;
        const card = target.closest('[data-card]');
        if (card && controller.route?.index && doc.querySelector('#card-dialog[open]')) controller.track('card_research_open',{index:controller.route.index,card:card.dataset.card});
        const share = target.closest('[data-share-story]');
        if (share && doc.querySelector('#share-dialog[open]')) { controller.track('share_open',{article:share.dataset.shareStory}); }
        const anchor = target.closest('a[href]'); if (!anchor) return;
        let url; try { url = new URL(anchor.href,win.location.href); } catch (_) { return; }
        if (url.protocol !== 'https:' && url.protocol !== 'http:') return;
        if (url.hostname === 'cards.alexkoh.me') controller.track('cta_click',{destination:'private_collection'});
        else if (url.origin !== win.location.origin) controller.track('source_outbound',{source:url.hostname});
        else {
          const destination = resolveRoute(url.href,config,catalogue(win));
          if (destination) {
            anchor.href = taggedDestination(url.href,win.location.href,config,catalogue(win));
            controller.track('cta_click',{destination:destination.id});
          }
        }
      });
      doc.addEventListener('input',event => {
        if (!event.target?.matches?.('.calculator input') || !controller.route || controller.route.id !== 'targets') return;
        const fields = Array.from(doc.querySelectorAll('.calculator input[type="number"]'));
        const valid = fields.length > 0 && fields.every(input => input.value.trim() !== '' && Number.isFinite(Number(input.value)) && Number(input.value) >= 0 && Number(input.value) <= 100000) && Number(doc.querySelector('#calc-selling')?.value) <= 100;
        if (valid) controller.track('calculator_used',{},'calculator_used');
      });
      let activeId = '', visibleMs = 0, lastTick = Date.now(); const engaged = new Set();
      if (controller.consent === 'granted') { try { JSON.parse(read(storageFor(win,'sessionStorage'),'buytrigger.cards.analytics.engaged.v1') || '[]').filter(safeSlug).forEach(id => engaged.add(id)); } catch (_) {} }
      win.setInterval(() => {
        const now = Date.now(), delta = Math.min(2000,Math.max(0,now-lastTick)); lastTick = now;
        if (!controller.allowed()) { visibleMs = 0; return; }
        const id = controller.route?.article;
        if (id !== activeId) { activeId = id; visibleMs = 0; }
        if (!id || engaged.has(id) || doc.visibilityState !== 'visible' || !doc.hasFocus()) return;
        const body = doc.querySelector('.article-body'); if (!body) return;
        visibleMs += delta;
        const rect = body.getBoundingClientRect(), depth = (win.innerHeight - rect.top) / Math.max(1,rect.height);
        if (visibleMs >= 45000 && depth >= .75 && controller.track('article_engaged',{article:id})) {
          engaged.add(id); write(storageFor(win,'sessionStorage'),'buytrigger.cards.analytics.engaged.v1',JSON.stringify(Array.from(engaged)));
        }
      },1000);
    }
    const configURL = new URL('analytics-config.json',source);
    if (configURL.origin !== win.location.origin) return;
    win.fetch(configURL.href,{credentials:'omit',cache:'no-cache',referrerPolicy:'no-referrer'}).then(r => { if (!r.ok) throw new Error('No analytics configuration'); return r.json(); }).then(value => {
      config = value; controller = createController(win,config,transmit);
      if (!controller.enabled) return;
      preferences(); bindEvents();
      controller.routeRendered();
    }).catch(() => { /* No configuration means no analytics, no fallback provider. */ });
    return api;
  }
  return {boot,validConfig,permittedSite,resolveRoute,campaign,taggedDestination,referrer,sanitizeEvent,approvedSourceHosts,createController,PREFERENCE_KEY,EXCLUSION_KEY};
});
