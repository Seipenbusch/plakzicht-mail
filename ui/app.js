'use strict';
/* Plakzicht Mail - interface. Praat met de server (app.py) via /api/; in het desktopvenster zijn er een paar extra's via pywebview. */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const FOLDER_NAMES = { inbox: 'Postvak IN', sent: 'Verzonden', archive: 'Archief', deleted: 'Verwijderde items' };
const STEPS = [['print', 'P', 'Printen'], ['lam', 'L', 'Lamineren'], ['plot', 'Pl', 'Plotten'], ['cut', 'S', 'Snijden/Stansen']];

const S = { st: null, view: null, filter: 'alle', search: '', mails: [], sel: null, mail: null, popout: false, layout: null };
const svg = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const ICON = {
  inbox: svg('<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>'),
  sent: svg('<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>'),
  archive: svg('<rect x="2" y="3" width="20" height="5" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/>'),
  pen: svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>'),
  collapse: svg('<path d="m11 17-5-5 5-5"/><path d="m18 17-5-5 5-5"/>'),
  expand: svg('<path d="m13 17 5-5-5-5"/><path d="m6 17 5-5-5-5"/>'),
  popout: svg('<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'),
  plus: svg('<path d="M12 5v14"/><path d="M5 12h14"/>'),
  reply: svg('<path d="M9 17 4 12l5-5"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/>'),
  replyAll: svg('<path d="m7 17-5-5 5-5"/><path d="m12 17-5-5 5-5"/><path d="M22 18v-2a4 4 0 0 0-4-4H7"/>'),
  forward: svg('<path d="m15 17 5-5-5-5"/><path d="M4 18v-2a4 4 0 0 1 4-4h12"/>'),
  trash: svg('<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M10 11v6"/><path d="M14 11v6"/>'),
  flag: svg('<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>'),
  tag: svg('<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8z"/><circle cx="7" cy="7" r="1.5"/>'),
  folder: svg('<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z"/><path d="m12 10 3 3-3 3"/><path d="M8 13h7"/>'),
  mail: svg('<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>'),
  mailOpen: svg('<path d="M21.2 8.4c.5.4.8 1 .8 1.6v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10c0-.6.3-1.2.8-1.6l8-6a2 2 0 0 1 2.4 0z"/><path d="m22 10-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 10"/>'),
  link: svg('<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>'),
  rules: svg('<path d="M3 6h11"/><path d="M3 12h7"/><path d="M3 18h11"/><path d="m16 15 3 3 3-3"/><path d="M19 6v12"/>'),
  bolt: svg('<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>'),
  check: svg('<path d="M20 6 9 17l-5-5"/>'),
  chev: svg('<path d="m9 18 6-6-6-6"/>'),
  panel: svg('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M15 3v18"/>'),
  clip: svg('<path d="m21.4 11.1-9.2 9.2a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5"/>'),
  msLogo: '<svg viewBox="0 0 21 21" aria-hidden="true" width="16" height="16"><rect x="1" y="1" width="9" height="9" fill="#f25022"/><rect x="11" y="1" width="9" height="9" fill="#7fba00"/><rect x="1" y="11" width="9" height="9" fill="#00a4ef"/><rect x="11" y="11" width="9" height="9" fill="#ffb900"/></svg>',
  download: svg('<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>'),
  hand: svg('<path d="M18 11V6a2 2 0 0 0-4 0v5"/><path d="M14 10V4a2 2 0 0 0-4 0v6"/><path d="M10 10.5V6a2 2 0 0 0-4 0v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>'),
  eye: svg('<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
  ban: svg('<circle cx="12" cy="12" r="9"/><path d="m5.7 5.7 12.6 12.6"/>'),
  chevDown: svg('<path d="m6 9 6 6 6-6"/>'),
  folderPlain: svg('<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z"/>'),
  refresh: svg('<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>'),
  bang: svg('<path d="M12 4v10"/><path d="M12 19h.01"/>'),
  bell: svg('<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>'),
  funnel: svg('<path d="M22 3H2l8 9.5V19l4 2v-8.5z"/>'),
  sort: svg('<path d="m3 16 4 4 4-4"/><path d="M7 20V4"/><path d="m21 8-4-4-4 4"/><path d="M17 4v16"/>'),
  columns: svg('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/>'),
  rows: svg('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>'),
  density: svg('<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>'),
  groups: svg('<path d="M3 5h18"/><path d="M7 9h14"/><path d="M7 13h14"/><path d="M3 17h18"/><path d="M7 21h14"/>'),
  sparkle: svg('<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>'),
  globe: svg('<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'),
  list: svg('<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>'),
  gear: svg('<circle cx="12" cy="12" r="3"/><path d="M12 2v3"/><path d="M12 19v3"/><path d="m4.9 4.9 2.1 2.1"/><path d="m17 17 2.1 2.1"/><path d="M2 12h3"/><path d="M19 12h3"/><path d="m4.9 19.1 2.1-2.1"/><path d="m17 7 2.1-2.1"/>'),
  info: svg('<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'),
  shield: svg('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M12 8v4"/><path d="M12 16h.01"/>'),
  search: svg('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'),
  book: svg('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><circle cx="12" cy="9" r="2.5"/><path d="M8.5 14c.8-1.5 2-2 3.5-2s2.7.5 3.5 2"/>'),
  speaker: svg('<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/>'),
  dots: svg('<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'),
  bellOff: svg('<path d="M8.7 3A6 6 0 0 1 18 8a21.3 21.3 0 0 0 .6 5"/><path d="M17 17H3s3-2 3-9a4.67 4.67 0 0 1 .3-1.7"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/><path d="m2 2 20 20"/>'),
  calendar: svg('<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>'),
};
const FOLDER_ICON = { inbox: ICON.inbox, sent: ICON.sent, archive: ICON.archive, deleted: ICON.trash };
const LAYOUT_DEFAULT = { side: 220, list: 560, pz: 290, collapsed: false, pz_hidden: false };
const LIMITS = { side: [160, 360], list: [240, 1400], pz: [220, 520] };

// ------------------------------------------------------------ verbinding met Python
const desk = () => (window.pywebview && window.pywebview.api && window.pywebview.api.popout) ? window.pywebview.api : null;
function openExternal(url) { const d = desk(); if (d) d.open_external(url); else window.open(url, '_blank', 'noopener'); }
async function api(name, ...args) {
  const r = await fetch('/api/' + name, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Plakzicht': '1' }, body: JSON.stringify(args) });
  const j = await r.json();
  if (!j.ok) throw new Error(j.error);
  return j.result;
}
async function run(fn) {
  try { return await fn(); }
  catch (e) {
    const msg = e.message || String(e);
    toast(msg);
    if (/Niet ingelogd/.test(msg)) showLogin();
    else if (/intussen|wordt al verplaatst/.test(msg) && S.st && !S.popout) {  // een collega was sneller
      S.sel = null; S.mail = null; renderReader(); renderPz();
      refreshState().then(loadList).catch(() => {});
    }
  }
}

// ------------------------------------------------------------ hulpjes
// Alleen vervangen wat echt veranderd is: zo verdwijnt een knop of regel niet onder je muis terwijl je klikt.
function setHtml(el, html) { if (!el) return false; if (el._h === html) return false; el.innerHTML = html; el._h = html; return true; }
// Is de gebruiker net aan het klikken? Dan even wachten met verversen op de achtergrond.
// Zelfde opbouw (zelfde regels in dezelfde volgorde)? Dan alleen de onderdelen vervangen die echt anders zijn.
function morph(el, html) {
  if (!el || el._h === html) return false;
  const tpl = document.createElement('div'); tpl.innerHTML = html;
  if (el._h == null) el.replaceChildren(...tpl.childNodes);
  else morphKids(el, tpl, 0);
  el._h = html;
  return true;
}
const _mkey = n => n.nodeType !== 1 ? '#' + n.nodeType : (n.dataset.id || n.dataset.grp || n.dataset.mb || n.dataset.drop || n.dataset.label || '') + '|' + n.tagName + '.' + (n.className || '').toString().split(' ')[0];
const _mtag = n => { const o = n.outerHTML; return o.slice(0, o.indexOf('>') + 1); };
function morphKids(a, b, depth) {
  const x = [...a.childNodes], y = [...b.childNodes];
  if (x.length !== y.length || !x.every((n, i) => _mkey(n) === _mkey(y[i]))) { a.replaceChildren(...y); return; }
  x.forEach((n, i) => {
    const m = y[i];
    if (n.nodeType !== 1) { if (n.nodeValue !== m.nodeValue) n.nodeValue = m.nodeValue; return; }
    if (n.outerHTML === m.outerHTML) return;
    // zelfde element met andere inhoud: alleen dieper vervangen als de tag zelf gelijk is (dan blijven knoppen en hun klik staan)
    if (depth < 5 && _mtag(n) === _mtag(m) && n.children.length) morphKids(n, m, depth + 1);
    else n.replaceWith(m);
  });
}
const PTR = { down: false, t: 0 };
document.addEventListener('pointerdown', () => { PTR.down = true; PTR.t = Date.now(); }, true);
document.addEventListener('pointerup', () => { PTR.down = false; PTR.t = Date.now(); }, true);
document.addEventListener('keydown', () => { PTR.t = Date.now(); }, true);
const userBusy = () => PTR.down || Date.now() - PTR.t < 700;
let toastT;
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => { t.hidden = true; }, Math.max(2800, msg.length * 45)); }
const DN = ['zo', 'ma', 'di', 'wo', 'do', 'vr', 'za'], MN = ['jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'];
function fmtDate(iso, long) {
  if (!iso) return '';
  const d = new Date(iso), now = new Date();
  const hm = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  const sameDay = (a, b) => a.toDateString() === b.toDateString();
  const y = new Date(now); y.setDate(now.getDate() - 1);
  const day = DN[d.getDay()] + ' ' + d.getDate() + ' ' + MN[d.getMonth()];
  if (long) return day + ' ' + d.getFullYear() + ', ' + hm;
  if (sameDay(d, now)) return hm;
  if (sameDay(d, y)) return 'Gisteren';
  return day;
}
function fmtDay(isoDate) { if (!isoDate) return '–'; const d = new Date(isoDate + 'T12:00'); return DN[d.getDay()] + ' ' + d.getDate() + ' ' + MN[d.getMonth()]; }
function labelBadge(l, removable) {
  return `<span class="badge lab" style="--c:${esc(l.color)}">${esc(l.name)}${removable ? `<button class="x" data-unlabel="${l.id}" aria-label="Label ${esc(l.name)} weghalen">×</button>` : ''}</span>`;
}
const STEP_CLS = { klaar: 'd', gepland: 'p', afgekeurd: 'f', 'niet nodig': 'n', 'nog te doen': '' };
function stepsHtml(prod) {
  if (!prod) return '';
  return '<span class="steps">' + prod.map(x => `<span class="st ${STEP_CLS[x.status] ?? ''}" title="${esc(x.naam)}: ${esc(x.status)}">${esc(x.kort)}</span>`).join('') + '</span>';
}
function stepsText(prod) {
  if (!prod) return 'nog niet in de planning';
  const by = st => prod.filter(x => x.status === st).map(x => x.naam.toLowerCase());
  const parts = [];
  if (by('klaar').length) parts.push(by('klaar').join(', ') + ' klaar');
  if (by('gepland').length) parts.push(by('gepland').join(', ') + ' gepland');
  if (by('afgekeurd').length) parts.push(by('afgekeurd').join(', ') + ' afgekeurd');
  return parts.join(' · ') || 'nog niet gestart';
}
const PROOF_CLS = { goedgekeurd: 'order', auto: 'order', afgekeurd: 'bad', open: 'off', bekeken: 'off', upload: '' };
function proofBadge(p) { return p ? `<span class="badge ${PROOF_CLS[p.status] || ''}" style="font-family:inherit" title="Drukproef">proef: ${esc(p.tekst)}</span>` : ''; }
function shipLine(v) {
  if (!v) return '';
  const t = v.status || ({ verzonden: 'verzonden', label: 'label gemaakt', probleem: 'probleem bij verzending' }[v.stand] || v.stand || '');
  return `<div class="kv"><span>Verzending</span><b>${v.track_url ? `<a href="${esc(v.track_url)}" target="_blank" rel="noopener" data-ext="${esc(v.track_url)}">${esc(t || 'track & trace')}</a>` : esc(t)}</b></div>`;
}
function eur(n) { return n == null ? '' : '€ ' + Number(n).toFixed(2).replace('.', ','); }
// Mailinhoud is niet te vertrouwen: alles wat code kan uitvoeren eruit halen.
function sanitize(html) {
  const doc = new DOMParser().parseFromString('<div>' + (html || '') + '</div>', 'text/html');
  $$('script,style,iframe,object,embed,link,meta,form,input,button,textarea,select', doc).forEach(n => n.remove());
  $$('*', doc).forEach(el => {
    [...el.attributes].forEach(a => {
      const n = a.name.toLowerCase(), v = a.value.trim().toLowerCase();
      if (n.startsWith('on') || n === 'srcdoc' || n === 'contenteditable') el.removeAttribute(a.name);
      else if ((n === 'href' || n === 'src' || n === 'xlink:href') && (v.startsWith('javascript:') || (v.startsWith('data:') && !v.startsWith('data:image/')))) el.removeAttribute(a.name);
    });
  });
  return doc.body.firstChild.innerHTML;
}
function mailboxById(id) { return S.st.mailboxes.find(m => m.id === id); }

// ------------------------------------------------------------ dialoog
function dialog(html, onOpen) {
  const d = $('#dlg');
  d.innerHTML = html;
  return new Promise(res => {
    const done = v => { d.close(); res(v); };
    d.onclose = () => res(null);
    d.onsubmit = e => { e.preventDefault(); done(new FormData(e.target)); };
    $$('[data-cancel]', d).forEach(b => b.onclick = () => done(null));
    d.showModal();
    if (onOpen) onOpen(d, done);
  });
}

// ------------------------------------------------------------ inloggen
async function showLogin() {
  $('#app').hidden = true; $('#login').hidden = false; $('#overlay').hidden = true;
  try {
    const info = await api('app_info'), ms = info.mode === 'microsoft';
    $('#loginmode').innerHTML = ms ? '<span class="modebadge ms">Microsoft 365</span> Echte mailboxen.' : '<span class="modebadge demo">Demo</span> Alles is nagebootst.';
    $('.demo-accounts').hidden = ms;
    $('#keepbox').hidden = !info.remember;
    $('#keepdays').textContent = info.remember ? `(tot ${info.remember} dagen zonder gebruik)` : '';
    S.version = info.version;
  } catch { /* geen info */ }
  setTimeout(() => $('#loginform [name=username]').focus(), 50);
}
$('#loginform').addEventListener('submit', async e => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    const st = await api('login', f.get('username'), f.get('password'), !$('#keepbox').hidden && f.has('remember'), deviceName());
    $('#loginerr').hidden = true; e.target.reset(); $('#loginform [name=remember]').checked = true;
    boot(st);
  } catch (err) { $('#loginerr').textContent = err.message; $('#loginerr').hidden = false; }
});
$('#btn-logout').onclick = async () => { setPresence(null); stopEvents(); await run(() => api('logout')); S.view = null; S.sel = null; S.mail = null; showLogin(); };

function deviceName() {
  const ua = navigator.userAgent;
  const os = /Windows/.test(ua) ? 'Windows' : /iPhone|iPad/.test(ua) ? 'iPhone/iPad' : /Mac OS X|Macintosh/.test(ua) ? 'Mac'
    : /Android/.test(ua) ? 'Android' : /Linux/.test(ua) ? 'Linux' : 'Onbekend';
  const app = window.pywebview ? 'Plakzicht Mail-app' : matchMedia('(display-mode: standalone)').matches ? 'geïnstalleerde app'
    : /Edg\//.test(ua) ? 'Edge' : /Chrome\//.test(ua) ? 'Chrome' : /Firefox\//.test(ua) ? 'Firefox' : /Safari\//.test(ua) ? 'Safari' : 'browser';
  return os + ' · ' + app;
}
function boot(st) {
  S.st = st;
  $('#login').hidden = true; $('#app').hidden = false;
  $('#whoami').textContent = st.user.name;
  $('#btn-admin').hidden = st.user.role !== 'beheerder';
  setDensity(st.user.density, false);
  S.layout = { ...LAYOUT_DEFAULT, ...(st.user.layout || {}) };
  applyLayout();
  if (!(st.user.layout || {}).list && st.user.prefs.listview === 'kolommen') S.layout.list = clampCol('list', colsNeeded(st.user.prefs.cols || DEFAULT_COLS) + 4), applyLayout();
  S.view = st.mailboxes.length ? inboxView(st.mailboxes[0]) : null;
  showModeBadge();
  S.sel = null; S.mail = null; S.cmp = null; S.ai = null; S.search = ''; $('#search').value = ''; S.filter = 'alle';
  loadDrafts(); S.multi.clear(); notifyBell();
  renderSide(); loadList(); renderReader(); renderPz(); renderRibbon();
  startEvents();
}
async function refreshState() {
  const st = await api('state'); S.st = st;
  // map verwijderd of mailbox weg? terug naar Postvak IN
  if (S.view && S.view.mailbox_id) {
    const mb = mailboxById(S.view.mailbox_id);
    if (!mb) S.view = S.st.mailboxes.length ? inboxView(S.st.mailboxes[0]) : null;
    else if (mb.folders.length && !mb.folders.some(f => f.id === S.view.folder)) S.view = inboxView(mb);
  }
  renderSide();
}

// ------------------------------------------------------------ regelweergave (per gebruiker)
function setDensity(d, save = true) {
  document.body.dataset.density = d;
  $$('.density button').forEach(b => b.classList.toggle('on', b.dataset.density === d));
  if (save) run(async () => { await api('set_density', d); S.st.user.density = d; toast('Regelweergave: ' + d + ' (bewaard voor ' + S.st.user.name + ')'); });
}
$$('.density button').forEach(b => b.onclick = () => setDensity(b.dataset.density));

// ------------------------------------------------------------ kolommen (per gebruiker)
function clampCol(key, w) {
  const [lo, hi] = LIMITS[key], L = S.layout;
  const width = k => (k === 'side' && L.collapsed ? 56 : k === 'pz' && L.pz_hidden ? 0 : L[k]);
  const cols = S.popout ? ['pz'] : ['side', 'list', 'pz'];
  const others = cols.filter(k => k !== key).reduce((t, k) => t + width(k), 0);
  const room = $('#main').clientWidth - 20 - cols.length * 10 - others - 320;  // leeskolom houdt minstens 320px
  return Math.round(Math.max(lo, Math.min(hi, w, Math.max(lo, room))));
}
function applyLayout() {
  const L = S.layout, m = $('#main');
  m.style.setProperty('--c-side', L.side + 'px');
  m.style.setProperty('--c-list', L.list + 'px');
  m.style.setProperty('--c-pz', L.pz + 'px');
  document.body.classList.toggle('side-collapsed', !!L.collapsed);
  document.body.classList.toggle('pz-hidden', !!L.pz_hidden);
}
let layoutT;
function saveLayout() { clearTimeout(layoutT); layoutT = setTimeout(() => run(async () => { S.layout = { ...S.layout, ...(await api('set_layout', S.layout)) }; }), 400); }
function setLayout(patch) { S.layout = { ...S.layout, ...patch }; applyLayout(); saveLayout(); }
$$('.gutter').forEach(g => {
  const key = g.dataset.g;
  const locked = () => key === 'side' && S.layout.collapsed;
  g.addEventListener('pointerdown', e => {
    if (locked() || e.button !== 0) return;
    e.preventDefault(); g.setPointerCapture(e.pointerId);
    const x0 = e.clientX, w0 = S.layout[key];
    g.classList.add('active'); document.body.classList.add('resizing');
    const move = ev => { const d = ev.clientX - x0; S.layout[key] = clampCol(key, w0 + (key === 'pz' ? -d : d)); applyLayout(); };
    const up = () => { g.removeEventListener('pointermove', move); g.removeEventListener('pointerup', up); g.removeEventListener('pointercancel', up);
      g.classList.remove('active'); document.body.classList.remove('resizing'); saveLayout(); };
    g.addEventListener('pointermove', move); g.addEventListener('pointerup', up); g.addEventListener('pointercancel', up);
  });
  g.addEventListener('dblclick', () => { if (!locked()) setLayout({ [key]: clampCol(key, LAYOUT_DEFAULT[key]) }); });
  g.addEventListener('keydown', e => {
    if (locked() || (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight')) return;
    e.preventDefault();
    const step = (e.key === 'ArrowRight' ? 16 : -16) * (key === 'pz' ? -1 : 1);
    setLayout({ [key]: clampCol(key, S.layout[key] + step) });
  });
});
window.addEventListener('resize', () => {
  if (!S.layout) return;
  for (const k of ['list', 'pz', 'side']) S.layout[k] = clampCol(k, S.layout[k]);
  applyLayout();
});

// ------------------------------------------------------------ mappen (boom per mailbox)
const isMs = () => S.st && S.st.mode === 'microsoft';
const WK_ICON = { inbox: ICON.inbox, sent: ICON.sent, archive: ICON.archive, deleted: ICON.trash, drafts: ICON.pen, junk: ICON.ban };
const folderIcon = f => WK_ICON[f.wk] || ICON.folderPlain;
function foldersOf(mbId) { const mb = mailboxById(mbId); return mb ? mb.folders : []; }
function folderOf(mbId, fid) { return foldersOf(mbId).find(f => f.id === fid) || null; }
function wkFolder(mbId, wk) { return foldersOf(mbId).find(f => f.wk === wk) || null; }
function inboxView(mb) { const f = mb.folders.find(x => x.wk === 'inbox') || mb.folders[0]; return { mailbox_id: mb.id, folder: f ? f.id : 'inbox' }; }
let EXP = new Set();
try { EXP = new Set(JSON.parse(localStorage.getItem('pm-exp') || '[]')); } catch { /* geen opslag */ }
function saveExp() { try { localStorage.setItem('pm-exp', JSON.stringify([...EXP])); } catch { /* geen opslag */ } }
function isOpen(key, dflt) { return EXP.has(key) ? true : EXP.has('-' + key) ? false : dflt; }
function setOpen(key, open) { EXP.delete(key); EXP.delete('-' + key); EXP.add(open ? key : '-' + key); saveExp(); }
// Toon een map als al zijn bovenliggende mappen open staan
function visibleFolders(mb) {
  const v = S.view || {}, active = v.mailbox_id === mb.id ? v.folder : null;
  const byId = Object.fromEntries(mb.folders.map(f => [f.id, f]));
  const onPath = new Set(); let p = active && byId[active] ? byId[active].parent : null;
  while (p) { onPath.add(p); p = byId[p] ? byId[p].parent : null; }
  return mb.folders.filter(f => {
    let q = f.parent;
    while (q) { if (!isOpen(mb.id + ':' + q, onPath.has(q))) return false; q = byId[q] ? byId[q].parent : null; }
    return true;
  }).map(f => ({ ...f, open: isOpen(mb.id + ':' + f.id, onPath.has(f.id)) }));
}
function renderSide() {
  const v = S.view || {};
  let h;
  if (S.layout && S.layout.collapsed) {
    h = `<div class="rail"><button class="ri" id="btn-collapse" title="Zijbalk uitklappen" aria-label="Zijbalk uitklappen">${ICON.expand}</button>
      <button class="ri newmail" id="btn-new" title="Nieuwe mail" aria-label="Nieuwe mail">${ICON.pen}</button></div><div class="rail">`;
    for (const mb of S.st.mailboxes) {
      const inbox = mb.folders.find(f => f.wk === 'inbox') || {}, active = v.mailbox_id === mb.id;
      h += `<button class="ri ${active && v.folder === inbox.id ? 'on' : ''}" data-mb="${mb.id}" data-folder="${esc(inbox.id || '')}" data-drop="mb" title="${esc(mb.address)} › ${esc(inbox.name || 'Postvak IN')}${mb.error ? ' (fout)' : ''}" aria-label="${esc(mb.address)}">
        <span class="av ${mb.error ? 'err' : ''}">${esc(mb.display.charAt(0))}</span>${inbox.unread ? `<span class="cnt">${inbox.unread}</span>` : ''}</button>`;
      if (active) for (const f of mb.folders.filter(f => f.depth === 0 && f.wk !== 'inbox')) {
        h += `<button class="ri sub ${v.folder === f.id ? 'on' : ''}" data-mb="${mb.id}" data-folder="${esc(f.id)}" data-drop="mb" title="${esc(mb.display)} › ${esc(f.name)}" aria-label="${esc(f.name)}">${folderIcon(f)}</button>`;
      }
    }
    h += `</div><div class="rail">`;
    for (const l of S.st.labels) {
      h += `<button class="ri ${v.label_id === l.id ? 'on' : ''}" data-label="${l.id}" data-drop="label" style="--c:${esc(l.color)}" title="Label: ${esc(l.name)}${l.count ? ' (' + l.count + ')' : ''}" aria-label="Label ${esc(l.name)}"><span class="ldot"></span></button>`;
    }
    h += `<button class="ri" id="btn-newlabel" title="Nieuw label" aria-label="Nieuw label">${ICON.plus}</button></div>
      <div class="rail"><button class="ri" id="btn-rules" title="Regels" aria-label="Regels">${ICON.rules}</button>
      ${isMs() ? '' : `<button class="ri" id="btn-sim" title="Testmail laten binnenkomen (demo)" aria-label="Testmail laten binnenkomen">${ICON.bolt}</button>`}</div>`;
    if (morph($('#side'), h)) wireSide();
    return;
  }
  h = `<div class="sidetop"><button class="btn primary big" id="btn-new">Nieuwe mail</button>
    <button class="iconbtn" id="btn-collapse" title="Zijbalk inklappen tot icoontjes" aria-label="Zijbalk inklappen">${ICON.collapse}</button></div>`;
  h += `<div class="tree"><div class="sh">Mailboxen</div>`;
  if (!S.st.mailboxes.length) h += `<p class="note" style="padding:0 6px">Je hebt nog geen toegang tot een mailbox. Vraag de beheerder.</p>`;
  for (const mb of S.st.mailboxes) {
    const open = isOpen('mb:' + mb.id, v.mailbox_id === mb.id), inbox = mb.folders.find(f => f.wk === 'inbox') || {};
    h += `<div class="mbhead" data-mbhead="${mb.id}">
      <button class="tw" data-twmb="${mb.id}" aria-expanded="${open}" aria-label="${open ? 'Inklappen' : 'Uitklappen'}: ${esc(mb.address)}">${open ? ICON.chevDown : ICON.chev}</button>
      <button class="mbname" data-mb="${mb.id}" data-folder="${esc(inbox.id || '')}" data-drop="mb" title="${esc(mb.address)}">${esc(mb.display)}
        <span class="kind">${mb.kind === 'persoonlijk' ? 'persoonlijk' : ''}</span><span class="n">${open ? '' : inbox.unread || ''}</span></button></div>`;
    if (mb.error) h += `<div class="mberr" title="${esc(mb.error)}">${ICON.flag} Niet bereikbaar. ${esc(mb.error)}</div>`;
    if (!open) continue;
    for (const f of visibleFolders(mb)) {
      h += `<div class="frow" style="--d:${f.depth}">
        ${f.has_children ? `<button class="tw" data-twf="${mb.id}:${esc(f.id)}" aria-expanded="${f.open}" aria-label="${f.open ? 'Inklappen' : 'Uitklappen'}: ${esc(f.name)}">${f.open ? ICON.chevDown : ICON.chev}</button>` : '<span class="tw"></span>'}
        <button class="si fi ${v.mailbox_id === mb.id && v.folder === f.id ? 'on' : ''}" data-mb="${mb.id}" data-folder="${esc(f.id)}" data-drop="mb" title="${esc(f.name)}${f.total ? ' (' + f.total + ' mails)' : ''}">
          ${folderIcon(f)}<span class="fn">${esc(f.name)}</span><span class="n">${f.unread || ''}</span></button></div>`;
    }
    h += `<button class="si newf" data-newf="${mb.id}">${ICON.plus} Nieuwe map</button>`;
  }
  h += `</div><div><div class="sh">Labels<button id="btn-newlabel" title="Nieuw label" aria-label="Nieuw label">+</button></div>`;
  for (const l of S.st.labels) {
    h += `<button class="si ${v.label_id === l.id ? 'on' : ''}" data-label="${l.id}" data-drop="label" style="--c:${esc(l.color)}">
      <span class="dot"></span>${esc(l.name)}<span class="n">${l.count || ''}</span></button>`;
  }
  h += `</div><div><div class="sh">Automatisch</div>
    <button class="si" id="btn-rules">${ICON.rules} Regels</button>
    ${isMs() ? '' : `<button class="si" id="btn-sim" title="Demo: laat een nieuwe mail binnenkomen, zodat je de regels ziet werken">${ICON.bolt} Testmail laten binnenkomen</button>`}`;
  h += `</div><p class="note" style="padding:0 6px">Tip: sleep een mail naar een map om hem te verplaatsen, of naar een label. Rechtermuisknop op een map: submap maken, hernoemen, verplaatsen. Dubbelklik op een mail opent een eigen venster.</p>`;
  if (morph($('#side'), h)) wireSide();
}
function wireSide() {
  $('#btn-collapse').onclick = () => { setLayout({ collapsed: !S.layout.collapsed }); renderSide(); };
  $('#btn-new').onclick = () => openCompose({ mode: 'new' });
  $('#btn-newlabel').onclick = () => newLabel();
  $('#btn-rules').onclick = () => openRules();
  if ($('#btn-sim')) $('#btn-sim').onclick = simulateIncoming;
  $$('#side [data-mb]').forEach(b => {
    b.onclick = () => {
      if (!b.dataset.folder) return toast('Deze mailbox is niet bereikbaar.');
      S.view = { mailbox_id: +b.dataset.mb, folder: b.dataset.folder }; S.sel = null; S.mail = null;
      if (b.classList.contains('mbname')) setOpen('mb:' + b.dataset.mb, true);
      renderSide(); loadList(); renderReader(); renderPz();
    };
    b.oncontextmenu = e => { e.preventDefault(); showMenu(e.clientX, e.clientY, b.classList.contains('mbname') ? mailboxMenu(+b.dataset.mb) : folderMenu(+b.dataset.mb, b.dataset.folder)); };
  });
  $$('#side [data-twmb]').forEach(b => b.onclick = () => { const k = 'mb:' + b.dataset.twmb; setOpen(k, b.getAttribute('aria-expanded') !== 'true'); renderSide(); });
  $$('#side [data-twf]').forEach(b => b.onclick = () => { setOpen(b.dataset.twf, b.getAttribute('aria-expanded') !== 'true'); renderSide(); });
  $$('#side [data-newf]').forEach(b => b.onclick = () => folderDialog('new', +b.dataset.newf, null));
  $$('#side [data-label]').forEach(b => b.onclick = () => { S.view = { label_id: +b.dataset.label }; S.sel = null; S.mail = null; renderSide(); loadList(); renderReader(); renderPz(); });
  $$('#side [data-drop]').forEach(t => {
    if (t._wired) return; t._wired = true;
    let openT;
    t.addEventListener('dragover', e => {
      e.preventDefault(); e.dataTransfer.dropEffect = 'move'; t.classList.add('over');
      // even boven een dichte map hangen = map openklappen
      const tw = t.parentNode.querySelector('[data-twf][aria-expanded=false]');
      if (tw && !openT) openT = setTimeout(() => { setOpen(tw.dataset.twf, true); renderSide(); }, 900);
    });
    t.addEventListener('dragleave', () => { t.classList.remove('over'); clearTimeout(openT); openT = null; });
    t.addEventListener('drop', e => {
      e.preventDefault(); t.classList.remove('over'); clearTimeout(openT);
      const id = e.dataTransfer.getData('text/plain');
      if (id) dropMail(id, t);
    });
  });
}
function mailboxMenu(mbId) {
  return [{ n: 'Nieuwe map…', icon: ICON.plus, run: () => folderDialog('new', mbId, null) },
    { n: 'Vernieuwen', icon: ICON.refresh, run: refreshAll }];
}
function folderMenu(mbId, fid) {
  const f = folderOf(mbId, fid); if (!f) return mailboxMenu(mbId);
  const own = !f.wk, admin = S.st.user.role === 'beheerder';
  const items = [{ n: 'Openen', icon: folderIcon(f), run: () => { S.view = { mailbox_id: mbId, folder: fid }; S.sel = null; S.mail = null; renderSide(); loadList(); renderReader(); renderPz(); } },
    '-', { n: 'Nieuwe submap…', icon: ICON.plus, run: () => folderDialog('new', mbId, fid) }];
  if (own) {
    items.push({ n: 'Hernoemen…', icon: ICON.pen, run: () => folderDialog('rename', mbId, fid) });
    // verplaatsen binnen dezelfde mailbox; niet in zichzelf of een eigen submap
    const desc = new Set([fid]); let grew = true;
    while (grew) { grew = false; for (const x of foldersOf(mbId)) if (desc.has(x.parent) && !desc.has(x.id)) { desc.add(x.id); grew = true; } }
    items.push({ n: 'Map verplaatsen naar', act: 'move', sub: [
      { n: 'Bovenste niveau', icon: ICON.folderPlain, disabled: !f.parent, run: () => moveFolder(mbId, fid, null) }, '-',
      ...foldersOf(mbId).filter(x => !desc.has(x.id)).map(x => ({ n: x.name, indent: x.depth, icon: folderIcon(x), disabled: x.id === f.parent, run: () => moveFolder(mbId, fid, x.id) }))] });
    if (admin) items.push('-', { n: 'Map verwijderen…', act: 'delete', danger: true, run: () => folderDialog('delete', mbId, fid) });
  }
  items.push('-', { n: 'Vernieuwen', icon: ICON.refresh, run: refreshAll });
  return items;
}
async function refreshAll() {
  await run(async () => {
    if (isMs()) { await api('refresh_now', S.view && S.view.mailbox_id ? S.view.mailbox_id : null); toast('Bezig met bijwerken vanaf Microsoft…'); await new Promise(r => setTimeout(r, 2500)); }
    await refreshState(); await loadList(); toast('Bijgewerkt');
  });
}
async function moveFolder(mbId, fid, dest) {
  await run(async () => { await api('move_folder', mbId, fid, dest); if (dest) setOpen(mbId + ':' + dest, true); await refreshState(); toast('Map verplaatst'); });
}
async function folderDialog(kind, mbId, fid) {
  const mb = mailboxById(mbId), f = fid ? folderOf(mbId, fid) : null;
  if (kind === 'delete') {
    const ok = await dialog(`<form><h2>Map “${esc(f.name)}” verwijderen?</h2>
      <p class="muted">De map en de submappen gaan met hun mails naar Verwijderde items van ${esc(mb.display)}${isMs() ? ' (ook in Outlook)' : ''}.</p>
      <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Verwijderen</button></div></form>`);
    if (!ok) return;
    return run(async () => {
      await api('delete_folder', mbId, fid);
      if (S.view && S.view.mailbox_id === mbId && S.view.folder === fid) S.view = inboxView(mb);
      await refreshState(); await loadList(); toast('Map verwijderd');
    });
  }
  const title = kind === 'rename' ? 'Map hernoemen' : f ? `Nieuwe submap in “${f.name}”` : `Nieuwe map in ${mb.display}`;
  const r = await dialog(`<form><h2>${esc(title)}</h2><div class="form"><label>Naam<input name="name" required maxlength="120" value="${esc(kind === 'rename' ? f.name : '')}"></label></div>
    ${isMs() ? '<p class="note">De map wordt ook in Outlook aangemaakt of aangepast.</p>' : ''}
    <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">${kind === 'rename' ? 'Opslaan' : 'Maken'}</button></div></form>`,
  d => { const i = $('[name=name]', d); i.focus(); i.select(); });
  if (!r) return;
  await run(async () => {
    if (kind === 'rename') { await api('rename_folder', mbId, fid, r.get('name')); toast('Map hernoemd'); }
    else {
      await api('create_folder', mbId, fid, r.get('name'));
      setOpen('mb:' + mbId, true); if (fid) setOpen(mbId + ':' + fid, true);
      toast('Map gemaakt');
    }
    await refreshState();
  });
}

// ------------------------------------------------------------ acties (zoals in Outlook), met kleur en sneltoets
const ACT = {
  reply: { n: 'Beantwoorden', i: 'reply', c: 'reply', k: 'Ctrl+R' },
  replyall: { n: 'Allen beantwoorden', i: 'replyAll', c: 'reply', k: 'Ctrl+Shift+R' },
  forward: { n: 'Doorsturen', i: 'forward', c: 'fwd', k: 'Ctrl+F' },
  archive: { n: 'Archiveren', i: 'archive', c: 'archive', k: 'Backspace' },
  delete: { n: 'Verwijderen', i: 'trash', c: 'del', k: 'Delete' },
  flag: { n: 'Vlag', i: 'flag', c: 'flag', k: 'Insert' },
  read: { n: 'Gelezen', i: 'mailOpen', c: 'read', k: 'Ctrl+Q' },
  unread: { n: 'Ongelezen', i: 'mail', c: 'read', k: 'Ctrl+U' },
  move: { n: 'Verplaatsen', i: 'folder', c: 'move' },
  label: { n: 'Label', i: 'tag', c: 'label' },
  link: { n: 'Order koppelen', i: 'link', c: 'link' },
  rule: { n: 'Regel maken', i: 'rules', c: 'rule' },
  popout: { n: 'Eigen venster', i: 'popout', c: 'move', k: 'Enter' },
  eml: { n: 'Opslaan als .eml', i: 'download', c: 'move' },
  claim: { n: 'Oppakken', i: 'hand', c: 'claim' },
  unclaim: { n: 'Vrijgeven', i: 'hand', c: 'claim' },
};
const actIcon = a => `<span class="ai" style="--ac:var(--a-${ACT[a].c})">${ICON[ACT[a].i]}</span>`;

async function after(id, gone) {
  if (S.popout) { if (gone) return closePopout(); await openMail(id, true); return; }
  await refreshState(); await loadList();
  if (S.sel === id) {
    if (gone || !S.mails.some(m => m.id === id)) { S.sel = null; S.mail = null; renderReader(); renderPz(); }
    else await openMail(id, true);
  }
}
const rowOf = id => S.mails.find(m => m.id === id) || (S.older && S.older.mails.find(m => m.id === id)) || (S.mail && S.mail.id === id ? S.mail : null);

const BULK_OK = new Set(['read', 'unread', 'flag', 'archive', 'delete', 'moveto', 'labelset', 'claim', 'unclaim']);
async function doAct(a, id, extra) {
  if (inBulk(id)) {
    if (BULK_OK.has(a)) return bulkAct(a, bulkIds(), extra);
    if (['reply', 'replyall', 'forward', 'link', 'rule', 'eml', 'popout'].includes(a)) return toast('Dit kan alleen met één mail. Klik eerst op één mail.');
  }
  const row = rowOf(id);
  if (a === 'reply' || a === 'replyall' || a === 'forward') {
    const m = S.mail && S.mail.id === id ? S.mail : await run(() => api('get_mail', id));
    if (m) openCompose({ mode: a, mail: m });
    return;
  }
  if (a === 'popout') return popoutMail(id);
  if (a === 'eml') return downloadEml(id);
  if (a === 'claim' || a === 'unclaim') return run(async () => { await api('claim_mail', id, a === 'claim'); toast(a === 'claim' ? 'Opgepakt: collega’s zien dat jij deze mail doet' : 'Vrijgegeven'); await after(id, false); });
  if (a === 'open') return openMail(id);
  if (a === 'link') { const m = S.mail && S.mail.id === id ? S.mail : await run(() => api('get_mail', id)); if (m) await linkDialog(m); return; }
  if (a === 'rule') { const m = S.mail && S.mail.id === id ? S.mail : await run(() => api('get_mail', id)); if (m) openRules({ fromMail: m }); return; }
  await run(async () => {
    if (a === 'read' || a === 'unread') { await api('set_read', id, a === 'read'); toast(a === 'read' ? 'Gemarkeerd als gelezen' : 'Gemarkeerd als ongelezen'); return after(id, false); }
    if (a === 'flag') { const on = !(row && row.flagged); await api('set_flag', id, on); toast(on ? 'Vlag gezet' : 'Vlag weggehaald'); return after(id, false); }
    if (a === 'archive') {
      if (row && row.folder_wk === 'archive') return toast('Deze mail staat al in Archief');
      await api('archive_mail', id); toast('Gearchiveerd'); return after(id, !!(S.view && S.view.mailbox_id));
    }
    if (a === 'delete') {
      if (row && row.folder_wk === 'deleted') {
        const ok = await dialog(`<form><h2>Definitief verwijderen?</h2><p class="muted">“${esc(row.subject)}” wordt definitief verwijderd.</p>
          <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Verwijderen</button></div></form>`);
        if (!ok) return;
      }
      const r = await api('delete_mail', id); toast(r === 'definitief' ? 'Definitief verwijderd' : 'Verplaatst naar Verwijderde items'); return after(id, true);
    }
    if (a === 'moveto') {
      if (row && row.mailbox_id === extra.mb && row.folder === extra.folder) return;
      const res = await api('move_mail', id, extra.mb, extra.folder);
      rememberFolder(extra.mb, extra.folder);
      const f = folderOf(extra.mb, extra.folder), where = mailboxById(extra.mb).display + ' › ' + (f ? f.name : FOLDER_NAMES[extra.folder] || 'map');
      if (res && res.queued) toast('Wordt op de achtergrond verplaatst naar ' + where + '. Je kunt gewoon verder.');
      else toast('Verplaatst naar ' + where + (res && res.warnings && res.warnings.length ? '. Let op: ' + res.warnings.join(' ') : ''));
      return after(id, !!(S.view && S.view.mailbox_id));
    }
    if (a === 'labelset') {
      await api('set_label', id, extra.label, extra.on);
      const l = S.st.labels.find(x => x.id === extra.label);
      toast(extra.on ? `Label "${l.name}" toegevoegd` : `Label "${l.name}" weggehaald`);
      return after(id, !extra.on && !!(S.view && S.view.label_id === extra.label));
    }
  });
}

// ------------------------------------------------------------ menu (rechtermuisknop en uitklapmenu's)
function closeMenu() { $$('.cmenu.root').forEach(m => m.remove()); }
function menuHtml(items) {
  return items.map((it, i) => {
    if (it === '-') return '<div class="csep" role="separator"></div>';
    if (it.head) return `<div class="chead">${esc(it.head)}</div>`;
    const icon = it.act ? actIcon(it.act) : it.dot ? `<span class="ai"><span class="mdot" style="--c:${esc(it.dot)}"></span></span>` : `<span class="ai">${it.icon || ''}</span>`;
    const check = it.checked !== undefined ? `<span class="ck">${it.checked ? ICON.check : ''}</span>` : '';
    return `<div class="cmi ${it.sub ? 'has-sub' : ''} ${it.danger ? 'danger' : ''}" ${it.indent ? `style="--ind:${it.indent}"` : ''}>
      <button type="button" role="menuitem" data-i="${i}" ${it.disabled ? 'disabled' : ''}>${icon}<span class="cl">${esc(it.n)}</span>${check}${it.k ? `<kbd>${esc(it.k)}</kbd>` : ''}${it.sub ? `<span class="arr">${ICON.chev}</span>` : ''}</button>
      ${it.sub ? `<div class="cmenu sub" role="menu">${menuHtml(it.sub)}</div>` : ''}</div>`;
  }).join('');
}
function showMenu(x, y, items) {
  closeMenu();
  const m = document.createElement('div');
  m.className = 'cmenu root'; m.setAttribute('role', 'menu');
  m.innerHTML = menuHtml(items);
  document.body.appendChild(m);
  const r = m.getBoundingClientRect();
  m.style.left = Math.max(4, Math.min(x, innerWidth - r.width - 4)) + 'px';
  m.style.top = Math.max(4, Math.min(y, innerHeight - r.height - 4)) + 'px';
  if (x + r.width * 2 > innerWidth) m.classList.add('flip');
  const walk = (box, list) => {
    $$(':scope > .cmi > button', box).forEach(b => {
      const it = list[+b.dataset.i];
      if (it.sub) {
        const sub = $(':scope > .cmenu.sub', b.parentNode);
        walk(sub, it.sub);
        b.onclick = e => { e.stopPropagation(); b.parentNode.classList.toggle('open'); };
        b.parentNode.onmouseenter = () => { const sr = b.getBoundingClientRect(); sub.style.top = Math.min(0, innerHeight - sr.top - sub.offsetHeight - 6) + 'px'; };
      } else b.onclick = e => { e.stopPropagation(); closeMenu(); it.run && it.run(); };
    });
  };
  walk(m, items);
  const first = $('button:not([disabled])', m); if (first) first.focus();
  m.addEventListener('keydown', e => {
    const all = $$('button:not([disabled])', m).filter(b => b.offsetParent !== null);
    const i = all.indexOf(document.activeElement);
    if (e.key === 'ArrowDown') { e.preventDefault(); (all[i + 1] || all[0]).focus(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); (all[i - 1] || all[all.length - 1]).focus(); }
    if (e.key === 'ArrowRight' && document.activeElement.parentNode.classList.contains('has-sub')) { document.activeElement.parentNode.classList.add('open'); const s = $('.cmenu.sub button', document.activeElement.parentNode); if (s) s.focus(); }
    if (e.key === 'ArrowLeft') { const p = document.activeElement.closest('.cmenu.sub'); if (p) { p.parentNode.classList.remove('open'); $(':scope > button', p.parentNode).focus(); } }
    if (e.key === 'Escape') closeMenu();
  });
}
document.addEventListener('mousedown', e => { if (!e.target.closest('.cmenu')) closeMenu(); });
window.addEventListener('blur', closeMenu);
window.addEventListener('resize', closeMenu);

function labelItems(id) {
  if (inBulk(id)) return bulkLabelItems();
  const row = rowOf(id), have = new Set((row ? row.labels : []).map(l => l.id));
  return [...S.st.labels.map(l => ({ n: l.name, dot: l.color, checked: have.has(l.id), run: () => doAct('labelset', id, { label: l.id, on: !have.has(l.id) }) })),
    '-', { n: 'Nieuw label…', icon: ICON.plus, run: () => newLabel(id) }];
}
let RECENT = [];
try { RECENT = JSON.parse(localStorage.getItem('pm-recent') || '[]'); } catch { /* geen opslag */ }
function rememberFolder(mb, folder) { RECENT = [{ mb, folder }, ...RECENT.filter(r => !(r.mb === mb && r.folder === folder))].slice(0, 5); try { localStorage.setItem('pm-recent', JSON.stringify(RECENT)); } catch { /* geen opslag */ } }
function moveItems(id, withRecent) {
  const all = moveItemsAll(id);
  const row = rowOf(id);
  const rec = withRecent ? RECENT.filter(r => folderOf(r.mb, r.folder)).map(r => { const f = folderOf(r.mb, r.folder), mb = mailboxById(r.mb);
    return { n: (S.st.mailboxes.length > 1 ? mb.display + ' › ' : '') + f.name, icon: folderIcon(f), disabled: row && row.mailbox_id === r.mb && row.folder === r.folder, run: () => doAct('moveto', id, { mb: r.mb, folder: r.folder }) }; }) : [];
  return rec.length ? [{ head: 'Recent gebruikt' }, ...rec, '-', ...all] : all;
}
function moveItemsAll(id) {
  const row = rowOf(id);
  const list = mb => mb.folders.map(f => ({ n: f.name, indent: f.depth, icon: folderIcon(f), disabled: row && row.mailbox_id === mb.id && row.folder === f.id,
    run: () => doAct('moveto', id, { mb: mb.id, folder: f.id }) }));
  const mbs = S.st.mailboxes.filter(mb => mb.folders.length);
  if (mbs.length === 1) return list(mbs[0]);
  // eigen mailbox eerst, daarna de andere mailboxen elk als submenu
  const own = mbs.find(mb => row && mb.id === row.mailbox_id);
  return [...(own ? [{ head: own.display }, ...list(own), '-'] : []),
    ...mbs.filter(mb => mb !== own).map(mb => ({ n: mb.display, icon: ICON.inbox, sub: list(mb) }))];
}
function mailMenu(id) {
  if (inBulk(id)) return bulkMenu();
  const row = rowOf(id);
  const it = a => ({ n: ACT[a].n, act: a, k: ACT[a].k, run: () => doAct(a, id) });
  return [
    { n: 'Openen', icon: ICON.mailOpen, run: () => openMail(id) }, it('popout'), '-',
    row && row.claim && row.claim.mine ? it('unclaim') : { ...it('claim'), disabled: !!(row && row.claim) }, '-',
    it('reply'), it('replyall'), it('forward'), '-',
    row && row.is_read ? it('unread') : it('read'),
    { ...it('flag'), n: row && row.flagged ? 'Vlag weghalen' : 'Vlag zetten' },
    { n: 'Opvolgen', act: 'flag', sub: followItems(id) },
    { n: 'Label', act: 'label', sub: labelItems(id) },
    { n: 'Verplaatsen naar', act: 'move', sub: moveItems(id, true) },
    it('archive'), { n: 'Snelle stappen', icon: ICON.bolt, sub: qsItems(id) }, { n: 'Melden', icon: ICON.shield, sub: reportItems(id) }, '-',
    { n: 'Koppelen aan order of offerte…', act: 'link', run: () => doAct('link', id) },
    { n: 'Afspraak maken…', icon: ICON.calendar, run: () => meetingFromMail(id) },
    { n: 'Regel maken van deze mail…', act: 'rule', run: () => doAct('rule', id) },
    it('eml'), '-',
    { ...it('delete'), danger: true, n: row && row.folder_wk === 'deleted' ? 'Definitief verwijderen' : 'Verwijderen' },
  ];
}

// ------------------------------------------------------------ lint (zoals het vereenvoudigde lint van Outlook)
let rbnTab = 'start';
const curMail = () => S.sel ? (rowOf(S.sel) || S.mail) : null;
const curFolder = () => S.view && S.view.mailbox_id ? folderOf(S.view.mailbox_id, S.view.folder) : null;
function claudeState() {
  const c = S.st.claude || {};
  if (!c.configured) return { ok: false, why: 'Claude is nog niet ingesteld (Beheer › Claude).' };
  if (!c.on) return { ok: false, why: 'Claude staat voor jou nog niet aan. Vraag de beheerder.' };
  if (c.limit && c.used >= c.limit) return { ok: false, why: `Je maandlimiet (${c.limit} verzoeken) is bereikt.` };
  return { ok: true, why: `Claude · deze maand ${c.used}${c.limit ? ' van ' + c.limit : ''} verzoeken` };
}
function rbnButtons() {
  const m = curMail(), has = !!S.sel, f = curFolder(), cl = claudeState();
  const many = S.multi.size > 1;
  const needMail = { dis: !has, why: 'Kies eerst een mail' };
  const needOne = { dis: !has || many, why: many ? 'Werkt met één mail; klik eerst op één mail' : 'Kies eerst een mail' };
  const qs = S.st.quicksteps || [];
  if (rbnTab === 'beeld') {
    const p = P();
    return [
      { id: 'v-cols', n: 'Kolommen', icon: ICON.columns, on: p.listview === 'kolommen', run: () => setListview('kolommen'), p: 1 },
      { id: 'v-compact', n: 'Compact', icon: ICON.rows, on: p.listview !== 'kolommen', run: () => setListview('compact'), p: 1 },
      { sep: 1 },
      ...['smal', 'middel', 'breed'].map(d => ({ id: 'v-d-' + d, n: d[0].toUpperCase() + d.slice(1), icon: ICON.density, on: document.body.dataset.density === d, run: () => { setDensity(d); renderRibbon(); }, p: 3, t: 'Regelhoogte: ' + d })),
      { sep: 1 },
      { id: 'v-groups', n: 'Scheidingsbalken', icon: ICON.groups, on: !!p.groups, run: toggleGroups, p: 1, t: 'Balken per dag (Vandaag, Gisteren, …, Ouder) of per waarde van de kolom waarop je sorteert' },
      { id: 'v-sort', n: 'Sorteren', icon: ICON.sort, menu: sortMenu, p: 1 },
      { id: 'v-colpick', n: 'Kolommen kiezen', icon: ICON.columns, menu: colItems, p: 2 },
      { sep: 1 },
      { id: 'v-reply', n: p.reply_in === 'pane' ? 'Antwoorden: in leesvenster' : 'Antwoorden: volledig scherm', icon: ICON.reply, menu: () => [
        { n: 'In het leesvenster (rechts)', checked: p.reply_in === 'pane', run: () => { savePrefs({ reply_in: 'pane' }); renderRibbon(); } },
        { n: 'Volledig scherm', checked: p.reply_in !== 'pane', run: () => { savePrefs({ reply_in: 'window' }); renderRibbon(); } }], p: 2 },
      { id: 'v-notify', n: N().on ? 'Meldingen aan' : 'Meldingen uit', icon: N().on ? ICON.bell : ICON.bellOff, on: N().on, run: () => { toggleNotify(); renderRibbon(); }, p: 2, t: 'Pop-up met geluid bij nieuwe mail' },
      { id: 'v-pz', n: S.layout.pz_hidden ? 'Plakzicht tonen' : 'Plakzicht verbergen', icon: ICON.panel, run: () => { setLayout({ pz_hidden: !S.layout.pz_hidden }); renderRibbon(); }, p: 2 },
      { id: 'v-side', n: S.layout.collapsed ? 'Zijbalk uitklappen' : 'Zijbalk inklappen', icon: S.layout.collapsed ? ICON.expand : ICON.collapse, run: () => { setLayout({ collapsed: !S.layout.collapsed }); renderSide(); renderRibbon(); }, p: 3 },
    ];
  }
  if (rbnTab === 'plakzicht') {
    const pz = S.mail && S.mail.plakzicht, nr = pz && (pz.order ? pz.order.nr : pz.offerte ? pz.offerte.nr : null);
    return [
      { id: 'p-link', n: 'Koppelen aan order', icon: ICON.link, c: 'link', ...needOne, run: () => doAct('link', S.sel), p: 1 },
      { id: 'p-open', n: nr ? 'Openen in Plakzicht' : 'Order openen', icon: ICON.popout, c: 'link', dis: !nr, why: 'Deze mail is niet gekoppeld', run: () => openOrder(nr), p: 1 },
      { id: 'p-meet', n: 'Afspraak maken', icon: ICON.calendar, c: 'reply', ...needOne, run: () => meetingFromMail(S.sel), p: 1, t: 'Afspraak in je agenda, met de order uit deze mail' },
      { id: 'p-find', n: 'Order zoeken', icon: ICON.search, c: 'link', run: () => $('#nav-orders').click(), p: 2 },
      { sep: 1 },
      { id: 'p-rule', n: 'Regel maken', icon: ICON.rules, c: 'rule', ...needOne, run: () => doAct('rule', S.sel), p: 2 },
      { id: 'p-rules', n: 'Regels', icon: ICON.rules, c: 'rule', run: () => openRules(), p: 3 },
      { sep: 1 },
      { id: 'p-eml', n: 'Opslaan als .eml', icon: ICON.download, c: 'move', ...needOne, run: () => doAct('eml', S.sel), p: 3 },
      { id: 'p-pop', n: 'Eigen venster', icon: ICON.popout, c: 'move', ...needOne, hide: S.popout, run: () => doAct('popout', S.sel), p: 3 },
    ];
  }
  if (rbnTab === 'claude') {
    const dis = !cl.ok || !has || many, why = !cl.ok ? cl.why : many ? 'Werkt met één mail' : 'Kies eerst een mail';
    return [
      { id: 'c-sum', n: 'Samenvatten', icon: ICON.sparkle, c: 'ai', dis, why, run: () => aiRun('summary'), p: 1 },
      { id: 'c-reply', n: 'Antwoord voorstellen', icon: ICON.sparkle, c: 'ai', dis, why, run: () => aiReply(), p: 1 },
      { id: 'c-tr', n: 'Vertalen', icon: ICON.globe, c: 'ai', dis, why, menu: () => translateItems(), p: 1 },
      { id: 'c-sug', n: 'Label en map voorstellen', icon: ICON.tag, c: 'ai', dis, why, run: () => aiRun('suggest'), p: 2 },
      { id: 'c-ext', n: 'Gegevens uit aanvraag', icon: ICON.list, c: 'ai', dis, why, run: () => aiRun('extract'), p: 2 },
      { sep: 1 },
      { id: 'c-set', n: 'Mijn Claude-instellingen', icon: ICON.gear, run: () => openMySettings(undefined, 'claude'), p: 3 },
      { id: 'c-info', n: cl.why, icon: ICON.info, info: 1, p: 4 },
    ];
  }
  const inDel = f && (f.wk === 'deleted' || f.wk === 'junk');
  const followN = m && m.flagged ? 'Opvolgen' : 'Opvolgen';
  return [
    { id: 'new', n: 'Nieuwe e-mail', icon: ICON.pen, c: 'new', cls: 'primary', run: () => openCompose({ mode: 'new' }), menu: () => newMailItems(), split: 1, p: 0 },
    { sep: 1 },
    { id: 'del', n: 'Verwijderen', icon: ICON.trash, c: 'del', ...needMail, run: () => doAct('delete', S.sel), split: 1, menu: () => [
      { ...ACTI('delete'), n: m && m.folder_wk === 'deleted' ? 'Definitief verwijderen' : 'Verwijderen', disabled: !has, run: () => doAct('delete', S.sel) },
      '-', { n: f ? `Map “${f.name}” leegmaken…` : 'Map leegmaken…', icon: ICON.trash, disabled: !inDel, run: () => emptyFolder() }], dis: false, p: 1 },
    { id: 'arch', n: 'Archiveren', icon: ICON.archive, c: 'archive', ...needMail, run: () => doAct('archive', S.sel), p: 1 },
    { id: 'move', n: 'Verplaatsen', icon: ICON.folder, c: 'move', ...needMail, menu: () => moveItems(S.sel, true), p: 2 },
    { id: 'report', n: 'Melden', icon: ICON.shield, c: 'del', ...needMail, menu: () => reportItems(S.sel), p: 6 },
    { sep: 1 },
    { id: 'reply', n: 'Beantwoorden', icon: ICON.reply, c: 'reply', ...needOne, run: () => doAct('reply', S.sel), p: 0 },
    { id: 'replyall', n: 'Allen beantwoorden', icon: ICON.replyAll, c: 'reply', ...needOne, run: () => doAct('replyall', S.sel), p: 1 },
    { id: 'fwd', n: 'Doorsturen', icon: ICON.forward, c: 'fwd', ...needOne, run: () => doAct('forward', S.sel), p: 1 },
    { id: 'assign', n: m && m.claim ? (m.claim.mine ? 'Opgepakt door jou' : 'Opgepakt: ' + m.claim.name.split(' ')[0]) : 'Toewijzen', icon: ICON.hand, c: 'claim', ...needMail, menu: () => assignItems(S.sel), p: 3, lbl: 1 },
    { sep: 1 },
    ...qs.slice(0, 2).map((q, i) => ({ id: 'qs' + q.id, n: q.name, icon: ICON.bolt, color: q.color, dis: !has && q.actions.new_to === undefined, why: 'Kies eerst een mail', run: () => runQuickStep(q, S.sel), lbl: 1, p: 4 + i, t: 'Snelle stap: ' + qsSummary(q) })),
    { id: 'qs', n: 'Snelle stappen', icon: ICON.bolt, c: 'move', menu: () => qsItems(S.sel), p: 4, lbl: 1 },
    { sep: 1 },
    { id: 'read', n: (many ? bulkIds().map(rowOf).some(r => r && !r.is_read) : m && !m.is_read) ? 'Gelezen' : 'Ongelezen', icon: m && !m.is_read ? ICON.mailOpen : ICON.mail, c: 'read', ...needMail,
      run: () => doAct((many ? bulkIds().map(rowOf).some(r => r && !r.is_read) : m && !m.is_read) ? 'read' : 'unread', S.sel), p: 3, t: 'Ongelezen/gelezen (Ctrl+Q / Ctrl+U)' },
    { id: 'cat', n: 'Categoriseren', icon: ICON.tag, c: 'label', ...needMail, menu: () => labelItems(S.sel), p: 3 },
    { id: 'follow', n: followN, icon: ICON.flag, c: 'flag', ...needMail, on: !!(m && m.flagged), run: () => doAct('flag', S.sel), split: 1, menu: () => followItems(S.sel), p: 3 },
    { sep: 1 },
    { id: 'people', n: 'Personen zoeken', icon: ICON.search, c: 'move', run: () => addressBook(true), p: 7 },
    { id: 'abook', n: 'Adresboek', icon: ICON.book, c: 'move', run: () => addressBook(false), p: 8 },
    { id: 'meet', n: 'Afspraak', icon: ICON.calendar, c: 'reply', ...needOne, run: () => meetingFromMail(S.sel), p: 6, t: 'Afspraak maken vanuit deze mail (met de order erin)' },
    { id: 'filter', n: S.filter === 'alle' ? 'E-mail filteren' : 'Filter: ' + (FILTERS.find(x => x[0] === S.filter) || ['', S.filter])[1], icon: ICON.funnel, c: 'move', on: S.filter !== 'alle', menu: () => FILTERS.map(([k, n]) => ({ n, checked: S.filter === k, run: () => setFilter(k) })), p: 5 },
    { sep: 1 },
    { id: 'speak', n: SPEAK.on ? 'Stoppen' : 'Voorlezen', icon: ICON.speaker, c: 'read', ...needOne, on: SPEAK.on, run: () => speakToggle(), p: 8 },
    { id: 'tr', n: 'Vertalen', icon: ICON.globe, c: 'ai', dis: !has || !cl.ok || many, why: !has ? 'Kies eerst een mail' : cl.why, menu: () => translateItems(), p: 7 },
    { id: 'claude', n: 'Claude', icon: ICON.sparkle, c: 'ai', dis: !cl.ok, why: cl.why, menu: () => claudeItems(), p: 4 },
  ];
}
const ACTI = a => ({ n: ACT[a].n, act: a, k: ACT[a].k });
function renderRibbon() {
  const el = $('#ribbon'); if (!el || !S.st) return;
  const tabs = S.popout ? [['start', 'Start'], ['plakzicht', 'Plakzicht'], ['claude', 'Claude']] : [['start', 'Start'], ['beeld', 'Beeld'], ['plakzicht', 'Plakzicht'], ['claude', 'Claude']];
  const items = rbnButtons().filter(b => !b.hide);
  const changed = setHtml(el, `<div class="rbn-tabs" role="tablist">${tabs.map(([k, n]) => `<button role="tab" class="rtab ${rbnTab === k ? 'on' : ''}" aria-selected="${rbnTab === k}" data-rtab="${k}">${n}</button>`).join('')}</div>
    <div class="rbn-row" role="toolbar" aria-label="Lint">${items.map((b, i) => b.sep ? `<span class="rsep" data-i="${i}"></span>` : b.info
      ? `<span class="rinfo" data-i="${i}" data-p="${b.p}">${b.icon}<span>${esc(b.n)}</span></span>`
      : `<span class="rbw ${b.split ? 'split' : ''}" data-i="${i}" data-p="${b.p ?? 5}" ${b.lbl ? 'data-lbl="1"' : ''}><button class="rb ${b.cls || ''} ${b.on ? 'on' : ''}" data-b="${i}" ${b.dis ? 'disabled' : ''} style="--ac:${b.color ? esc(b.color) : `var(--a-${b.c || 'move'})`}"
        title="${esc(b.dis ? b.why || '' : b.t || b.n)}" ${b.on ? 'aria-pressed="true"' : ''}>${b.icon}<span class="rl">${esc(b.n)}</span>${b.menu && !b.split ? '<span class="dd">▾</span>' : ''}</button>${b.split ? `<button class="rb dd-only" data-dd="${i}" ${b.dis ? 'disabled' : ''} title="Meer: ${esc(b.n)}" aria-label="Meer: ${esc(b.n)}">▾</button>` : ''}</span>`).join('')}
      <span class="rbw more"><button class="rb" id="rbn-more" title="Meer opties" aria-label="Meer opties">${ICON.dots}</button></span></div>`);
  $$('[data-rtab]', el).forEach(t => t.onclick = () => { rbnTab = t.dataset.rtab; renderRibbon(); });
  const open = async (b, anchor) => { const r = anchor.getBoundingClientRect(); showMenu(r.left, r.bottom + 4, await b.menu()); };
  $$('[data-b]', el).forEach(btn => btn.onclick = () => { const b = items[+btn.dataset.b]; if (b.run) b.run(); else if (b.menu) open(b, btn); });
  $$('[data-dd]', el).forEach(btn => btn.onclick = () => open(items[+btn.dataset.dd], btn));
  if (changed || renderRibbon.force) fitRibbon(items); else if ($('#rbn-more')) fitRibbon.more(items);
  renderRibbon.force = false;
}
function fitRibbon(items) {
  const row = $('#ribbon .rbn-row'); if (!row) return;
  const wraps = $$('.rbw[data-p], .rinfo[data-p]', row);
  wraps.forEach(w => w.classList.remove('ovf', 'icon'));
  const over = () => row.scrollWidth > row.clientWidth + 1;
  // eerst labels weghalen bij de minst belangrijke knoppen, daarna knoppen naar het ⋯-menu
  const levels = [...new Set(wraps.map(w => +w.dataset.p))].filter(p => p > 0).sort((a, b) => b - a);
  const hidden = [];
  // eerst labels weghalen bij de minder belangrijke knoppen, daarna knoppen naar het ⋯-menu
  for (const lv of levels.filter(p => p >= 3)) for (const w of wraps.filter(w => +w.dataset.p === lv).reverse()) {
    if (!over()) break; if (!w.dataset.lbl && !w.classList.contains('rinfo')) w.classList.add('icon');
  }
  for (const lv of levels) for (const w of wraps.filter(w => +w.dataset.p === lv).reverse()) {
    if (!over()) break; w.classList.add('ovf'); hidden.push(+w.dataset.i);
  }
  $$('.rsep', row).forEach(s => { const prev = s.previousElementSibling; s.classList.toggle('ovf', !prev || prev.classList.contains('ovf') || prev.classList.contains('rsep') && prev.classList.contains('ovf')); });
  fitRibbon.hidden = hidden;
  fitRibbon.more(items);
}
fitRibbon.more = function (items) {
  const hidden = fitRibbon.hidden || [];
  $('#rbn-more').onclick = () => {
    const r = $('#rbn-more').getBoundingClientRect();
    const extra = hidden.sort((a, b) => a - b).map(i => items[i]).filter(b => !b.info).map(b => {
      if (b.menu && !b.split) { const sub = b.menu(); return sub instanceof Promise ? { n: b.n, icon: b.icon, disabled: b.dis, run: async () => showMenu(r.right - 260, r.bottom + 4, await sub) } : { n: b.n, icon: b.icon, disabled: b.dis, sub }; }
      return { n: b.n, icon: b.icon, disabled: b.dis, run: b.run || (() => {}) };
    });
    const tail = S.sel && rbnTab === 'start' ? [{ ...ACTI('link'), run: () => doAct('link', S.sel) }, { ...ACTI('rule'), run: () => doAct('rule', S.sel) }, { ...ACTI('eml'), run: () => doAct('eml', S.sel) },
      ...(S.popout ? [] : [{ ...ACTI('popout'), run: () => doAct('popout', S.sel) }])] : [];
    showMenu(r.right - 260, r.bottom + 4, [...extra, ...(extra.length && tail.length ? ['-'] : []), ...tail, ...(extra.length || tail.length ? ['-'] : []),
      { n: 'Mijn instellingen', icon: ICON.gear, run: () => openMySettings() }]);
  };
}
let rbnT;
window.addEventListener('resize', () => { clearTimeout(rbnT); rbnT = setTimeout(() => { renderRibbon.force = true; renderRibbon(); }, 120); });

// ------------------------------------------------------------ lint: menu's
function newMailItems() {
  return [{ head: 'Nieuwe mail vanuit' }, ...S.st.mailboxes.map(mb => ({ n: mb.address, icon: ICON.mail, run: () => openCompose({ mode: 'new', from: mb.id }) })),
    '-', ...(S.st.quicksteps || []).filter(q => q.actions.new_to !== undefined).map(q => ({ n: q.name, icon: ICON.bolt, run: () => runQuickStep(q, null) }))];
}
function reportItems(id) {
  const row = rowOf(id), inJunk = row && row.folder_wk === 'junk';
  return [{ n: 'Ongewenste e-mail', icon: ICON.ban, disabled: inJunk, run: () => reportMail(id, 'junk') },
    { n: 'Phishing', icon: ICON.shield, disabled: inJunk, run: () => reportMail(id, 'phishing') }, '-',
    { n: 'Geen ongewenste e-mail', icon: ICON.inbox, disabled: !inJunk, run: () => reportMail(id, 'notjunk') }];
}
async function reportMail(id, kind) {
  if (kind === 'phishing') {
    const ok = await dialog(`<form><h2>Melden als phishing?</h2><p class="muted">De mail gaat naar Ongewenste e-mail. Klik niet op links of bijlagen in deze mail. Twijfel je? Laat het de beheerder weten.</p>
      <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Melden</button></div></form>`);
    if (!ok) return;
  }
  if (inBulk(id)) return bulkAct('report', bulkIds(), { kind });
  await run(async () => { await api('report_junk', id, kind); toast(kind === 'notjunk' ? 'Teruggezet naar Postvak IN' : 'Verplaatst naar Ongewenste e-mail'); await after(id, true); });
}
async function emptyFolder() {
  const f = curFolder(); if (!f) return;
  const ok = await dialog(`<form><h2>“${esc(f.name)}” leegmaken?</h2><p class="muted">Alle ${f.total || ''} mails in deze map worden definitief verwijderd${isMs() ? ', ook in Outlook' : ''}. Dit kun je niet ongedaan maken.</p>
    <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Definitief verwijderen</button></div></form>`);
  if (!ok) return;
  await run(async () => { toast('Bezig met leegmaken…'); const n = await api('empty_folder', S.view.mailbox_id, S.view.folder); toast(`${n} ${n === 1 ? 'mail' : 'mails'} definitief verwijderd`); S.sel = null; S.mail = null; await refreshState(); await loadList(); renderReader(); renderPz(); });
}
function followItems(id) {
  const row = rowOf(id), fu = w => () => inBulk(id) ? bulkAct('followup', bulkIds(), { when: w }) : run(async () => { await api('set_followup', id, w); toast({ today: 'Opvolgen: vandaag', tomorrow: 'Opvolgen: morgen', thisweek: 'Opvolgen: deze week', nextweek: 'Opvolgen: volgende week', nodate: 'Vlag gezet', complete: 'Gemarkeerd als voltooid', clear: 'Vlag weggehaald' }[w] || 'Opvolgen: ' + fmtDay(w)); await after(id, false); });
  return [{ head: row && row.flag_due ? 'Opvolgen: ' + fmtDay(row.flag_due) : 'Opvolgen' },
    { n: 'Vandaag', icon: ICON.flag, run: fu('today') }, { n: 'Morgen', icon: ICON.flag, run: fu('tomorrow') },
    { n: 'Deze week', icon: ICON.flag, run: fu('thisweek') }, { n: 'Volgende week', icon: ICON.flag, run: fu('nextweek') },
    { n: 'Zonder datum', icon: ICON.flag, run: fu('nodate') }, { n: 'Aangepast…', icon: ICON.calendar, run: async () => {
      const r = await dialog(`<form><h2>Opvolgen op</h2><input type="date" name="d" required value="${esc(row && row.flag_due || isoDay(new Date()))}" style="width:100%">
        <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Opslaan</button></div></form>`);
      if (r && r.get('d')) fu(r.get('d'))();
    } }, '-',
    { n: 'Markeren als voltooid', icon: ICON.check, disabled: !(row && row.flagged), run: fu('complete') },
    { n: 'Vlag wissen', icon: ICON.ban, disabled: !(row && (row.flagged || row.flag_done)), run: fu('clear') }];
}
const ASSIGN_CACHE = {};
async function assignItems(id) {
  if (!ASSIGN_CACHE[id]) { try { ASSIGN_CACHE[id] = await api('colleagues', id); } catch (e) { toast(e.message); ASSIGN_CACHE[id] = []; } }
  return assignItemsSync(id);
}
function assignItemsSync(id) {
  const row = rowOf(id), mine = row && row.claim && row.claim.mine, other = row && row.claim && !row.claim.mine;
  const cols = ASSIGN_CACHE[id];
  return [mine ? { ...ACTI('unclaim'), run: () => doAct('unclaim', id) } : { ...ACTI('claim'), n: 'Zelf oppakken', disabled: other && S.st.user.role !== 'beheerder', run: () => doAct('claim', id) },
    ...(other ? [{ ...ACTI('unclaim'), n: 'Vrijgeven (' + row.claim.name + ')', disabled: S.st.user.role !== 'beheerder', run: () => doAct('unclaim', id) }] : []),
    '-', { head: 'Toewijzen aan collega' },
    ...(cols ? cols.filter(c => !c.me).map(c => ({ n: c.name, icon: ICON.hand, checked: !!(row && row.claim && row.claim.name === c.name), run: () => assignTo(id, c) }))
      : [{ n: 'Laden…', disabled: true }])];
}
async function assignTo(id, c) {
  if (inBulk(id)) return bulkAct('assign', bulkIds(), { user: c });
  await run(async () => { await api('assign_mail', id, c.id); toast(`Toegewezen aan ${c.name}. ${c.name.split(' ')[0]} krijgt een melding.`); await after(id, false); });
}
function qsSummary(q) {
  const a = q.actions, p = [];
  if (a.read === true) p.push('gelezen'); if (a.read === false) p.push('ongelezen');
  if (a.flag) p.push({ on: 'vlag', off: 'vlag weg', complete: 'vlag voltooid', today: 'opvolgen vandaag', tomorrow: 'opvolgen morgen', thisweek: 'opvolgen deze week', nextweek: 'opvolgen volgende week' }[a.flag]);
  if (a.claim) p.push(a.claim === 'claim' ? 'oppakken' : 'vrijgeven');
  if ((a.labels || []).length) p.push('label ' + a.labels.map(id => (S.st.labels.find(l => l.id === id) || {}).name || '?').join(', '));
  if (a.move) { const fk = a.move.folder; p.push('naar ' + (fk.startsWith('wk:') ? { archive: 'Archief', deleted: 'Verwijderde items', inbox: 'Postvak IN', junk: 'Ongewenste e-mail' }[fk.slice(3)] || fk : ((mailboxById(a.move.mb) || {}).display || '') + ' › ' + ((folderOf(a.move.mb, fk) || {}).name || 'map'))); }
  if (a.forward_to !== undefined) p.push('doorsturen' + (a.forward_to ? ' aan ' + a.forward_to : ''));
  if (a.new_to !== undefined) p.push('nieuwe mail' + (a.new_to ? ' aan ' + a.new_to : ''));
  if (a.reply) p.push('beantwoorden met vaste tekst');
  return p.join(', ');
}
function qsItems(id) {
  const qs = S.st.quicksteps || [];
  return [...qs.map(q => ({ n: q.name, dot: q.color, disabled: !id && q.actions.new_to === undefined, run: () => runQuickStep(q, id) })),
    ...(qs.length ? ['-'] : []), { n: 'Snelle stappen beheren…', icon: ICON.gear, run: () => openMySettings(undefined, 'qs') }];
}
async function runQuickStep(q, id) {
  const a = q.actions;
  if (a.new_to !== undefined) { openCompose({ mode: 'new', to: a.new_to, text: a.text }); return; }
  if (!id) return toast('Kies eerst een mail');
  if (inBulk(id)) {
    if (a.forward_to !== undefined || a.reply) toast('Beantwoorden of doorsturen uit deze snelle stap wordt bij meerdere mails overgeslagen.');
    return bulkAct('qs', bulkIds(), { q });
  }
  const row = rowOf(id);
  const ok = await run(async () => {
    if (a.read === true || a.read === false) await api('set_read', id, a.read);
    if (a.flag) await api('set_followup', id, { on: 'nodate', off: 'clear' }[a.flag] || a.flag);
    for (const l of a.labels || []) await api('set_label', id, l, true);
    if (a.claim === 'claim' && !(row && row.claim && row.claim.mine)) { try { await api('claim_mail', id, true); } catch (e) { toast(e.message); } }
    if (a.claim === 'release' && row && row.claim) { try { await api('claim_mail', id, false); } catch (e) { toast(e.message); } }
    return true;
  });
  if (!ok) return;
  if (a.forward_to !== undefined || a.reply) {
    const m = S.mail && S.mail.id === id ? S.mail : await run(() => api('get_mail', id));
    if (m) openCompose({ mode: a.reply ? 'reply' : 'forward', mail: m, to: a.forward_to || undefined, text: a.text });
  }
  if (a.move && row) {
    const mb = a.move.mb || row.mailbox_id, fk = a.move.folder;
    const fid = fk.startsWith('wk:') ? (wkFolder(mb, fk.slice(3)) || {}).id || (isMs() ? null : fk.slice(3)) : fk;
    if (!fid) { toast('Map voor de snelle stap niet gevonden in deze mailbox.'); await after(id, false); return; }
    if (!(row.mailbox_id === mb && row.folder === fid)) { await doAct('moveto', id, { mb, folder: fid }); toast(`Snelle stap “${q.name}” uitgevoerd`); return; }
  }
  toast(`Snelle stap “${q.name}” uitgevoerd`);
  await after(id, false);
}

async function qsApply(q, id) {
  const a = q.actions, row = rowOf(id);
  if (a.read === true || a.read === false) await api('set_read', id, a.read);
  if (a.flag) await api('set_followup', id, { on: 'nodate', off: 'clear' }[a.flag] || a.flag);
  for (const l of a.labels || []) await api('set_label', id, l, true);
  if (a.claim === 'claim' && !(row && row.claim && row.claim.mine)) { try { await api('claim_mail', id, true); } catch { /* al door iemand anders */ } }
  if (a.claim === 'release' && row && row.claim) { try { await api('claim_mail', id, false); } catch { /* niet van mij */ } }
  if (a.move && row) {
    const mb = a.move.mb || row.mailbox_id, fk = a.move.folder;
    const fid = fk.startsWith('wk:') ? (wkFolder(mb, fk.slice(3)) || {}).id || (isMs() ? null : fk.slice(3)) : fk;
    if (!fid) throw new Error('map voor de snelle stap niet gevonden');
    if (!(row.mailbox_id === mb && row.folder === fid)) return api('move_mail', id, mb, fid);
  }
  return true;
}

// ------------------------------------------------------------ adresboek en personen zoeken
async function addressBook(focusSearch, pick) {
  return dialog(`<form class="abook"><h2>${pick ? 'Kies een adres' : focusSearch ? 'Personen zoeken' : 'Adresboek'}</h2>
    <input name="q" type="search" placeholder="Zoek op naam, bedrijf of mailadres" style="width:100%" autocomplete="off">
    <div class="results ab" id="abres"><div class="empty">Laden…</div></div>
    <p class="note">Klanten uit Plakzicht en iedereen met wie in je mailboxen is gemaild.</p>
    <div class="dlgbtns"><button type="button" class="btn" data-cancel>Sluiten</button></div></form>`, (d, done) => {
    const box = $('#abres', d), inp = $('[name=q]', d);
    let t;
    const search = async () => {
      let r = []; try { r = await api('address_book', inp.value); } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
      box.innerHTML = r.length ? r.map(x => `<div class="abrow"><div class="abn"><b>${esc(x.name || x.address)}</b><span class="note">${esc(x.address)}</span></div>
        <span class="badge ${x.source === 'Plakzicht-klant' ? 'order' : ''}" style="font-family:inherit">${esc(x.source)}</span>
        ${pick ? `<button type="button" class="btn small primary" data-pick="${esc(x.address)}">Kiezen</button>` : `<button type="button" class="btn small" data-mail="${esc(x.address)}">Mail</button><button type="button" class="btn small" data-copy="${esc(x.address)}">Kopiëren</button>`}</div>`).join('')
        : '<div class="empty">Niemand gevonden</div>';
      $$('[data-pick]', box).forEach(b => b.onclick = () => done(b.dataset.pick));
      $$('[data-mail]', box).forEach(b => b.onclick = () => { done(null); openCompose({ mode: 'new', to: b.dataset.mail }); });
      $$('[data-copy]', box).forEach(b => b.onclick = async () => { try { await navigator.clipboard.writeText(b.dataset.copy); toast('Gekopieerd'); } catch { toast(b.dataset.copy); } });
    };
    inp.oninput = () => { clearTimeout(t); t = setTimeout(search, 200); };
    search(); if (focusSearch || pick) inp.focus();
  });
}

// ------------------------------------------------------------ voorlezen (stem van Windows of de browser)
const SPEAK = { on: false };
function speakToggle() {
  if (!('speechSynthesis' in window)) return toast('Voorlezen werkt niet in deze browser.');
  if (SPEAK.on) { speechSynthesis.cancel(); SPEAK.on = false; renderRibbon(); return; }
  const m = S.mail; if (!m) return;
  const txt = new DOMParser().parseFromString(sanitize(m.body || ''), 'text/html').body.textContent.replace(/\s+/g, ' ').trim();
  const u = new SpeechSynthesisUtterance(`Mail van ${m.from_name || m.from_addr}. Onderwerp: ${m.subject || 'geen onderwerp'}. ${txt}`.slice(0, 30000));
  const v = speechSynthesis.getVoices().find(x => /^nl/i.test(x.lang)); if (v) u.voice = v;
  u.lang = v ? v.lang : 'nl-NL'; u.rate = 1;
  u.onend = u.onerror = () => { SPEAK.on = false; renderRibbon(); };
  SPEAK.on = true; speechSynthesis.speak(u); renderRibbon();
}

// ------------------------------------------------------------ Claude
function translateItems(forText) {
  return ['Nederlands', 'Engels', 'Duits', 'Frans', 'Spaans', 'Pools'].map(l => ({ n: 'Naar het ' + l, icon: ICON.globe, run: () => forText ? forText(l) : aiRun('translate', { lang: l }) }));
}
function claudeItems() {
  return [{ n: 'Samenvatten', icon: ICON.sparkle, disabled: !S.sel, run: () => aiRun('summary') },
    { n: 'Antwoord voorstellen…', icon: ICON.sparkle, disabled: !S.sel, run: () => aiReply() },
    { n: 'Vertalen', icon: ICON.globe, disabled: !S.sel, sub: translateItems() },
    { n: 'Label en map voorstellen', icon: ICON.tag, disabled: !S.sel, run: () => aiRun('suggest') },
    { n: 'Gegevens uit aanvraag halen', icon: ICON.list, disabled: !S.sel, run: () => aiRun('extract') },
    '-', { n: 'Mijn Claude-instellingen', icon: ICON.gear, run: () => openMySettings(undefined, 'claude') }];
}
const AI_TITLES = { summary: 'Samenvatting', translate: 'Vertaling', suggest: 'Voorstel', extract: 'Gegevens uit de aanvraag' };
async function aiRun(kind, extra) {
  const id = S.sel; if (!id) return;
  S.ai = { id, kind, loading: true, title: AI_TITLES[kind] + (extra && extra.lang ? ' (' + extra.lang + ')' : '') };
  renderAi();
  try {
    const r = await api('claude_run', kind, id, extra || {});
    if (!S.ai || S.ai.id !== id) return;
    S.ai = { ...S.ai, loading: false, r };
  } catch (e) { if (S.ai && S.ai.id === id) S.ai = { ...S.ai, loading: false, err: e.message }; }
  refreshClaudeUsage();
  renderAi();
}
async function refreshClaudeUsage() { try { const st = await api('state'); S.st.claude = st.claude; renderRibbon(); } catch { /* stil */ } }
function aiHtml() {
  const a = S.ai; if (!a || a.id !== S.sel || (S.cmp && S.cmp.refId === S.sel)) return '';
  let body = '';
  if (a.loading) body = '<div class="row"><span class="spin"></span><span class="note">Claude is bezig…</span></div>';
  else if (a.err) body = `<div class="callout">${esc(a.err)}</div>`;
  else if (a.kind === 'suggest') {
    const r = a.r;
    body = `${r.reason ? `<p class="note">${esc(r.reason)}</p>` : ''}<div class="row">${r.labels.map(l => `<button class="btn small" data-ailab="${l.id}">${labelBadge(l)} toevoegen</button>`).join('')}
      ${r.folder ? `<button class="btn small" data-aimove>${ICON.folder} Naar “${esc(r.folder.name)}”</button>` : ''}${!r.labels.length && !r.folder ? '<span class="note">Geen passend label of map gevonden.</span>' : ''}</div>`;
  } else if (a.kind === 'extract') {
    body = a.r.fields.length ? `<table class="t kvt">${a.r.fields.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</table>
      <div class="row"><button class="btn small" data-aicopy>Kopiëren</button></div>` : '<p class="note">Geen aanvraaggegevens gevonden.</p>';
  } else body = `<div class="aitext">${sanitize(a.r.html)}</div><div class="row"><button class="btn small" data-aicopy>Kopiëren</button>${a.kind === 'translate' ? '' : ''}</div>`;
  return `<div class="aibox"><div class="aihead">${ICON.sparkle}<b>${esc(a.title)}</b><span class="note">door Claude · controleer altijd zelf</span><button class="x" data-aiclose aria-label="Sluiten">×</button></div>${body}</div>`;
}
function renderAi() {
  const slot = $('#reader .aislot'); if (!slot) return renderReader();
  slot.innerHTML = aiHtml();
  $$('[data-aiclose]', slot).forEach(b => b.onclick = () => { S.ai = null; renderAi(); });
  $$('[data-aicopy]', slot).forEach(b => b.onclick = async () => {
    const a = S.ai, txt = a.kind === 'extract' ? a.r.fields.map(([k, v]) => k + ': ' + v).join('\n') : new DOMParser().parseFromString(a.r.html, 'text/html').body.innerText;
    try { await navigator.clipboard.writeText(txt); toast('Gekopieerd'); } catch { toast('Kopiëren lukt niet in dit venster.'); }
  });
  $$('[data-ailab]', slot).forEach(b => b.onclick = () => doAct('labelset', S.sel, { label: +b.dataset.ailab, on: true }));
  $$('[data-aimove]', slot).forEach(b => b.onclick = () => { const f = S.ai.r.folder; S.ai = null; doAct('moveto', S.sel, { mb: f.mb, folder: f.id }); });
}
async function aiReply(c) {
  const id = c ? c.refId : S.sel; if (!id) return;
  const f = await dialog(`<form><h2>${ICON.sparkle} Antwoord laten voorstellen</h2>
    <label class="form"><span class="muted" style="font-size:12px">Wat moet er in het antwoord staan? (mag leeg)</span>
    <textarea name="i" rows="3" style="width:100%" placeholder="Bijvoorbeeld: levering lukt volgende week dinsdag, proef volgt morgen"></textarea></label>
    <p class="note">Claude krijgt alleen deze mail en de gegevens van de gekoppelde order of offerte. Er wordt niets verstuurd; je ziet eerst het concept.</p>
    <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Voorstellen</button></div></form>`, d => $('textarea', d).focus());
  if (!f) return;
  if (!c) { const m = S.mail && S.mail.id === id ? S.mail : await run(() => api('get_mail', id)); if (!m) return; openCompose({ mode: 'reply', mail: m }); c = S.cmp; }
  if (!c) return;
  const ed = $('#editor'); if (ed) { ed.insertAdjacentHTML('afterbegin', '<p class="aiwait" contenteditable="false">✨ Claude schrijft een voorstel…</p>'); }
  try {
    const r = await api('claude_run', 'reply', id, { instructions: f.get('i') || '' });
    const e2 = $('#editor'); if (!e2) return;
    $$('.aiwait', e2).forEach(x => x.remove());
    replaceOwnText(e2, r.html);
    toast('Voorstel van Claude staat in je antwoord. Lees het na voor je verstuurt.');
  } catch (e) { $$('#editor .aiwait').forEach(x => x.remove()); toast(e.message); }
  refreshClaudeUsage();
}
// Eigen tekst in de editor = alles vóór de handtekening
function ownText(ed) { const t = ed.cloneNode(true); $$('[data-sig], .aiwait', t).forEach(n => n.remove()); return t.innerText.trim(); }
function replaceOwnText(ed, html) {
  const sig = $('[data-sig]', ed); const keep = sig ? sig.outerHTML : '';
  ed.innerHTML = sanitize(html) + '<p><br></p>' + keep;
}

// ------------------------------------------------------------ meerdere mails tegelijk (Ctrl/Shift-klik of vinkje)
S.multi = new Set();
const inBulk = id => S.multi.size > 1 && S.multi.has(String(id));
const bulkIds = () => [...S.multi];
function selToggle(id) {
  id = String(id);
  if (!S.multi.size && S.sel && S.sel !== id) S.multi.add(S.sel);
  if (S.multi.has(id)) S.multi.delete(id); else S.multi.add(id);
  afterSelChange(id);
}
function selRange(id) {
  const order = S.shown || [], a = order.indexOf(S.anchor || S.sel), b = order.indexOf(String(id));
  if (a < 0 || b < 0) return selToggle(id);
  S.multi = new Set(order.slice(Math.min(a, b), Math.max(a, b) + 1));
  afterSelChange(id, true);
}
function selAll() { S.multi = new Set(S.shown || []); if (S.multi.size < 2) { S.multi.clear(); return; } afterSelChange(S.sel || [...S.multi][0], true); }
function selClear(render = true) { if (!S.multi.size) return; S.multi.clear(); if (render) { renderList(); renderReader(); renderPz(); } }
function afterSelChange(id, keepAnchor) {
  if (!keepAnchor) S.anchor = String(id);
  if (S.multi.size === 1) { const only = [...S.multi][0]; S.multi.clear(); openMail(only); return; }
  if (!S.multi.size) { S.sel = null; S.mail = null; setPresence(null); renderList(); renderReader(); renderPz(); return; }
  if (S.cmp && !S.cmp.full) stashCompose();
  if (!S.multi.has(S.sel)) S.sel = S.multi.has(String(id)) ? String(id) : [...S.multi][0];
  setPresence(null);
  renderList(); renderReader(); renderPz();
}
function pruneSel() {
  if (!S.multi.size) return;
  const have = new Set([...(S.mails || []).map(m => m.id), ...(S.older ? S.older.mails.map(m => m.id) : [])]);
  for (const id of [...S.multi]) if (!have.has(id)) S.multi.delete(id);
  if (S.multi.size < 2) { const only = [...S.multi][0]; S.multi.clear(); if (only && only !== S.sel) { S.sel = only; } }
}
const BULK_VERB = { read: 'als gelezen gemarkeerd', unread: 'als ongelezen gemarkeerd', flag: 'bijgewerkt (vlag)', archive: 'gearchiveerd', delete: 'verwijderd',
  moveto: 'verplaatst', labelset: 'bijgewerkt (label)', claim: 'opgepakt', unclaim: 'vrijgegeven', followup: 'bijgewerkt (opvolgen)', assign: 'toegewezen',
  report: 'verplaatst naar Ongewenste e-mail', qs: 'verwerkt met de snelle stap' };
const BULK_GONE = new Set(['archive', 'delete', 'moveto', 'report']);
async function bulkAct(a, ids, extra = {}) {
  ids = ids.map(String);
  const rows = ids.map(rowOf).filter(Boolean);
  if (a === 'delete' && rows.length && rows.every(r => r.folder_wk === 'deleted')) {
    const ok = await dialog(`<form><h2>${ids.length} mails definitief verwijderen?</h2><p class="muted">Dit kun je niet ongedaan maken.</p>
      <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Verwijderen</button></div></form>`);
    if (!ok) return;
  }
  if (a === 'flag') extra = { ...extra, on: rows.some(r => !r.flagged) };
  if (a === 'moveto') ids = ids.filter(id => { const r = rowOf(id); return !(r && r.mailbox_id === extra.mb && r.folder === extra.folder); });
  if (a === 'archive') ids = ids.filter(id => { const r = rowOf(id); return !(r && r.folder_wk === 'archive'); });
  if (!ids.length) return toast('Er hoeft niets te gebeuren met deze selectie.');
  const one = id => {
    switch (a) {
      case 'read': case 'unread': return api('set_read', id, a === 'read');
      case 'flag': return api('set_flag', id, extra.on);
      case 'archive': return api('archive_mail', id);
      case 'delete': return api('delete_mail', id);
      case 'moveto': return api('move_mail', id, extra.mb, extra.folder);
      case 'labelset': return api('set_label', id, extra.label, extra.on);
      case 'claim': return api('claim_mail', id, true);
      case 'unclaim': return api('claim_mail', id, false);
      case 'followup': return api('set_followup', id, extra.when);
      case 'assign': return api('assign_mail', id, extra.user.id);
      case 'report': return api('report_junk', id, extra.kind);
      case 'qs': return qsApply(extra.q, id, false);
    }
    return Promise.reject(new Error('Kan niet met meerdere mails.'));
  };
  let done = 0, okN = 0, queued = 0; const fails = [];
  const tick = () => toast(`Bezig: ${done} van ${ids.length}…`);
  tick();
  const todo = [...ids];
  const worker = async () => { while (todo.length) { const id = todo.shift(); try { const r = await one(id); okN++; if (r && r.queued) queued++; } catch (e) { fails.push(e.message); } done++; if (done % 3 === 0) tick(); } };
  await Promise.all([worker(), worker(), worker(), worker()]);
  if (a === 'moveto') rememberFolder(extra.mb, extra.folder);
  let msg = `${okN} ${okN === 1 ? 'mail' : 'mails'} ${a === 'assign' ? 'toegewezen aan ' + extra.user.name : a === 'moveto' ? 'verplaatst naar ' + (mailboxById(extra.mb) || {}).display + ' › ' + ((folderOf(extra.mb, extra.folder) || {}).name || 'map') : BULK_VERB[a]}`;
  if (queued) msg += ` (${queued} op de achtergrond naar de andere mailbox)`;
  if (fails.length) msg += `. ${fails.length} niet gelukt: ${fails[0]}`;
  toast(msg);
  if (BULK_GONE.has(a) && !(a === 'moveto' && S.view && S.view.label_id)) { S.multi.clear(); S.sel = null; S.mail = null; }
  await refreshState(); await loadList(); renderReader(); renderPz();
}
function bulkLabelItems() {
  const rows = bulkIds().map(rowOf).filter(Boolean);
  const all = l => rows.length && rows.every(r => r.labels.some(x => x.id === l.id));
  return [...S.st.labels.map(l => ({ n: l.name, dot: l.color, checked: all(l), run: () => bulkAct('labelset', bulkIds(), { label: l.id, on: !all(l) }) })),
    '-', { n: 'Nieuw label…', icon: ICON.plus, run: () => newLabel() }];
}
function bulkMenu() {
  const ids = bulkIds(), first = ids[0], rows = ids.map(rowOf).filter(Boolean), anyUnread = rows.some(r => !r.is_read);
  return [{ head: `${ids.length} mails geselecteerd` },
    { n: anyUnread ? 'Als gelezen markeren' : 'Als ongelezen markeren', act: 'read', run: () => bulkAct(anyUnread ? 'read' : 'unread', ids) },
    { n: rows.some(r => !r.flagged) ? 'Vlag zetten' : 'Vlag weghalen', act: 'flag', run: () => bulkAct('flag', ids) },
    { n: 'Opvolgen', act: 'flag', sub: followItems(first) },
    { n: 'Label', act: 'label', sub: bulkLabelItems() },
    { n: 'Toewijzen / oppakken', act: 'claim', run: async () => { const r = $('#list .mrow.msel') ? $('#list .mrow.msel').getBoundingClientRect() : { left: 200, bottom: 200 }; showMenu(r.left + 40, r.bottom, await assignItems(first)); } },
    { n: 'Verplaatsen naar', act: 'move', sub: moveItems(first, true) },
    { n: 'Archiveren', act: 'archive', k: 'Backspace', run: () => bulkAct('archive', ids) },
    { n: 'Snelle stappen', icon: ICON.bolt, sub: qsItems(first) },
    { n: 'Melden', icon: ICON.shield, sub: reportItems(first) }, '-',
    { n: 'Selectie opheffen', icon: ICON.ban, k: 'Esc', run: () => selClear() },
    { n: 'Verwijderen', act: 'delete', k: 'Delete', danger: true, run: () => bulkAct('delete', ids) }];
}
function bulkReader() {
  const ids = bulkIds(), rows = ids.map(rowOf).filter(Boolean);
  const mbs = [...new Set(rows.map(r => r.mailbox))];
  $('#reader').innerHTML = `<div class="bulk">
    <div class="bulkhead"><div class="bulkn">${ids.length}</div><div><h2>mails geselecteerd</h2>
      <p class="note">${mbs.length > 1 ? 'Uit ' + mbs.map(esc).join(', ') : esc(mbs[0] || '')} · Ctrl-klik om er een toe te voegen of weg te halen, Shift-klik voor een reeks, Esc om op te heffen.</p></div></div>
    <div class="bulkbtns">
      ${[['archive', 'Archiveren'], ['delete', 'Verwijderen'], ['move', 'Verplaatsen ▾'], ['label', 'Label ▾'], ['claim', 'Toewijzen ▾'], ['read', rows.some(r => !r.is_read) ? 'Gelezen' : 'Ongelezen'], ['flag', 'Vlag'], ['qs', 'Snelle stap ▾']]
        .map(([a, n]) => `<button class="sbtn" data-bulk="${a}" style="--ac:var(--a-${{ qs: 'move', claim: 'claim' }[a] || ACT[a] && ACT[a].c || 'move'})">${a === 'qs' ? ICON.bolt : ICON[(ACT[a] || {}).i] || ''}<span>${n}</span></button>`).join('')}
      <button class="sbtn" data-bulk="clear">${ICON.ban}<span>Opheffen</span></button></div>
    <div class="bulklist">${rows.slice(0, 12).map(r => `<div class="bl"><span class="ell"><b>${esc(whoOf(r))}</b> · ${esc(r.subject || '(geen onderwerp)')}</span><span class="note">${esc(fmtDate(r.date))}</span></div>`).join('')}
      ${rows.length > 12 ? `<div class="note">en nog ${rows.length - 12}…</div>` : ''}</div>
    <p class="note">Tip: sleep de selectie naar een map of mailbox links om alles in één keer te verplaatsen, of naar een label.</p></div>`;
  $$('#reader [data-bulk]').forEach(b => b.onclick = async () => {
    const a = b.dataset.bulk, r = b.getBoundingClientRect(), first = bulkIds()[0];
    if (a === 'clear') return selClear();
    if (a === 'move') return showMenu(r.left, r.bottom + 4, moveItems(first, true));
    if (a === 'label') return showMenu(r.left, r.bottom + 4, bulkLabelItems());
    if (a === 'claim') return showMenu(r.left, r.bottom + 4, await assignItems(first));
    if (a === 'qs') return showMenu(r.left, r.bottom + 4, qsItems(first));
    if (a === 'read') return bulkAct(rows.some(x => !x.is_read) ? 'read' : 'unread', bulkIds());
    bulkAct(a, bulkIds());
  });
  renderRibbon();
}

// ------------------------------------------------------------ melding bij nieuwe mail (pop-up met geluid)
const NOTE = { queue: [], t: null, unseen: 0, baseTitle: document.title };
const N = () => (S.st && S.st.user.prefs.notify) || { on: true, sound: true, desktop: true, mute: [] };
function notifyBell() {
  const b = $('#btn-notify'); if (!b || !S.st) return;
  const on = N().on;
  b.innerHTML = on ? ICON.bell : ICON.bellOff;
  b.classList.toggle('off', !on);
  b.title = on ? 'Meldingen bij nieuwe mail staan aan (klik om uit te zetten)' : 'Meldingen staan uit (klik om aan te zetten)';
  b.setAttribute('aria-pressed', String(on));
}
function toggleNotify() {
  const n = { ...N(), on: !N().on };
  savePrefs({ notify: n }); notifyBell();
  toast(n.on ? 'Meldingen bij nieuwe mail aan' : 'Meldingen bij nieuwe mail uit');
  if (n.on && n.desktop) askDesktop();
}
function askDesktop() { try { if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission(); } catch { /* niet beschikbaar */ } }
function onNewMail(ev) {
  const n = N();
  if (!n.on || S.popout) return;
  if ((n.mute || []).some(id => (ev.mb || []).includes(id))) return;
  NOTE.queue.push(ev);
  clearTimeout(NOTE.t);
  NOTE.t = setTimeout(flushNotes, 900);  // meerdere mails tegelijk = één melding
}
function flushNotes() {
  const list = NOTE.queue.splice(0); if (!list.length) return;
  const n = N();
  if (n.sound) chime(list.some(x => x.high));
  showNotePopup(list);
  if (document.hidden || !document.hasFocus()) {
    NOTE.unseen += list.length;
    document.title = `(${NOTE.unseen}) Nieuwe mail · ${NOTE.baseTitle}`;
    if (n.desktop && 'Notification' in window && Notification.permission === 'granted') {
      try {
        const one = list[0];
        const nt = new Notification(list.length === 1 ? (one.from || 'Nieuwe mail') : `${list.length} nieuwe mails`, {
          body: list.length === 1 ? `${one.subject}\n${one.mailbox}` : list.slice(0, 4).map(x => `${x.from}: ${x.subject}`).join('\n'), tag: 'plakzicht-mail', silent: true });
        nt.onclick = () => { window.focus(); openFromNote(one); nt.close(); };
      } catch { /* niet beschikbaar in dit venster */ }
    }
  }
}
window.addEventListener('focus', () => { if (NOTE.unseen) { NOTE.unseen = 0; document.title = NOTE.baseTitle; } });
let AC = null;
function chime(high) {
  try {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    if (AC.state === 'suspended') AC.resume();
    const t0 = AC.currentTime, notes = high ? [880, 1175, 880, 1175] : [660, 990];
    notes.forEach((f, i) => {
      const o = AC.createOscillator(), g = AC.createGain();
      o.type = 'sine'; o.frequency.value = f;
      const t = t0 + i * 0.13;
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.18, t + 0.015); g.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
      o.connect(g).connect(AC.destination); o.start(t); o.stop(t + 0.4);
    });
  } catch { /* geen geluid mogelijk */ }
}
document.addEventListener('pointerdown', () => { try { if (AC && AC.state === 'suspended') AC.resume(); } catch { /* */ } }, { once: false, passive: true });
function showNotePopup(list) {
  let box = $('#notes'); if (!box) { box = document.createElement('div'); box.id = 'notes'; box.className = 'notes'; box.setAttribute('aria-live', 'polite'); document.body.appendChild(box); }
  const card = document.createElement('div');
  card.className = 'note-card' + (list.some(x => x.high) ? ' hi' : '');
  const one = list[0];
  card.innerHTML = `<div class="nc-top">${ICON.mail}<b>${list.length === 1 ? 'Nieuwe mail' : list.length + ' nieuwe mails'}</b><span class="note">${esc([...new Set(list.map(x => x.mailbox))].join(', '))}</span>
      <button class="x" aria-label="Sluiten">×</button></div>
    ${list.slice(0, 3).map((x, i) => `<button class="nc-mail" data-i="${i}">${x.high ? '<span class="imp hi">!</span> ' : ''}<b>${esc(x.from)}</b><span>${esc(x.subject || '(geen onderwerp)')}</span>${list.length === 1 && x.preview ? `<span class="note">${esc(x.preview)}</span>` : ''}</button>`).join('')}
    ${list.length > 3 ? `<div class="note">en nog ${list.length - 3}…</div>` : ''}
    <div class="nc-foot"><button class="linkish" data-mute>Meldingen uitzetten</button></div>`;
  box.prepend(card);
  while (box.children.length > 3) box.lastChild.remove();
  const close = () => { card.classList.add('gone'); setTimeout(() => card.remove(), 250); };
  $('.x', card).onclick = close;
  $('[data-mute]', card).onclick = () => { close(); toggleNotify(); };
  $$('.nc-mail', card).forEach(b => b.onclick = () => { close(); openFromNote(list[+b.dataset.i]); });
  let t = setTimeout(close, 9000);
  card.onmouseenter = () => clearTimeout(t);
  card.onmouseleave = () => { t = setTimeout(close, 4000); };
  void one;
}
async function openFromNote(ev) {
  if (!ev || !ev.key) return;
  if (!$('#overlay').hidden && !(S.cmp && S.cmp.full)) closeOverlay();
  const mb = (ev.mb || [])[0], box = mailboxById(mb);
  if (box) { const inbox = box.folders.find(f => f.wk === 'inbox'); if (inbox && !(S.view && S.view.mailbox_id === mb && S.view.folder === inbox.id)) { S.view = { mailbox_id: mb, folder: inbox.id }; S.filter = 'alle'; renderSide(); await loadList(); } }
  selClear(false);
  await openMail(ev.key);
  const r = $(`#list .mrow[data-id="${CSS.escape(String(ev.key))}"]`); if (r) r.scrollIntoView({ block: 'nearest' });
}
function myNotify() {
  const n = N();
  $('#mybody').innerHTML = `<div class="grid2"><form class="panel form" id="nform"><h2>${ICON.bell} Meldingen bij nieuwe mail</h2>
      <div class="checks">
        <label><input type="checkbox" name="on" ${n.on ? 'checked' : ''}> Meldingen aan (pop-up rechtsonder)</label>
        <label><input type="checkbox" name="sound" ${n.sound ? 'checked' : ''}> Met geluid</label>
        <label><input type="checkbox" name="desktop" ${n.desktop ? 'checked' : ''}> Ook een melding van het systeem als Plakzicht Mail op de achtergrond staat${window.isSecureContext ? '' : ' <span class="note">(werkt alleen via https, bijvoorbeeld mail.plakzicht.nl)</span>'}</label></div>
      <fieldset><legend>Voor welke mailboxen</legend><div class="checks">
        ${S.st.mailboxes.map(mb => `<label><input type="checkbox" name="mb" value="${mb.id}" ${(n.mute || []).includes(mb.id) ? '' : 'checked'}> ${esc(mb.address)}</label>`).join('')}</div>
        <p class="note">Bijvoorbeeld alleen je eigen mailbox en info@, en niet verkoop@ als je daar maar af en toe in werkt.</p></fieldset>
      <div class="row"><button type="button" class="btn" id="n-test">${ICON.bell} Proefmelding</button></div></form>
    <div class="panel"><h2>Goed om te weten</h2>
      <p class="note">Een melding komt alleen voor nieuwe, ongelezen mail in Postvak IN. Bij Microsoft 365 controleert de server Postvak IN elke 15 seconden, dus de melding kan tot zo lang na binnenkomst verschijnen.</p>
      <p class="note">Snel aan of uit: het belletje rechtsboven.</p>
      <p class="note">Hoor je geen geluid? Klik eerst ergens in het venster; browsers spelen pas geluid af nadat je het venster hebt gebruikt.</p></div></div>`;
  const save = () => {
    const f = new FormData($('#nform')), on = new Set(f.getAll('mb').map(Number));
    const nn = { on: f.has('on'), sound: f.has('sound'), desktop: f.has('desktop'), mute: S.st.mailboxes.map(m => m.id).filter(id => !on.has(id)) };
    savePrefs({ notify: nn }); notifyBell(); toast('Opgeslagen');
    if (nn.desktop) askDesktop();
  };
  $$('#nform input').forEach(i => i.onchange = save);
  $('#n-test').onclick = () => { const mb = S.st.mailboxes[0]; chime(false); showNotePopup([{ from: 'Proefmelding', subject: 'Zo ziet een melding van nieuwe mail eruit', mailbox: mb ? mb.display : '', mb: [], preview: '' }]); };
}

// ------------------------------------------------------------ agenda (Microsoft 365, in de demo nagebootst)
const CAL = { view: 'week', date: new Date(), info: null, on: null, pz: true, events: [], orders: [], errors: [], loading: false };
try { const s = JSON.parse(localStorage.getItem('pm-cal') || '{}'); if (s.view) CAL.view = s.view; if ('pz' in s) CAL.pz = s.pz; if (s.on) CAL.on = new Set(s.on); } catch { /* geen opslag */ }
function calSave() { try { localStorage.setItem('pm-cal', JSON.stringify({ view: CAL.view, pz: CAL.pz, on: CAL.on ? [...CAL.on] : null })); } catch { /* */ } }
const HOUR = 44;
const DAYS_NL = ['zondag', 'maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag'];
const MONTHS_NL = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december'];
const pad = n => String(n).padStart(2, '0');
const isoLocal = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
const parseLocal = s => { const [d, t = '00:00'] = s.split('T'); const [y, m, dd] = d.split('-').map(Number); const [h, mi] = t.split(':').map(Number); return new Date(y, m - 1, dd, h || 0, mi || 0); };
const dayStart = d => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const sameDay = (a, b) => a.toDateString() === b.toDateString();
function calRange() {
  const d = dayStart(CAL.date);
  if (CAL.view === 'day') return [d, addDays(d, 1)];
  if (CAL.view === 'month') { const f = new Date(d.getFullYear(), d.getMonth(), 1); const s = addDays(f, -((f.getDay() + 6) % 7)); return [s, addDays(s, 42)]; }
  const mon = addDays(d, -((d.getDay() + 6) % 7));
  return [mon, addDays(mon, CAL.view === 'workweek' ? 5 : 7)];
}
function calTitle() {
  const [s, e] = calRange(), last = addDays(e, -1);
  if (CAL.view === 'month') return MONTHS_NL[CAL.date.getMonth()] + ' ' + CAL.date.getFullYear();
  if (CAL.view === 'day') return DAYS_NL[s.getDay()] + ' ' + s.getDate() + ' ' + MONTHS_NL[s.getMonth()] + ' ' + s.getFullYear();
  return s.getDate() + (s.getMonth() !== last.getMonth() ? ' ' + MONTHS_NL[s.getMonth()] : '') + ' – ' + last.getDate() + ' ' + MONTHS_NL[last.getMonth()] + ' ' + last.getFullYear();
}
const calColor = id => ((CAL.info && CAL.info.calendars.find(c => c.id === id)) || {}).color || '#1f6fb2';
function setNav(which) { ['nav-mail', 'nav-cal'].forEach(id => $('#' + id) && $('#' + id).classList.toggle('on', id === which)); }

async function openCalendar() {
  if (S.cmp && S.cmp.full) stashCompose();
  setNav('nav-cal');
  const ov = $('#overlay');
  ov.classList.add('calpage'); ov.hidden = false;
  ov.innerHTML = `<div class="cal"><aside class="cal-side" id="cal-side"><div class="empty">Laden…</div></aside><section class="cal-main" id="cal-main"></section></div>`;
  try { CAL.info = await api('cal_info'); } catch (e) { CAL.info = { calendars: [], errors: [{ account: '', error: e.message }] }; }
  if (!CAL.on || ![...CAL.on].some(id => CAL.info.calendars.some(c => c.id === id))) CAL.on = new Set(CAL.info.calendars.map(c => c.id));
  renderCalSide(); await loadCal();
}
async function loadCal() {
  const [s, e] = calRange();
  CAL.loading = true; renderCalMain();
  const ids = CAL.info.calendars.map(c => c.id).filter(id => CAL.on.has(id));
  try {
    const r = ids.length ? await api('cal_events', isoLocal(s), isoLocal(e), ids) : { events: [], errors: [] };
    CAL.events = r.events; CAL.errors = r.errors;
    CAL.orders = CAL.pz ? await api('cal_orders', isoLocal(s), isoLocal(e)) : [];
  } catch (err) { CAL.errors = [err.message]; }
  CAL.loading = false; renderCalMain();
}
function miniMonth() {
  const d = CAL.date, f = new Date(d.getFullYear(), d.getMonth(), 1), s = addDays(f, -((f.getDay() + 6) % 7)), today = new Date();
  const [rs, re] = calRange();
  let h = `<div class="mini"><div class="mini-h"><button class="iconbtn" data-mini="-1" aria-label="Vorige maand">‹</button><b>${MONTHS_NL[d.getMonth()]} ${d.getFullYear()}</b><button class="iconbtn" data-mini="1" aria-label="Volgende maand">›</button></div><div class="mini-g">`;
  h += ['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo'].map(x => `<span class="mh">${x}</span>`).join('');
  for (let i = 0; i < 42; i++) { const x = addDays(s, i); h += `<button class="md ${x.getMonth() !== d.getMonth() ? 'out' : ''} ${sameDay(x, today) ? 'today' : ''} ${x >= rs && x < re ? 'inr' : ''}" data-day="${isoLocal(x)}">${x.getDate()}</button>`; }
  return h + '</div></div>';
}
function renderCalSide() {
  const info = CAL.info, by = {};
  for (const c of info.calendars) (by[c.account] = by[c.account] || []).push(c);
  $('#cal-side').innerHTML = `<button class="btn primary big block" id="cal-new">${ICON.plus} Nieuwe afspraak</button>
    ${miniMonth()}
    <div class="cal-list">${Object.entries(by).map(([acc, list]) => `<div class="sh">${esc(acc)}</div>${list.map(c => `<label class="calchk"><input type="checkbox" data-calon="${esc(c.id)}" ${CAL.on.has(c.id) ? 'checked' : ''}><span class="swatch" style="--c:${esc(c.color)}"></span>${esc(c.name)}${c.can_edit ? '' : ' <span class="note">(alleen lezen)</span>'}</label>`).join('')}`).join('')}
      ${!info.calendars.length && !info.errors.length ? `<p class="note">${info.no_accounts ? 'Je hebt geen toegang tot de agenda van een aangemeld Microsoft-account. De agenda van een account zie je als je bij de eigen mailbox van dat account kunt.' : 'Geen agenda gevonden.'}</p>` : ''}
      <div class="sh">Plakzicht</div>
      <label class="calchk"><input type="checkbox" id="cal-pz" ${CAL.pz ? 'checked' : ''}><span class="swatch" style="--c:var(--brand)"></span>Verzenddatums van orders</label></div>
    ${info.errors.map(e => `<div class="callout small">${esc(e.error)}</div>`).join('')}
    ${info.mode === 'microsoft' && !info.enabled ? `<div class="callout small">${S.st.user.role === 'beheerder' ? 'De agenda staat nog niet aan. Zet hem aan onder Beheer › Microsoft-koppeling (daar staan ook de stappen).' : 'De agenda is nog niet ingeschakeld door de beheerder.'}</div>` : ''}
    ${info.mode === 'demo' ? '<p class="note">Demo: de agenda is nagebootst. In Microsoft 365 zie je hier de agenda\'s van de aangemelde accounts.</p>' : ''}`;
  $('#cal-new').onclick = () => calEdit({});
  $$('#cal-side [data-mini]').forEach(b => b.onclick = () => { CAL.date = new Date(CAL.date.getFullYear(), CAL.date.getMonth() + +b.dataset.mini, 1); renderCalSide(); loadCal(); });
  $$('#cal-side [data-day]').forEach(b => b.onclick = () => { CAL.date = parseLocal(b.dataset.day); renderCalSide(); loadCal(); });
  $$('#cal-side [data-calon]').forEach(i => i.onchange = () => { i.checked ? CAL.on.add(i.dataset.calon) : CAL.on.delete(i.dataset.calon); calSave(); loadCal(); });
  $('#cal-pz').onchange = e => { CAL.pz = e.target.checked; calSave(); loadCal(); };
}
function evTime(ev) { const s = parseLocal(ev.start), e = parseLocal(ev.end); return ev.allday ? 'Hele dag' : `${pad(s.getHours())}:${pad(s.getMinutes())}–${pad(e.getHours())}:${pad(e.getMinutes())}`; }
function evChip(ev, cls = '') {
  return `<button class="ev ${cls} ${ev.show_as === 'free' ? 'free' : ev.show_as === 'tentative' ? 'tent' : ''}" style="--c:${esc(calColor(ev.cal))}" data-ev="${esc(ev.id)}" title="${esc(ev.subject + ' · ' + evTime(ev) + (ev.location ? ' · ' + ev.location : ''))}">
    <b>${esc(ev.subject)}</b>${cls.includes('timed') ? `<span>${esc(evTime(ev))}${ev.location ? ' · ' + esc(ev.location) : ''}</span>` : ''}${ev.order_nr || ev.offerte_nr ? `<span class="evpz">${esc(ev.order_nr ? '#' + ev.order_nr.replace(/^0+/, '') : ev.offerte_nr)}</span>` : ''}</button>`;
}
function orderChip(o) { return `<button class="ev pzo" data-order="${esc(o.nr)}" title="Order ${esc(o.nr)} · ${esc(o.klant)} · uiterlijk verzenden"><b>Verzenden #${esc(o.nr.replace(/^0+/, ''))}</b> ${esc(o.klant)}</button>`; }
function layoutDay(evs) {
  // overlappende afspraken naast elkaar zetten
  const items = evs.map(ev => ({ ev, s: parseLocal(ev.start), e: parseLocal(ev.end) })).sort((a, b) => a.s - b.s || b.e - a.e);
  let cluster = [], end = 0; const out = [];
  const flush = () => { const cols = []; for (const it of cluster) { let c = cols.findIndex(t => t <= it.s); if (c < 0) { c = cols.length; cols.push(0); } cols[c] = it.e; it.col = c; } cluster.forEach(it => { it.n = cols.length; out.push(it); }); cluster = []; };
  for (const it of items) { if (cluster.length && it.s >= end) flush(); cluster.push(it); end = Math.max(end, +it.e); }
  if (cluster.length) flush();
  return out;
}
function renderCalMain() {
  const [s, e] = calRange(), today = new Date();
  const views = [['day', 'Dag'], ['workweek', 'Werkweek'], ['week', 'Week'], ['month', 'Maand']];
  let h = `<div class="cal-head"><button class="btn" id="cal-today">Vandaag</button><button class="iconbtn" id="cal-prev" aria-label="Vorige">‹</button><button class="iconbtn" id="cal-next" aria-label="Volgende">›</button>
    <h1>${esc(calTitle())}</h1>${CAL.loading ? '<span class="spin"></span>' : ''}<span class="grow"></span>
    <div class="seg">${views.map(([k, n]) => `<button class="${CAL.view === k ? 'on' : ''}" data-view="${k}">${n}</button>`).join('')}</div>
    <button class="btn" id="cal-back">${ICON.mail} Naar mail</button></div>
    ${CAL.errors.length ? `<div class="callout small">${CAL.errors.map(esc).join('<br>')}</div>` : ''}`;
  const evs = CAL.events, ords = CAL.orders;
  if (CAL.view === 'month') {
    h += `<div class="month"><div class="mrowh">${['maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag'].map(x => `<span>${x}</span>`).join('')}</div><div class="mgrid">`;
    for (let i = 0; i < 42; i++) {
      const d = addDays(s, i), d2 = addDays(d, 1), dk = isoLocal(d).slice(0, 10);
      const list = evs.filter(x => parseLocal(x.start) < d2 && parseLocal(x.end) > d).sort((a, b) => (b.allday - a.allday) || a.start.localeCompare(b.start));
      const ol = ords.filter(o => o.due === dk);
      const items = [...ol.map(orderChip), ...list.map(x => evChip(x, x.allday ? 'allday' : 'dot'))];
      h += `<div class="mcell ${d.getMonth() !== CAL.date.getMonth() ? 'out' : ''} ${sameDay(d, today) ? 'today' : ''}" data-cell="${dk}"><button class="mnum" data-gotoday="${dk}">${d.getDate()}</button>
        ${items.slice(0, 3).join('')}${items.length > 3 ? `<button class="more" data-gotoday="${dk}">nog ${items.length - 3}</button>` : ''}</div>`;
    }
    h += '</div></div>';
  } else {
    const days = []; for (let d = new Date(s); d < e; d = addDays(d, 1)) days.push(new Date(d));
    const cols = `56px repeat(${days.length}, minmax(0, 1fr))`;
    h += `<div class="wk" style="--cols:${cols}"><div class="wk-h"><span></span>${days.map(d => `<button class="wk-d ${sameDay(d, today) ? 'today' : ''}" data-gotoday="${isoLocal(d).slice(0, 10)}"><span>${DAYS_NL[d.getDay()].slice(0, 2)}</span><b>${d.getDate()}</b></button>`).join('')}</div>
      <div class="wk-ad"><span class="note">hele dag</span>${days.map(d => { const d2 = addDays(d, 1), dk = isoLocal(d).slice(0, 10);
        return `<div class="adcell" data-adday="${dk}">${ords.filter(o => o.due === dk).map(orderChip).join('')}${evs.filter(x => x.allday && parseLocal(x.start) < d2 && parseLocal(x.end) > d).map(x => evChip(x, 'allday')).join('')}</div>`; }).join('')}</div>
      <div class="wk-body" id="wk-body"><div class="wk-grid" style="height:${24 * HOUR}px"><div class="wk-times">${Array.from({ length: 24 }, (_, i) => `<span style="top:${i * HOUR}px">${i ? pad(i) + ':00' : ''}</span>`).join('')}</div>
        ${days.map(d => { const d2 = addDays(d, 1);
          const timed = layoutDay(evs.filter(x => !x.allday && parseLocal(x.start) < d2 && parseLocal(x.end) > d));
          return `<div class="wk-col ${sameDay(d, today) ? 'today' : ''}" data-colday="${isoLocal(d).slice(0, 10)}">${timed.map(it => {
            const st = Math.max(0, (it.s - d) / 60000), en = Math.min(1440, (it.e - d) / 60000);
            return `<div class="evbox" style="top:${st / 60 * HOUR}px;height:${Math.max(20, (en - st) / 60 * HOUR - 2)}px;left:calc(${it.col / it.n * 100}% + 2px);width:calc(${100 / it.n}% - 4px)">${evChip(it.ev, 'timed')}</div>`; }).join('')}
            ${sameDay(d, today) ? `<div class="nowline" style="top:${(today.getHours() * 60 + today.getMinutes()) / 60 * HOUR}px"></div>` : ''}</div>`; }).join('')}
      </div></div></div>`;
  }
  const keep = $('#wk-body') ? $('#wk-body').scrollTop : null;
  $('#cal-main').innerHTML = h;
  if ($('#wk-body')) $('#wk-body').scrollTop = keep ?? 7 * HOUR;
  $('#cal-today').onclick = () => { CAL.date = new Date(); renderCalSide(); loadCal(); };
  const step = n => { const d = CAL.date; CAL.date = CAL.view === 'month' ? new Date(d.getFullYear(), d.getMonth() + n, 1) : addDays(d, n * (CAL.view === 'day' ? 1 : 7)); renderCalSide(); loadCal(); };
  $('#cal-prev').onclick = () => step(-1); $('#cal-next').onclick = () => step(1);
  $('#cal-back').onclick = () => closeOverlay();
  $$('#cal-main [data-view]').forEach(b => b.onclick = () => { CAL.view = b.dataset.view; calSave(); renderCalSide(); loadCal(); });
  $$('#cal-main [data-gotoday]').forEach(b => b.onclick = e => { e.stopPropagation(); CAL.date = parseLocal(b.dataset.gotoday); CAL.view = 'day'; calSave(); renderCalSide(); loadCal(); });
  $$('#cal-main [data-ev]').forEach(b => b.onclick = e => { e.stopPropagation(); calShow(b.dataset.ev); });
  $$('#cal-main [data-order]').forEach(b => b.onclick = e => { e.stopPropagation(); closeOverlay(); openOrder(b.dataset.order); });
  $$('#cal-main .wk-col').forEach(col => col.onclick = e => {
    if (e.target.closest('.ev')) return;
    const r = col.getBoundingClientRect(), min = Math.floor((e.clientY - r.top) / HOUR * 2) * 30, d = parseLocal(col.dataset.colday);
    d.setMinutes(min); calEdit({ start: isoLocal(d), end: isoLocal(new Date(+d + 3600000)) });
  });
  $$('#cal-main .adcell').forEach(c => c.ondblclick = e => { if (e.target.closest('.ev')) return; const d = parseLocal(c.dataset.adday); calEdit({ allday: true, start: isoLocal(d), end: isoLocal(addDays(d, 1)) }); });
  $$('#cal-main .mcell').forEach(c => c.ondblclick = e => { if (e.target.closest('.ev, .mnum, .more')) return; const d = parseLocal(c.dataset.cell); d.setHours(9); calEdit({ start: isoLocal(d), end: isoLocal(new Date(+d + 3600000)) }); });
}
async function calShow(id) {
  const ev0 = CAL.events.find(x => x.id === id) || {};
  let ev = ev0;
  try { ev = { ...ev0, ...(await api('cal_event', id)), cal: ev0.cal }; } catch (e) { toast(e.message); }
  const cal = CAL.info.calendars.find(c => c.id === ev.cal) || {};
  const s = parseLocal(ev.start), nr = ev.order_nr || ev.offerte_nr;
  const r = await dialog(`<form class="evshow"><h2><span class="swatch" style="--c:${esc(calColor(ev.cal))}"></span> ${esc(ev.subject)}</h2>
    <div class="kv"><span>Wanneer</span><b>${esc(DAYS_NL[s.getDay()] + ' ' + s.getDate() + ' ' + MONTHS_NL[s.getMonth()])} · ${esc(evTime(ev))}</b></div>
    ${ev.location ? `<div class="kv"><span>Waar</span><b>${esc(ev.location)}</b></div>` : ''}
    <div class="kv"><span>Agenda</span><span>${esc(cal.name || '')} · ${esc(cal.account || '')}</span></div>
    ${ev.organizer && !ev.is_organizer ? `<div class="kv"><span>Organisator</span><span>${esc(ev.organizer)}</span></div>` : ''}
    ${ev.attendees && ev.attendees.length ? `<div class="kv"><span>Genodigden</span><span>${ev.attendees.map(esc).join(', ')}</span></div>` : ''}
    ${ev.recurring ? '<p class="note">Terugkerende afspraak: wijzigen geldt alleen voor deze keer.</p>' : ''}
    ${nr ? `<div class="row"><span class="badge ${ev.order_nr ? 'order' : 'off'}">${esc(nr)}</span><button type="button" class="btn small" data-c="pz">Openen in Plakzicht</button></div>` : ''}
    ${ev.body ? `<div class="evbody">${sanitize(ev.body)}</div>` : ev.preview ? `<p class="note">${esc(ev.preview)}</p>` : ''}
    <div class="dlgbtns">${ev.online ? `<button type="button" class="btn" data-c="join">Deelnemen</button>` : ''}${ev.web ? `<button type="button" class="btn" data-c="web">Openen in Outlook</button>` : ''}
      ${cal.can_edit !== false ? `<button type="button" class="btn danger" data-c="del">Verwijderen</button><button type="button" class="btn primary" data-c="edit">Bewerken</button>` : ''}
      <button type="button" class="btn" data-cancel>Sluiten</button></div></form>`, (d, done) => {
    $$('[data-c]', d).forEach(b => b.onclick = () => done(b.dataset.c));
  });
  if (r === 'pz') { closeOverlay(); openOrder(nr); }
  if (r === 'web') openExternal(ev.web);
  if (r === 'join') openExternal(ev.online);
  if (r === 'edit') calEdit(ev);
  if (r === 'del') {
    const ok = await dialog(`<form><h2>Afspraak verwijderen?</h2><p class="muted">“${esc(ev.subject)}”${ev.attendees && ev.attendees.length ? '. Genodigden krijgen bericht dat de afspraak niet doorgaat' : ''}${isMs() ? ' (ook in Outlook)' : ''}.</p>
      <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Verwijderen</button></div></form>`);
    if (ok) await run(async () => { await api('cal_delete', id); toast('Afspraak verwijderd'); await loadCal(); });
  }
}
async function ensureCalInfo() { if (!CAL.info) { CAL.info = await api('cal_info'); if (!CAL.on) CAL.on = new Set(CAL.info.calendars.map(c => c.id)); } return CAL.info; }
async function calEdit(ev, opts = {}) {
  let info; try { info = await ensureCalInfo(); } catch (e) { return toast(e.message); }
  const cals = info.calendars.filter(c => c.can_edit);
  if (!cals.length) return toast(info.errors.length ? info.errors[0].error : 'Er is geen agenda waarin je afspraken kunt maken.');
  const isNew = !ev.id;
  const now = new Date(); now.setMinutes(0, 0, 0); now.setHours(now.getHours() + 1);
  const st = ev.start ? parseLocal(ev.start) : now, en = ev.end ? parseLocal(ev.end) : new Date(+st + 3600000);
  if (ev.allday) en.setDate(en.getDate() - 1);  // eind = laatste dag (inclusief)
  const defCal = ev.cal && cals.some(c => c.id === ev.cal) ? ev.cal : (opts.preferUpn && (cals.find(c => c.default && c.upn && opts.preferUpn.includes(c.upn.toLowerCase())) || {}).id) || (cals.find(c => c.default) || cals[0]).id;
  const order = ev.order_nr || ev.offerte_nr || opts.order || '';
  const ds = d => isoLocal(d).slice(0, 10), ts = d => isoLocal(d).slice(11, 16);
  const f = await dialog(`<form class="evedit"><h2>${isNew ? 'Nieuwe afspraak' : 'Afspraak bewerken'}</h2><div class="form">
    <label>Onderwerp<input name="subject" required value="${esc(ev.subject || opts.subject || '')}" maxlength="250"></label>
    ${isNew && cals.length > 1 ? `<label>Agenda<select name="cal">${cals.map(c => `<option value="${esc(c.id)}" ${c.id === defCal ? 'selected' : ''}>${esc(c.account)} · ${esc(c.name)}</option>`).join('')}</select></label>` : `<input type="hidden" name="cal" value="${esc(defCal)}">`}
    <div class="checks"><label><input type="checkbox" name="allday" ${ev.allday ? 'checked' : ''}> Hele dag</label></div>
    <div class="row evtimes"><label>Begin<input type="date" name="sd" required value="${ds(st)}"></label><label class="tm">&nbsp;<input type="time" name="stt" step="900" value="${ts(st)}"></label>
      <label>Einde<input type="date" name="ed" required value="${ds(en)}"></label><label class="tm">&nbsp;<input type="time" name="ett" step="900" value="${ts(en)}"></label></div>
    <label>Locatie<input name="location" value="${esc(ev.location || '')}" placeholder="Bijvoorbeeld: bij de klant, telefonisch"></label>
    <div class="acwrap"><label>Genodigden (mailadressen, met komma's; zij krijgen een uitnodiging)<input name="attendees" id="ev-att" autocomplete="off" value="${esc((ev.attendees || []).join(', '))}"></label>
      ${opts.sender ? `<button type="button" class="linkish" id="ev-sender">+ ${esc(opts.sender)} uitnodigen</button>` : ''}</div>
    <div class="row"><label style="flex:1">Herinnering<select name="reminder">${[['', 'Geen'], ['0', 'Bij begin'], ['5', '5 minuten'], ['15', '15 minuten'], ['30', '30 minuten'], ['60', '1 uur'], ['1440', '1 dag']].map(([k, n]) => `<option value="${k}" ${String(ev.reminder ?? (isNew ? 15 : '')) === k ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
      <label style="flex:1">Weergeven als<select name="show_as">${[['busy', 'Bezet'], ['tentative', 'Voorlopig'], ['free', 'Vrij'], ['oof', 'Afwezig'], ['workingElsewhere', 'Werkt elders']].map(([k, n]) => `<option value="${k}" ${(ev.show_as || 'busy') === k ? 'selected' : ''}>${n}</option>`).join('')}</select></label></div>
    <label>Order of offerte uit Plakzicht (optioneel)<input name="order" id="ev-ord" list="ev-ordlist" value="${esc(order)}" placeholder="ordernummer, offerte of klant" autocomplete="off"><datalist id="ev-ordlist"></datalist></label>
    <div><div class="muted" style="font-size:12px;margin-bottom:3px">Notities</div><div class="sigedit evnotes" id="ev-body" contenteditable="true">${sanitize(ev.body || opts.body || '')}</div></div>
    ${ev.recurring ? '<p class="note">Terugkerende afspraak: je wijzigt alleen deze keer.</p>' : ''}
    </div><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">${isNew ? 'Opslaan' : 'Wijzigingen opslaan'}</button></div></form>`, d => {
    const sync = () => { const on = $('[name=allday]', d).checked; $$('.tm', d).forEach(x => x.hidden = on); };
    $('[name=allday]', d).onchange = sync; sync();
    $('[name=sd]', d).onchange = () => { const a = $('[name=sd]', d), b = $('[name=ed]', d); if (b.value < a.value) b.value = a.value; };
    let ot; $('#ev-ord', d).oninput = e => { clearTimeout(ot); ot = setTimeout(async () => { try { const r = await api('search_plakzicht', e.target.value);
      $('#ev-ordlist', d).innerHTML = r.slice(0, 12).map(x => `<option value="${esc(x.nr)}">${esc(x.klant)} (${x.soort})</option>`).join(''); } catch { /* */ } }, 200); };
    if ($('#ev-sender', d)) $('#ev-sender', d).onclick = () => { const i = $('#ev-att', d); i.value = (i.value.trim() ? i.value.replace(/[,;\s]*$/, '') + ', ' : '') + opts.sender; $('#ev-sender', d).remove(); };
    autocomplete($('#ev-att', d));
    $('[name=subject]', d).focus();
  });
  if (!f) return;
  const allday = f.has('allday');
  let start = f.get('sd') + 'T' + (allday ? '00:00' : f.get('stt') || '09:00'), end = f.get('ed') + 'T' + (allday ? '00:00' : f.get('ett') || '10:00');
  if (allday) end = isoLocal(addDays(parseLocal(end), 1));
  const body = sanitize($('#ev-body') ? $('#ev-body').innerHTML : (ev.body || ''));
  await run(async () => {
    await api('cal_save', { id: ev.id || null, cal: f.get('cal'), subject: f.get('subject'), start, end, allday, location: f.get('location'),
      attendees: f.get('attendees'), reminder: f.get('reminder'), show_as: f.get('show_as'), order_nr: (f.get('order') || '').trim().split(/\s/)[0], body });
    toast(isNew ? (f.get('attendees').trim() ? 'Afspraak gemaakt; uitnodigingen zijn verstuurd' : 'Afspraak gemaakt') : 'Afspraak bijgewerkt');
    if (!$('#overlay').hidden && $('#cal-main')) { CAL.date = parseLocal(start); renderCalSide(); await loadCal(); }
    else calTodayCache = null, renderPz();
  });
}
// Afspraak maken vanuit een mail (met de order erin)
async function meetingFromMail(id) {
  const m = S.mail && S.mail.id === id ? S.mail : await run(() => api('get_mail', id)); if (!m) return;
  const mb = mailboxById(m.mailbox_id);
  const subj = String(m.subject || '').replace(/^\s*((re|fw|fwd|antw)\s*:\s*)+/i, '');
  calEdit({}, { subject: subj, order: m.order_nr || m.offerte_nr || '', sender: m.folder_wk === 'sent' ? null : m.from_addr, preferUpn: mb ? mb.address.toLowerCase() : '',
    body: `<p>Naar aanleiding van de mail van ${esc(m.from_name || m.from_addr)} (${esc(fmtDate(m.date, true))}): “${esc(m.subject || '')}”.</p>` });
}
// Vandaag in de agenda, in het Plakzicht-paneel als er geen mail open is
let calTodayCache = null;
async function todayHtml() {
  if (calTodayCache && Date.now() - calTodayCache.t < 120000) return calTodayCache.h;
  try {
    const info = await ensureCalInfo(); if (!info.calendars.length) return '';
    const d = dayStart(new Date()), ids = info.calendars.map(c => c.id).filter(id => !CAL.on || CAL.on.has(id));
    const r = await api('cal_events', isoLocal(d), isoLocal(addDays(d, 1)), ids);
    const o = await api('cal_orders', isoLocal(d), isoLocal(addDays(d, 1)));
    const evs = r.events.sort((a, b) => (b.allday - a.allday) || a.start.localeCompare(b.start));
    const h = `<div class="panel today"><h2>${ICON.calendar} Vandaag <small><button class="linkish" id="pz-cal">Agenda openen</button></small></h2>
      ${o.map(x => `<div class="kv"><button class="linkish" data-open="${esc(x.nr)}">Verzenden #${esc(x.nr.replace(/^0+/, ''))}</button><span class="muted">${esc(x.klant)}</span></div>`).join('')}
      ${evs.length ? evs.map(ev => `<button class="tday" data-tev="${esc(ev.id)}" style="--c:${esc(calColor(ev.cal))}"><span>${esc(evTime(ev))}</span><b>${esc(ev.subject)}</b></button>`).join('') : '<p class="note">Geen afspraken meer vandaag.</p>'}</div>`;
    calTodayCache = { t: Date.now(), h }; return h;
  } catch { return ''; }
}

// ------------------------------------------------------------ sneltoetsen
document.addEventListener('keydown', e => {
  if (!S.st || $('#app').hidden || $('#dlg').open || $('.cmenu.root')) return;
  if (!$('#overlay').hidden) return;
  if (e.target.closest('input, textarea, select, [contenteditable=true]')) return;
  const ctrl = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
  if (ctrl && k === 'n' && !S.popout) { e.preventDefault(); return openCompose({ mode: 'new' }); }
  if (ctrl && k === 'a' && !S.popout) { e.preventDefault(); return selAll(); }
  if (e.key === 'Escape' && S.multi.size) { e.preventDefault(); return selClear(); }
  if (!S.sel) return;
  const map = { r: e.shiftKey ? 'replyall' : 'reply', f: 'forward', q: 'read', u: 'unread' };
  if (ctrl && map[k]) { e.preventDefault(); return doAct(map[k], S.sel); }
  if (!ctrl && e.key === 'Delete') { e.preventDefault(); return doAct('delete', S.sel); }
  if (!ctrl && e.key === 'Backspace') { e.preventDefault(); return doAct('archive', S.sel); }
  if (!ctrl && e.key === 'Insert') { e.preventDefault(); return doAct('flag', S.sel); }
  if (S.popout) return;
  if (!ctrl && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
    if (e.shiftKey) { const order = S.shown || [], i = order.indexOf(S.sel), nid = order[i + (e.key === 'ArrowDown' ? 1 : -1)]; if (nid) { e.preventDefault(); if (!S.multi.size) S.anchor = S.sel; S.sel = nid; selRange(nid); } return; }
    if (S.multi.size) selClear(false);
    const order = S.shown || S.mails.map(m => m.id), i = order.indexOf(S.sel), nid = order[i + (e.key === 'ArrowDown' ? 1 : -1)];
    if (nid) { e.preventDefault(); openMail(nid).then(() => { const r = $(`#list .mrow[data-id="${CSS.escape(nid)}"]`); if (r) { r.scrollIntoView({ block: 'nearest' }); r.focus(); } }); }
  }
  if (!ctrl && e.key === 'Enter' && e.target.closest('.mrow')) { e.preventDefault(); popoutMail(S.sel); }
});

async function dropMail(id, t) {
  if (id.startsWith('[')) {
    let ids = []; try { ids = JSON.parse(id); } catch { return; }
    if (t.dataset.drop === 'mb') return bulkAct('moveto', ids, { mb: +t.dataset.mb, folder: t.dataset.folder });
    return bulkAct('labelset', ids, { label: +t.dataset.label, on: true });
  }
  if (t.dataset.drop === 'mb') return doAct('moveto', id, { mb: +t.dataset.mb, folder: t.dataset.folder });
  const row = rowOf(id), lid = +t.dataset.label;
  if (row && row.labels.some(l => l.id === lid)) return toast('Deze mail heeft dat label al');
  return doAct('labelset', id, { label: lid, on: true });
}
async function newLabel(forMail) {
  const f = await dialog(`<form><h2>Nieuw label</h2><div class="form">
    <label>Naam<input name="name" required placeholder="Bijvoorbeeld: Spoed"></label>
    <label>Kleur<input name="color" type="color" value="#1f6fb2" style="height:34px;width:70px;padding:2px"></label></div>
    <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Maken</button></div></form>`);
  if (!f) return;
  await run(async () => {
    const lid = await api('save_label', { name: f.get('name'), color: f.get('color') });
    await refreshState(); toast('Label gemaakt');
    if (forMail) await doAct('labelset', forMail, { label: lid, on: true });
  });
}

// ------------------------------------------------------------ lijst
function periodName(days) { const p = (S.st.periods || []).find(x => x[0] === days); return p ? p[1] : days + ' dagen'; }
async function loadOlder() {
  const b = $('#btn-older'); if (b) { b.disabled = true; b.textContent = 'Bezig…'; }
  await run(async () => {
    const last = S.older && S.older.mails.length ? S.older.mails[S.older.mails.length - 1].date : null;
    const r = await api('list_older', S.view.mailbox_id, S.view.folder, last, S.search || null, S.filter);
    const have = new Set([...S.mails.map(m => m.id), ...(S.older ? S.older.mails.map(m => m.id) : [])]);
    const add = r.mails.map(m => ({ ...m, id: String(m.id) })).filter(m => !have.has(m.id));
    S.older = { mails: [...(S.older ? S.older.mails : []), ...add], more: r.more && add.length > 0 };
  });
  renderList();
}
async function loadList() {
  S.older = null;
  const prevView = JSON.stringify(S.view);
  if (S._lastView !== prevView) { S.multi.clear(); S._lastView = prevView; }
  if (!S.view) { S.mails = []; renderList(); return; }
  await run(async () => { S.mails = (await api('list_mails', { ...S.view, filter: S.filter, search: S.search, sort: P().sort })).map(m => ({ ...m, id: String(m.id) })); });
  pruneSel();
  renderList();
}
function listTitle() {
  const v = S.view;
  if (!v) return 'Geen mailbox';
  if (v.label_id) { const l = S.st.labels.find(x => x.id === v.label_id); return esc(l ? l.name : 'Label') + ' <small>alle mailboxen</small>'; }
  const mb = mailboxById(v.mailbox_id), f = folderOf(v.mailbox_id, v.folder);
  return esc(mb ? mb.display : '') + ' · ' + esc(f ? f.name : FOLDER_NAMES[v.folder] || '');
}
function initials(n) { return String(n || '?').split(/\s+/).map(x => x[0]).join('').slice(0, 2).toUpperCase(); }
function collabChips(m) {
  let h = '';
  if (m.claim) h += `<span class="badge claim ${m.claim.mine ? 'mine' : ''}" title="Opgepakt door ${esc(m.claim.mine ? 'jou' : m.claim.name)}">${ICON.hand}${esc(m.claim.mine ? 'jij' : m.claim.name.split(' ')[0])}</span>`;
  if (m.busy) h += m.busy.map(b => `<span class="badge busy ${b.state === 'antwoordt' ? 'replying' : ''}" title="${esc(b.name)} ${b.state === 'antwoordt' ? 'is aan het beantwoorden' : 'heeft deze mail open'}">${b.state === 'antwoordt' ? ICON.pen : ICON.eye}${esc(initials(b.name))}</span>`).join('');
  if (m.replied) h += `<span class="badge replied" title="${esc(m.replied.action === 'doorgestuurd' ? 'Doorgestuurd' : 'Beantwoord')} door ${esc(m.replied.name)}, ${fmtDate(new Date(m.replied.at * 1000).toISOString(), true)}">${ICON[m.replied.action === 'doorgestuurd' ? 'forward' : 'reply']}${esc(m.replied.name.split(' ')[0])}</span>`;
  return h;
}
// ------------------------------------------------------------ voorkeuren per gebruiker (kolommen, sorteren, scheidingsbalken, antwoorden)
const P = () => S.st.user.prefs;
let prefT;
function savePrefs(patch, quiet) {
  Object.assign(S.st.user.prefs, patch);
  clearTimeout(prefT);
  prefT = setTimeout(() => api('set_prefs', patch).then(p => { S.st.user.prefs = p; }).catch(e => !quiet && toast(e.message)), 250);
}

// ------------------------------------------------------------ lijst: kolommen, sorteren en groeperen (zoals Outlook)
const COLDEF = {
  imp: { h: () => ICON.bang, t: 'Urgentie', w: 24, s: 'importance', icon: 1 },
  rem: { h: () => ICON.bell, t: 'Herinnering (opvolgdatum)', w: 26, s: 'due', icon: 1 },
  type: { h: () => ICON.mail, t: 'Pictogram: ongelezen, gelezen, beantwoord of doorgestuurd', w: 26, s: 'read', icon: 1 },
  att: { h: () => ICON.clip, t: 'Bijlage', w: 24, s: 'att', icon: 1 },
  from: { h: () => sentView() ? 'Aan' : 'Van', w: 140, s: () => sentView() ? 'to' : 'from' },
  subj: { h: () => 'Onderwerp', w: 0, min: 120, s: 'subject' },
  date: { h: () => sentView() ? 'Verzonden' : 'Ontvangen', w: 96, s: 'date' },
  size: { h: () => 'Grootte', w: 60, s: 'size', right: 1 },
  cats: { h: () => 'Categorieën', w: 100, s: 'cats' },
  mention: { h: () => '@', t: 'Vermelding: jouw naam met @ in de mail', w: 26, s: 'mention', icon: 1 },
  flag: { h: () => ICON.flag, t: 'Vlag en opvolgen', w: 26, s: 'flag', icon: 1 },
  order: { h: () => 'Order/offerte', w: 112, s: 'order' },
  claim: { h: () => 'Opgepakt door', w: 112, s: 'claim' },
  mailbox: { h: () => 'Mailbox', w: 100, s: 'mailbox' },
};
const COL_NAMES = { imp: 'Urgentie (!)', rem: 'Herinnering', type: 'Pictogram', att: 'Bijlage', from: 'Van / Aan', subj: 'Onderwerp', date: 'Ontvangen', size: 'Grootte',
  cats: 'Categorieën (labels)', mention: 'Vermelding (@)', flag: 'Vlag', order: 'Order/offerte (Plakzicht)', claim: 'Opgepakt door', mailbox: 'Mailbox' };
const DEFAULT_COLS = ['imp', 'rem', 'type', 'att', 'from', 'subj', 'date', 'size', 'cats', 'mention', 'flag'];
const SORT_NAMES = { date: 'Datum', from: 'Van', to: 'Aan', subject: 'Onderwerp', size: 'Grootte', importance: 'Urgentie', due: 'Opvolgdatum', read: 'Gelezen',
  att: 'Bijlage', cats: 'Categorieën', mention: 'Vermelding', flag: 'Vlag', order: 'Order/offerte', claim: 'Opgepakt door', mailbox: 'Mailbox' };
const FILTERS = [['alle', 'Alle'], ['ongelezen', 'Ongelezen'], ['gemarkeerd', 'Met vlag'], ['bijlage', 'Met bijlage'], ['vermeld', 'Vermeld (@)'],
  ['mijn', 'Opgepakt door mij'], ['vrij', 'Nog niet opgepakt'], ['zonder_order', 'Zonder order']];
const sentView = () => { const f = S.view && S.view.mailbox_id ? folderOf(S.view.mailbox_id, S.view.folder) : null; return !!(f && (f.wk === 'sent' || f.wk === 'drafts')); };
const colSortKey = k => { const s = COLDEF[k].s; return typeof s === 'function' ? s() : s; };
const colW = k => (P().colw || {})[k] || COLDEF[k].w;
const whoOf = m => m.folder_wk === 'sent' || m.folder_wk === 'drafts' ? (m.to_addr || '') : (m.from_name || m.from_addr || '');
const normSubj = s => String(s || '').replace(/^\s*((re|fw|fwd|antw|doorst)\s*:\s*)+/i, '').trim().toLowerCase();
const isoDay = d => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');

function sortVal(m, key) {
  switch (key) {
    case 'date': return m.date || '';
    case 'from': return whoOf(m).toLowerCase();
    case 'to': return (m.to_addr || '').toLowerCase();
    case 'subject': return normSubj(m.subject);
    case 'size': return m.size || 0;
    case 'importance': return m.importance === 'high' ? 2 : m.importance === 'low' ? 0 : 1;
    case 'due': return m.flagged && m.flag_due ? m.flag_due : m.flagged ? '9999' : '';
    case 'read': return m.is_read ? 1 : 0;
    case 'att': return m.has_attachments ? 1 : 0;
    case 'cats': return m.labels.length ? m.labels[0].name.toLowerCase() : '';
    case 'mention': return m.mention ? 1 : 0;
    case 'flag': return m.flagged ? 2 : m.flag_done ? 1 : 0;
    case 'order': return m.order_nr || m.offerte_nr || '';
    case 'claim': return m.claim ? m.claim.name.toLowerCase() : '';
    case 'mailbox': return (m.mailbox || '').toLowerCase();
  }
  return '';
}
function sortMails(list) {
  const { key, dir } = P().sort, f = dir === 'asc' ? 1 : -1;
  return [...list].sort((a, b) => {
    const x = sortVal(a, key), y = sortVal(b, key);
    const r = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'nl');
    if (r) return r * f;
    return -String(a.date || '').localeCompare(String(b.date || ''));  // daarna nieuwste eerst
  });
}
const DAYNAMES = ['Zondag', 'Maandag', 'Dinsdag', 'Woensdag', 'Donderdag', 'Vrijdag', 'Zaterdag'];
function groupOf(m, key) {
  switch (key) {
    case 'date': {
      if (!m.date) return 'Zonder datum';
      const d = new Date(m.date), t0 = new Date(); t0.setHours(0, 0, 0, 0);
      const dd = new Date(d); dd.setHours(0, 0, 0, 0);
      const days = Math.round((t0 - dd) / 86400000);
      if (days <= 0) return 'Vandaag';
      if (days === 1) return 'Gisteren';
      if (days < 7) return DAYNAMES[d.getDay()];
      return 'Ouder';
    }
    case 'from': return whoOf(m) || '(onbekend)';
    case 'to': return m.to_addr || '(geen ontvanger)';
    case 'subject': return m.subject ? m.subject.replace(/^\s*((re|fw|fwd|antw|doorst)\s*:\s*)+/i, '') || '(geen onderwerp)' : '(geen onderwerp)';
    case 'size': { const s = m.size || 0; return !s ? 'Onbekend' : s < 25600 ? 'Klein (minder dan 25 kB)' : s < 102400 ? 'Gemiddeld (25 tot 100 kB)' : s < 1048576 ? 'Groot (100 kB tot 1 MB)' : 'Zeer groot (meer dan 1 MB)'; }
    case 'importance': return m.importance === 'high' ? 'Urgentie: hoog' : m.importance === 'low' ? 'Urgentie: laag' : 'Urgentie: normaal';
    case 'due': {
      if (!m.flagged) return 'Geen vlag';
      if (!m.flag_due) return 'Zonder datum';
      const today = isoDay(new Date()), tm = new Date(); tm.setDate(tm.getDate() + 1);
      if (m.flag_due < today) return 'Te laat';
      if (m.flag_due === today) return 'Vandaag';
      if (m.flag_due === isoDay(tm)) return 'Morgen';
      return 'Later: ' + fmtDay(m.flag_due);
    }
    case 'read': return m.is_read ? 'Gelezen' : 'Ongelezen';
    case 'att': return m.has_attachments ? 'Met bijlage' : 'Zonder bijlage';
    case 'cats': return m.labels.length ? m.labels[0].name : 'Geen categorie';
    case 'mention': return m.mention ? 'Jij wordt vermeld' : 'Niet vermeld';
    case 'flag': return m.flagged ? 'Met vlag' : m.flag_done ? 'Voltooid' : 'Zonder vlag';
    case 'order': return m.order_nr ? 'Order ' + m.order_nr : m.offerte_nr ? 'Offerte ' + m.offerte_nr : 'Geen order of offerte';
    case 'claim': return m.claim ? 'Opgepakt door ' + (m.claim.mine ? 'jou' : m.claim.name) : 'Niet opgepakt';
    case 'mailbox': return m.mailbox || '';
  }
  return '';
}
function setSort(key, dir) {
  const cur = P().sort;
  if (!dir) dir = cur.key === key ? (cur.dir === 'asc' ? 'desc' : 'asc') : (key === 'date' || key === 'size' || key === 'importance' || key === 'flag' ? 'desc' : 'asc');
  savePrefs({ sort: { key, dir } });
  S.gcol = new Set();
  if (isMs() && ['date', 'from', 'to', 'subject', 'size', 'importance', 'due', 'read', 'att', 'cats', 'flag'].includes(key)) loadList(); else renderList();
}
function fmtCol(iso) {
  if (!iso) return '';
  const d = new Date(iso), now = new Date(), hm = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  if (d.toDateString() === now.toDateString()) return hm;
  if ((now - d) / 86400000 < 6.5) return DN[d.getDay()] + ' ' + hm;
  return DN[d.getDay()] + ' ' + String(d.getDate()).padStart(2, '0') + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + d.getFullYear();
}
function sizeCell(b) { if (!b) return ''; return b < 1048576 ? Math.max(1, Math.round(b / 1024)) + ' kB' : (b / 1048576).toFixed(1).replace('.', ',') + ' MB'; }
function typeIcon(m) {
  if (m.replied) return `<span class="ti ${m.replied.action === 'doorgestuurd' ? 'fw' : 're'}" title="${esc(m.replied.action === 'doorgestuurd' ? 'Doorgestuurd' : 'Beantwoord')} door ${esc(m.replied.name)}">${ICON[m.replied.action === 'doorgestuurd' ? 'forward' : 'reply']}</span>`;
  return `<span class="ti" title="${m.is_read ? 'Gelezen' : 'Ongelezen'}">${m.is_read ? ICON.mailOpen : ICON.mail}</span>`;
}
function flagCell(m) {
  const t = m.flagged ? 'Vlag' + (m.flag_due ? ' · opvolgen ' + fmtDay(m.flag_due) : '') + ' (klik: opvolgen)' : m.flag_done ? 'Voltooid' : 'Vlag zetten (Insert)';
  return `<button class="rowflag ${m.flag_done ? 'done' : ''}" data-flag="${m.id}" title="${esc(t)}" aria-label="${esc(t)}">${m.flag_done ? ICON.check : ICON.flag}</button>`;
}
function cell(m, k) {
  switch (k) {
    case 'imp': return m.importance === 'high' ? `<span class="imp hi" title="Urgentie: hoog">!</span>` : m.importance === 'low' ? `<span class="imp lo" title="Urgentie: laag">↓</span>` : '';
    case 'rem': return m.flagged && m.flag_due ? `<span class="rem ${m.flag_due < isoDay(new Date()) ? 'late' : ''}" title="Opvolgen: ${esc(fmtDay(m.flag_due))}">${ICON.bell}</span>` : '';
    case 'type': return typeIcon(m);
    case 'att': return m.has_attachments ? `<span class="att" title="Met bijlage">${ICON.clip}</span>` : '';
    case 'from': return `<span class="ell">${esc(whoOf(m))}</span>${collabChips({ ...m, replied: null, claim: P().cols.includes('claim') ? null : m.claim })}`;
    case 'subj': return `<span class="ell">${draftOf(m.id) ? '<span class="draftmark">[Concept]</span> ' : ''}${esc(m.subject || '(geen onderwerp)')}</span>`;
    case 'date': return esc(fmtCol(m.date));
    case 'size': return esc(sizeCell(m.size));
    case 'cats': return m.labels.map(l => labelBadge(l)).join('');
    case 'mention': return m.mention ? '<span class="at" title="Je wordt vermeld">@</span>' : '';
    case 'flag': return flagCell(m);
    case 'order': return m.order_nr ? `<span class="badge order">#${esc(m.order_nr.replace(/^0+/, ''))}</span>` : m.offerte_nr ? `<span class="badge off">${esc(m.offerte_nr)}</span>` : '';
    case 'claim': return m.claim ? `<span class="badge claim ${m.claim.mine ? 'mine' : ''}">${ICON.hand}${esc(m.claim.mine ? 'jij' : m.claim.name)}</span>` : '';
    case 'mailbox': return esc(m.mailbox || '');
  }
  return '';
}
function colsTemplate(cols) { return '28px ' + cols.map(k => k === 'subj' ? `minmax(${COLDEF.subj.min}px, 1fr)` : colW(k) + 'px').join(' '); }
function colsNeeded(cols) { return cols.reduce((t, k) => t + (k === 'subj' ? COLDEF.subj.min : colW(k)), 0) + 58; }

function listMode() {
  const cols = P().cols && P().cols.length ? P().cols : DEFAULT_COLS;
  if (P().listview !== 'kolommen') return { mode: 'compact', cols };
  const w = $('#list').clientWidth;
  return { mode: w && w < colsNeeded(cols) ? 'compact' : 'kolommen', narrow: w && w < colsNeeded(cols), cols };
}
let lastMode = null;
new ResizeObserver(() => { if (!S.st || S.popout) return; const m = listMode().mode; if (lastMode && m !== lastMode) renderList(); }).observe($('#list'));

function filterPills() {
  const main = ['alle', 'ongelezen', 'gemarkeerd', 'zonder_order'];
  let h = FILTERS.filter(([k]) => main.includes(k)).map(([k, n]) => `<button class="pill ${S.filter === k ? 'on' : ''}" data-filter="${k}">${n}</button>`).join('');
  if (!main.includes(S.filter)) { const f = FILTERS.find(x => x[0] === S.filter); h += `<button class="pill on" data-filter="alle" title="Filter weghalen">${esc(f ? f[1] : S.filter)} ×</button>`; }
  return h;
}
function renderList() {
  if (!S.st) return;
  const fv = S.view && S.view.mailbox_id ? folderOf(S.view.mailbox_id, S.view.folder) : null;
  const syncNote = isMs() && fv && fv.synced === false ? '<span class="syncnote" title="Deze map staat nog niet in de lokale kopie; hij wordt nu rechtstreeks bij Microsoft opgehaald en op de achtergrond bewaard.">wordt gesynchroniseerd…</span>' : '';
  const { mode, cols, narrow } = listMode(); lastMode = mode;
  const so = P().sort, groups = P().groups;
  const sortBtn = `<button class="sortbtn" id="btn-sort" title="Sorteren en groeperen">${esc(SORT_NAMES[so.key] || so.key)} ${so.dir === 'asc' ? '↑' : '↓'}</button>`;
  let h = `<div class="listhead"><h1>${listTitle()} <small>${S.mails.length} ${S.mails.length === 1 ? 'mail' : 'mails'}</small>${syncNote}
    <span class="lh-right">${mode === 'compact' ? sortBtn : ''}<button class="iconbtn sm" id="btn-refresh" title="Vernieuwen" aria-label="Vernieuwen">${ICON.refresh}</button></span></h1>
    <div class="filters">${filterPills()}${narrow ? '<button class="linkish narrowhint" id="btn-widen" title="De kolommen passen niet in deze breedte; daarom de compacte weergave">Kolommen passen niet: lijst breder maken</button>' : ''}</div></div>`;
  if (mode === 'kolommen') {
    h += `<div class="chdr" role="row" style="--cols:${colsTemplate(cols)}"><div class="ch ic"><button class="selbox ${S.multi.size && S.multi.size === S.mails.length ? 'on' : S.multi.size ? 'part' : ''}" id="btn-selall" role="checkbox" aria-checked="${S.multi.size ? 'true' : 'false'}" title="Alles selecteren (Ctrl+A)" aria-label="Alles selecteren">${ICON.check}</button></div>${cols.map(k => {
      const d = COLDEF[k], sk = colSortKey(k), on = so.key === sk;
      return `<div class="ch ${d.icon ? 'ic' : ''} ${d.right ? 'r' : ''} ${on ? 'on' : ''}" data-col="${k}" role="columnheader" aria-sort="${on ? (so.dir === 'asc' ? 'ascending' : 'descending') : 'none'}" title="${esc((d.t || COL_NAMES[k]) + ' — klik om te sorteren')}" tabindex="0">
        <span class="chl">${d.h()}</span>${on ? `<span class="arrow">${so.dir === 'asc' ? '▲' : '▼'}</span>` : ''}${k !== 'subj' ? `<span class="rz" data-rz="${k}"></span>` : ''}</div>`;
    }).join('')}<button class="ch ic fbtn" id="btn-colmenu" title="Filteren, kolommen en scheidingsbalken" aria-label="Filteren, kolommen en scheidingsbalken">${ICON.funnel}</button></div>`;
  }
  if (!S.mails.length && !S.older) h += `<div class="empty">${S.search ? 'Niets gevonden voor “' + esc(S.search) + '”.' : S.filter !== 'alle' ? 'Geen mails met dit filter.' : 'Geen mails in deze map.'}</div>`;
  const mbv = S.view && S.view.mailbox_id ? mailboxById(S.view.mailbox_id) : null;
  const canOlder = isMs() && mbv && fv && fv.synced && (mbv.cache_days || 0) > 0;
  const sorted = sortMails(S.mails);
  S.shown = [];
  let grp = null, gcount = {};
  if (groups) for (const m of sorted) { const g = groupOf(m, so.key); gcount[g] = (gcount[g] || 0) + 1; }
  S.gcol = S.gcol || new Set();
  const rowHtml = m => {
    S.shown.push(m.id);
    const picked = S.multi.has(m.id);
    const cls = `mrow ${m.is_read ? '' : 'unread'} ${m.flagged ? 'flagged' : ''} ${(S.multi.size ? picked : S.sel === m.id) ? 'sel' : ''} ${picked ? 'msel' : ''} ${m.importance === 'high' ? 'hi' : ''}`;
    const sb = `<button class="selbox ${picked ? 'on' : ''}" data-selbox="${esc(m.id)}" role="checkbox" aria-checked="${picked}" title="Selecteren (Ctrl+klik)" aria-label="Selecteren" tabindex="-1">${ICON.check}</button>`;
    if (mode === 'kolommen') return `<div class="${cls} crow" style="--cols:${colsTemplate(cols)}" draggable="true" data-id="${esc(m.id)}" tabindex="0" role="row" aria-label="${esc(whoOf(m) + ': ' + m.subject)}">
      <span class="c c-sel">${sb}</span>${cols.map(k => `<span class="c c-${k} ${COLDEF[k].right ? 'r' : ''}">${cell(m, k)}</span>`).join('')}<span class="c"></span></div>`;
    let chips = '';
    if (m.order_nr) chips += `<span class="badge order" title="Gekoppeld aan order">#${esc(m.order_nr.replace(/^0+/, ''))}</span>`;
    if (m.offerte_nr) chips += `<span class="badge off" title="Gekoppeld aan offerte">${esc(m.offerte_nr)}</span>`;
    chips += m.labels.map(l => labelBadge(l)).join('');
    if (S.view.label_id) chips += `<span class="badge">${esc(m.mailbox)}</span>`;
    chips += collabChips(m);
    const pre = (m.importance === 'high' ? '<span class="imp hi" title="Urgentie: hoog">!</span>' : '') + (m.has_attachments ? `<span class="att" title="Met bijlage">${ICON.clip}</span>` : '') + (m.mention ? '<span class="at" title="Je wordt vermeld">@</span>' : '');
    return `<div class="${cls}" draggable="true" data-id="${esc(m.id)}" tabindex="0" role="button" aria-label="${esc(whoOf(m) + ': ' + m.subject)}">${sb}
      <span class="from">${pre}${esc(whoOf(m))}</span>
      <span class="date">${m.flagged && m.flag_due ? `<span class="rem ${m.flag_due < isoDay(new Date()) ? 'late' : ''}" title="Opvolgen: ${esc(fmtDay(m.flag_due))}">${ICON.bell}</span>` : ''}${fmtDate(m.date)}${flagCell(m)}</span>
      <span class="subj">${draftOf(m.id) ? '<span class="draftmark">[Concept]</span> ' : ''}${esc(m.subject || '(geen onderwerp)')}</span>
      <span class="snip">${esc(m.snippet)}</span><span class="chips">${chips}</span></div>`;
  };
  for (const m of sorted) {
    if (groups) {
      const g = groupOf(m, so.key);
      if (g !== grp) {
        grp = g; const closed = S.gcol.has(g);
        h += `<button class="grp ${closed ? 'closed' : ''}" data-grp="${esc(g)}" aria-expanded="${!closed}">${closed ? ICON.chev : ICON.chevDown}<span>${esc(g)}</span><span class="gn">${gcount[g]}</span></button>`;
      }
      if (S.gcol.has(g)) continue;
    }
    h += rowHtml(m);
  }
  if (S.older) {
    h += `<div class="oldsep">Ouder dan ${esc(periodName(mbv.cache_days).toLowerCase())}: rechtstreeks bij Microsoft</div>`;
    if (!S.older.mails.length) h += '<div class="empty">Geen oudere mails gevonden.</div>';
    for (const m of S.older.mails) h += rowHtml(m);
  }
  if (canOlder && (!S.older || S.older.more)) h += `<div class="olderbox"><button class="btn small" id="btn-older">${S.older ? 'Nog oudere mails ophalen' : S.search ? 'Ook in oudere mails zoeken bij Microsoft' : 'Oudere mails ophalen bij Microsoft'}</button>
    ${S.older ? '' : `<div class="note">De lokale kopie bevat de mails van ${esc(periodName(mbv.cache_days).toLowerCase())}.</div>`}</div>`;
  const keepScroll = $('#list').scrollTop;
  if (!morph($('#list'), h)) return;  // niets veranderd: regels en knoppen blijven staan
  $('#list').scrollTop = keepScroll;
  $('#list').classList.toggle('cols', mode === 'kolommen');
  const lh = $('#list .listhead'); if (lh) $('#list').style.setProperty('--lh', lh.offsetHeight + 'px');
  if ($('#btn-older')) $('#btn-older').onclick = loadOlder;
  if ($('#btn-widen')) $('#btn-widen').onclick = () => {
    setLayout({ list: clampCol('list', colsNeeded(cols) + 4) });
    setTimeout(() => { if (listMode().mode !== 'kolommen') toast('Nog steeds te smal. Verberg het Plakzicht-paneel of de zijbalk (Beeld), of kies minder kolommen.'); renderList(); }, 50);
  };
  $$('#list [data-filter]').forEach(b => b.onclick = () => setFilter(b.dataset.filter));
  if ($('#btn-refresh')) $('#btn-refresh').onclick = refreshAll;
  if ($('#btn-sort')) $('#btn-sort').onclick = () => { const r = $('#btn-sort').getBoundingClientRect(); showMenu(r.left, r.bottom + 4, sortMenu()); };
  if ($('#btn-colmenu')) $('#btn-colmenu').onclick = () => { const r = $('#btn-colmenu').getBoundingClientRect(); showMenu(r.right - 240, r.bottom + 4, viewMenu()); };
  $$('#list .grp').forEach(b => b.onclick = () => { const g = b.dataset.grp; S.gcol.has(g) ? S.gcol.delete(g) : S.gcol.add(g); renderList(); });
  $$('#list .ch[data-col]').forEach(c => {
    c.onclick = e => { if (e.target.classList.contains('rz')) return; setSort(colSortKey(c.dataset.col)); };
    c.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSort(colSortKey(c.dataset.col)); } };
    c.oncontextmenu = e => { e.preventDefault(); showMenu(e.clientX, e.clientY, viewMenu()); };
  });
  $$('#list .rz').forEach(z => !z._wired && (z._wired = true) && z.addEventListener('pointerdown', e => {
    e.preventDefault(); e.stopPropagation(); z.setPointerCapture(e.pointerId);
    const k = z.dataset.rz, x0 = e.clientX, w0 = colW(k), colw = { ...(P().colw || {}) };
    document.body.classList.add('resizing');
    const mv = ev => { colw[k] = Math.max(18, Math.min(600, w0 + ev.clientX - x0)); S.st.user.prefs.colw = colw; const t = colsTemplate(cols); $$('#list .chdr, #list .crow').forEach(r => r.style.setProperty('--cols', t)); };
    const up = () => { z.removeEventListener('pointermove', mv); z.removeEventListener('pointerup', up); document.body.classList.remove('resizing'); savePrefs({ colw }, true); };
    z.addEventListener('pointermove', mv); z.addEventListener('pointerup', up);
  }));
  $$('#list [data-selbox]').forEach(b => b.onclick = e => { e.stopPropagation(); if (e.shiftKey && (S.sel || S.anchor)) selRange(b.dataset.selbox); else selToggle(b.dataset.selbox); });
  if ($('#btn-selall')) $('#btn-selall').onclick = () => S.multi.size ? selClear() : selAll();
  document.body.classList.toggle('has-multi', S.multi.size > 1);
  $$('#list .rowflag').forEach(b => {
    b.onclick = e => { e.stopPropagation(); const m = rowOf(b.dataset.flag); if (m && m.flagged) { const r = b.getBoundingClientRect(); showMenu(r.left, r.bottom + 2, followItems(m.id)); } else doAct('flag', b.dataset.flag); };
    b.oncontextmenu = e => { e.preventDefault(); e.stopPropagation(); showMenu(e.clientX, e.clientY, followItems(b.dataset.flag)); };
  });
  $$('#list .mrow').forEach(r => {
    if (r._wired) return; r._wired = true;
    const id = r.dataset.id;
    r.onclick = e => {
      if (e.target.closest('.selbox')) return;
      if (e.ctrlKey || e.metaKey) return selToggle(id);
      if (e.shiftKey && (S.sel || S.anchor)) return selRange(id);
      if (S.multi.size) selClear(false);
      S.anchor = id; openMail(id);
    };
    r.ondblclick = e => { if (!e.ctrlKey && !e.shiftKey && !e.target.closest('.selbox')) popoutMail(id); };
    r.oncontextmenu = e => { e.preventDefault(); $$('#list .mrow.ctx').forEach(x => x.classList.remove('ctx')); r.classList.add('ctx'); showMenu(e.clientX, e.clientY, mailMenu(id)); };
    r.addEventListener('dragstart', e => {
      closeMenu();
      if (inBulk(id)) {
        e.dataTransfer.setData('text/plain', JSON.stringify(bulkIds())); e.dataTransfer.effectAllowed = 'move';
        const g = document.createElement('div'); g.className = 'dragcount'; g.textContent = S.multi.size + ' mails'; document.body.appendChild(g);
        e.dataTransfer.setDragImage(g, 10, 10); setTimeout(() => g.remove(), 0);
        $$('#list .mrow.msel').forEach(x => x.classList.add('dragsrc')); document.body.classList.add('dragging'); return;
      }
      e.dataTransfer.setData('text/plain', r.dataset.id); e.dataTransfer.effectAllowed = 'move'; r.classList.add('dragsrc'); document.body.classList.add('dragging'); });
    r.addEventListener('dragend', () => { $$('#list .mrow.dragsrc').forEach(x => x.classList.remove('dragsrc')); document.body.classList.remove('dragging'); });
  });
}
function setFilter(f) { S.filter = f; loadList(); renderRibbon(); }
function sortMenu() {
  const so = P().sort, keys = sentView() ? ['date', 'to', 'subject', 'size', 'importance', 'flag', 'due', 'read', 'att', 'cats', 'order', 'claim', 'mailbox'] : ['date', 'from', 'subject', 'size', 'importance', 'flag', 'due', 'read', 'att', 'cats', 'mention', 'order', 'claim', 'mailbox'];
  return [{ head: 'Sorteren op' }, ...keys.map(k => ({ n: SORT_NAMES[k], checked: so.key === k, run: () => setSort(k, so.key === k ? so.dir : undefined) })), '-',
    { n: 'Oplopend (A–Z, oud–nieuw)', checked: so.dir === 'asc', run: () => setSort(so.key, 'asc') },
    { n: 'Aflopend (Z–A, nieuw–oud)', checked: so.dir === 'desc', run: () => setSort(so.key, 'desc') }, '-',
    { n: 'Scheidingsbalken tonen', checked: !!P().groups, run: () => toggleGroups() }];
}
function toggleGroups() { savePrefs({ groups: !P().groups }); S.gcol = new Set(); renderList(); renderRibbon(); toast(P().groups ? 'Scheidingsbalken aan' : 'Scheidingsbalken uit'); }
function colItems() {
  const cols = P().cols && P().cols.length ? P().cols : DEFAULT_COLS;
  return [...Object.keys(COLDEF).map(k => ({ n: COL_NAMES[k], checked: cols.includes(k), disabled: k === 'from' || k === 'subj',
    run: () => { const order = Object.keys(COLDEF); const next = cols.includes(k) ? cols.filter(x => x !== k) : [...cols, k].sort((a, b) => order.indexOf(a) - order.indexOf(b)); savePrefs({ cols: next }); renderList(); } })),
    '-', { n: 'Standaardkolommen en -breedtes', icon: ICON.refresh, run: () => { savePrefs({ cols: DEFAULT_COLS, colw: {} }); renderList(); } }];
}
function viewMenu() {
  return [{ n: 'Filter', icon: ICON.funnel, sub: FILTERS.map(([k, n]) => ({ n, checked: S.filter === k, run: () => setFilter(k) })) },
    { n: 'Sorteren', icon: ICON.sort, sub: sortMenu() },
    { n: 'Kolommen', icon: ICON.columns, sub: colItems() }, '-',
    { n: 'Scheidingsbalken tonen', checked: !!P().groups, run: toggleGroups },
    { n: 'Weergave: kolommen', checked: P().listview === 'kolommen', run: () => setListview('kolommen') },
    { n: 'Weergave: compact', checked: P().listview !== 'kolommen', run: () => setListview('compact') }];
}
function setListview(v) {
  savePrefs({ listview: v });
  if (v === 'kolommen' && $('#list').clientWidth < colsNeeded(P().cols || DEFAULT_COLS)) {
    setLayout({ list: clampCol('list', colsNeeded(P().cols || DEFAULT_COLS) + 4) });
  }
  renderList(); renderRibbon();
}

let searchT;
$('#search').addEventListener('input', e => { clearTimeout(searchT); searchT = setTimeout(() => { S.search = e.target.value.trim(); loadList(); }, 250); });

// ------------------------------------------------------------ lezen
let presKey = null, presState = null;
function setPresence(key, state) {
  if (presKey && presKey !== key) api('presence', presKey, null).catch(() => {});
  presKey = key; presState = state;
  if (key) api('presence', key, state).catch(() => {});
}
setInterval(() => { if (presKey && presState && !document.hidden) api('presence', presKey, presState).catch(() => {}); }, 20000);
window.addEventListener('beforeunload', () => { if (presKey) navigator.sendBeacon && fetch('/api/presence', { method: 'POST', keepalive: true, headers: { 'Content-Type': 'application/json', 'X-Plakzicht': '1' }, body: JSON.stringify([presKey, null]) }); });
async function openMail(id, quiet) {
  id = String(id);
  if (quiet && S.cmp && !S.cmp.full && S.cmp.refId !== id) {
    // automatisch verversen (terug in het venster, wijziging van een collega) terwijl je een mail schrijft:
    // het schrijfvenster blijft staan; alleen de gegevens op de achtergrond bijwerken
    await run(async () => { const m = await api('get_mail', id); if (S.sel === id) { S.mail = m; S.mail.id = String(m.id); } });
    if (!S.popout) renderList();
    renderRibbon();
    return;
  }
  if (S.cmp && !S.cmp.full && S.cmp.refId !== id) stashCompose();  // andere mail: concept blijft bewaard
  if (S.ai && S.ai.id !== id) S.ai = null;
  if (SPEAK.on && S.sel !== id) { speechSynthesis.cancel(); SPEAK.on = false; }
  S.sel = id;
  if (!quiet && !S.popout && !S.multi.size) {  // direct laten zien dat de klik is aangekomen
    $$('#list .mrow.sel').forEach(r => r.classList.remove('sel'));
    const r = $(`#list .mrow[data-id="${CSS.escape(id)}"]`); if (r) r.classList.add('sel');
  }
  if (!S.cmp && DRAFTS[id]) { S.cmp = { ...DRAFTS[id], full: false }; setPresence(id, 'antwoordt'); }
  else if (presKey !== id) setPresence(id, 'leest');
  await run(async () => {
    S.mail = await api('get_mail', id); S.mail.id = String(S.mail.id);
    const row = S.mails.find(m => m.id === id);
    if (row && !row.is_read) { row.is_read = 1; if (!S.popout) refreshState(); }
    if (S.popout) { document.title = (S.mail.subject || 'Mail') + ' - Plakzicht Mail'; S.mails = [{ ...S.mail }]; }
  });
  if (!quiet && !S.popout) renderList();
  renderReader(); renderPz();
}
function smallBtn(a, label) {
  return `<button class="sbtn" data-act="${a}" style="--ac:var(--a-${ACT[a].c})" title="${esc(ACT[a].n)}${ACT[a].k ? ' (' + ACT[a].k + ')' : ''}">${ICON[ACT[a].i]}<span>${esc(label || ACT[a].n)}</span></button>`;
}
function collabBanner(m) {
  const parts = [];
  if (m.claim && !m.claim.mine) parts.push(`<div class="cb claim">${ICON.hand}<span><b>${esc(m.claim.name)}</b> heeft deze mail opgepakt.</span></div>`);
  for (const b of m.busy || []) parts.push(`<div class="cb ${b.state === 'antwoordt' ? 'warn' : ''}">${b.state === 'antwoordt' ? ICON.pen : ICON.eye}<span><b>${esc(b.name)}</b> ${b.state === 'antwoordt' ? 'is deze mail nu aan het beantwoorden.' : 'heeft deze mail ook open.'}</span></div>`);
  if (m.replied) parts.push(`<div class="cb ok">${ICON.check}<span>${m.replied.action === 'doorgestuurd' ? 'Doorgestuurd' : 'Beantwoord'} door <b>${esc(m.replied.name)}</b>, ${fmtDate(new Date(m.replied.at * 1000).toISOString(), true)}.</span></div>`);
  return parts.length ? `<div class="collab">${parts.join('')}</div>` : '';
}
function renderReader() {
  if (S.multi.size > 1) return bulkReader();
  if (S.cmp && !S.cmp.full && (!S.cmp.refId || S.cmp.refId === S.sel)) { renderComposePane(); renderRibbon(); return; }
  const m = S.mail;
  if (!m) {
    const nd = Object.values(DRAFTS).filter(d => !d.refId);
    $('#reader').innerHTML = `<div class="empty">Kies een mail om te lezen.<br><span class="note">Rechtermuisknop op een mail geeft snelle acties. Dubbelklik opent de mail in een eigen venster.</span>
      ${nd.length ? `<div class="drafts"><div class="note">Concepten</div>${nd.map(d => `<button class="btn small" data-draft="${esc(d.key)}">${ICON.pen} ${esc(d.subj || '(geen onderwerp)')}</button>`).join('')}</div>` : ''}</div>`;
    $$('#reader [data-draft]').forEach(b => b.onclick = () => resumeDraft(b.dataset.draft));
    renderRibbon(); return;
  }
  const row = rowOf(m.id) || m;
  const html = `
    <div class="rbar" role="toolbar" aria-label="Snelle acties">${smallBtn('reply')}${smallBtn('replyall', 'Allen')}${smallBtn('forward')}
      <span class="grow"></span>
      ${S.layout && S.layout.pz_hidden ? `<button class="sbtn" data-act="showpz" style="--ac:var(--a-link)">${ICON.panel}<span>Plakzicht</span></button>` : ''}
      ${S.popout ? '' : `<button class="sbtn ic" data-act="popout" title="Eigen venster (Enter)" aria-label="Eigen venster">${ICON.popout}</button>`}
      <button class="sbtn ic" data-act="more" title="Meer acties" aria-label="Meer acties">${ICON.dots}</button></div>
    <div class="rhead">
      <h1>${row.importance === 'high' ? '<span class="imp hi" title="Urgentie: hoog">!</span> ' : ''}${row.flagged ? `<span class="hflag" title="Met vlag">${ICON.flag}</span>` : ''}${esc(m.subject || '(geen onderwerp)')}</h1>
      <div class="meta">${esc(m.from_name)} &lt;${esc(m.from_addr)}&gt; → ${esc(m.to_addr)}${m.cc ? ' · cc ' + esc(m.cc) : ''}</div>
      <div class="meta">${fmtDate(m.date, true)} · ${esc(m.mailbox)} › ${esc(m.folder_name || FOLDER_NAMES[m.folder] || '')}${m.size ? ' · ' + sizeCell(m.size) : ''}</div>
      ${row.flagged && row.flag_due ? `<div class="meta fu ${row.flag_due < isoDay(new Date()) ? 'late' : ''}">${ICON.bell} Opvolgen: ${esc(fmtDay(row.flag_due))}</div>` : row.flag_done ? `<div class="meta fu done">${ICON.check} Opvolgen voltooid</div>` : ''}
      <div class="labs">${m.labels.map(l => labelBadge(l, true)).join('')}</div>
      ${collabBanner(m)}
      ${(m.activity || []).length ? `<details class="hist"><summary>Geschiedenis (${m.activity.length})</summary>
        ${m.activity.map(a => `<div><b>${esc(a.user_name)}</b> ${esc(a.action)}${a.detail ? ' ' + esc(a.detail) : ''} <span class="muted">· ${fmtDate(new Date(a.at * 1000).toISOString(), true)}</span></div>`).join('')}</details>` : ''}
    </div>
    <div class="aislot">${aiHtml()}</div>
    <iframe class="rbody" sandbox title="Inhoud van de mail"></iframe>`;
  const frame = $('#reader iframe.rbody'), sig = m.id + ':' + (m.body || '').length;
  if (frame && frame.dataset.sig === sig && $('#reader .rbar')) {
    // zelfde mail, alleen kop bijwerken: tekst en scrollpositie blijven staan
    const tmp = document.createElement('div'); tmp.innerHTML = html;
    for (const sel of ['.rbar', '.rhead', '.aislot']) { const cur = $('#reader ' + sel), nw = $(sel, tmp); if (cur && nw && cur.outerHTML !== nw.outerHTML) cur.replaceWith(nw); }
  } else {
    $('#reader').innerHTML = html;
    const f = $('#reader iframe.rbody'); f.dataset.sig = sig;
    f.srcdoc = `<!doctype html><meta charset="utf-8"><base target="_blank"><style>body{font:14px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;color:#1d2320;margin:16px 18px;overflow-wrap:anywhere}img{max-width:100%}blockquote{border-left:3px solid #e2e4df;margin:8px 0;padding-left:12px;color:#555}</style>${m.body || ''}`;
  }
  $$('#reader [data-act]').forEach(b => b.onclick = () => {
    const a = b.dataset.act;
    if (a === 'showpz') { setLayout({ pz_hidden: false }); renderReader(); return; }
    if (a === 'more') { const r = b.getBoundingClientRect(); showMenu(r.right - 240, r.bottom + 4, mailMenu(m.id)); return; }
    doAct(a, m.id);
  });
  $$('#reader [data-unlabel]').forEach(b => b.onclick = () => doAct('labelset', m.id, { label: +b.dataset.unlabel, on: false }));
  renderAi();
  renderRibbon();
}

// ------------------------------------------------------------ concepten (blijven bewaard als je naar een andere mail gaat)
let DRAFTS = {};
const draftKeyStore = () => 'pm-drafts-' + (S.st ? S.st.user.id : '');
function loadDrafts() { try { DRAFTS = JSON.parse(localStorage.getItem(draftKeyStore()) || '{}') || {}; } catch { DRAFTS = {}; } }
function saveDrafts() { try { localStorage.setItem(draftKeyStore(), JSON.stringify(DRAFTS)); } catch { /* vol of geen opslag: alleen in dit venster */ } }
const draftOf = id => !!(DRAFTS[id] || (S.cmp && S.cmp.refId === id));
let draftT;
function readCompose() {
  const c = S.cmp; if (!c || !$('#editor')) return;
  c.mb = +$('#c-from').value; c.to = $('#c-to').value; c.cc = $('#c-cc').value; c.subj = $('#c-subj').value;
  c.html = $('#editor').innerHTML; c.sigId = $('#c-sig').value;
}
function touchDraft() { clearTimeout(draftT); draftT = setTimeout(() => { if (!S.cmp) return; readCompose(); DRAFTS[S.cmp.key] = { ...S.cmp, full: false }; saveDrafts(); }, 800); }
function stashCompose() {
  const c = S.cmp; if (!c) return;
  readCompose();
  const typed = ownText($('#editor') || document.createElement('div')) || c.to !== c.to0 || c.subj !== c.subj0;
  if (typed || DRAFTS[c.key]) { DRAFTS[c.key] = { ...c, full: false }; saveDrafts(); }
  S.cmp = null;
  if (c.refId) setPresence(S.sel === c.refId ? c.refId : null, S.sel === c.refId ? 'leest' : null);
  if (c.full) { closeOverlay(); }
}
function dropDraft(key) { delete DRAFTS[key]; saveDrafts(); }
async function resumeDraft(key) {
  const d = DRAFTS[key]; if (!d) return;
  if (d.refId && d.refId !== S.sel) { await openMail(d.refId); return; }
  if (S.cmp) stashCompose();
  S.cmp = { ...d };
  if (S.cmp.refId) setPresence(S.cmp.refId, 'antwoordt');
  showCompose();
}

// ------------------------------------------------------------ opstellen (in het leesvenster of volledig scherm)
async function openCompose(o) {
  if (!S.st.mailboxes.length) return toast('Je hebt geen mailbox om vanuit te versturen.');
  const m = o.mail, refId = m && o.mode !== 'new' ? m.id : null;
  if (S.cmp && S.cmp.refId && S.cmp.refId === refId) { if (o.full) { S.cmp.full = true; showCompose(); } return; }
  if (S.cmp) stashCompose();
  if (refId && DRAFTS[refId]) { S.cmp = { ...DRAFTS[refId] }; toast('Je concept voor deze mail is weer geopend'); }
  else S.cmp = buildCompose(o);
  if (o.full || P().reply_in === 'window') S.cmp.full = true;
  if (refId) {
    setPresence(refId, 'antwoordt');
    if (!S.cmp.full && S.sel !== refId) { S.sel = refId; S.mail = m; if (!S.popout) renderList(); renderPz(); }
  }
  showCompose();
}
function buildCompose(o) {
  const m = o.mail;
  let mbId = o.from || (m && m.mailbox_id) || (S.view && S.view.mailbox_id) || S.st.mailboxes[0].id;
  if (!mailboxById(mbId)) mbId = S.st.mailboxes[0].id;
  let to = o.to || '', cc = '', subject = o.subject || '', quote = '', order = o.order_nr || '';
  if (m && o.mode !== 'new') {
    const mine = S.st.mailboxes.map(b => b.address.toLowerCase());
    const sender = m.folder_wk === 'sent' ? m.to_addr : m.from_addr;
    if (o.mode === 'reply' || o.mode === 'replyall') {
      to = o.to || sender; subject = /^re:/i.test(m.subject) ? m.subject : 'Re: ' + m.subject;
      if (o.mode === 'replyall') cc = [m.to_addr, m.cc].join(',').split(/[;,\s]+/).filter(a => a && !mine.includes(a.toLowerCase()) && a !== sender).join(', ');
    } else { subject = /^fw:/i.test(m.subject) ? m.subject : 'Fw: ' + m.subject; to = o.to || ''; }
    quote = `<blockquote>${o.mode === 'forward' ? `<b>Doorgestuurd bericht</b><br>Van: ${esc(m.from_name)} &lt;${esc(m.from_addr)}&gt;<br>Datum: ${esc(fmtDate(m.date, true))}<br>Aan: ${esc(m.to_addr)}<br>Onderwerp: ${esc(m.subject)}<br><br>` : `Op ${fmtDate(m.date, true)} schreef ${esc(m.from_name)} &lt;${esc(m.from_addr)}&gt;:<br>`}${sanitize(m.body)}</blockquote>`;
    order = m.order_nr || m.offerte_nr || '';
  }
  const sig = sigFor(mbId);
  const others = m ? [...(m.claim && !m.claim.mine ? [`${m.claim.name} heeft deze mail opgepakt`] : []),
    ...(m.busy || []).filter(b => b.state === 'antwoordt').map(b => `${b.name} is deze mail ook aan het beantwoorden`),
    ...(m.replied ? [`al ${m.replied.action} door ${m.replied.name} (${fmtDate(new Date(m.replied.at * 1000).toISOString(), true)})`] : [])] : [];
  return { key: m && o.mode !== 'new' ? m.id : 'new:' + Date.now(), mode: o.mode, refId: m && o.mode !== 'new' ? m.id : null,
    refSubject: m ? m.subject : '', mb: mbId, to, cc, subj: subject, to0: to, subj0: subject, order, quote, others, showQuote: false,
    html: (o.text ? sanitize(o.text) : '<p><br></p>') + `<div data-sig>${sig ? sigHtml(sig, mbId) : ''}</div>`, sigId: sig ? String(sig.id) : '' };
}
const MODE_TITLE = { new: 'Nieuwe mail', reply: 'Beantwoorden', replyall: 'Allen beantwoorden', forward: 'Doorsturen' };
function composeHtml(c) {
  const cl = claudeState();
  return `<div class="cmp ${c.full ? 'full' : 'pane'}" data-key="${esc(c.key)}">
    <div class="cmpbar">
      <button class="btn primary" data-c="send">${ICON.sent} Versturen</button>
      <button class="btn" data-c="discard" title="Concept weggooien">${ICON.trash} Verwijderen</button>
      <span class="ctitle">${esc(MODE_TITLE[c.mode] || '')}</span>
      <span class="grow"></span>
      <button class="btn" data-c="ai" ${cl.ok ? '' : 'disabled'} title="${esc(cl.ok ? 'Claude: antwoord schrijven, tekst verbeteren of vertalen' : cl.why)}">${ICON.sparkle} Claude ▾</button>
      <button class="btn" data-c="insert" id="c-insert" title="Ordergegevens uit Plakzicht in de mail zetten">${ICON.link} Ordergegevens</button>
      ${S.popout ? '' : c.full ? `<button class="btn" data-c="pane" title="Terug naar het leesvenster">Naar leesvenster</button>` : `<button class="btn" data-c="full" title="Volledig scherm">${ICON.popout} Uitklappen</button>`}
      <button class="iconbtn" data-c="close" title="Sluiten; het concept blijft bewaard" aria-label="Sluiten, concept bewaren">×</button>
    </div>
    ${c.others && c.others.length ? `<div class="callout cwarn"><b>Let op:</b> ${c.others.map(esc).join('; ')}.</div>` : ''}
    <div class="cfield"><span>Van</span><select id="c-from">${S.st.mailboxes.map(b => `<option value="${b.id}" ${b.id === c.mb ? 'selected' : ''}>${esc(b.address)}</option>`).join('')}</select></div>
    <div class="cfield acwrap"><button type="button" class="cbtn" data-c="pickto" title="Kies uit het adresboek">Aan</button><input id="c-to" value="${esc(c.to)}" placeholder="naam@voorbeeld.nl" autocomplete="off"></div>
    <div class="cfield acwrap"><button type="button" class="cbtn" data-c="pickcc" title="Kies uit het adresboek">CC</button><input id="c-cc" value="${esc(c.cc)}" autocomplete="off"></div>
    <label class="cfield"><span>Onderwerp</span><input id="c-subj" value="${esc(c.subj)}" style="font-weight:600"></label>
    <div class="cfield"><span>Order</span><div id="c-order-view" class="row"></div></div>
    ${toolbarHtml(true)}
    <div class="editor" id="editor" contenteditable="true" spellcheck="true">${c.html}</div>
    ${c.quote ? `<div class="cquote"><button type="button" class="linkish" data-c="quote">${c.showQuote ? 'Eerdere berichten verbergen' : '··· Eerdere berichten tonen'}</button>${c.showQuote ? `<div class="qbody">${c.quote}</div>` : ''}</div>` : ''}
    <div class="cfoot"><label class="row">Handtekening <select id="c-sig">${sigOptions(S.st.signatures.find(s => String(s.id) === String(c.sigId)))}</select></label>
      <span class="note">${c.refId ? 'Het oorspronkelijke bericht gaat mee onder je tekst.' : ''}${isMs() ? ' Wordt echt verstuurd via Microsoft 365.' : ' Demo: er wordt niets echt verstuurd.'}</span></div>
  </div>`;
}
function showCompose() {
  const c = S.cmp; if (!c) return;
  if (c.full) {
    const ov = $('#overlay');
    ov.innerHTML = `<div class="ohead"><button class="btn" data-close>← Terug (concept bewaren)</button><h1>${esc(MODE_TITLE[c.mode])}</h1></div>
      <div class="grid2"><div id="cmpslot"></div><div style="display:grid;gap:12px">
        <div class="panel"><h2>Uit Plakzicht</h2><p class="note">Koppel de mail aan een order of offerte; dan staat hij ook op de orderpagina.</p><div id="c-pzinfo"></div></div>
        ${c.refSubject ? `<div class="panel"><h2>Antwoord op</h2><p class="note">${esc(c.refSubject)}</p></div>` : ''}</div></div>`;
    ov.hidden = false;
    $('[data-close]', ov).onclick = () => { stashCompose(); renderReader(); renderList(); };
    $('#cmpslot').innerHTML = composeHtml(c);
    wireCompose($('#cmpslot'));
    return;
  }
  if (!$('#overlay').hidden && $('#overlay .cmp')) closeOverlay();
  renderReader();
}
function renderComposePane() {
  const c = S.cmp;
  if ($(`#reader .cmp[data-key="${CSS.escape(c.key)}"]`)) return;  // staat er al: niet opnieuw opbouwen (tekst blijft)
  $('#reader').innerHTML = composeHtml(c);
  wireCompose($('#reader'));
}
function wireCompose(root) {
  const c = S.cmp, ed = $('#editor', root);
  wireToolbar(root, '#editor');
  let orderNr = c.order;
  const showOrder = async () => {
    c.order = orderNr;
    $('#c-order-view', root).innerHTML = orderNr ? `<span class="badge ${/^\d+$/.test(orderNr) ? 'order' : 'off'}">${esc(orderNr)}</span><button type="button" class="btn small" id="c-chg">Wijzigen</button><button type="button" class="btn small" id="c-rm">Weghalen</button>`
      : `<button type="button" class="btn small" id="c-chg">Koppelen aan order of offerte</button>`;
    $('#c-chg', root).onclick = async () => { const nr = await pickPlakzicht('Koppelen aan order of offerte'); if (nr && typeof nr === 'string') { orderNr = nr; showOrder(); touchDraft(); } };
    if ($('#c-rm', root)) $('#c-rm', root).onclick = () => { orderNr = ''; showOrder(); touchDraft(); };
    $('#c-insert', root).disabled = !orderNr;
    if ($('#c-pzinfo')) $('#c-pzinfo').innerHTML = '';
    if (!orderNr) return;
    const r = await api('get_order', orderNr).catch(() => null); if (!r) return;
    const d = r.data;
    if ($('#c-pzinfo')) $('#c-pzinfo').innerHTML = r.soort === 'order'
      ? `<div class="kv"><b class="mono">#${esc(d.nr)}</b><span>${esc(d.klant)}</span></div><div class="row">${stepsHtml(d.productie)}<span class="note">${esc(stepsText(d.productie))}</span></div><div class="kv"><span>Uiterlijk verzenden</span><b>${fmtDay(d.due)}</b></div>`
      : `<div class="kv"><b class="mono">${esc(d.nr)}</b><span>${esc(d.status)}</span></div><div class="note">${esc(d.omschrijving)}</div>`;
    $('#c-insert', root).onclick = () => {
      const block = r.soort === 'order'
        ? `<div style="border:1px solid #e2e4df;border-left:3px solid #1f6f54;border-radius:6px;padding:8px 12px;margin:8px 0;background:#f4f5f2;font-size:13px"><b>Order ${esc(d.nr)}</b>${d.omschrijving ? ' · ' + esc(d.omschrijving) : ''}<br>Productie: ${esc(stepsText(d.productie))}${d.proof ? '<br>Drukproef: ' + esc(d.proof.tekst) : ''}<br>Verwachte verzending: ${fmtDay(d.due)}${d.verzending && d.verzending.track_url ? `<br>Track &amp; trace: <a href="${esc(d.verzending.track_url)}">${esc(d.verzending.track_url)}</a>` : ''}</div><p><br></p>`
        : `<div style="border:1px solid #e2e4df;border-left:3px solid #b26a00;border-radius:6px;padding:8px 12px;margin:8px 0;background:#fff8ec;font-size:13px"><b>Offerte ${esc(d.nr)}</b><br>${esc(d.omschrijving)}<br>Status: ${esc(d.status)}</div><p><br></p>`;
      let node = savedRange ? savedRange.startContainer : ed.firstChild;
      while (node && node.parentNode !== ed) node = node.parentNode;
      if (!node || node.hasAttribute?.('data-sig')) node = null;
      if (node) node.insertAdjacentHTML('afterend', block); else ed.insertAdjacentHTML('afterbegin', block);
      touchDraft();
    };
  };
  showOrder();
  const setSig = id => { const s = S.st.signatures.find(x => x.id === +id), mbv = +$('#c-from', root).value, html = s ? sigHtml(s, mbv) : '';
    const slot = $('[data-sig]', ed); if (slot) slot.innerHTML = html; else if (s) ed.insertAdjacentHTML('beforeend', `<div data-sig>${html}</div>`); touchDraft(); };
  $('#c-from', root).onchange = e => { const s = sigFor(+e.target.value); $('#c-sig', root).value = s ? s.id : ''; setSig(s ? s.id : ''); };
  $('#c-sig', root).onchange = e => setSig(e.target.value);
  ['#c-to', '#c-cc', '#c-subj'].forEach(s => $(s, root).addEventListener('input', touchDraft));
  ed.addEventListener('input', touchDraft);
  autocomplete($('#c-to', root)); autocomplete($('#c-cc', root));
  const pick = async sel => { const a = await addressBook(false, true); if (a && typeof a === 'string') { const i = $(sel, root); i.value = (i.value.trim() ? i.value.replace(/[,;\s]*$/, '') + ', ' : '') + a; touchDraft(); } };
  const C = {
    send: () => sendCompose(),
    discard: async () => {
      if (ownText(ed)) {
        const ok = await dialog(`<form><h2>Concept weggooien?</h2><p class="muted">Wat je hebt geschreven gaat verloren.</p><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Weggooien</button></div></form>`);
        if (!ok) return;
      }
      const k = c.key, wasFull = c.full; dropDraft(k); S.cmp = null;
      if (c.refId) setPresence(S.sel === c.refId ? c.refId : null, S.sel === c.refId ? 'leest' : null);
      if (wasFull) closeOverlay();
      renderReader(); if (!S.popout) renderList();
    },
    close: () => { const wasFull = c.full; stashCompose(); if (!wasFull) renderReader(); else renderReader(); if (!S.popout) renderList(); },
    full: () => { readCompose(); c.full = true; $('#reader').innerHTML = ''; showCompose(); },
    pane: () => { readCompose(); c.full = false; closeOverlay(); if (c.refId && S.sel !== c.refId) { openMail(c.refId); return; } renderReader(); },
    quote: () => { readCompose(); c.showQuote = !c.showQuote; const k = c.key; if (c.full) showCompose(); else { $('#reader').innerHTML = ''; renderComposePane(); } },
    pickto: () => pick('#c-to'), pickcc: () => pick('#c-cc'),
    ai: b => { const r = b.getBoundingClientRect(); showMenu(r.left, r.bottom + 4, composeAiItems(c, ed)); },
    insert: () => {},
  };
  $$('[data-c]', root).forEach(b => { if (b.dataset.c !== 'insert') b.onclick = () => C[b.dataset.c](b); });
  const range = document.createRange(); range.setStart(ed.firstChild || ed, 0); range.collapse(true); savedRange = range;
  (c.mode === 'new' && !c.to ? $('#c-to', root) : c.mode === 'forward' && !c.to ? $('#c-to', root) : ed).focus();
}
function composeAiItems(c, ed) {
  const imp = how => async () => {
    const txt = ownText(ed); if (!txt) return toast('Schrijf eerst wat tekst.');
    toast('Claude is bezig…');
    try { const r = await api('claude_run', 'improve', null, { text: txt, how }); replaceOwnText(ed, r.html); touchDraft(); toast('Tekst aangepast door Claude. Lees hem na.'); }
    catch (e) { toast(e.message); }
    refreshClaudeUsage();
  };
  const tr = async lang => {
    const txt = ownText(ed); if (!txt) return toast('Schrijf eerst wat tekst.');
    toast('Claude vertaalt…');
    try { const r = await api('claude_run', 'translate', null, { text: txt, lang }); replaceOwnText(ed, r.html); touchDraft(); toast('Vertaald naar het ' + lang); }
    catch (e) { toast(e.message); }
    refreshClaudeUsage();
  };
  return [{ n: 'Antwoord laten schrijven…', icon: ICON.sparkle, disabled: !c.refId, run: () => aiReply(c) }, '-',
    { n: 'Tekst verbeteren', icon: ICON.sparkle, run: imp('verbeter') }, { n: 'Korter maken', icon: ICON.sparkle, run: imp('korter') },
    { n: 'Formeler', icon: ICON.sparkle, run: imp('formeler') }, { n: 'Vriendelijker', icon: ICON.sparkle, run: imp('vriendelijker') }, '-',
    { n: 'Mijn tekst vertalen', icon: ICON.globe, sub: translateItems(tr) }];
}
async function sendCompose() {
  const c = S.cmp; if (!c) return;
  readCompose();
  const own = sanitize($('#editor').innerHTML.replace(/<div data-sig="">/g, '<div>'));
  const body = own + (c.quote ? '<br>' + c.quote : '');
  const btn = $('.cmp [data-c=send]'); if (btn) btn.disabled = true;
  const ok = await run(async () => {
    await api('send_mail', { mailbox_id: c.mb, to: c.to, cc: c.cc, subject: c.subj, body, order_nr: c.order, reply_to: c.refId, mode: c.mode });
    return true;
  });
  if (!ok) { if (btn) btn.disabled = false; return; }
  dropDraft(c.key); S.cmp = null;
  if (c.refId) setPresence(S.sel === c.refId ? c.refId : null, S.sel === c.refId ? 'leest' : null);
  if (c.full) closeOverlay();
  toast(isMs() ? 'Verstuurd' : 'Verstuurd (demo) en opgeslagen in Verzonden');
  if (S.popout) { if (S.sel) await openMail(S.sel, true); else renderReader(); return; }
  await refreshState(); await loadList();
  if (S.sel) await openMail(S.sel, true); else renderReader();
}
// Adressen aanvullen tijdens het typen (adresboek)
function autocomplete(inp) {
  let box = null, t = null, items = [], idx = 0;
  const close = () => { if (box) box.remove(); box = null; };
  const token = () => { const v = inp.value, i = Math.max(v.lastIndexOf(','), v.lastIndexOf(';')); return v.slice(i + 1).trim(); };
  const choose = a => { const v = inp.value, i = Math.max(v.lastIndexOf(','), v.lastIndexOf(';')); inp.value = (i >= 0 ? v.slice(0, i + 1) + ' ' : '') + a + ', '; close(); inp.focus(); inp.dispatchEvent(new Event('input')); };
  const show = () => {
    close(); if (!items.length) return;
    box = document.createElement('div'); box.className = 'acbox';
    box.innerHTML = items.map((x, i) => `<button type="button" class="${i === idx ? 'on' : ''}" data-i="${i}"><b>${esc(x.name || x.address)}</b> <span class="note">${esc(x.address)}</span>${x.source === 'Plakzicht-klant' ? ' <span class="badge order" style="font-family:inherit">klant</span>' : ''}</button>`).join('');
    inp.parentNode.appendChild(box);
    $$('button', box).forEach(b => b.onmousedown = e => { e.preventDefault(); choose(items[+b.dataset.i].address); });
  };
  inp.addEventListener('input', e => {
    if (!e.isTrusted) return;
    clearTimeout(t); const q = token();
    if (q.length < 2) { close(); return; }
    t = setTimeout(async () => { try { items = (await api('address_book', q)).slice(0, 8); idx = 0; if (token() === q) show(); } catch { /* stil */ } }, 180);
  });
  inp.addEventListener('keydown', e => {
    if (!box) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); idx = (idx + 1) % items.length; show(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); idx = (idx - 1 + items.length) % items.length; show(); }
    else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); choose(items[idx].address); }
    else if (e.key === 'Escape') close();
  });
  inp.addEventListener('blur', () => setTimeout(close, 150));
}

// ------------------------------------------------------------ regels (automatisch verplaatsen, labelen, ...)
const R_FIELDS = [['from', 'Afzender'], ['to', 'Ontvanger'], ['subject', 'Onderwerp'], ['body', 'Tekst'], ['any', 'Onderwerp of tekst'], ['order', 'Plakzicht-koppeling']];
const R_OPS = [['contains', 'bevat'], ['not_contains', 'bevat niet'], ['is', 'is precies'], ['starts', 'begint met']];
const R_ORDER = [['has', 'heeft een order of offerte'], ['none', 'heeft geen order of offerte']];
function ruleSummary(r) {
  const fn = Object.fromEntries(R_FIELDS), on = Object.fromEntries([...R_OPS, ...R_ORDER]);
  const cond = r.conditions.map(c => c.field === 'order' ? on[c.op] : `${fn[c.field].toLowerCase()} ${on[c.op]} “${c.value}”`).join(' en ');
  const a = r.actions, acts = [];
  if (a.move_folder) { const f = a.move_mailbox ? folderOf(a.move_mailbox, a.move_folder) : null;
    acts.push('verplaatsen naar ' + (a.move_mailbox ? ((mailboxById(a.move_mailbox) || {}).display || '?') + ' › ' : '') + (f ? f.name : FOLDER_NAMES[a.move_folder] || 'map')); }
  if ((a.label_ids || []).length) acts.push('label ' + a.label_ids.map(id => (S.st.labels.find(l => l.id === id) || {}).name || '?').join(', '));
  if (a.mark_read) acts.push('als gelezen markeren');
  if (a.flag) acts.push('vlag zetten');
  return `Als ${cond}: ${acts.join(', ')}${r.stop ? '. Daarna stoppen.' : '.'}`;
}
let RULES = [];
async function openRules(opt = {}) {
  await run(async () => {
    RULES = await api('list_rules');
    const ov = $('#overlay');
    ov.innerHTML = `<div class="ohead"><button class="btn" data-close>← Terug naar mail</button><h1>Regels</h1>
      <span class="note">Regels lopen automatisch op nieuwe mail in Postvak IN, van boven naar beneden.</span>
      <div class="right">${isMs() ? '' : `<button class="btn" id="r-sim">${ICON.bolt} Testmail laten binnenkomen</button>`}</div></div>
      ${isMs() ? '<div class="callout" style="margin-bottom:12px">In deze testversie werken regels alleen in de demo-stand. Je kunt ze hier al wel maken; automatisch uitvoeren op Microsoft-mailboxen komt in een volgende stap.</div>' : ''}
      <div class="grid2 rules"><div class="panel" id="r-list"></div><div class="panel" id="r-edit"></div></div>`;
    ov.hidden = false;
    $('[data-close]', ov).onclick = async () => { closeOverlay(); await refreshState(); await loadList(); };
    if ($('#r-sim')) $('#r-sim').onclick = simulateIncoming;
    renderRuleList();
    if (opt.fromMail) {
      const m = opt.fromMail;
      editRule({ name: 'Mails van ' + (m.from_name || m.from_addr), mailbox_id: m.mailbox_id, active: 1, stop: 0,
        conditions: [{ field: 'from', op: 'contains', value: m.from_addr }], actions: { label_ids: [], move_folder: '', move_mailbox: null } });
    } else editRule(RULES[0] || null);
  });
}
function renderRuleList(selId) {
  const admin = S.st.user.role === 'beheerder';
  $('#r-list').innerHTML = `<h2>Mijn regels <small>${admin ? 'je ziet als beheerder alle regels' : ''}</small></h2>
    ${RULES.length ? RULES.map((r, i) => `<div class="rrow ${r.active ? '' : 'off'} ${selId === r.id ? 'sel' : ''}" data-r="${r.id}">
      <label class="sw" title="Regel aan of uit"><input type="checkbox" data-tog="${r.id}" ${r.active ? 'checked' : ''}><span></span></label>
      <div class="rtxt"><b>${esc(r.name)}</b><span class="note">${esc(ruleSummary(r))}</span>
        <span class="note">${r.mailbox_id ? 'Alleen ' + esc((mailboxById(r.mailbox_id) || {}).display || '?') : 'Alle mailboxen'}${admin && r.owner ? ' · van ' + esc(r.owner) : ''}</span></div>
      <div class="rbtns"><button class="iconbtn" data-up="${r.id}" ${i === 0 ? 'disabled' : ''} title="Hoger" aria-label="Regel hoger">↑</button>
        <button class="iconbtn" data-down="${r.id}" ${i === RULES.length - 1 ? 'disabled' : ''} title="Lager" aria-label="Regel lager">↓</button></div></div>`).join('')
      : '<p class="note">Nog geen regels.</p>'}
    <div><button class="btn primary" id="r-new">${ICON.plus} Nieuwe regel</button></div>`;
  $('#r-new').onclick = () => editRule(null);
  $$('#r-list [data-r]').forEach(d => d.onclick = e => { if (!e.target.closest('input,button,label')) editRule(RULES.find(r => r.id === +d.dataset.r)); });
  $$('#r-list [data-tog]').forEach(c => c.onchange = () => run(async () => { await api('toggle_rule', +c.dataset.tog, c.checked); RULES = await api('list_rules'); renderRuleList(selId); toast(c.checked ? 'Regel aangezet' : 'Regel uitgezet'); }));
  $$('#r-list [data-up], #r-list [data-down]').forEach(b => b.onclick = () => run(async () => {
    await api('move_rule', +(b.dataset.up || b.dataset.down), b.dataset.up ? -1 : 1); RULES = await api('list_rules'); renderRuleList(selId); }));
}
function condRow(c) {
  const isOrder = c.field === 'order';
  return `<div class="cond">
    <select data-k="field">${R_FIELDS.map(([k, n]) => `<option value="${k}" ${c.field === k ? 'selected' : ''}>${n}</option>`).join('')}</select>
    <select data-k="op">${(isOrder ? R_ORDER : R_OPS).map(([k, n]) => `<option value="${k}" ${c.op === k ? 'selected' : ''}>${n}</option>`).join('')}</select>
    <input data-k="value" value="${esc(c.value || '')}" placeholder="bijv. @leverancier.nl" ${isOrder ? 'hidden' : ''}>
    <button type="button" class="iconbtn" data-rmcond title="Voorwaarde weghalen" aria-label="Voorwaarde weghalen">×</button></div>`;
}
function editRule(r) {
  const isNew = !r || !r.id;
  r = r || { name: '', mailbox_id: null, active: 1, stop: 0, conditions: [{ field: 'from', op: 'contains', value: '' }], actions: { label_ids: [] } };
  const a = r.actions || {};
  const moveVal = a.move_folder ? (a.move_mailbox || '') + '|' + a.move_folder : '';
  const moveOpts = [`<option value="">Niet verplaatsen</option>`,
    `<optgroup label="In dezelfde mailbox">${S.st.folders.filter(f => f.key !== 'inbox').map(f => `<option value="|${f.key}" ${moveVal === '|' + f.key ? 'selected' : ''}>${f.name}</option>`).join('')}</optgroup>`,
    ...S.st.mailboxes.map(mb => `<optgroup label="${esc(mb.display)}">${mb.folders.map(f => `<option value="${mb.id}|${esc(f.id)}" ${moveVal === mb.id + '|' + f.id ? 'selected' : ''}>${'\u00a0\u00a0'.repeat(f.depth)}${esc(mb.display)} › ${esc(f.name)}</option>`).join('')}</optgroup>`)].join('');
  $('#r-edit').innerHTML = `<form class="form" id="rform"><h2>${isNew ? 'Nieuwe regel' : 'Regel wijzigen'}</h2>
    <label>Naam<input name="name" value="${esc(r.name)}" required placeholder="Bijvoorbeeld: Facturen naar Archief"></label>
    <label>Geldt voor<select name="mailbox_id"><option value="">Alle mailboxen waar ik bij kan</option>
      ${S.st.mailboxes.map(mb => `<option value="${mb.id}" ${r.mailbox_id === mb.id ? 'selected' : ''}>Alleen ${esc(mb.address)}</option>`).join('')}</select></label>
    <fieldset><legend>Als alle voorwaarden kloppen</legend><div id="conds">${r.conditions.map(condRow).join('')}</div>
      <button type="button" class="btn small" id="addcond">${ICON.plus} Voorwaarde</button></fieldset>
    <fieldset><legend>Dan</legend>
      <label><span>${actIcon('move')} Verplaatsen naar</span><select name="move">${moveOpts}</select></label>
      <div class="checks"><span class="muted" style="font-size:12px">${actIcon('label')} Label toevoegen</span>
        ${S.st.labels.map(l => `<label><input type="checkbox" name="label" value="${l.id}" ${(a.label_ids || []).includes(l.id) ? 'checked' : ''}><span class="swatch" style="--c:${esc(l.color)}"></span> ${esc(l.name)}</label>`).join('')}</div>
      <div class="checks">
        <label><input type="checkbox" name="mark_read" ${a.mark_read ? 'checked' : ''}> ${actIcon('read')} Als gelezen markeren</label>
        <label><input type="checkbox" name="flag" ${a.flag ? 'checked' : ''}> ${actIcon('flag')} Vlag zetten</label>
      </div></fieldset>
    <div class="checks">
      <label><input type="checkbox" name="stop" ${r.stop ? 'checked' : ''}> Daarna geen andere regels meer uitvoeren</label>
      <label><input type="checkbox" name="active" ${r.active ? 'checked' : ''}> Regel staat aan</label></div>
    <div class="row"><button class="btn primary">Opslaan</button>
      ${isNew ? '' : `<button type="button" class="btn" id="r-run">Nu toepassen op Postvak IN</button><button type="button" class="btn danger" id="r-del">Verwijderen</button>`}</div></form>`;
  if (!isNew) renderRuleList(r.id);
  const wireConds = () => {
    $$('#conds .cond').forEach(row => {
      $('[data-k=field]', row).onchange = e => {
        const c = { field: e.target.value, op: e.target.value === 'order' ? 'none' : 'contains', value: $('[data-k=value]', row).value };
        row.outerHTML = condRow(c); wireConds();
      };
      $('[data-rmcond]', row).onclick = () => { if ($$('#conds .cond').length > 1) { row.remove(); } else toast('Een regel heeft minstens één voorwaarde'); };
    });
  };
  wireConds();
  $('#addcond').onclick = () => { $('#conds').insertAdjacentHTML('beforeend', condRow({ field: 'subject', op: 'contains', value: '' })); wireConds(); };
  $('#rform').onsubmit = e => {
    e.preventDefault();
    const f = new FormData(e.target), mv = f.get('move') || '', mvMb = mv.slice(0, mv.indexOf('|')), mvF = mv.slice(mv.indexOf('|') + 1);
    const data = {
      id: isNew ? null : r.id, name: f.get('name'), mailbox_id: f.get('mailbox_id') ? +f.get('mailbox_id') : null,
      active: f.has('active'), stop: f.has('stop'),
      conditions: $$('#conds .cond').map(row => ({ field: $('[data-k=field]', row).value, op: $('[data-k=op]', row).value, value: $('[data-k=value]', row).value })),
      actions: { move_folder: mvF || '', move_mailbox: mvMb ? +mvMb : null, label_ids: f.getAll('label').map(Number), mark_read: f.has('mark_read'), flag: f.has('flag') },
    };
    run(async () => { const id = await api('save_rule', data); RULES = await api('list_rules'); toast('Regel opgeslagen'); editRule(RULES.find(x => x.id === id)); });
  };
  if ($('#r-run')) $('#r-run').onclick = () => run(async () => { const n = await api('run_rule_now', r.id); toast(n ? `Regel toegepast op ${n} ${n === 1 ? 'mail' : 'mails'}` : 'Geen mails in Postvak IN die aan deze regel voldoen'); });
  if ($('#r-del')) $('#r-del').onclick = async () => {
    const ok = await dialog(`<form><h2>Regel verwijderen?</h2><p class="muted">“${esc(r.name)}” wordt verwijderd.</p><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Verwijderen</button></div></form>`);
    if (ok) run(async () => { await api('delete_rule', r.id); RULES = await api('list_rules'); renderRuleList(); editRule(RULES[0] || null); toast('Regel verwijderd'); });
  };
}
async function simulateIncoming() {
  await run(async () => {
    const r = await api('simulate_incoming', S.view && S.view.mailbox_id ? S.view.mailbox_id : null);
    toast(`Nieuwe mail: “${r.subject}”` + (r.rules.length ? ` → regel “${r.rules.join('”, “')}” → ${r.mailbox} › ${FOLDER_NAMES[r.folder] || 'map'}` : ` → ${r.mailbox} › Postvak IN (geen regel)`));
    if ($('#overlay').hidden) { await refreshState(); await loadList(); } else await refreshState();
  });
}

// ------------------------------------------------------------ Plakzicht-paneel
function renderPz() {
  if (S.multi.size > 1) { $('#pz').innerHTML = `<div class="panel"><h2>Plakzicht</h2><p class="note">${S.multi.size} mails geselecteerd. Kies één mail om de order te zien.</p></div>`; return; }
  const m = S.mail;
  if (!m) {
    $('#pz').innerHTML = `<div class="panel"><h2>Plakzicht</h2><p class="note">Open een mail. Staat er een ordernummer of offertenummer in, dan zie je de order hier.</p></div><div id="pz-today"></div>`;
    todayHtml().then(h => { const slot = $('#pz-today'); if (!slot || S.mail) return; slot.innerHTML = h;
      if ($('#pz-cal')) $('#pz-cal').onclick = () => openCalendar();
      $$('#pz-today [data-open]').forEach(b => b.onclick = () => openOrder(b.dataset.open));
      $$('#pz-today [data-tev]').forEach(b => b.onclick = async () => { await openCalendar(); calShow(b.dataset.tev); }); });
    return;
  }
  const pz = m.plakzicht;
  let h = `<div class="pzbar">Plakzicht${pz.live ? '' : ' <span class="badge" title="Nagebootste Plakzicht (demo)">demo</span>'}<button id="pz-hide" title="Paneel verbergen">Verbergen ×</button></div>`;
  if (pz.pending) { setHtml($('#pz'), h + '<div class="panel"><div class="row"><span class="spin"></span><span class="note">Gegevens uit Plakzicht ophalen…</span></div></div>'); loadPz(m.id); return; }
  if (pz.error) h += `<div class="callout small">${esc(pz.error)}</div>`;
  const linkBtns = `<div class="row"><button class="btn small" data-link>Andere koppelen</button><button class="btn small" data-unlink>Ontkoppelen</button></div>`;
  if (pz.order) {
    const o = pz.order;
    h += `<div class="panel"><h2>Gekoppelde order <small>${esc(pz.how)}</small></h2>
      <div class="row"><b class="mono">#${esc(o.nr)}</b>${o.spoed ? '<span class="badge bad">spoed</span>' : ''}<span class="muted" style="font-size:12px">${esc(o.klant)}</span></div>
      ${o.omschrijving ? `<div class="note">${esc(o.omschrijving)}</div>` : ''}
      <div class="row">${o.status ? `<span class="badge">${esc(o.status)}</span>` : ''}${proofBadge(o.proof)}
        ${o.on_hold ? `<span class="badge" style="background:${esc(o.on_hold.kleur)};color:#fff">${esc(o.on_hold.status)}</span>` : ''}</div>
      <div class="kv"><span>Uiterlijk verzenden</span><b>${fmtDay(o.due)}</b></div>
      ${o.leverdatum ? `<div class="kv"><span>Leverdatum</span><b>${fmtDay(o.leverdatum)}</b></div>` : ''}
      <div class="row">${stepsHtml(o.productie)}<span class="note">${esc(stepsText(o.productie))}</span></div>
      ${shipLine(o.verzending)}
      ${o.openstaand ? `<div class="kv"><span>Nog te betalen</span><b>${eur(o.openstaand)}</b></div>` : ''}
      <div class="row"><button class="btn primary" data-open="${esc(o.nr)}">Bekijken</button>${o.url ? `<button class="btn" data-ext="${esc(o.url)}">Openen in Plakzicht</button>` : ''}</div>
      ${linkBtns}</div>`;
  }
  if (pz.offerte) {
    const o = pz.offerte;
    h += `<div class="panel"><h2>Gekoppelde offerte <small>${esc(pz.how)}</small></h2>
      <div class="row"><b class="mono">${pz.live ? 'Offerte ' : ''}${esc(o.nr)}</b>${o.status ? `<span class="badge">${esc(o.status)}</span>` : ''}</div>
      <div class="note">${esc(o.klant)}${o.omschrijving ? ' · ' + esc(o.omschrijving) : ''}${o.bedrag ? ' · ' + eur(o.bedrag) : ''}</div>
      ${o.geldig_tot ? `<div class="kv"><span>Geldig tot</span><b>${fmtDay(o.geldig_tot)}</b></div>` : ''}
      ${(o.orders || []).map(n => `<div class="kv"><span>Werd order</span><button class="linkish mono" data-open="${esc(n)}">#${esc(n)}</button></div>`).join('')}
      <div class="row"><button class="btn primary" data-open="${esc(o.nr)}">Bekijken</button>${o.url ? `<button class="btn" data-ext="${esc(o.url)}">Openen in Plakzicht</button>` : ''}</div>
      ${linkBtns}</div>`;
  }
  if ((pz.missing || []).length) {
    h += `<div class="panel"><h2>Niet gevonden</h2><p class="note">${pz.missing.map(x => esc(x[0].toUpperCase() + x.slice(1))).join(' en ')} uit deze mail bestaat niet in Plakzicht.</p>${linkBtns}</div>`;
  } else if (!pz.order && !pz.offerte && !pz.error) {
    h += `<div class="panel"><h2>Geen order gekoppeld</h2><p class="note">In deze mail staat geen bekend order- of offertenummer.</p>
      <button class="btn" data-link>Koppelen aan order of offerte</button></div>`;
  }
  if (pz.klant) {
    const k = pz.klant;
    h += `<div class="panel"><h2>Klant in Plakzicht</h2><b>${esc(k.naam)}</b>
      ${k.orders.map(o => `<div class="kv"><button class="linkish mono" data-open="${esc(o.nr)}">Order #${esc(o.nr)}</button><span class="muted">${o.due ? 'verz. ' + fmtDay(o.due) : esc(o.status || '')}</span></div>`).join('')}
      ${k.offertes.map(o => `<div class="kv"><button class="linkish mono" data-open="${esc(o.nr)}">${pz.live ? 'Offerte ' : ''}${esc(o.nr)}</button><span class="muted">${esc(o.status || '')}</span></div>`).join('')}
      ${k.n_orders > k.orders.length ? `<div class="note">${k.n_orders} orders in totaal</div>` : ''}
      <div class="kv"><span>Mails met deze klant</span><b>${k.mails}</b></div></div>`;
  } else if (!pz.error) {
    h += `<div class="panel"><h2>Klant</h2><p class="note">${esc(m.folder_wk === 'sent' ? m.to_addr : m.from_addr)} is nog geen klant in Plakzicht.</p></div>`;
  }
  setHtml($('#pz'), h);
  $('#pz-hide').onclick = () => { setLayout({ pz_hidden: true }); renderReader(); };
  $$('#pz [data-open]').forEach(b => b.onclick = () => openOrder(b.dataset.open));
  $$('#pz [data-ext]').forEach(b => b.onclick = e => { e.preventDefault(); openExternal(b.dataset.ext); });
  $$('#pz [data-link]').forEach(b => b.onclick = () => linkDialog(m));
  $$('#pz [data-unlink]').forEach(b => b.onclick = () => run(async () => { await api('link_mail', m.id, ''); await openMail(m.id); await loadList(); toast('Ontkoppeld'); }));
}
const PZWAIT = new Set();
async function loadPz(id) {
  if (PZWAIT.has(id)) return; PZWAIT.add(id);
  try { const pz = await api('mail_plakzicht', id); if (S.mail && S.mail.id === id) { S.mail.plakzicht = pz; renderPz(); renderRibbon(); } }
  catch (e) { if (S.mail && S.mail.id === id) { S.mail.plakzicht = { error: e.message, missing: [], live: true }; renderPz(); } }
  finally { PZWAIT.delete(id); }
}
async function pickPlakzicht(title) {
  return dialog(`<form><h2>${esc(title)}</h2><input name="q" placeholder="Zoek op ordernummer, offerte of klant" style="width:100%" autocomplete="off">
    <div class="results" id="pzres"></div><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button></div></form>`,
  (d, done) => {
    const box = $('#pzres', d), inp = $('[name=q]', d);
    const search = async () => {
      const r = await api('search_plakzicht', inp.value);
      box.innerHTML = r.length ? r.map(x => `<button type="button" data-nr="${esc(x.nr)}"><b class="mono">${esc(x.nr)}</b><span>${esc(x.klant)}</span><span class="badge" style="margin-left:auto">${x.soort}</span></button>`).join('') : '<div class="empty">Niets gevonden</div>';
      $$('[data-nr]', box).forEach(b => b.onclick = () => done(b.dataset.nr));
    };
    inp.oninput = search; search(); inp.focus();
  });
}
async function linkDialog(m) {
  const nr = await pickPlakzicht('Koppelen aan order of offerte');
  if (!nr || typeof nr !== 'string') return;
  await run(async () => { await api('link_mail', m.id, nr); await openMail(m.id); await loadList(); toast('Gekoppeld aan ' + nr); });
}

// ------------------------------------------------------------ orderpagina (nagebootst Plakzicht)
async function openOrder(nr) {
  if (!S.st.plakzicht_live && S.st.plakzicht_url) { openExternal(S.st.plakzicht_url.replace('{nr}', encodeURIComponent(nr))); return; }
  await run(async () => {
    const r = await api('get_order', nr), o = r.data, isOrder = r.soort === 'order';
    const ov = $('#overlay');
    ov.innerHTML = `<div class="ohead"><button class="btn" data-close>← Terug naar mail</button>
      <h1>${isOrder ? `<span class="mono">#${esc(o.nr)}</span>` : `Offerte <span class="mono">${esc(o.nr)}</span>`} · ${esc(o.klant)}</h1>
      ${o.url ? `<button class="btn" id="pz-ext">Openen in Plakzicht</button>` : '<span class="badge">nagebootste Plakzicht-pagina</span>'}</div>
      <div class="grid2"><div class="panel">
        <h2>Mails bij deze ${isOrder ? 'order' : 'offerte'} <small>${r.mails.length}</small></h2>
        <div class="row"><button class="btn primary" id="mailklant">Mail aan klant</button></div>
        ${r.mails.length ? `<table class="t"><thead><tr><th></th><th>Onderwerp</th><th>Mailbox</th><th>Datum</th></tr></thead><tbody>
          ${r.mails.map(x => `<tr class="${x.toegang ? 'click' : ''}" data-mail="${esc(x.id)}" data-mb="${x.mailbox_id}" data-folder="${esc(x.folder)}">
            <td><span class="badge ${x.folder === 'sent' ? '' : 'order'}" style="font-family:inherit">${x.folder === 'sent' ? 'uit' : 'in'}</span></td>
            <td>${esc(x.subject)}${x.toegang ? '' : ' <span class="note">(geen toegang)</span>'}</td><td>${esc(x.mailbox)}</td><td>${fmtDate(x.date)}</td></tr>`).join('')}
          </tbody></table>` : '<p class="note">Nog geen mails gekoppeld.</p>'}
        <p class="note">Mails komen hier vanzelf bij als het nummer erin staat, of als iemand ze in Mail koppelt.</p>
      </div><div style="display:grid;gap:12px">
        ${isOrder ? `<div class="panel"><h2>Order</h2>
          ${o.omschrijving ? `<div class="note">${esc(o.omschrijving)}</div>` : ''}
          ${o.status ? `<div class="kv"><span>Status</span><b>${esc(o.status)}</b></div>` : ''}
          <div class="kv"><span>Uiterlijk verzenden</span><b>${fmtDay(o.due)}</b></div>
          ${o.leverdatum ? `<div class="kv"><span>Leverdatum</span><b>${fmtDay(o.leverdatum)}</b></div>` : ''}
          <div class="kv"><span>Drukproef</span><b>${esc((o.proof || {}).tekst || 'geen')}</b></div>
          ${o.on_hold ? `<div class="kv"><span>On hold</span><b>${esc(o.on_hold.status)}</b></div>` : ''}
          ${shipLine(o.verzending)}
          ${o.bedrag != null ? `<div class="kv"><span>Bedrag</span><b>${eur(o.bedrag)}</b></div>` : ''}
          ${o.openstaand ? `<div class="kv"><span>Nog te betalen</span><b>${eur(o.openstaand)}</b></div>` : ''}
          ${(o.offertes || []).map(q => `<div class="kv"><span>Offerte</span><button class="linkish mono" data-goto="${esc(q)}">${esc(q)}</button></div>`).join('')}
          ${(o.regels || []).length ? `<h3 class="sub">Regels</h3>${o.regels.map(r => `<div class="kv"><span>${esc(r.naam)}${r.specificatie ? ' · ' + esc(r.specificatie) : ''}</span><b>${r.aantal != null ? esc(String(r.aantal).replace('.0', '')) : ''}</b></div>`).join('')}` : ''}
        </div><div class="panel"><h2>Productie</h2><div class="row">${stepsHtml(o.productie)}</div><p class="note">${esc(stepsText(o.productie))}</p></div>`
        : `<div class="panel"><h2>Offerte</h2><div class="kv"><span>Status</span><b>${esc(o.status)}</b></div>
          ${o.omschrijving ? `<div class="note">${esc(o.omschrijving)}</div>` : ''}
          ${o.bedrag != null ? `<div class="kv"><span>Bedrag</span><b>${eur(o.bedrag)}</b></div>` : ''}
          ${o.geldig_tot ? `<div class="kv"><span>Geldig tot</span><b>${fmtDay(o.geldig_tot)}</b></div>` : ''}
          ${(o.orders || []).map(n => `<div class="kv"><span>Order</span><button class="linkish mono" data-goto="${esc(n)}">#${esc(n)}</button></div>`).join('')}</div>`}
      </div></div>`;
    ov.hidden = false;
    $('[data-close]', ov).onclick = closeOverlay;
    $$('[data-goto]', ov).forEach(b => b.onclick = () => openOrder(b.dataset.goto));
    if ($('#pz-ext', ov)) $('#pz-ext', ov).onclick = () => openExternal(o.url);
    $$('[data-ext]', ov).forEach(b => b.onclick = e => { e.preventDefault(); openExternal(b.dataset.ext); });
    $('#mailklant').onclick = () => openCompose({ mode: 'new', to: o.email, order_nr: o.nr, subject: (isOrder ? 'Uw order ' : 'Offerte ') + o.nr });
    $$('tr.click', ov).forEach(tr => tr.onclick = async () => {
      closeOverlay();
      if (S.popout || isMs()) { await openMail(tr.dataset.mail); return; }
      S.view = { mailbox_id: +tr.dataset.mb, folder: tr.dataset.folder }; S.filter = 'alle';
      renderSide(); await loadList(); await openMail(tr.dataset.mail);
    });
  });
}
function closeOverlay() {
  if (S.cmp && S.cmp.full) { stashCompose(); renderReader(); if (!S.popout) renderList(); return; }
  $('#overlay').hidden = true; $('#overlay').innerHTML = ''; $('#overlay').classList.remove('calpage'); setNav('nav-mail'); if (evPending.list) { clearTimeout(evT); evT = setTimeout(applyEvents, 50); } }
$('#nav-orders').onclick = async () => { const nr = await pickPlakzicht('Order of offerte openen'); if (nr && typeof nr === 'string') openOrder(nr); };
$('#nav-mail').onclick = closeOverlay;
$('#nav-cal').onclick = () => openCalendar();
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#overlay').hidden && !$('#dlg').open) closeOverlay(); });

// ------------------------------------------------------------ opstellen
let savedRange = null;
function saveSel() { const s = getSelection(); if (s.rangeCount && $('#editor') && $('#editor').contains(s.anchorNode)) savedRange = s.getRangeAt(0).cloneRange(); }
function restoreSel() { const ed = $('#editor'); ed.focus(); if (savedRange) { const s = getSelection(); s.removeAllRanges(); s.addRange(savedRange); } }
function exec(cmd, val) { restoreSel(); document.execCommand('styleWithCSS', false, true); document.execCommand(cmd, false, val); saveSel(); }
function insertHtml(html) { restoreSel(); document.execCommand('insertHTML', false, html); saveSel(); }
function pickImage() {
  return new Promise(res => {
    const p = $('#filepick'); p.value = '';
    p.onchange = () => {
      const f = p.files[0]; if (!f) return res(null);
      if (f.size > 1500000) { toast('Afbeelding is groter dan 1,5 MB; kies een kleinere.'); return res(null); }
      const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(f);
    };
    p.click();
  });
}
function toolbarHtml(full) {
  return `<div class="toolbar" role="toolbar" aria-label="Tekstopmaak">
    ${full ? `<select data-cmd="formatBlock" aria-label="Stijl"><option value="p">Normaal</option><option value="h2">Kop</option><option value="h3">Tussenkop</option><option value="blockquote">Citaat</option></select>
    <select data-cmd="fontName" aria-label="Lettertype"><option value="">Lettertype</option><option>Arial</option><option>Georgia</option><option>Verdana</option><option>Courier New</option></select>
    <select data-cmd="fontSize" aria-label="Grootte"><option value="">Grootte</option><option value="2">Klein</option><option value="3">Normaal</option><option value="4">Groot</option><option value="5">Heel groot</option></select>
    <span class="sep"></span>` : ''}
    <button class="tb" data-cmd="bold" title="Vet (Ctrl+B)" style="font-weight:700">B</button>
    <button class="tb" data-cmd="italic" title="Cursief (Ctrl+I)" style="font-style:italic">I</button>
    <button class="tb" data-cmd="underline" title="Onderstrepen (Ctrl+U)" style="text-decoration:underline">U</button>
    ${full ? `<button class="tb" data-cmd="strikeThrough" title="Doorhalen" style="text-decoration:line-through">S</button>` : ''}
    <label class="colorbtn" title="Tekstkleur" style="color:#a3431f">A<input type="color" data-color="foreColor" value="#a3431f"></label>
    ${full ? `<label class="colorbtn" title="Markeren" style="background:#fff3df">ab<input type="color" data-color="hiliteColor" value="#fff3a8"></label>
    <span class="sep"></span>
    <button class="tb" data-cmd="insertUnorderedList" title="Opsomming">• Lijst</button>
    <button class="tb" data-cmd="insertOrderedList" title="Genummerde lijst">1. Lijst</button>
    <button class="tb" data-cmd="justifyLeft" title="Links uitlijnen">⯇</button>
    <button class="tb" data-cmd="justifyCenter" title="Centreren">≡</button>
    <span class="sep"></span>` : ''}
    <button class="tb" data-act="link" title="Link">Link</button>
    <button class="tb" data-act="image" title="Afbeelding invoegen">Afbeelding</button>
    ${full ? `<button class="tb" data-cmd="removeFormat" title="Opmaak wissen">Opmaak wissen</button>` : ''}
  </div>`;
}
function wireToolbar(root, editorSel) {
  const ed = $(editorSel, root);
  const keep = () => { const s = getSelection(); if (s.rangeCount && ed.contains(s.anchorNode)) savedRange = s.getRangeAt(0).cloneRange(); };
  ed.addEventListener('keyup', keep); ed.addEventListener('mouseup', keep); ed.addEventListener('blur', keep);
  const run2 = (cmd, val) => { ed.focus(); if (savedRange) { const s = getSelection(); s.removeAllRanges(); s.addRange(savedRange); } document.execCommand('styleWithCSS', false, true); document.execCommand(cmd, false, val); keep(); };
  $$('button[data-cmd]', root).forEach(b => { b.onmousedown = e => e.preventDefault(); b.onclick = () => run2(b.dataset.cmd); });
  $$('select[data-cmd]', root).forEach(s => s.onchange = () => { if (s.value) run2(s.dataset.cmd, s.dataset.cmd === 'formatBlock' ? '<' + s.value + '>' : s.value); s.selectedIndex = 0; });
  $$('input[data-color]', root).forEach(i => i.oninput = () => run2(i.dataset.color, i.value));
  $$('[data-act=link]', root).forEach(b => { b.onmousedown = e => e.preventDefault(); b.onclick = async () => {
    const f = await dialog(`<form><h2>Link invoegen</h2><input name="url" placeholder="https://" style="width:100%" required>
      <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Invoegen</button></div></form>`);
    if (f) { let u = f.get('url').trim(); if (!/^(https?:|mailto:)/i.test(u)) u = 'https://' + u; run2('createLink', u); }
  }; });
  $$('[data-act=image]', root).forEach(b => { b.onmousedown = e => e.preventDefault(); b.onclick = async () => {
    const src = await pickImage(); if (src) run2('insertHTML', `<img src="${src}" alt="" style="max-width:100%">`);
  }; });
}
// Eigen handtekening voor deze mailbox, dan eigen standaard, dan de algemene van de mailbox
function sigFor(mbId) {
  const me = S.st.user.id, L = S.st.signatures;
  return L.find(s => s.user_id === me && s.mailbox_id === mbId) || L.find(s => s.user_id === me && !s.mailbox_id)
    || L.find(s => !s.user_id && s.mailbox_id === mbId) || null;
}
function sigHtml(s, mbId) {
  const mb = mailboxById(mbId);
  return sanitize(s.html).replace(/\{naam\}/gi, esc(S.st.user.name)).replace(/\{mailbox\}/gi, esc(mb ? mb.address : ''));
}
function sigOptions(sel) {
  const mine = S.st.signatures.filter(s => s.user_id), gen = S.st.signatures.filter(s => !s.user_id);
  const o = s => `<option value="${s.id}" ${sel && sel.id === s.id ? 'selected' : ''}>${esc(s.name)}</option>`;
  return `<option value="">Geen</option>${mine.length ? `<optgroup label="Mijn handtekeningen">${mine.map(o).join('')}</optgroup>` : ''}${gen.length ? `<optgroup label="Algemeen">${gen.map(o).join('')}</optgroup>` : ''}`;
}

// ------------------------------------------------------------ beheer
let ADM = null, admTab = 'users';
async function openAdmin(tab) {
  admTab = tab || admTab;
  await run(async () => {
    ADM = await api('admin_data');
    const tabs = [['users', 'Gebruikers'], ['mailboxes', 'Microsoft-mailboxen'], ['labels', 'Labels'], ['sigs', 'Handtekeningen'], ['detect', 'Herkenning en Plakzicht'], ['ms', 'Microsoft-koppeling'], ['claude', 'Claude'], ['server', 'Server en back-up']];
    const ov = $('#overlay');
    ov.innerHTML = `<div class="ohead"><button class="btn" data-close>← Terug naar mail</button><h1>Beheer</h1></div>
      <div class="tabs">${tabs.map(([k, n]) => `<button class="pill ${admTab === k ? 'on' : ''}" data-tab="${k}">${n}</button>`).join('')}</div>
      <div id="admbody"></div>`;
    ov.hidden = false;
    $('[data-close]', ov).onclick = async () => {
      closeOverlay(); await refreshState();
      if (!S.view || (S.view.mailbox_id && !mailboxById(S.view.mailbox_id))) S.view = S.st.mailboxes.length ? inboxView(S.st.mailboxes[0]) : null;
      $('#whoami').textContent = S.st.user.name;
      renderSide(); await loadList(); renderRibbon();
    };
    $$('[data-tab]', ov).forEach(b => b.onclick = () => openAdmin(b.dataset.tab));
    await ({ users: admUsers, mailboxes: admMailboxes, labels: admLabels, sigs: admSigs, detect: admDetect, ms: admMs, claude: admClaude, server: admServer })[admTab]();
  });
}
$('#btn-admin').onclick = () => openAdmin('users');
$('#nav-rules').onclick = () => openRules();
const mbName = id => (ADM.mailboxes.find(m => m.id === id) || {}).display || '?';

function admUsers(edit) {
  const u = edit || null;
  $('#admbody').innerHTML = `<div class="grid2"><div class="panel"><h2>Gebruikers <small>loggen in met eigen naam en wachtwoord</small></h2>
    <table class="t"><thead><tr><th>Naam</th><th>Gebruikersnaam</th><th>Rol</th><th>Mailboxen</th><th>Ingelogd op</th></tr></thead><tbody>
    ${ADM.users.map(x => `<tr class="click" data-u="${x.id}"><td><b>${esc(x.name)}</b></td><td class="mono">${esc(x.username)}</td><td>${x.role}</td>
      <td>${x.role === 'beheerder' ? 'alle' : x.mailboxes.map(mbName).map(esc).join(', ') || '<span class="muted">geen</span>'}</td><td>${x.devices ? x.devices + ' apparaat' + (x.devices > 1 ? 'en' : '') : '<span class="muted">—</span>'}</td></tr>`).join('')}
    </tbody></table><div><button class="btn primary" id="u-new">+ Gebruiker aanmaken</button></div></div>
    <form class="panel form" id="uform"><h2>${u ? 'Gebruiker wijzigen' : 'Nieuwe gebruiker'}</h2>
      <label>Naam<input name="name" value="${esc(u ? u.name : '')}" required></label>
      <label>Gebruikersnaam<input name="username" value="${esc(u ? u.username : '')}" required pattern="[a-z0-9._\\-]{2,40}" title="kleine letters, cijfers, - . _"></label>
      <label>${u ? 'Nieuw wachtwoord (leeg = niet wijzigen)' : 'Wachtwoord'}<input name="password" type="password" ${u ? '' : 'required'}></label>
      <label>Rol<select name="role"><option value="gebruiker">Gebruiker</option><option value="beheerder" ${u && u.role === 'beheerder' ? 'selected' : ''}>Beheerder (ziet alles)</option></select></label>
      <div class="checks"><span class="muted" style="font-size:12px">Toegang tot mailboxen</span>
        ${ADM.mailboxes.map(m => `<label><input type="checkbox" name="mb" value="${m.id}" ${u && u.mailboxes.includes(m.id) ? 'checked' : ''}> ${esc(m.address)}</label>`).join('')}</div>
      <div class="row"><button class="btn primary">Opslaan</button>${u ? `<button type="button" class="btn" id="u-off" title="Bijvoorbeeld bij een verloren laptop">Overal afmelden</button><button type="button" class="btn danger" id="u-del">Verwijderen</button>` : ''}</div>
      ${u ? `<p class="note">Een nieuw wachtwoord invullen meldt ${esc(u.name)} ook overal af.</p>` : ''}
    </form></div>`;
  $$('[data-u]').forEach(tr => tr.onclick = () => admUsers(ADM.users.find(x => x.id === +tr.dataset.u)));
  $('#u-new').onclick = () => admUsers();
  $('#uform').onsubmit = e => {
    e.preventDefault(); const f = new FormData(e.target);
    run(async () => {
      await api('save_user', { id: u && u.id, name: f.get('name'), username: f.get('username'), password: f.get('password'), role: f.get('role'), mailboxes: f.getAll('mb').map(Number) });
      toast('Gebruiker opgeslagen'); await openAdmin('users');
    });
  };
  if ($('#u-off')) $('#u-off').onclick = () => run(async () => { await api('user_logout_all', u.id); toast(`${u.name} is op alle apparaten afgemeld`); await openAdmin('users'); });
  if ($('#u-del')) $('#u-del').onclick = async () => {
    const ok = await dialog(`<form><h2>${esc(u.name)} verwijderen?</h2><p class="muted">Deze gebruiker kan daarna niet meer inloggen.</p><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Verwijderen</button></div></form>`);
    if (ok) run(async () => { await api('delete_user', u.id); toast('Gebruiker verwijderd'); await openAdmin('users'); });
  };
}
function fmtSize(b) { b = b || 0; return b < 1048576 ? Math.max(1, Math.round(b / 1024)) + ' kB' : (b / 1048576).toFixed(b < 10485760 ? 1 : 0).replace('.', ',') + ' MB'; }
function fmtAgo(t) {
  if (!t) return 'nog niet';
  const sec = Math.round(Date.now() / 1000 - t);
  if (sec < 60) return 'zojuist';
  if (sec < 3600) return Math.round(sec / 60) + ' min geleden';
  return fmtDate(new Date(t * 1000).toISOString(), true);
}
function syncCell(m) {
  const st = m.sync; if (!st) return '';
  if (st.error) return `<span class="badge" style="background:var(--bad-soft);color:var(--bad)" title="${esc(st.error)}">fout</span><div class="note" style="max-width:280px">${esc(st.error)}</div>`;
  const busy = st.busy || st.folders_synced < st.folders;
  if (st.warn && !busy) return `<span class="badge off" style="font-family:inherit" title="${esc(st.warn)}">deels</span><div class="note" style="max-width:280px">${esc(st.warn)}</div>
    <div class="note">${st.mails} mails · ${fmtSize(st.bytes)} · ${fmtAgo(st.last_ok)}</div>`;
  return `<span class="badge ${busy ? 'off' : 'order'}" style="font-family:inherit">${busy ? 'bezig' : 'bijgewerkt'}</span>
    <div class="note">${st.mails} mails, ${st.bodies} met inhoud · ${fmtSize(st.bytes)} · ${st.folders_synced}/${st.folders} mappen · ${fmtAgo(st.last_ok)}</div>`;
}
function admMailboxes() {
  const ms = isMs(), user = ADM.auth === 'user', accts = ADM.accounts || [];
  const acctSel = m => `<select data-acct="${m.id}" aria-label="Account voor ${esc(m.address)}">
      ${m.ms_account ? '' : '<option value="">— kies een account —</option>'}
      ${accts.map(a => `<option value="${esc(a.id)}" ${a.id === m.ms_account ? 'selected' : ''}>${esc(a.upn)}</option>`).join('')}</select>`;
  $('#admbody').innerHTML = `<div class="grid2"><div class="panel"><h2>Gekoppelde mailboxen</h2>
    <div style="overflow-x:auto"><table class="t"><thead><tr><th>Adres</th><th>Soort</th>${ms && user ? '<th>Via account</th>' : ''}${ms ? '<th>Offline bewaren</th>' : ''}<th>${ms ? 'Lokale kopie' : 'Status'}</th><th></th></tr></thead><tbody>
    ${ADM.mailboxes.map(m => `<tr><td>${esc(m.address)}</td><td>${m.kind}</td>
      ${ms && user ? `<td>${acctSel(m)}</td>` : ''}
      ${ms ? `<td><select data-days="${m.id}" aria-label="Offline bewaren voor ${esc(m.address)}">${(ADM.periods || []).map(([d, n]) => `<option value="${d}" ${(m.cache_days ?? 90) === d ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></td>` : ''}
      <td>${ms ? syncCell(m) : '<span class="badge order" style="font-family:inherit">demo</span>'}</td>
      <td style="white-space:nowrap">${ms ? `<button class="btn small" data-sync="${m.id}" title="Nu bijwerken">Bijwerken</button> <button class="btn small" data-clear="${m.id}" title="Lokale kopie wissen en opnieuw ophalen">Opnieuw</button> ` : ''}<button class="btn small danger" data-rm="${m.id}">Ontkoppelen</button></td></tr>`).join('')}
    </tbody></table></div>
    ${ms ? '<p class="note">De server houdt van elke mailbox een lokale kopie bij (zoals het offline-bestand van Outlook) en werkt die elke minuut bij. Per mailbox kies je hoe ver terug: mails binnen die periode staan met inhoud op de server en openen direct. Oudere mails blijven bij Microsoft en haal je op met de knop onder de maillijst.</p>' : ''}</div>
    <form class="panel form" id="mbform"><h2>Mailbox koppelen</h2>
      <label>Mailadres<input name="address" placeholder="naam@jouwbedrijf.nl" required></label>
      <label>Soort<select name="kind"><option value="gedeeld">Gedeelde mailbox</option><option value="persoonlijk">Persoonlijke mailbox</option></select></label>
      <button class="btn primary">Koppelen</button>
      <p class="note">${ms ? (user ? 'Het programma zoekt zelf met welk aangemeld Microsoft-account de mailbox bereikbaar is (eerst het account met hetzelfde adres). Je kunt dat daarna per mailbox aanpassen.' : 'Bij koppelen controleert het programma of de app bij de mailbox mag.') + ' Ontkoppelen haalt alleen de koppeling weg; in Microsoft 365 blijft alles staan.' : 'Demo: er wordt een nagebootste mailbox aangemaakt.'}</p></form></div>`;
  $('#mbform').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target); run(async () => { toast('Bezig met controleren…'); await api('add_mailbox', f.get('address'), f.get('kind')); toast('Mailbox gekoppeld'); await openAdmin('mailboxes'); }); };
  $$('[data-days]').forEach(sel => sel.onchange = () => run(async () => {
    const d = +sel.value;
    if (d === 0 || d >= 730) toast('Let op: de eerste keer ophalen van zoveel mail kan lang duren en veel ruimte innemen.');
    await api('set_mailbox_cache', +sel.dataset.days, d); toast('Bewaarperiode gewijzigd; de kopie wordt bijgewerkt'); await openAdmin('mailboxes'); }));
  $$('[data-acct]').forEach(sel => sel.onchange = () => run(async () => {
    await api('set_mailbox_account', +sel.dataset.acct, sel.value); toast('Account gewijzigd; de mailbox wordt opnieuw opgehaald'); await openAdmin('mailboxes'); }));
  $$('[data-sync]').forEach(b => b.onclick = () => run(async () => { await api('refresh_now', +b.dataset.sync); toast('Bijwerken gestart'); setTimeout(() => { if ($('#admbody') && admTab === 'mailboxes') openAdmin('mailboxes'); }, 3000); }));
  $$('[data-clear]').forEach(b => b.onclick = async () => {
    const ok = await dialog(`<form><h2>Lokale kopie opnieuw opbouwen?</h2><p class="muted">De kopie op de server wordt gewist en opnieuw opgehaald bij Microsoft. In Microsoft 365 verandert niets.</p><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Opnieuw ophalen</button></div></form>`);
    if (ok) run(async () => { await api('clear_cache', +b.dataset.clear); toast('Wordt opnieuw opgehaald'); await openAdmin('mailboxes'); });
  });
  $$('[data-rm]').forEach(b => b.onclick = async () => {
    const m = ADM.mailboxes.find(x => x.id === +b.dataset.rm);
    const ok = await dialog(`<form><h2>${esc(m.address)} ontkoppelen?</h2><p class="muted">${ms ? 'Alleen de koppeling en de lokale kopie verdwijnen; in Microsoft 365 blijft alles staan.' : 'In de demo worden de mails van deze mailbox ook verwijderd.'}</p><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Ontkoppelen</button></div></form>`);
    if (ok) run(async () => { await api('remove_mailbox', m.id); S.view = null; await openAdmin('mailboxes'); });
  });
}
function admLabels(edit) {
  const l = edit || null;
  $('#admbody').innerHTML = `<div class="grid2"><div class="panel"><h2>Labels <small>zichtbaar voor iedereen</small></h2>
    <table class="t"><thead><tr><th>Label</th><th>Hoort bij gebruiker</th></tr></thead><tbody>
    ${ADM.labels.map(x => `<tr class="click" data-l="${x.id}"><td><span class="swatch" style="--c:${esc(x.color)}"></span> ${esc(x.name)}</td>
      <td>${x.user_id ? esc((ADM.users.find(u => u.id === x.user_id) || {}).name || '') : '<span class="muted">algemeen</span>'}</td></tr>`).join('')}
    </tbody></table><div><button class="btn primary" id="l-new">+ Label maken</button></div></div>
    <form class="panel form" id="lform"><h2>${l ? 'Label wijzigen' : 'Nieuw label'}</h2>
      <label>Naam<input name="name" value="${esc(l ? l.name : '')}" required></label>
      <label>Kleur<input type="color" name="color" value="${esc(l ? l.color : '#1f6fb2')}" style="height:34px;width:70px;padding:2px"></label>
      <label>Hoort bij gebruiker (optioneel)<select name="user_id"><option value="">Niemand: algemeen label</option>
        ${ADM.users.map(u => `<option value="${u.id}" ${l && l.user_id === u.id ? 'selected' : ''}>${esc(u.name)}</option>`).join('')}</select></label>
      <div class="row"><button class="btn primary">Opslaan</button>${l ? `<button type="button" class="btn danger" id="l-del">Verwijderen</button>` : ''}</div></form></div>`;
  $$('[data-l]').forEach(tr => tr.onclick = () => admLabels(ADM.labels.find(x => x.id === +tr.dataset.l)));
  $('#l-new').onclick = () => admLabels();
  $('#lform').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target); run(async () => {
    await api('save_label', { id: l && l.id, name: f.get('name'), color: f.get('color'), user_id: f.get('user_id') ? +f.get('user_id') : null });
    toast('Label opgeslagen'); await openAdmin('labels'); }); };
  if ($('#l-del')) $('#l-del').onclick = () => run(async () => { await api('delete_label', l.id); toast('Label verwijderd'); await openAdmin('labels'); });
}
function sigEditor(root, s, opts) {
  // opts: { users: [...]|null (beheerder), mailboxes: [...], onSaved, onDeleted }
  root.innerHTML = `<div class="form"><h2>${s && s.id ? 'Handtekening wijzigen' : 'Nieuwe handtekening'}</h2>
      <label>Naam<input id="s-name" value="${esc(s ? s.name : '')}" placeholder="Bijvoorbeeld: Standaard of Kort"></label>
      ${opts.users ? `<label>Voor<select id="s-user"><option value="">Iedereen (algemene handtekening)</option>
        ${opts.users.map(u => `<option value="${u.id}" ${s && s.user_id === u.id ? 'selected' : ''}>${esc(u.name)}</option>`).join('')}</select></label>` : ''}
      <label>Automatisch gebruiken bij mailbox<select id="s-mb"><option value="">${opts.users ? 'Geen (alleen handmatig kiezen)' : 'Alle mailboxen (mijn standaard)'}</option>
        ${opts.mailboxes.map(m => `<option value="${m.id}" ${s && s.mailbox_id === m.id ? 'selected' : ''}>${esc(m.address)}</option>`).join('')}</select></label>
      <div><div class="muted" style="font-size:12px;margin-bottom:3px">Handtekening (afbeelding of logo: klik op Afbeelding)</div>
        <div style="border:1px solid var(--line);border-radius:8px;overflow:hidden">${toolbarHtml(false)}<div class="sigedit" id="s-edit" contenteditable="true">${s && s.html ? sanitize(s.html) : '<p><b>{naam}</b><br>[Functie] · [telefoon]</p>'}</div></div>
        <p class="note"><span class="mono">{naam}</span> wordt de naam van wie verstuurt, <span class="mono">{mailbox}</span> het adres van de mailbox.</p></div>
      <div class="row"><button class="btn primary" id="s-save">Opslaan</button>${s && s.id ? `<button class="btn danger" id="s-del">Verwijderen</button>` : ''}</div></div>`;
  wireToolbar(root, '#s-edit');
  $('#s-save', root).onclick = () => run(async () => {
    const id = await api('save_signature', { id: s && s.id, name: $('#s-name', root).value, mailbox_id: $('#s-mb', root).value ? +$('#s-mb', root).value : null,
      user_id: opts.users ? ($('#s-user', root).value ? +$('#s-user', root).value : null) : 'me', html: sanitize($('#s-edit', root).innerHTML) });
    toast('Handtekening opgeslagen'); await refreshState(); opts.onSaved(id);
  });
  if ($('#s-del', root)) $('#s-del', root).onclick = async () => {
    const ok = await dialog(`<form><h2>Handtekening “${esc(s.name)}” verwijderen?</h2><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Verwijderen</button></div></form>`);
    if (ok) run(async () => { await api('delete_signature', s.id); await refreshState(); toast('Verwijderd'); opts.onDeleted(); });
  };
}
function admSigs(edit) {
  const s = edit === undefined ? ADM.signatures[0] || null : edit;
  const groups = [[null, 'Algemeen (iedereen)'], ...ADM.users.map(u => [u.id, u.name])];
  $('#admbody').innerHTML = `<div class="grid2"><div class="panel" id="s-box"></div>
    <div class="panel"><h2>Handtekeningen</h2>
      ${groups.map(([uid, label]) => { const list = ADM.signatures.filter(x => (x.user_id || null) === uid); return list.length ? `<h3 class="sub">${esc(label)}</h3>
        ${list.map(x => `<div class="kv"><button class="linkish" data-s="${x.id}">${esc(x.name)}</button><span class="muted">${x.mailbox_id ? esc(mbName(x.mailbox_id)) : uid ? 'standaard' : ''}</span></div>`).join('')}` : ''; }).join('')}
      <button class="btn" id="s-new">+ Nieuwe handtekening</button>
      <p class="note">Welke handtekening iemand krijgt: eerst zijn eigen handtekening voor die mailbox, dan zijn eigen standaard, dan de algemene van de mailbox. Iedere gebruiker kan zijn eigen handtekeningen ook zelf maken via zijn naam rechtsboven.</p></div></div>`;
  sigEditor($('#s-box'), s, { users: ADM.users, mailboxes: ADM.mailboxes,
    onSaved: async id => { await openAdmin('sigs'); }, onDeleted: () => openAdmin('sigs') });
  $$('[data-s]').forEach(b => b.onclick = () => admSigs(ADM.signatures.find(x => x.id === +b.dataset.s)));
  $('#s-new').onclick = () => admSigs(null);
}
// ------------------------------------------------------------ mijn instellingen (iedere gebruiker)
let mySec = 'view';
async function openMySettings(editId, section) {
  if (section) mySec = section;
  await run(async () => { await refreshState(); });
  const secs = [['view', 'Weergave'], ['notify', 'Meldingen'], ['qs', 'Snelle stappen'], ['claude', 'Claude'], ['sig', 'Handtekeningen'], ['pw', 'Wachtwoord'], ['dev', 'Apparaten']];
  const ov = $('#overlay');
  ov.innerHTML = `<div class="ohead"><button class="btn" data-close>← Terug naar mail</button><h1>Mijn instellingen</h1><span class="note">${esc(S.st.user.name)} · ${esc(S.st.user.username)}</span></div>
    <div class="tabs">${secs.map(([k, n]) => `<button class="pill ${mySec === k ? 'on' : ''}" data-sec="${k}">${n}</button>`).join('')}</div><div id="mybody"></div>`;
  ov.hidden = false;
  $('[data-close]', ov).onclick = () => { closeOverlay(); renderList(); renderRibbon(); };
  $$('[data-sec]', ov).forEach(b => b.onclick = () => openMySettings(undefined, b.dataset.sec));
  ({ view: myView, notify: myNotify, qs: myQuicksteps, claude: myClaude, sig: () => mySigs(editId), pw: myPw, dev: myDevices })[mySec](editId);
}
function myView() {
  const p = P();
  $('#mybody').innerHTML = `<div class="grid2"><form class="panel form" id="vform"><h2>Maillijst</h2>
      <fieldset><legend>Weergave</legend><div class="checks">
        <label><input type="radio" name="listview" value="kolommen" ${p.listview === 'kolommen' ? 'checked' : ''}> Kolommen (zoals Outlook: Van, Onderwerp, Ontvangen, Grootte…)</label>
        <label><input type="radio" name="listview" value="compact" ${p.listview !== 'kolommen' ? 'checked' : ''}> Compact (afzender, onderwerp en labels onder elkaar)</label></div>
        <p class="note">Is de lijst te smal voor de kolommen, dan schakelt hij vanzelf naar compact. Kolommen kiezen en breedtes slepen doe je in de kolomkoppen.</p></fieldset>
      <fieldset><legend>Scheidingsbalken</legend><div class="checks">
        <label><input type="checkbox" name="groups" ${p.groups ? 'checked' : ''}> Scheidingsbalken tonen</label></div>
        <p class="note">Op datum gesorteerd: Vandaag, Gisteren, de dagen van de afgelopen week en daarna Ouder. Gesorteerd op een andere kolom: een balk per waarde (bijvoorbeeld per afzender). Klik op een balk om hem in te klappen.</p></fieldset>
      <fieldset><legend>Regelhoogte</legend><div class="checks">${['smal', 'middel', 'breed'].map(d => `<label><input type="radio" name="density" value="${d}" ${document.body.dataset.density === d ? 'checked' : ''}> ${d[0].toUpperCase() + d.slice(1)}</label>`).join('')}</div></fieldset>
      <fieldset><legend>Beantwoorden en doorsturen</legend><div class="checks">
        <label><input type="radio" name="reply_in" value="pane" ${p.reply_in === 'pane' ? 'checked' : ''}> In het leesvenster rechts (de lijst en Plakzicht blijven zichtbaar)</label>
        <label><input type="radio" name="reply_in" value="window" ${p.reply_in !== 'pane' ? 'checked' : ''}> Volledig scherm</label></div></fieldset>
    </form><div class="panel"><h2>Bewaard per gebruiker</h2><p class="note">Deze instellingen staan op de server bij jouw naam, dus je hebt ze op elke pc waar je inlogt. Ook je sortering, gekozen kolommen en kolombreedtes worden bewaard.</p></div></div>`;
  $$('#vform input').forEach(i => i.onchange = () => {
    const f = new FormData($('#vform'));
    savePrefs({ listview: f.get('listview'), groups: f.has('groups'), reply_in: f.get('reply_in') });
    if (f.get('density') !== document.body.dataset.density) setDensity(f.get('density'));
    else toast('Opgeslagen');
  });
}
function myPw() {
  $('#mybody').innerHTML = `<div class="grid2"><form class="panel form" id="pwform"><h2>Wachtwoord wijzigen</h2>
      <label>Huidig wachtwoord<input type="password" name="old" required autocomplete="current-password"></label>
      <label>Nieuw wachtwoord (minstens 8 tekens)<input type="password" name="new" required minlength="8" autocomplete="new-password"></label>
      <label>Nieuw wachtwoord nogmaals<input type="password" name="new2" required minlength="8" autocomplete="new-password"></label>
      <div><button class="btn primary">Wijzigen</button></div></form><div></div></div>`;
  $('#pwform').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target);
    if (f.get('new') !== f.get('new2')) return toast('De twee nieuwe wachtwoorden zijn niet gelijk.');
    run(async () => { await api('change_password', f.get('old'), f.get('new')); e.target.reset(); toast('Wachtwoord gewijzigd'); }); };
}
async function myDevices() {
  const d = await api('my_devices');
  const when = t => fmtDate(new Date(t * 1000).toISOString(), true);
  $('#mybody').innerHTML = `<div class="grid2"><div class="panel"><h2>Ingelogd blijven <small>op deze apparaten hoef je niet opnieuw in te loggen</small></h2>
      ${d.devices.length ? `<table class="t devtable"><thead><tr><th>Apparaat</th><th>Laatst gebruikt</th><th>Sinds</th><th></th></tr></thead><tbody>
        ${d.devices.map(x => `<tr><td data-label="Apparaat"><b>${esc(x.device || 'Onbekend apparaat')}</b>${x.current ? ' <span class="badge order">dit apparaat</span>' : ''}<div class="note mono">${esc(x.ip || '')}</div></td>
          <td data-label="Laatst gebruikt">${when(x.last)}</td><td data-label="Sinds">${when(x.created)}</td>
          <td><button class="btn" data-devoff="${esc(x.id)}">Afmelden</button></td></tr>`).join('')}</tbody></table>
        <div class="row"><button class="btn" id="dev-others" ${d.devices.some(x => !x.current) ? '' : 'disabled'}>Alle andere apparaten afmelden</button></div>`
      : '<p class="note">Je bent nergens ingelogd gebleven. Vink bij het inloggen <b>Ingelogd blijven op deze computer</b> aan om na een herstart niet opnieuw te hoeven inloggen.</p>'}
    </div><div class="panel"><h2>Hoe werkt het?</h2>
      <p class="note">${d.days ? `Gebruik je een apparaat ${d.days} dagen niet, dan moet je daar opnieuw inloggen.` : 'Ingelogd blijven staat op dit moment uit (Beheer › Server).'} Wijzig je je wachtwoord, dan worden alle andere apparaten afgemeld. Kwijt of verkocht? Meld het apparaat hier af, of vraag de beheerder je overal af te melden.</p>
      ${d.current_kept ? '' : '<p class="note">Dit apparaat blijft niet ingelogd: na het sluiten of opnieuw opstarten vraagt het weer om je wachtwoord.</p>'}
      ${desk() && desk().client_settings ? `<h3 class="sub">Deze app</h3><p class="note">Verbonden met <span class="mono">${esc(location.origin)}</span>. De app probeert eerst het adres in het netwerk en anders het internetadres.</p>
        <div><button class="btn" id="dev-client">Serveradressen van deze app wijzigen</button></div>` : ''}</div></div>`;
  $$('[data-devoff]').forEach(b => b.onclick = () => run(async () => {
    const cur = d.devices.find(x => x.id === b.dataset.devoff && x.current);
    await api('device_logout', b.dataset.devoff);
    if (cur) { toast('Dit apparaat blijft niet meer ingelogd'); } else toast('Apparaat afgemeld');
    openMySettings(undefined, 'dev');
  }));
  if ($('#dev-client')) $('#dev-client').onclick = () => desk().client_settings();
  if ($('#dev-others')) $('#dev-others').onclick = () => run(async () => { await api('device_logout', 'others'); toast('Alle andere apparaten zijn afgemeld'); openMySettings(undefined, 'dev'); });
}
function mySigs(editId) {
  const mine = S.st.signatures.filter(x => x.user_id === S.st.user.id);
  const cur = editId === 'new' ? null : mine.find(x => x.id === editId) || mine[0] || null;
  $('#mybody').innerHTML = `<div class="grid2"><div class="panel" id="s-box"></div>
    <div class="panel"><h2>Mijn handtekeningen</h2>
      ${mine.map(x => `<div class="kv"><button class="linkish" data-s="${x.id}">${esc(x.name)}</button><span class="muted">${x.mailbox_id ? esc((mailboxById(x.mailbox_id) || {}).display || '') : 'standaard'}</span></div>`).join('') || '<p class="note">Nog geen eigen handtekening; je krijgt dan de algemene handtekening van de mailbox.</p>'}
      <button class="btn" id="s-new">+ Nieuwe handtekening</button></div></div>`;
  sigEditor($('#s-box'), cur, { users: null, mailboxes: S.st.mailboxes, onSaved: id => openMySettings(id, 'sig'), onDeleted: () => openMySettings(undefined, 'sig') });
  $$('[data-s]').forEach(b => b.onclick = () => openMySettings(+b.dataset.s, 'sig'));
  $('#s-new').onclick = () => openMySettings('new', 'sig');
}
function myClaude() {
  const cl = S.st.claude || {}, cp = P().claude, st = claudeState();
  $('#mybody').innerHTML = `<div class="grid2"><form class="panel form" id="clform"><h2>${ICON.sparkle} Claude <small>${esc(st.why)}</small></h2>
      ${st.ok ? '' : `<div class="callout">${esc(st.why)} Je kunt je voorkeuren hieronder alvast instellen.</div>`}
      <label>Toon van voorgestelde antwoorden<select name="tone">
        ${[['zakelijk', 'Zakelijk en vriendelijk'], ['formeel', 'Formeel'], ['informeel', 'Informeel en hartelijk'], ['kort', 'Zo kort mogelijk']].map(([k, n]) => `<option value="${k}" ${cp.tone === k ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
      <label>Aanspreken met<select name="aanhef"><option value="u" ${cp.aanhef === 'u' ? 'selected' : ''}>u</option><option value="je" ${cp.aanhef === 'je' ? 'selected' : ''}>je / jij</option></select></label>
      <label>Taal van het antwoord<select name="lang"><option value="mail" ${cp.lang === 'mail' ? 'selected' : ''}>Dezelfde taal als de mail</option><option value="nl" ${cp.lang === 'nl' ? 'selected' : ''}>Altijd Nederlands</option></select></label>
      <label>Extra aanwijzingen (optioneel)<textarea name="extra" rows="4" maxlength="1000" placeholder="Bijvoorbeeld: noem altijd de verwachte verzenddatum; eindig met 'Met vriendelijke groet' en mijn voornaam">${esc(cp.extra || '')}</textarea></label>
      <div><button class="btn primary">Opslaan</button></div></form>
    <div class="panel"><h2>Wat Claude doet</h2>
      <p class="note">Samenvatten, een antwoord voorstellen (met de gegevens van de gekoppelde order of offerte), vertalen, een label of map voorstellen en gegevens uit een aanvraag halen. Te vinden in het lint (Start › Claude en het tabblad Claude) en bij het schrijven van een mail.</p>
      <p class="note">Alleen de mail waar je op klikt gaat naar Claude, met de gegevens van de gekoppelde order. Claude verstuurt nooit zelf iets: een voorgesteld antwoord komt als concept in je editor.</p>
      ${cl.configured && cl.on ? `<div class="kv"><span>Gebruik deze maand</span><b>${cl.used}${cl.limit ? ' van ' + cl.limit : ''} verzoeken</b></div>` : ''}</div></div>`;
  $('#clform').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target);
    savePrefs({ claude: { tone: f.get('tone'), aanhef: f.get('aanhef'), lang: f.get('lang'), extra: f.get('extra') } }); toast('Opgeslagen'); };
}
function myQuicksteps(editId) {
  const list = S.st.quicksteps || [], admin = S.st.user.role === 'beheerder';
  const q = editId === 'new' ? null : list.find(x => x.id === editId) || null;
  const a = q ? q.actions : {};
  const canEdit = !q || !q.shared || admin;
  const moveVal = a.move ? (a.move.mb || '') + '|' + a.move.folder : '';
  const moveOpts = `<option value="">Niet verplaatsen</option><optgroup label="In dezelfde mailbox als de mail">
      ${[['archive', 'Archief'], ['inbox', 'Postvak IN'], ['junk', 'Ongewenste e-mail'], ['deleted', 'Verwijderde items']].map(([k, n]) => `<option value="|wk:${k}" ${moveVal === '|wk:' + k ? 'selected' : ''}>${n}</option>`).join('')}</optgroup>
    ${S.st.mailboxes.map(mb => `<optgroup label="${esc(mb.display)}">${mb.folders.map(f => `<option value="${mb.id}|${esc(f.id)}" ${moveVal === mb.id + '|' + f.id ? 'selected' : ''}>${'  '.repeat(f.depth)}${esc(mb.display)} › ${esc(f.name)}</option>`).join('')}</optgroup>`).join('')}`;
  $('#mybody').innerHTML = `<div class="grid2"><form class="panel form" id="qform"><h2>${q ? 'Snelle stap wijzigen' : 'Nieuwe snelle stap'}</h2>
      ${canEdit ? '' : '<div class="callout">Deze snelle stap is door de beheerder voor iedereen gemaakt. Je kunt hem gebruiken maar niet wijzigen.</div>'}
      <div class="row"><label style="flex:1">Naam<input name="name" value="${esc(q ? q.name : '')}" required maxlength="60" placeholder="Bijvoorbeeld: Behandeld"></label>
        <label>Kleur<input type="color" name="color" value="${esc(q ? q.color || '#44504a' : '#1f6f54')}" style="height:34px;width:60px;padding:2px"></label></div>
      <fieldset><legend>Wat moet er gebeuren?</legend>
        <label>Gelezen<select name="read"><option value="">Niet wijzigen</option><option value="1" ${a.read === true ? 'selected' : ''}>Als gelezen markeren</option><option value="0" ${a.read === false ? 'selected' : ''}>Als ongelezen markeren</option></select></label>
        <label>Vlag en opvolgen<select name="flag"><option value="">Niet wijzigen</option>${[['on', 'Vlag zetten'], ['today', 'Opvolgen vandaag'], ['tomorrow', 'Opvolgen morgen'], ['thisweek', 'Opvolgen deze week'], ['nextweek', 'Opvolgen volgende week'], ['complete', 'Markeren als voltooid'], ['off', 'Vlag weghalen']].map(([k, n]) => `<option value="${k}" ${a.flag === k ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
        <label>Oppakken<select name="claim"><option value="">Niet wijzigen</option><option value="claim" ${a.claim === 'claim' ? 'selected' : ''}>Zelf oppakken</option><option value="release" ${a.claim === 'release' ? 'selected' : ''}>Vrijgeven</option></select></label>
        <div class="checks"><span class="muted" style="font-size:12px">Labels toevoegen</span>${S.st.labels.map(l => `<label><input type="checkbox" name="label" value="${l.id}" ${(a.labels || []).includes(l.id) ? 'checked' : ''}><span class="swatch" style="--c:${esc(l.color)}"></span> ${esc(l.name)}</label>`).join('')}</div>
        <label>Verplaatsen naar<select name="move">${moveOpts}</select></label>
        <label>Daarna een mail openen<select name="compose"><option value="">Nee</option>
          <option value="forward" ${a.forward_to !== undefined ? 'selected' : ''}>Doorsturen</option><option value="reply" ${a.reply ? 'selected' : ''}>Beantwoorden</option>
          <option value="new" ${a.new_to !== undefined ? 'selected' : ''}>Nieuwe mail (ook zonder gekozen mail)</option></select></label>
        <label>Aan (bij doorsturen of nieuwe mail; mag leeg)<input name="to" value="${esc(a.forward_to || a.new_to || '')}" placeholder="manager@jouwbedrijf.nl"></label>
        <label>Vaste tekst (optioneel)<textarea name="text" rows="3" placeholder="Bijvoorbeeld: Hierbij ter info.">${esc(a.text ? new DOMParser().parseFromString(a.text, 'text/html').body.innerText : '')}</textarea></label>
      </fieldset>
      ${admin ? `<div class="checks"><label><input type="checkbox" name="shared" ${q && q.shared ? 'checked' : ''}> Voor iedereen (alle gebruikers zien deze snelle stap)</label></div>` : ''}
      <div class="row">${canEdit ? '<button class="btn primary">Opslaan</button>' : ''}${q && canEdit ? '<button type="button" class="btn danger" id="q-del">Verwijderen</button>' : ''}</div></form>
    <div class="panel"><h2>Snelle stappen</h2><p class="note">Meerdere acties met één klik, in het lint onder Start › Snelle stappen en via de rechtermuisknop.</p>
      ${list.map(x => `<div class="kv"><button class="linkish" data-q="${x.id}"><span class="mdot" style="--c:${esc(x.color || '#44504a')}"></span> ${esc(x.name)}</button><span class="muted">${x.shared ? 'iedereen' : 'alleen ik'}</span></div><div class="note" style="margin:-4px 0 4px 16px">${esc(qsSummary(x))}</div>`).join('')}
      <button class="btn" id="q-new">+ Nieuwe snelle stap</button></div></div>`;
  $$('[data-q]').forEach(b => b.onclick = () => myQuicksteps(+b.dataset.q));
  $('#q-new').onclick = () => myQuicksteps('new');
  if (!canEdit) $$('#qform input, #qform select, #qform textarea').forEach(i => i.disabled = true);
  $('#qform').onsubmit = e => {
    e.preventDefault(); const f = new FormData(e.target), acts = {};
    if (f.get('read')) acts.read = f.get('read') === '1';
    if (f.get('flag')) acts.flag = f.get('flag');
    if (f.get('claim')) acts.claim = f.get('claim');
    const labs = f.getAll('label').map(Number); if (labs.length) acts.labels = labs;
    const mv = f.get('move'); if (mv) { const i = mv.indexOf('|'); acts.move = { mb: mv.slice(0, i) ? +mv.slice(0, i) : null, folder: mv.slice(i + 1) }; }
    const cm = f.get('compose'), to = f.get('to').trim(), txt = f.get('text').trim();
    if (cm === 'forward') acts.forward_to = to; if (cm === 'new') acts.new_to = to; if (cm === 'reply') acts.reply = true;
    if (cm && txt) acts.text = txt.split(/\n\s*\n/).map(p => '<p>' + esc(p).replace(/\n/g, '<br>') + '</p>').join('');
    run(async () => {
      const id = await api('save_quickstep', { id: q && q.id, name: f.get('name'), color: f.get('color'), shared: f.has('shared'), actions: acts });
      await refreshState(); toast('Snelle stap opgeslagen'); renderRibbon(); myQuicksteps(id);
    });
  };
  if ($('#q-del')) $('#q-del').onclick = () => run(async () => { await api('delete_quickstep', q.id); await refreshState(); toast('Verwijderd'); renderRibbon(); myQuicksteps(); });
}
$('#whoami').onclick = () => openMySettings();
$('#btn-notify').onclick = toggleNotify;

// ------------------------------------------------------------ beheer: Claude
async function admClaude() {
  const c = await api('claude_admin');
  const pin = parseFloat(c.price_in) || 0, pout = parseFloat(c.price_out) || 0;
  const cost = u => pin || pout ? '$' + ((u.tin * pin + u.tout * pout) / 1e6).toFixed(2).replace('.', ',') : '';
  $('#admbody').innerHTML = `<div class="grid2"><div style="display:grid;gap:12px">
    <form class="panel form" id="clcfg"><h2>${ICON.sparkle} Claude koppelen <small>${c.configured ? 'ingesteld' : 'nog niet ingesteld'}</small></h2>
      ${c.configured ? `<div class="okbox">Er is een API-sleutel opgeslagen (${esc(c.hint)})${c.protected ? ', versleuteld met je Windows-account' : ''}.</div>` : '<div class="callout">Nog geen API-sleutel. Tot die er is, staan de Claude-knoppen grijs.</div>'}
      <label>API-sleutel van Anthropic${c.configured ? ' (leeg laten om de huidige te houden)' : ''}<input name="key" type="password" autocomplete="new-password" placeholder="sk-ant-…"></label>
      <label>Model<select name="model">${c.models.map(([k, n]) => `<option value="${esc(k)}" ${c.model === k ? 'selected' : ''}>${esc(n)}</option>`).join('')}
        ${c.models.some(([k]) => k === c.model) ? '' : `<option value="${esc(c.model)}" selected>${esc(c.model)}</option>`}</select></label>
      <div class="row"><label style="flex:1">Prijs invoer ($ per miljoen tokens, optioneel)<input name="price_in" value="${esc(c.price_in)}" inputmode="decimal"></label>
        <label style="flex:1">Prijs uitvoer ($ per miljoen tokens)<input name="price_out" value="${esc(c.price_out)}" inputmode="decimal"></label></div>
      <p class="note">Vul de prijzen van je model in (zie de prijzenpagina in de Anthropic Console); dan rekent het overzicht de kosten per gebruiker uit.</p>
      <div class="row"><button class="btn primary">Opslaan</button><button type="button" class="btn" id="cl-test" ${c.configured ? '' : 'disabled'}>Verbinding testen</button>
        ${c.configured ? '<button type="button" class="btn danger" id="cl-rm">Sleutel verwijderen</button>' : ''}</div><div id="cl-res"></div></form>
    <div class="panel"><h2>Per gebruiker <small>deze maand</small></h2>
      <table class="t"><thead><tr><th>Gebruiker</th><th>Claude</th><th>Limiet per maand</th><th>Gebruik</th><th>Tokens</th>${pin || pout ? '<th>Kosten</th>' : ''}</tr></thead><tbody>
      ${c.users.map(u => `<tr><td><b>${esc(u.name)}</b></td>
        <td><label class="sw" title="Claude aan of uit voor ${esc(u.name)}"><input type="checkbox" data-clon="${u.id}" ${u.claude_on ? 'checked' : ''}><span></span></label></td>
        <td><input type="number" min="0" max="100000" step="10" value="${u.claude_limit ?? 200}" data-cllim="${u.id}" style="width:90px" aria-label="Limiet voor ${esc(u.name)}"> <span class="note">verzoeken</span></td>
        <td>${u.req}</td><td class="note">${(u.tin + u.tout).toLocaleString('nl-NL')}</td>${pin || pout ? `<td>${cost(u)}</td>` : ''}</tr>`).join('')}
      </tbody></table><p class="note">Limiet 0 = geen limiet. Elk verzoek (samenvatten, antwoord, vertalen…) telt als één.</p></div></div>
    <div class="panel steps"><h2>Zo stel je het in</h2><ol>
      <li>Ga naar <b>console.anthropic.com</b> en log in of maak een account voor het bedrijf.</li>
      <li>Zet bij <b>Billing</b> tegoed op het account (of koppel een betaalmethode) en stel daar eventueel een maandlimiet in.</li>
      <li>Maak bij <b>API keys</b> een nieuwe sleutel, bijvoorbeeld “Plakzicht Mail”. Kopieer hem direct (je ziet hem maar één keer).</li>
      <li>Plak de sleutel hiernaast en klik op <b>Opslaan</b>, daarna op <b>Verbinding testen</b>.</li>
      <li>Zet Claude aan voor de collega's die het mogen gebruiken en kies een limiet.</li></ol>
      <p class="note"><b>Privacy:</b> alleen de mail waarop iemand op een Claude-knop klikt gaat naar Anthropic, met de gegevens van de gekoppelde order of offerte. Er wordt niets automatisch of op de achtergrond verstuurd. Via de API gebruikt Anthropic deze gegevens standaard niet om modellen te trainen.</p>
      <p class="note">De sleutel staat in <span class="mono">config.json</span> op de server${navigator.platform.startsWith('Win') ? ', versleuteld met het Windows-account' : ''}, en geldt voor zowel de demo als Microsoft 365.</p></div></div>`;
  $('#clcfg').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target);
    run(async () => { await api('save_claude_config', Object.fromEntries(f)); toast('Opgeslagen'); await refreshState(); renderRibbon(); await openAdmin('claude'); }); };
  $('#cl-test').onclick = () => { $('#cl-res').innerHTML = '<p class="note">Bezig…</p>';
    api('claude_test').then(m => { $('#cl-res').innerHTML = `<div class="okbox">${esc(m)}</div>`; }).catch(e => { $('#cl-res').innerHTML = `<div class="callout">${esc(e.message)}</div>`; }); };
  if ($('#cl-rm')) $('#cl-rm').onclick = async () => {
    const ok = await dialog(`<form><h2>API-sleutel verwijderen?</h2><p class="muted">Claude werkt daarna niet meer tot je een nieuwe sleutel invult.</p><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Verwijderen</button></div></form>`);
    if (ok) run(async () => { await api('save_claude_config', { remove: true }); await refreshState(); renderRibbon(); await openAdmin('claude'); });
  };
  const saveU = id => run(async () => { await api('set_user_claude', id, $(`[data-clon="${id}"]`).checked, $(`[data-cllim="${id}"]`).value); await refreshState(); renderRibbon(); toast('Opgeslagen'); });
  $$('[data-clon]').forEach(i => i.onchange = () => saveU(+i.dataset.clon));
  $$('[data-cllim]').forEach(i => i.onchange = () => saveU(+i.dataset.cllim));
}

async function admDetect() {
  const st = ADM.settings, pc = await api('plakzicht_config');
  $('#admbody').innerHTML = `<div class="grid2"><div style="display:grid;gap:12px">
    <form class="panel form" id="pzform"><h2>Koppeling met Plakzicht <small>${pc.live ? 'in gebruik' : pc.url && pc.has_key ? (pc.mode === 'microsoft' ? 'ingesteld' : 'ingesteld · demo gebruikt de nagebootste') : 'nog niet ingesteld'}</small></h2>
      <p class="note">Plakzicht Mail leest orders en offertes uit Plakzicht (alleen lezen). Zet in Plakzicht onder <b>Instellingen › Plakzicht Mail</b> de koppeling aan en kopieer de API-sleutel.</p>
      <label>Adres van Plakzicht in het netwerk<input name="url" value="${esc(pc.url)}" placeholder="http://192.168.1.10:5000" autocomplete="off"></label>
      <p class="note">Het adres van de Unraid-server met de poort van Plakzicht. Niet app.plakzicht.nl: daar staat Cloudflare Access voor.</p>
      <label>API-sleutel${pc.has_key ? ' (leeg laten om de huidige te houden)' : ''}<input name="key" type="password" autocomplete="new-password" placeholder="${pc.has_key ? '••••••••••••' : 'pzm_…'}"></label>
      <label>Adres om pagina's te openen (optioneel)<input name="open" value="${esc(pc.open)}" placeholder="https://app.plakzicht.nl" autocomplete="off"></label>
      <p class="note">Voor de knop "Openen in Plakzicht" in je browser. Leeg = hetzelfde adres als hierboven.</p>
      <div class="row"><button class="btn primary">Opslaan</button><button type="button" class="btn" id="pz-test" ${pc.url && pc.has_key ? '' : 'disabled'}>Verbinding testen</button>
        ${pc.has_key ? '<button type="button" class="btn danger" id="pz-rm">Sleutel verwijderen</button>' : ''}</div><div id="pz-res"></div></form>
    <form class="panel form" id="dform"><h2>Herkennen in mails</h2>
      <p class="note">Mail zoekt in onderwerp en tekst naar deze patronen (reguliere expressies). ${pc.live ? 'Of het nummer echt bestaat, wordt bij het openen van de mail in Plakzicht nagekeken.' : 'Het nummer moet in Plakzicht bestaan.'}</p>
      <label>Ordernummer<input name="order_pattern" class="mono" value="${esc(st.order_pattern)}"></label>
      <label>Offertenummer<input name="offerte_pattern" class="mono" value="${esc(st.offerte_pattern)}"></label>
      <p class="note">Met haakjes kies je het deel dat het nummer is: <span class="mono">Offertenummer[\\s:"'#]*(\\d+)</span> herkent “- Offertenummer 338” als 338.</p>
      ${pc.live ? '' : `<label>Plakzicht-adres voor "Openen in Plakzicht" zonder koppeling (optioneel, {nr} = nummer)<input name="plakzicht_url" value="${esc(st.plakzicht_url)}" placeholder="https://plakzicht.jouwbedrijf.nl/orders/{nr}"></label>`}
      <button class="btn primary">Opslaan en mails opnieuw nalopen</button></form></div>
    <div class="panel"><h2>Uitproberen</h2><textarea id="d-test" rows="5" style="width:100%">Graag de status van order 000000415.\n- Offertenummer 338\nOf offerte OFF-2026-121 in de demo.</textarea>
      <div id="d-out" class="row"></div></div></div>`;
  const test = () => {
    const out = [], t = $('#d-test').value;
    for (const [k, cls] of [['order_pattern', 'order'], ['offerte_pattern', 'off']]) {
      try { for (const mm of t.matchAll(new RegExp($(`[name=${k}]`).value, 'gi'))) out.push(`<span class="badge ${cls}">${esc(mm[1] || mm[0])}</span>`); }
      catch { out.push(`<span class="badge" style="color:var(--bad)">patroon klopt niet</span>`); }
    }
    $('#d-out').innerHTML = out.join('') || '<span class="note">Niets herkend</span>';
  };
  $('#d-test').oninput = test; $$('#dform input').forEach(i => i.oninput = test); test();
  $('#dform').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target); if (!f.has('plakzicht_url')) f.set('plakzicht_url', st.plakzicht_url || ''); run(async () => {
    await api('save_settings', Object.fromEntries(f)); await refreshState(); toast('Opgeslagen; koppelingen bijgewerkt'); await openAdmin('detect'); }); };
  $('#pzform').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target); run(async () => {
    await api('save_plakzicht_config', Object.fromEntries(f)); await refreshState(); toast('Opgeslagen'); await openAdmin('detect'); }); };
  $('#pz-test').onclick = () => { $('#pz-res').innerHTML = '<p class="note">Bezig…</p>';
    api('plakzicht_test').then(m => { $('#pz-res').innerHTML = `<div class="okbox">${esc(m)}</div>`; }).catch(e => { $('#pz-res').innerHTML = `<div class="callout">${esc(e.message)}</div>`; }); };
  if ($('#pz-rm')) $('#pz-rm').onclick = () => run(async () => { await api('save_plakzicht_config', { url: pc.url, open: pc.open, remove: true }); await refreshState(); await openAdmin('detect'); });
}
let msAuthView = null, signinPoll = null;
async function admMs() {
  const cfg = await api('ms_config'), ms = cfg.mode === 'microsoft';
  const auth = msAuthView || cfg.auth;
  const userSteps = `<ol>
      <li>Ga naar <b>entra.microsoft.com</b> › Identiteit › Toepassingen › <b>App-registraties</b> › <b>Nieuwe registratie</b>. Naam: “Plakzicht Mail”, alleen accounts in deze organisatie.</li>
      <li>Kies bij omleidings-URI het platform <b>Openbare client/systeemeigen (mobiel en desktop)</b> en vul <span class="mono">http://localhost</span> in. Registreren.</li>
      <li>Kopieer op het overzicht de <b>Toepassings-ID (client)</b> en de <b>Map-ID (tenant)</b> en vul ze hiernaast in.</li>
      <li>Zet onder <b>Verificatie</b> “Openbare clientstromen toestaan” op <b>Ja</b> en sla op.</li>
      <li><b>API-machtigingen</b> › Machtiging toevoegen › Microsoft Graph › <b>Gedelegeerde machtigingen</b>: <span class="mono">Mail.ReadWrite</span>, <span class="mono">Mail.ReadWrite.Shared</span>, <span class="mono">Mail.Send</span>, <span class="mono">Mail.Send.Shared</span> (User.Read staat er al), en voor de agenda <span class="mono">Calendars.ReadWrite</span>. Klik op <b>Beheerderstoestemming verlenen</b>.</li>
      <li>Geef je eigen account in het Exchange-beheercentrum <b>Volledige toegang</b> op de gedeelde mailboxen die je wilt koppelen (info@, verkoop@ …). Wil je ook vanuit die mailboxen versturen, geef dan ook <b>Verzenden als</b>. Nieuwe rechten kunnen tot een uur duren.</li>
      <li>Klik hiernaast op <b>Opslaan</b> en daarna op <b>Aanmelden met Microsoft</b>. Je krijgt een code; vul die in op microsoft.com/devicelogin en meld je aan. Herhaal dit voor elk account dat je wilt toevoegen.</li>
      <li>Klik op <b>Overschakelen naar Microsoft 365</b>, log opnieuw in, en koppel onder <b>Microsoft-mailboxen</b> de mailboxen. Per mailbox kies je via welk account hij loopt.</li>
    </ol>
    <p class="note">Er is geen clientgeheim nodig. Elk account kan alleen bij mailboxen waar dat account zelf rechten op heeft. Wat medewerkers in een mailbox doen, ziet Microsoft als acties van het account van die mailbox.</p>
    <p class="note">Werkt aanmelden met een code niet (melding over voorwaardelijke toegang)? Gebruik dan op de server zelf <b>Aanmelden via deze browser</b>.</p>`;
  const appSteps = `<ol>
      <li>Ga naar <b>entra.microsoft.com</b> › Identiteit › Toepassingen › <b>App-registraties</b> › <b>Nieuwe registratie</b>. Naam bijvoorbeeld “Plakzicht Mail”, alleen accounts in deze organisatie.</li>
      <li>Kopieer de <b>Toepassings-ID (client)</b> en de <b>Map-ID (tenant)</b> en vul ze hiernaast in.</li>
      <li><b>API-machtigingen</b> › Microsoft Graph › <b>Toepassingsmachtigingen</b>: <span class="mono">Mail.ReadWrite</span> en <span class="mono">Mail.Send</span>. Klik op <b>Beheerderstoestemming verlenen</b>.</li>
      <li><b>Certificaten en geheimen</b> › Nieuw clientgeheim. Kopieer direct de <b>Waarde</b> en vul hem hiernaast in.</li>
      <li><b>Beperk de toegang</b> tot alleen de mailboxen die je koppelt; anders kan de app bij álle mailboxen. In Exchange Online PowerShell, met een e-mailbeveiligingsgroep met die mailboxen:
        <pre>New-ServicePrincipal -AppId &lt;client-ID&gt; -ObjectId &lt;object-ID van de ondernemingstoepassing&gt; -DisplayName "Plakzicht Mail"
New-ManagementScope -Name "Plakzicht Mail" -RecipientRestrictionFilter "MemberOfGroup -eq '&lt;DN van de groep&gt;'"
New-ManagementRoleAssignment -App &lt;client-ID&gt; -Role "Application Mail.ReadWrite" -CustomResourceScope "Plakzicht Mail"
New-ManagementRoleAssignment -App &lt;client-ID&gt; -Role "Application Mail.Send" -CustomResourceScope "Plakzicht Mail"</pre>
        Haal daarna de Graph-machtigingen uit stap 3 weg, anders gelden die voor alle mailboxen.</li>
      <li>Testen, overschakelen en mailboxen koppelen.</li>
    </ol>`;
  const can = cfg.tenant && cfg.client_id;
  const signinBox = `<h3 class="sub">Aangemelde Microsoft-accounts</h3>
    ${cfg.accounts.length ? `<div class="accts">${cfg.accounts.map(a => `<div class="acct"><span class="av">${esc((a.name || a.upn).charAt(0))}</span>
        <div><b>${esc(a.name || a.upn)}</b><div class="note">${esc(a.mail || a.upn)}${a.added ? ' · sinds ' + esc(a.added) : ''}${cfg.calendar ? (a.cal ? ' · <span style="color:var(--brand)">agenda ✓</span>' : ' · <span style="color:var(--warn-ink)">agenda: opnieuw aanmelden</span>') : ''}</div></div>
        ${ms ? `<button type="button" class="btn small" data-ownmb="${esc(a.id)}" title="De mailbox van dit account toevoegen aan Plakzicht Mail">Eigen mailbox koppelen</button>` : ''}
        <button type="button" class="btn small danger" data-rmacct="${esc(a.id)}">Afmelden</button></div>`).join('')}</div>`
      : '<p class="note">Nog geen account aangemeld.</p>'}
    <div class="row">
      <button type="button" class="btn primary msbtn" data-signin="code" ${can ? '' : 'disabled'}>${ICON.msLogo} ${cfg.accounts.length ? 'Nog een account aanmelden' : 'Aanmelden met Microsoft'}</button>
      ${cfg.local ? `<button type="button" class="btn" data-signin="browser" ${can ? '' : 'disabled'} title="Alleen op de pc waar de server draait">Aanmelden via deze browser</button>` : ''}
    </div>
    ${can ? '<p class="note">Je krijgt een code die je invult op microsoft.com/devicelogin, vanaf deze pc of je telefoon. Daar kies je met welk account je aanmeldt. Zo kun je meerdere accounts toevoegen; per mailbox kies je welk account gebruikt wordt.</p>' : '<p class="note">Vul eerst tenant-ID en client-ID in en klik op Opslaan.</p>'}`;
  $('#admbody').innerHTML = `<div class="grid2"><div style="display:grid;gap:12px">
    <div class="panel"><h2>Stand <small>${ms ? 'echte mailboxen' : 'alles nagebootst'}</small></h2>
      <div class="${ms ? 'okbox' : 'callout'}">${ms ? 'Plakzicht Mail werkt nu met <b>echte Microsoft 365-mailboxen</b>. Verplaatsen, mappen maken en verwijderen gebeurt ook echt in Outlook.'
        : 'Demo-stand: er is geen verbinding met Microsoft. Mails komen uit een nagebootste mailbox.'}</div>
      <div class="row">${ms ? `<button class="btn" id="m-demo">Terug naar de demo</button>` : `<button class="btn primary" id="m-ms" ${cfg.ready ? '' : 'disabled'}>Overschakelen naar Microsoft 365</button>`}</div>
      ${!ms && !cfg.ready ? `<p class="note">Eerst ${auth === 'user' ? 'minstens één Microsoft-account aanmelden' : 'het clientgeheim invullen'} (hieronder).</p>` : ''}
      <p class="note">Beide standen hebben hun eigen gegevens. De eerste keer in Microsoft 365 worden gebruikers, labels, handtekeningen en instellingen uit de demo overgenomen; mailboxen koppel je daarna zelf. Na overschakelen log je opnieuw in.</p>
    </div>
    <form class="panel form" id="msform"><h2>Koppeling met Microsoft</h2>
      ${cfg.auth === 'app' && cfg.accounts.length ? `<div class="callout"><b>Let op:</b> er zijn ${cfg.accounts.length} accounts aangemeld, maar het programma staat op <b>App met clientgeheim</b>. Kies hieronder <b>Aanmelden met Microsoft</b> en klik op Opslaan.</div>` : ''}
      <div class="authpick" role="radiogroup" aria-label="Manier van koppelen">
        <label class="${auth === 'user' ? 'on' : ''}"><input type="radio" name="auth" value="user" ${auth === 'user' ? 'checked' : ''}>
          <span><b>Aanmelden met Microsoft</b> (aanbevolen)<br><span class="note">Je meldt je één keer aan met je eigen account. Geen geheim, geen PowerShell.</span></span></label>
        <label class="${auth === 'app' ? 'on' : ''}"><input type="radio" name="auth" value="app" ${auth === 'app' ? 'checked' : ''}>
          <span><b>App met clientgeheim</b><br><span class="note">De app werkt zelfstandig; toegang beperken via Exchange.</span></span></label>
      </div>
      <label>Tenant-ID (map-ID)<input name="tenant" class="mono" value="${esc(cfg.tenant)}" placeholder="00000000-0000-0000-0000-000000000000" autocomplete="off"></label>
      <label>Client-ID (toepassings-ID)<input name="client_id" class="mono" value="${esc(cfg.client_id)}" placeholder="00000000-0000-0000-0000-000000000000" autocomplete="off"></label>
      ${auth === 'app' ? `<label>Clientgeheim (waarde, niet de geheim-ID)${cfg.has_secret ? ' — leeg laten om het huidige te houden' : ''}<input name="secret" type="password" autocomplete="new-password" placeholder="${cfg.has_secret ? '••••••••••••' : ''}"></label>
      <p class="note">${cfg.has_secret ? (cfg.secret_protected ? 'Het geheim staat versleuteld met je Windows-account in config.json.' : 'Het geheim staat in config.json naast het programma. Bewaar de map veilig.') : 'Nog geen geheim opgeslagen.'}</p>` : ''}
      <div class="row"><button class="btn ${auth === 'user' && can ? '' : 'primary'}">Opslaan</button></div>
      ${auth === 'user' ? `<div class="signin" id="m-signbox">${signinBox}</div>` : ''}
    </form>
    ${auth === 'user' ? `<div class="panel form"><h2>${ICON.calendar} Agenda</h2>
      <label class="row" style="color:var(--ink);font-size:13px"><input type="checkbox" id="m-cal" ${cfg.calendar ? 'checked' : ''}> Agenda gebruiken (afspraken bekijken, maken en wijzigen)</label>
      <ol class="note" style="margin:0;padding-left:18px;display:grid;gap:4px">
        <li>Voeg in de app-registratie bij <b>API-machtigingen</b> de gedelegeerde machtiging <span class="mono">Calendars.ReadWrite</span> toe en klik op <b>Beheerderstoestemming verlenen</b>.</li>
        <li>Zet hierboven het vinkje aan.</li>
        <li>Meld elk account <b>opnieuw</b> aan (Nog een account aanmelden, met hetzelfde account). Bij het account staat daarna “agenda ✓”.</li></ol>
      <p class="note">Een collega ziet de agenda van een account als hij bij de eigen mailbox van dat account kan. Mail blijft gewoon werken, ook als een account nog niet opnieuw is aangemeld.</p></div>` : ''}
    <form class="panel form" id="mstest"><h2>Verbinding testen</h2>
      <label>Mailbox om te proberen (optioneel)<input name="address" placeholder="info@jouwbedrijf.nl"></label>
      <div class="row"><button class="btn">Testen</button></div><div id="m-res"></div>
    </form></div>
    <div class="panel steps"><h2>Zo stel je het in (eenmalig)</h2>${auth === 'user' ? userSteps : appSteps}</div></div>
    ${ms ? '' : `<div class="panel" style="margin-top:14px"><h2>Demo</h2><p class="note">Alle demo-gegevens terugzetten naar de beginsituatie. Je wordt daarna uitgelogd.</p>
      <div><button class="btn danger" id="reset">Demo terugzetten</button></div></div>`}`;
  $$('#msform [name=auth]').forEach(r => r.onchange = () => { msAuthView = r.value; admMs(); });
  $('#msform').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target);
    run(async () => { await api('save_ms_config', Object.fromEntries(f)); msAuthView = null; toast('Opgeslagen'); await openAdmin('ms'); }); };
  $('#mstest').onsubmit = e => { e.preventDefault(); const f = new FormData(e.target);
    $('#m-res').innerHTML = '<p class="note">Bezig…</p>';
    run(async () => { const r = await api('test_ms', f.get('address')); $('#m-res').innerHTML = `<div class="${r.ok ? 'okbox' : 'callout'}">${esc(r.message)}</div>`; }); };
  $$('[data-signin]').forEach(b => b.onclick = () => startSignin(b.dataset.signin));
  if ($('#m-cal')) $('#m-cal').onchange = e => run(async () => { await api('set_calendar_enabled', e.target.checked); CAL.info = null; toast(e.target.checked ? 'Agenda aan. Meld de accounts nu opnieuw aan.' : 'Agenda uit'); await openAdmin('ms'); });
  $$('[data-ownmb]').forEach(b => b.onclick = () => run(async () => { await api('link_own_mailbox', b.dataset.ownmb); await refreshState(); toast('Mailbox gekoppeld; hij staat nu links in de lijst'); }));
  $$('[data-rmacct]').forEach(b => b.onclick = async () => {
    const a = cfg.accounts.find(x => x.id === b.dataset.rmacct);
    const ok = await dialog(`<form><h2>${esc(a.upn)} afmelden?</h2><p class="muted">De aanmelding wordt van de server gewist. Mailboxen die via dit account liepen, werken pas weer als je ze aan een ander account koppelt of dit account opnieuw aanmeldt.</p>
      <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Afmelden</button></div></form>`);
    if (ok) run(async () => { await api('ms_remove_account', a.id); toast('Afgemeld'); await openAdmin('ms'); });
  });
  const sw = async mode => {
    const ok = await dialog(`<form><h2>${mode === 'microsoft' ? 'Overschakelen naar Microsoft 365?' : 'Terug naar de demo?'}</h2>
      <p class="muted">${mode === 'microsoft' ? 'Daarna werk je met echte mailboxen. Alles wat je verplaatst of verwijdert, gebeurt ook in Outlook.' : 'De koppeling met Microsoft blijft bewaard; je kunt later terugschakelen.'} Je wordt uitgelogd.</p>
      <div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Overschakelen</button></div></form>`);
    if (ok) run(async () => { await api('set_mode', mode); closeOverlay(); S.view = null; S.sel = null; S.mail = null; await showLogin(); toast('Overgeschakeld. Log opnieuw in.'); });
  };
  if ($('#m-ms')) $('#m-ms').onclick = () => sw('microsoft');
  if ($('#m-demo')) $('#m-demo').onclick = () => sw('demo');
  if ($('#reset')) $('#reset').onclick = async () => {
    const ok = await dialog(`<form><h2>Demo terugzetten?</h2><p class="muted">Alle wijzigingen gaan verloren.</p><div class="dlgbtns"><button type="button" class="btn" data-cancel>Annuleren</button><button class="btn primary">Terugzetten</button></div></form>`);
    if (ok) run(async () => { await api('reset_demo'); closeOverlay(); showLogin(); toast('Demo teruggezet'); });
  };
}
async function startSignin(method) {
  await run(async () => {
    const r = await api('ms_signin_start', method);
    const box = $('#m-signbox');
    if (r.method === 'browser') {
      openExternal(r.url);
      if (box) box.innerHTML = `<div class="callout">Er is een browservenster geopend. Meld je daar aan en kom daarna hier terug.
        <br><span class="note">Geen venster gezien? <a href="${esc(r.url)}" target="_blank" rel="noopener">Open de aanmeldpagina</a>.</span></div>
        <div class="row"><span class="spin" aria-hidden="true"></span><span class="note">Wachten op aanmelden…</span><button type="button" class="btn small" id="m-cancel">Annuleren</button></div>`;
    } else if (box) {
      box.innerHTML = `<div class="codebox"><div class="note">Ga naar</div>
          <a href="${esc(r.url)}" target="_blank" rel="noopener" id="m-url" class="big">${esc(r.url.replace(/^https?:\/\//, ''))}</a>
          <div class="note">en vul deze code in:</div>
          <div class="code"><span id="m-code">${esc(r.code)}</span><button type="button" class="btn small" id="m-copy">Kopiëren</button></div>
          <div class="note">Meld je daarna aan met het Microsoft-account dat je wilt toevoegen. De code is 15 minuten geldig.</div></div>
        <div class="row"><span class="spin" aria-hidden="true"></span><span class="note">Wachten op aanmelden…</span><button type="button" class="btn small" id="m-cancel">Annuleren</button></div>`;
      $('#m-url').onclick = e => { e.preventDefault(); openExternal(r.url); };
      $('#m-copy').onclick = async () => { try { await navigator.clipboard.writeText(r.code); toast('Code gekopieerd'); } catch { toast('Kopiëren lukt niet; neem de code over.'); } };
    }
    if ($('#m-cancel')) $('#m-cancel').onclick = () => { clearInterval(signinPoll); signinPoll = null; api('ms_signin_cancel').catch(() => {}); openAdmin('ms'); };
    clearInterval(signinPoll);
    signinPoll = setInterval(async () => {
      if (!$('#m-signbox')) { clearInterval(signinPoll); signinPoll = null; return; }
      let st; try { st = await api('ms_signin_status'); } catch { return; }
      if (st.state === 'waiting') return;
      clearInterval(signinPoll); signinPoll = null;
      toast(st.message || (st.state === 'ok' ? 'Aangemeld' : 'Aanmelden mislukt'));
      await openAdmin('ms');
      if (st.state === 'error' && $('#m-res')) $('#m-res').innerHTML = `<div class="callout">${esc(st.message)}</div>`;
    }, 2000);
  });
}
async function admServer() {
  const b = await api('backup_info');
  const here = location.protocol + '//' + location.host;
  const where = b.docker ? 'Docker' : b.frozen ? 'Windows (geïnstalleerd)' : 'Windows/Python (programmamap)';
  $('#admbody').innerHTML = `<div class="grid2"><div style="display:grid;gap:12px">
    <div class="panel"><h2>Werkplekken</h2>
      <p style="margin:0">Collega's openen Plakzicht Mail via dit adres:</p>
      <div class="codebox"><span class="big mono">${esc(here)}</span></div>
      <p class="note"><b>Windows:</b> installeer de Plakzicht Mail-app (setup.exe, kies <i>Werkplek</i>) en vul het adres in het netwerk en het internetadres in, bijvoorbeeld <span class="mono">https://mail.plakzicht.nl</span>. De app kiest zelf: op kantoor het adres in het netwerk, anders via internet.<br>
      <b>Mac en overige:</b> open het internetadres in Chrome, Edge of Safari en installeer het als app (Chrome/Edge: knop <i>Installeren</i> in de adresbalk; Safari: Archief › <i>Zet in Dock</i>). Via https werken ook de meldingen rechtsboven.
      ${/^(localhost|127\.)/.test(location.hostname) ? '<br>Staat hier <span class="mono">localhost</span>? Gebruik dan het netwerkadres van de server.' : ''}</p></div>
    <form class="panel form" id="keepform"><h2>Ingelogd blijven</h2>
      <label>Ingelogd blijven tot zoveel dagen zonder gebruik (0 = uit)<input name="days" type="number" min="0" max="365" value="${b.remember_days}" style="max-width:120px"></label>
      <p class="note">Medewerkers kunnen bij het inloggen <i>Ingelogd blijven op deze computer</i> aanvinken; dan hoeven ze na een herstart niet opnieuw in te loggen. Op 0 zetten meldt iedereen die is ingelogd gebleven direct af. Een medewerker overal afmelden doe je bij Gebruikers.</p>
      <div><button class="btn primary">Opslaan</button></div></form>
    <div class="panel"><h2>Back-up</h2>
      <p class="note">Elke nacht om 02:30 maakt de server zelf een back-up van de gegevens (gebruikers, labels, handtekeningen, koppelingen met orders, logboek, instellingen en aangemelde accounts). De laatste 14 worden bewaard in <span class="mono">${esc(b.dir)}</span>. De mail zelf staat veilig bij Microsoft.</p>
      ${b.list.length ? `<div class="note">Laatste: <b>${esc(b.list[0].replace('_', ' ').replace(/(\d\d)(\d\d)$/, '$1:$2'))}</b> · ${b.list.length} bewaard</div>` : '<div class="note">Nog geen back-up gemaakt.</div>'}
      <div><button class="btn" id="bk-now">Nu back-up maken</button></div>
      <p class="note">De opgeslagen geheimen (aanmeldingen bij Microsoft, API-sleutels) zijn versleuteld met <span class="mono">secrets.key</span>. Die staat bewust <b>niet</b> in de back-up: bewaar hem apart (bijvoorbeeld in je wachtwoordkluis). Zonder dat bestand moet je de geheimen na terugzetten opnieuw invullen.</p></div></div>
    <div class="panel"><h2>Deze server</h2>
      <div class="kv"><span>Versie</span><b class="mono">${esc(b.version)}</b></div>
      <div class="kv"><span>Draait als</span><b>${where}</b></div>
      <div class="kv"><span>Gegevensmap</span><span class="mono">${esc(b.data)}</span></div>
      <div class="kv"><span>Achter Cloudflare/proxy</span><span>${b.trust_proxy ? 'ja (echte adressen van de pc\'s worden gebruikt)' : 'nee'}</span></div>
      ${b.docker ? `<p class="note">Bijwerken: in Unraid › Docker de container bijwerken (<i>Check for updates</i>). Gegevens staan in de gekoppelde map en blijven bewaard.</p>`
        : `<p class="note">Bijwerken: start de nieuwe setup.exe op deze pc; gegevens en instellingen blijven bewaard. Draait de server als dienst, dan start hij vanzelf met de pc.</p>`}</div></div>`;
  $('#bk-now').onclick = () => run(async () => { const st = await api('backup_make'); toast('Back-up gemaakt: ' + st); await openAdmin('server'); });
  $('#keepform').onsubmit = e => { e.preventDefault(); run(async () => { await api('save_remember', new FormData(e.target).get('days')); toast('Opgeslagen'); await openAdmin('server'); }); };
}
function showModeBadge() {
  const b = $('#modebadge'); if (!b || !S.st) return;
  b.textContent = isMs() ? 'Microsoft 365' : 'Demo'; b.className = 'modebadge ' + (isMs() ? 'ms' : 'demo');
  b.title = isMs() ? 'Echte mailboxen via Microsoft 365' : 'Demo: alles nagebootst';
}

// Automatisch verversen (nieuwe mail), alleen als je niet bezig bent
setInterval(async () => {
  if (userBusy()) return;
  if (!S.st || S.popout || $('#app').hidden || !$('#overlay').hidden || $('#dlg').open || $('.cmenu.root') || document.body.classList.contains('dragging') || document.hidden) return;
  try { await refreshState(); const sel = S.sel; await loadList(); if (sel && !S.mails.some(m => m.id === sel)) { S.sel = null; S.mail = null; renderReader(); renderPz(); } } catch { /* stil */ }
}, 60000);  // reserve; normaal komen wijzigingen direct binnen via live bijwerken

// ------------------------------------------------------------ live bijwerken: de server meldt wijzigingen van collega's direct
let ES = null, evT = null;
const ASSIGNQ = [];
const evPending = { list: false, sel: false, by: null };
function startEvents() {
  if (ES) ES.close();
  ES = new EventSource('/events');
  ES.onmessage = e => { let ev; try { ev = JSON.parse(e.data); } catch { return; } onEvent(ev); };
}
function stopEvents() { if (ES) { ES.close(); ES = null; } }
function onEvent(ev) {
  if (!S.st) return;
  if (ev.t === 'job') { toast(ev.msg + (ev.warnings && ev.warnings.length ? ' Let op: ' + ev.warnings.join(' ') : '')); }
  if (ev.t === 'assign') { ASSIGNQ.push(ev); clearTimeout(ASSIGNQ.t); ASSIGNQ.t = setTimeout(() => { const l = ASSIGNQ.splice(0);
    toast(l.length === 1 ? l[0].msg : l[0].msg.split(' heeft ')[0] + ` heeft ${l.length} mails aan je toegewezen.`); if (N().on && N().sound) chime(false); }, 800); }
  if (ev.t === 'newmail') onNewMail(ev);
  const mine = new Set(S.st.mailboxes.map(m => m.id));
  if (ev.t !== 'job' && ev.t !== 'assign' && !(ev.mb || []).some(x => mine.has(x))) return;
  evPending.list = true;
  if (ev.key && S.sel && ev.key === S.sel) { evPending.sel = true; evPending.by = ev.by; }
  clearTimeout(evT); evT = setTimeout(applyEvents, 350);
}
async function applyEvents() {
  if (userBusy()) { clearTimeout(evT); evT = setTimeout(applyEvents, 500); return; }
  const busy = $('#dlg').open || $('.cmenu.root') || document.body.classList.contains('dragging') || document.body.classList.contains('resizing');
  if (busy || (!S.popout && !$('#overlay').hidden)) { clearTimeout(evT); evT = setTimeout(applyEvents, 1500); return; }
  const sel = S.sel, selChanged = evPending.sel, by = evPending.by;
  evPending.list = evPending.sel = false; evPending.by = null;
  try {
    if (S.popout) { if (selChanged && sel) await openMail(sel, true); return; }
    await refreshState(); await loadList();
    if (sel && S.sel === sel) {
      if (!S.mails.some(m => m.id === sel)) {
        if (by !== S.st.user.id) toast('Deze mail is intussen door een collega verplaatst of verwijderd.');
        S.sel = null; S.mail = null; setPresence(null); renderReader(); renderPz();
      } else if (selChanged) { await openMail(sel, true); }
    }
  } catch { /* volgende melding probeert opnieuw */ }
}

// ------------------------------------------------------------ mail in een eigen venster
async function popoutMail(id) {
  const d = desk(), row = rowOf(String(id));
  if (d) { d.popout(String(id), (row && row.subject) || 'Mail'); return; }
  const w = window.open(`index.html?popout=${encodeURIComponent(id)}`, 'mail' + String(id).slice(-12).replace(/\W/g, ''), 'width=1000,height=780');
  if (!w) toast('Het venster werd geblokkeerd door de browser.');
}
async function closePopout() {
  const d = desk();
  if (d) { try { await d.close_window(); return; } catch { /* valt terug op window.close */ } }
  window.close();
}
function downloadEml(id) {
  const a = document.createElement('a');
  a.href = '/download/eml?id=' + encodeURIComponent(id); a.download = '';
  document.body.appendChild(a); a.click(); a.remove();
}
async function startPopout(id) {
  S.popout = true;
  document.body.classList.add('popout');
  const st = await api('state');
  S.st = st;
  $('#login').hidden = true; $('#app').hidden = false;
  setDensity(st.user.density, false);
  S.layout = { ...LAYOUT_DEFAULT, ...(st.user.layout || {}) };
  applyLayout();
  loadDrafts();
  await openMail(id);
  renderRibbon();
  // geen eigen live-verbinding: browsers staan maar enkele verbindingen per server toe; ververst bij terugkomen
  window.addEventListener('focus', () => { if (S.sel) openMail(S.sel, true); });
}
// Het hoofdvenster ververst als je terugkomt uit een ander venster.
let focusT;
window.addEventListener('focus', () => {
  if (S.popout || !S.st || $('#app').hidden || !$('#overlay').hidden) return;
  clearTimeout(focusT);
  const go = async () => {
    if (userBusy()) { focusT = setTimeout(go, 500); return; }
    await run(refreshState); await loadList();
    if (S.sel && !S.mails.some(m => m.id === S.sel)) { S.sel = null; S.mail = null; renderReader(); renderPz(); }
    else if (S.sel) await openMail(S.sel, true);
  };
  focusT = setTimeout(go, 800);  // eerst je klik laten afhandelen
});

// Installeren als app (Chrome/Edge op Mac en Windows); alleen via https of localhost, en niet in de Windows-app.
if ('serviceWorker' in navigator && window.isSecureContext && !window.pywebview && !new URLSearchParams(location.search).get('popout')) {
  navigator.serviceWorker.register('sw.js').catch(() => {});
}
// ------------------------------------------------------------ start
(async () => {
  const pop = new URLSearchParams(location.search).get('popout') || '';
  try {
    if (pop) await startPopout(pop);
    else boot(await api('state'));
  } catch { showLogin(); }
})();
