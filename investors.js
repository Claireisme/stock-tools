(() => {
  const $ = id => document.getElementById(id);
  const en = !/^\/zh(?:\/|$)/.test(location.pathname);
  const words = {nav:['持仓追踪','Disclosure Watch'],title:['投资者披露追踪','Investor Disclosure Watch'],intro:['查看基金交易、内幕交易和公开持仓披露。','Explore fund trades, insider transactions and holdings disclosures.'],open:['打开工具 →','Open tool →'],home:['首页','Home'],note:['披露有延迟，并不等同于实时交易。ARK 是基金交易；13F 是季度末持仓快照；国会披露金额通常为区间，交易人可能是家庭成员。','Disclosures are delayed, not live trades. ARK reports fund trades; 13F reports quarter-end holdings; Congressional disclosures generally use amount ranges and may include family members.'],refresh:['检查更新','Check for updates'],events:['披露事件','Disclosure events'],source:['来源','Source'],all:['全部','All'],search:['搜索人物或代码','Search name or ticker'],roster:['关注名单','Watchlist'],identity:['未核验唯一标识的对象不会按姓名自动匹配。','People without verified identifiers are not matched by name.']};
  document.querySelectorAll('[data-investor]').forEach(n => { const w = words[n.dataset.investor]; if (w) n.textContent = w[en ? 1 : 0]; });
  const t = (zh, english) => en ? english : zh;
  const el = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; };
  const timeZoneKey = 'investor-time-zone-v1';
  const timeZones = [
    ['America/New_York', t('美东时间（纽约）','Eastern Time (New York)')],
    ['Asia/Shanghai', t('北京时间','China Time (Beijing)')],
    ['Europe/London', t('伦敦时间','London Time')],
    ['America/Los_Angeles', t('美西时间（洛杉矶）','Pacific Time (Los Angeles)')],
    ['UTC', t('协调世界时（UTC）','Coordinated Universal Time (UTC)')],
    ['local', t('设备本地时间','Device local time')]
  ];
  const extraTimeZones = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone').filter(zone => !timeZones.some(([value]) => value === zone)) : [];
  let selectedTimeZone = 'America/New_York';
  try {
    const saved = localStorage.getItem(timeZoneKey);
    if (timeZones.some(([value]) => value === saved) || extraTimeZones.includes(saved)) selectedTimeZone = saved;
  } catch (_) {}
  function formatTime(value) {
    if (value == null || value === '') return '—';
    const raw = String(value);
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
    if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw)) return raw;
    const date = new Date(raw);
    if (!Number.isFinite(date.getTime())) return raw;
    const zone = selectedTimeZone === 'local' ? Intl.DateTimeFormat().resolvedOptions().timeZone : selectedTimeZone;
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {timeZone:zone, year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hourCycle:'h23', timeZoneName:'shortOffset'}).formatToParts(date).map(part => [part.type, part.value]));
    return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute} ${parts.timeZoneName}`;
  }
  function timeZoneControl() {
    const label = el('label', null, 'investor-timezone');
    label.append(el('span', t('显示时区','Display time zone')));
    const select = el('select', null, 'investor-timezone-select');
    for (const [value, name] of timeZones) { const option = el('option', name); option.value = value; select.append(option); }
    if (extraTimeZones.length) {
      const group = el('optgroup'); group.label = t('其他时区','Other time zones');
      for (const value of extraTimeZones) { const option = el('option', value.replaceAll('_', ' ')); option.value = value; group.append(option); }
      select.append(group);
    }
    select.value = selectedTimeZone;
    select.addEventListener('change', () => {
      selectedTimeZone = select.value;
      try { localStorage.setItem(timeZoneKey, selectedTimeZone); } catch (_) {}
      document.querySelectorAll('.investor-timezone-select').forEach(control => { control.value = selectedTimeZone; });
      window.dispatchEvent(new Event('investor-timezone-change'));
    });
    label.append(select);
    return label;
  }
  window.InvestorTimeZone = {get: () => selectedTimeZone, format: formatTime, createControl: timeZoneControl};
  $('investor-timezone-control').append(timeZoneControl());
  let data = null, loaded = false, timer, searchTimer, loadSequence = 0;
  function render() {
    if (!data) return;
    const records = data.records || [], events = data.events || [], byId = Object.fromEntries(records.map(r => [r.id, r]));
    const sourceBox = $('investor-sources'); sourceBox.replaceChildren();
    const sources = data.sources || [];
    for (const [key, value] of Object.entries(sources)) {
      const s = typeof value === 'object' && value !== null ? value : {status: value};
      const card = el('div', null, 'investor-source-card');
      const status = {active: t('已连接','Connected'), pending: t('等待检查','Awaiting check'), error: t('错误','Error')}[s.status] || s.status || '—';
      card.append(el('strong', s.label || s.name || key), el('span', status), el('span', s.message || s.description || '')); if (s.last_success) card.append(el('span', `${t('最近成功','Last success')}: ${formatTime(s.last_success)}`)); sourceBox.append(card);
    }
    const query = $('investor-search').value.trim().toLowerCase(), filter = $('investor-source').value;
    const match = (r, e = {}) => !query || [r.name_en, r.name_zh, r.associated_entity, ...(r.related_tickers || []), e.ticker, e.details].some(v => String(v || '').toLowerCase().includes(query));
    const box = $('investor-events'); box.replaceChildren();
    const shown = events.filter(e => (!filter || e.source === (filter === 'ark_daily' ? 'ark' : filter)) && match(byId[e.investor_id] || {}, e));
    if (!shown.length) box.append(el('p', t('暂无已采集事件。请查看上方来源状态。','No collected events. Check the source status above.'), 'investor-empty'));
    for (const e of shown) {
      const r = byId[e.investor_id] || {}, row = el('article', null, 'investor-event');
      let detail = e.details; try { if (typeof detail === 'string' && detail.startsWith('{')) detail = JSON.parse(detail); } catch (_) {}
      const label = e.source === 'ark' ? (e.event_type === 'buy' ? t('买入','Buy') : e.event_type === 'sell' ? t('卖出','Sell') : e.event_type) : e.event_type;
      const head = el('div', null, 'investor-event-head'); const name = `${r.name_zh || r.name_en || e.investor_id || (detail && detail.candidate_name) || '—'} · ${e.ticker || (detail && detail.issuer) || '—'}`; const title = e.investor_id ? el('a', name, 'investor-profile-link') : el('strong', name); if (e.investor_id) title.href = `#investors/${encodeURIComponent(e.investor_id)}`; head.append(title, el('span', `${e.source || ''} / ${label || '—'}`)); row.append(head);
      const details = [e.transaction_date && `${t('交易日期','Transaction')}: ${formatTime(e.transaction_date)}`, e.accepted_at && `${t('受理','Accepted')}: ${formatTime(e.accepted_at)}`, e.reported_at && `${t('披露','Reported')}: ${formatTime(e.reported_at)}`, e.observed_at && `${t('采集','Observed')}: ${formatTime(e.observed_at)}`, e.shares != null && `${e.source === '13f' ? t('持仓变化','Position change') : t('数量','Shares')}: ${e.shares}`, e.price != null && `${t('价格','Price')}: ${e.price}`, e.plan_10b5_1 && t('申报文件标记 10b5-1','10b5-1 indicated on filing')].filter(Boolean);
      row.append(el('p', details.join(' · ')));
      if (detail && typeof detail === 'object') {
        if (e.source === '13f') row.append(el('p', `${detail.cusip || ''} · ${detail.class || ''} ${detail.put_call || ''} · ${detail.previous_period || ''}: ${detail.previous_amount || '0'} → ${detail.current_period || ''}: ${detail.current_amount || '0'} ${detail.unit || ''}`), el('p', detail.note || ''));
        else if (e.source === 'ark') row.append(el('p', [detail.fund, detail.name, detail.isin, detail.percent_of_etf != null && `${t('基金权重','Fund weight')}: ${detail.percent_of_etf}%`].filter(Boolean).join(' · ')));
        else if (e.source === 'congress') row.append(el('p', [detail.asset, detail.owner && `${t('交易人','Owner')}: ${detail.owner}`, (detail.amount_range || (detail.amount_low && `${detail.amount_low} – ${detail.amount_high}`)), detail.disclosure_delay_days != null && `${t('披露延迟','Disclosure delay')}: ${detail.disclosure_delay_days} ${t('天','days')}`].filter(Boolean).join(' · ')), el('p', detail.note || ''));
        else row.append(el('p', JSON.stringify(detail)));
      } else if (detail) row.append(el('p', detail));
      if (e.source_url) { try { const url = new URL(e.source_url); if (url.protocol === 'https:') { const a = el('a', t('查看原始披露 ↗','View source ↗')); a.href = url.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; row.append(a); } } catch (_) {} }
      box.append(row);
    }
    const roster = $('investor-roster'); roster.replaceChildren();
    for (const r of records.filter(r => (!filter || r.category === filter) && match(r))) {
      const row = el('div', null, 'investor-person');
      const left = el('div'); const link = el('a', `${r.name_zh || ''} ${r.name_en || ''}`, 'investor-profile-link'); link.href = `#investors/${encodeURIComponent(r.id)}`; left.append(link, el('p', `${r.associated_entity || ''} · ${r.disclosure_form || ''}`));
      const status = r.reporting_person_cik ? t('已核验 CIK','CIK verified') : r.category === 'congress' ? t('议席身份已匹配','Member identity matched') : r.category === 'ark_daily' ? t('基金来源','Fund source') : t('身份待核验','Identity pending');
      row.append(left, el('span', status, 'investor-tag')); roster.append(row);
    }
  }
  window.addEventListener('investor-timezone-change', render);
  async function load() { const sequence = ++loadSequence; try { const source = $('investor-source').value; const params = new URLSearchParams(); if (source) params.set('source', source === 'ark_daily' ? 'ark' : source); const query = $('investor-search').value.trim(); if (query) params.set('q', query); const response = await fetch('/api/investors?' + params); const result = await response.json(); if (sequence !== loadSequence) return; if (!response.ok) throw new Error(result.error || response.status); data = result; loaded = true; render(); if (result.running && location.hash === '#investors') { clearTimeout(timer); timer = setTimeout(load, 5000); } } catch (e) { $('investor-status').textContent = t('无法加载追踪数据：','Unable to load data: ') + e.message; } }
  $('investor-refresh').addEventListener('click', async () => { const b = $('investor-refresh'); b.disabled = true; $('investor-status').textContent = t('正在检查更新…','Checking for updates…'); try { const response = await fetch('/api/investors/refresh', {method:'POST'}); const result = await response.json(); if (!response.ok) throw new Error(result.error || response.status); $('investor-status').textContent = result.started ? t('更新已启动，请稍后查看来源状态。','Update started; check source status shortly.') : t('更新正在进行。','Update already in progress.'); await load(); clearTimeout(timer); timer = setTimeout(load, 5000); } catch (e) { $('investor-status').textContent = t('更新失败：','Update failed: ') + e.message; } finally { b.disabled = false; } });
  $('investor-source').addEventListener('change', load); $('investor-search').addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(load, 250); });
  const alertKey = 'investor-alert-cursor-v1';
  let checkingAlerts = false;
  function alertState() {
    const enabled = localStorage.getItem(alertKey) !== null;
    $('investor-alerts').textContent = enabled ? t('关闭浏览器提醒','Disable browser alerts') : t('启用浏览器提醒','Enable browser alerts');
    $('investor-alert-status').textContent = enabled ? t('提醒已启用：保持此页面打开，浏览器每分钟检查新披露。','Alerts enabled: keep this page open; the browser checks for new disclosures every minute.') : t('浏览器提醒需要此页面保持打开，并允许通知。','Browser alerts require this page to remain open and notification permission.');
  }
  async function checkAlerts() {
    const cursor = localStorage.getItem(alertKey);
    if (cursor === null || checkingAlerts || !('Notification' in window) || Notification.permission !== 'granted') return;
    checkingAlerts = true;
    try {
      const response = await fetch(`/api/investors/alerts?after=${encodeURIComponent(cursor)}`, {cache:'no-store'});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const result = await response.json();
      if (result.events.length) {
        const first = result.events[0];
        const notification = new Notification(t('新的投资披露','New investment disclosures'), {body: `${result.events.length} ${t('条新事件','new events')} · ${first.ticker || first.investor_id || ''} ${first.event_type || ''}`});
        notification.onclick = () => { window.focus(); location.hash = '#investors'; load(); notification.close(); };
        if (location.hash === '#investors') load();
      }
      localStorage.setItem(alertKey, String(result.cursor));
    } catch (_) { $('investor-alert-status').textContent = t('提醒检查失败，将在下一次重试。','Alert check failed; will retry.'); }
    finally { checkingAlerts = false; }
  }
  $('investor-alerts').addEventListener('click', async () => {
    if (localStorage.getItem(alertKey) !== null) { localStorage.removeItem(alertKey); alertState(); return; }
    if (!('Notification' in window) || !window.isSecureContext) { $('investor-alert-status').textContent = t('浏览器提醒需要 HTTPS 或本机地址。','Browser alerts require HTTPS or localhost.'); return; }
    try {
      if (await Notification.requestPermission() !== 'granted') { $('investor-alert-status').textContent = t('浏览器未授予通知权限。','Notification permission was not granted.'); return; }
      const response = await fetch('/api/investors/alerts', {cache:'no-store'});
      if (!response.ok) throw new Error();
      const result = await response.json(); localStorage.setItem(alertKey, String(result.cursor)); alertState();
    } catch (_) { $('investor-alert-status').textContent = t('无法启用提醒，请重试。','Could not enable alerts. Try again.'); }
  });
  alertState(); setInterval(checkAlerts, 60000); checkAlerts();
  function route() { if ((location.hash === '#investors' || location.hash.startsWith('#investors/')) && !loaded) load(); }
  window.addEventListener('hashchange', route); route();
})();
