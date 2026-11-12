(() => {
  const root = document.getElementById('investor-profile');
  const dashboard = document.getElementById('investor-dashboard');
  const en = !/^\/zh(?:\/|$)/.test(location.pathname);
  const t = (zh, english) => en ? english : zh;
  const el = (tag, value, cls) => { const node = document.createElement(tag); if (value != null) node.textContent = value; if (cls) node.className = cls; return node; };
  const n = value => value == null ? '—' : new Intl.NumberFormat(en ? 'en-US' : 'zh-CN', {maximumFractionDigits: 2}).format(value);
  let current = '', filter = {}, offset = 0, requestId = 0;
  function details(event) { try { return typeof event.details === 'string' ? JSON.parse(event.details) : event.details || {}; } catch (_) { return {}; } }
  function cleanAsset(value) {
    return String(value).replace(/\s*\[(?:ST|OP|GS|MF|EF|AB|CS|CT)\]\s*$/, '').trim();
  }
  function sourceName(source) {
    return ({congress:t('众议院披露','House disclosure'), ark:t('ARK 基金交易','ARK fund trade'), form4:'SEC Form 4', '13f':'SEC 13F', '13d':'SEC 13D'})[source] || source || t('公开披露','Disclosure');
  }
  function describeAction(event) {
    const kind = String(event.event_type || '');
    if (event.source === 'congress') {
      if (kind === 'PTR 披露') return t('提交交易披露文件','Transaction disclosure filing');
      if (kind === 'P') return t('买入','Purchase');
      if (/^S\s*\(partial\)$/i.test(kind)) return t('卖出部分','Partial sale');
      if (/^S\s*\(full\)$/i.test(kind)) return t('全部卖出','Full sale');
      if (kind === 'S') return t('卖出','Sale');
      if (kind === 'E') return t('交换','Exchange');
    }
    if (event.source === 'ark') return kind === 'buy' ? t('基金买入','Fund purchase') : kind === 'sell' ? t('基金卖出','Fund sale') : t('其他交易','Other transaction');
    if (event.source === 'form4') {
      if (kind.startsWith('P ')) return t('买入（公开市场或私下）','Purchase (open market or private)');
      if (kind.startsWith('S ')) return t('卖出（公开市场或私下）','Sale (open market or private)');
      const labels = {'期权行权或转换':t('行权或转换','Exercise or conversion'), '税款或行权价扣缴':t('缴税或支付行权价','Tax or exercise-price payment'), '赠与':t('赠与','Gift'), '其他交易':t('其他交易','Other transaction')};
      return labels[kind] || t('其他申报','Other reported transaction');
    }
    if (event.source === '13f') return ({'新建仓':t('季度末新出现的持仓','New quarter-end position'), '增仓':t('季度末持仓增加','Quarter-end position increased'), '减仓':t('季度末持仓减少','Quarter-end position decreased'), '退出持仓':t('季度末不再申报此持仓','Position no longer reported')})[kind] || t('季度持仓变化','Quarterly position change');
    if (event.source === '13d') return /\/A$/.test(kind) ? t('持股申报更新','Ownership filing amendment') : t('持股申报','Ownership filing');
    return kind || t('其他披露','Other disclosure');
  }
  function actionTone(event) {
    const kind = String(event.event_type || '');
    if (event.source === 'ark') return kind === 'buy' ? 'buy' : kind === 'sell' ? 'sell' : 'neutral';
    if (event.source === 'congress') return kind === 'P' ? 'buy' : /^S(?:\s*\((?:partial|full)\))?$/i.test(kind) ? 'sell' : 'neutral';
    if (event.source === 'form4') return kind.startsWith('P ') ? 'buy' : kind.startsWith('S ') ? 'sell' : 'neutral';
    if (event.source === '13f') return ['新建仓', '增仓'].includes(kind) ? 'buy' : ['减仓', '退出持仓'].includes(kind) ? 'sell' : 'neutral';
    return 'neutral';
  }
  function ownerLabel(value) {
    return ({SP:t('配偶','Spouse'), DC:t('受抚养子女','Dependent child'), JT:t('共同持有','Jointly held')})[value] || t('未能确认，请查看原文','Not confirmed; see filing');
  }
  function formatObserved(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
  }
  function sourceLink(url) { try { const u = new URL(url); if (u.protocol !== 'https:') return null; const a = el('a', t('查看原文 ↗', 'Source ↗')); a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; } catch (_) { return null; } }
  function card(label, value, note) { const box = el('div', null, 'profile-metric'); box.append(el('span', label), el('strong', value)); if (note) box.append(el('small', note)); return box; }
  function section(title, subtitle) { const node = el('section', null, 'profile-panel'); node.append(el('h2', title)); if (subtitle) node.append(el('p', subtitle, 'profile-muted')); return node; }
  function select(label, key, choices, active) {
    const wrap = el('label'); wrap.append(el('span', label)); const input = el('select');
    for (const [value, text] of choices) { const option = el('option', text); option.value = value; option.selected = value === (active || ''); input.append(option); }
    input.addEventListener('change', () => { filter[key] = input.value; offset = 0; load(); }); wrap.append(input); return wrap;
  }
  function render(data) {
    const r = data.record, s = data.summary, category = r.category, events = data.events, pages = data.pagination;
    root.replaceChildren();
    const back = el('a', t('← 返回关注名单','← Back to watchlist'), 'profile-back'); back.href = '#investors'; root.append(back);
    const hero = el('div', null, 'profile-hero'); const heading = el('div');
    heading.append(el('p', 'DISCLOSURE WATCH / PROFILE', 'eyebrow'), el('h1', `${r.name_zh || ''} ${r.name_en || ''}`), el('p', [r.associated_entity, r.disclosure_form].filter(Boolean).join(' · ')));
    hero.append(heading); root.append(hero);
    const note = category === 'ark_daily' ? t('展示 ARK 基金公开的交易通知，并非凯西·伍德个人交易；已采集文件并不代表完整历史或当前持仓。','ARK fund trade notifications, not Cathie Wood’s personal trades. Collected files do not represent complete history or current holdings.') : category === 'congress' ? t('展示已采集并解析的众议院披露；金额为区间，交易人可能是家庭成员。扫描件或无法识别的交易可能缺失。','Collected House disclosures only; amounts are ranges and traders may be family members. Scans and unrecognized transactions may be missing.') : category === '13f' ? t('机构季度末持仓快照的变化，并非逐笔交易或个人持仓。','Changes in institutional quarter-end snapshots, not individual trades or personal holdings.') : t('展示已采集的官方申报，披露时间可能晚于交易日期。','Collected official filings; disclosures may follow transactions.');
    root.append(el('div', note, 'investor-note'));
    const controls = el('div', null, 'profile-controls');
    controls.append(select(t('年份','Year'), 'year', [['',t('全部年份','All years')], ...(data.filters.years || []).map(y => [String(y),String(y)])], filter.year), select(t('方向','Direction'),'side', [['',t('全部方向','All directions')],['buy',t('买入 / 增仓','Buy / increase')],['sell',t('卖出 / 减仓','Sell / decrease')],['other',t('其他','Other')]], filter.side));
    if ((data.filters.funds || []).length) controls.append(select(t('基金','Fund'),'fund', [['',t('全部基金','All funds')], ...data.filters.funds.map(f => [f,f])], filter.fund));
    const search = el('form', null, 'profile-search'); const searchLabel = el('label'); searchLabel.append(el('span',t('标的搜索','Security search'))); const searchInput = el('input'); searchInput.type = 'search'; searchInput.placeholder = t('代码 / 名称 / CUSIP','Ticker / name / CUSIP'); searchInput.value = filter.q || ''; searchLabel.append(searchInput); const searchButton = el('button', t('搜索','Search'), 'options-secondary'); searchButton.type = 'submit'; search.append(searchLabel,searchButton); search.addEventListener('submit', event => { event.preventDefault(); filter.q = searchInput.value.trim(); offset = 0; load(); }); controls.append(search);
    root.append(controls);
    const metrics = el('div', null, 'profile-metrics');
    const countLabel = category === '13f' ? t('持仓变化','Position changes') : t('已解析交易','Parsed transactions');
    metrics.append(card(countLabel, n(category === '13f' ? s.position_change_count : s.transaction_count)), card(category === '13f' ? t('增仓 / 新建仓','Increase / new') : t('买入','Buy'), n(s.buy_count)), card(category === '13f' ? t('减仓 / 退出','Decrease / exit') : t('卖出','Sell'), n(s.sell_count)), card(t('最近交易日期','Latest transaction'), s.latest_transaction_date || '—', category === '13f' ? t('13F 无交易日期','13F has no trade date') : null));
    if (category === 'congress') metrics.append(card(t('披露金额合计区间','Disclosed amount range'), s.amount_count ? `$${n(s.amount_low)} – ${s.amount_high == null ? t('无上限','unbounded') : '$' + n(s.amount_high)}` : '—', t(`基于 ${s.amount_count || 0} 笔已识别金额，可能不完整`, `Based on ${s.amount_count || 0} parsed amounts; may be incomplete`)));
    if (category !== 'ark_daily') metrics.append(card(t('已采集申报','Collected filings'), n(s.filing_count)));
    root.append(metrics);
    const coverage = data.coverage || {};
    const coverageText = t('统计仅覆盖本地已采集及可解析的数据；未采集的历史、扫描件和缺失字段不计入。', 'Statistics cover locally collected and parsed data only; uncollected history, scans and missing fields are excluded.');
    root.append(el('p', coverageText + ((coverage.first_activity_date || coverage.last_activity_date) ? ` ${t('已采集数据日期范围','Collected activity dates')}: ${coverage.first_activity_date || '—'} – ${coverage.last_activity_date || '—'}` : ''), 'profile-coverage'));
    if (category === 'ark_daily') { const holdings = el('section', null, 'profile-panel'); root.append(holdings); if (window.renderArkHoldings) window.renderArkHoldings(holdings, filter.fund); }
    const trend = section(t('披露活动趋势','Disclosure activity'), t('按月份展示最近 18 个有数据的月份；13F 按快照日期。','Showing the latest 18 months with activity; 13F uses snapshot dates.'));
    if (!(data.timeline || []).length) trend.append(el('p',t('暂无可用数据','No data available.'),'investor-empty'));
    else { const chart = el('div',null,'profile-chart'); const points = data.timeline.slice(-18).reverse(), max = Math.max(1,...points.map(p => (p.buy_count||0)+(p.sell_count||0)+(p.other_count||0))); for (const p of points) { const row = el('div',null,'profile-chart-row'); const track = el('div',null,'profile-bars'); for (const [key,cls] of [['buy_count','buy'],['sell_count','sell'],['other_count','other']]) { const amount = p[key] || 0; if (amount) { const bar = el('span',null,cls); bar.style.width = `${100*amount/max}%`; bar.title = `${key}: ${amount}`; track.append(bar); } } row.append(el('span',p.month),track,el('span',String((p.buy_count||0)+(p.sell_count||0)+(p.other_count||0)))); chart.append(row); } trend.append(chart,el('p',t('绿色：买入 / 增仓　红色：卖出 / 减仓　灰色：其他','Green: buy / increase　Red: sell / decrease　Gray: other'),'profile-legend')); } root.append(trend);
    const activity = section(t('活跃标的','Most active securities'), t('按已解析变化次数排列，不代表当前持仓。','Ranked by parsed activity, not current holdings.'));
    const leaders = (data.activity || []).slice(0, 12); if (!leaders.length) activity.append(el('p',t('暂无可用数据','No data available.'),'investor-empty'));
    else { const grid = el('div',null,'profile-leaders'); for (const item of leaders) { const box = el('div',null,'profile-leader'); box.append(el('strong',item.ticker || item.name || '—'),el('span', [item.fund, `${category === '13f' ? t('增仓','Increase') : t('买入','Buy')} ${n(item.buy_count)} · ${category === '13f' ? t('减仓','Decrease') : t('卖出','Sell')} ${n(item.sell_count)}`, item.buy_shares != null && `${t('买入股数','Shares bought')} ${n(item.buy_shares)}`, item.sell_shares != null && `${t('卖出股数','Shares sold')} ${n(item.sell_shares)}`].filter(Boolean).join(' · '))); grid.append(box); } activity.append(grid); } root.append(activity);
    if (category !== 'ark_daily') { const unavailable = section(t('当前持仓与收益','Current holdings and returns'),t('暂无足够数据计算。持仓、净资产和收益需要完整的持仓基线、价格及估值方法，不能直接由这些披露推算。','Insufficient data. Holdings, net worth and returns require complete baseline positions, prices and valuation methods.')); root.append(unavailable); }
    const table = section(t('披露明细','Disclosure details'), t('了解每笔记录的类型、日期和披露金额；可打开原文核对。','See the type, dates, and disclosed amount for each record; open the source to verify.'));
    if (!events.length) table.append(el('p',t('此筛选条件下暂无记录。','No records match these filters.'),'investor-empty'));
    for (const e of events) {
      const d = details(e), row = el('article', null, 'profile-record'), header = el('div', null, 'profile-record-head');
      const action = describeAction(e), source = sourceName(e.source);
      const asset = d.asset || d.name || d.issuer || '';
      const validTicker = e.ticker && (!d.asset || d.asset.includes(`(${e.ticker})`));
      const title = validTicker ? `${e.ticker}${asset && !asset.startsWith(e.ticker) ? ' · ' + cleanAsset(asset) : ''}` : (asset ? cleanAsset(asset) : t('披露文件','Disclosure filing'));
      const meta = el('div', null, 'profile-record-meta'); meta.append(el('span', source, 'profile-record-source'), el('span', action, `profile-action profile-action-${actionTone(e)}`));
      header.append(el('strong', title), meta); row.append(header);
      const parts = [];
      if (e.source === 'congress' && /\[OP\]\s*$/.test(asset)) parts.push(t('资产类型：期权','Asset type: option'));
      if (d.fund) parts.push(`${t('基金','Fund')}：${d.fund}`);
      if (e.source === 'congress' && e.event_type === 'PTR 披露') {
        const count = d.parsed_trade_count;
        parts.push(count != null ? t(`从该文件识别出 ${count} 笔交易`, `${count} transactions identified in this filing`) : t('交易明细请查看原文','See the filing for transaction details'));
      } else if (e.source === 'congress') {
        parts.push(`${t('申报归属','Reported ownership')}：${ownerLabel(d.owner)}`);
        if (d.amount_low && d.amount_high) parts.push(`${t('披露金额','Disclosed amount')}：${d.amount_low} – ${d.amount_high}`);
      }
      if (e.source === '13f' && d.current_period) {
        const unit = d.unit === 'PRN' ? t('申报本金','reported principal') : t('申报数量','reported quantity');
        parts.push(`${unit}：${d.previous_period || '—'} ${n(d.previous_amount)} → ${d.current_period} ${n(d.current_amount)}`);
        if (d.put_call) parts.push(d.put_call === 'PUT' ? t('看跌期权','Put option') : d.put_call === 'CALL' ? t('看涨期权','Call option') : `${t('类型','Type')}：${d.put_call}`);
      } else if (e.shares != null) {
        parts.push(`${e.source === 'ark' ? t('交易股数','Shares traded') : t('申报数量','Reported quantity')}：${n(e.shares)}`);
      }
      if (e.price != null) {
        const price = Number(e.price), quantity = Number(e.shares);
        const priceText = Number.isFinite(price) ? new Intl.NumberFormat(en ? 'en-US' : 'zh-CN', {maximumFractionDigits: 8}).format(price) : '—';
        parts.push(`${t('申报单价','Reported price')}：$${priceText}`);
        if (e.source === 'form4' && String(e.id || '').includes(':nonDerivativeTable:') && /^(P |S )/.test(e.event_type || '') && e.shares != null && String(e.shares).trim() && String(e.price).trim() && Number.isFinite(price) && price > 0 && Number.isFinite(quantity) && quantity > 0 && Number.isFinite(price * quantity)) {
          parts.push(`${t('估算总金额','Estimated total')}：$${n(price * quantity)}`);
        }
      }
      if (d.percent_of_etf != null && e.source === 'ark') parts.push(`${t('交易金额占基金比重','Trade as % of fund')}：${d.percent_of_etf}%`);
      if (e.transaction_date) parts.push(`${t('交易日期','Transaction date')}：${e.transaction_date}`);
      if (e.reported_at) parts.push(`${t('披露日期','Disclosure date')}：${e.reported_at}`);
      if (d.disclosure_delay_days != null) parts.push(t(`交易后 ${d.disclosure_delay_days} 天披露`, `Disclosed ${d.disclosure_delay_days} days after the transaction`));
      if (e.observed_at) parts.push(`${t('数据收录','Collected')}：${formatObserved(e.observed_at)}`);
      row.append(el('p',parts.join(' · ')));
      if (e.source === '13f') row.append(el('p', t('这是两个季度末的持仓对比，不表示具体交易时间。','This compares quarter-end positions; it does not indicate when a trade occurred.'), 'profile-record-note'));
      if (e.source === 'congress' && e.event_type === 'PTR 披露') row.append(el('p', t('扫描件或未识别内容可能不完整，请查阅原文。','Scans and unrecognized content may be incomplete; review the original.'), 'profile-record-note'));
      if (e.plan_10b5_1) row.append(el('p', t('该文件标记了预设交易计划；不能据此确认每笔交易均属于该计划。','This filing indicates a trading plan; individual transactions are not necessarily covered by it.'), 'profile-record-note'));
      const link = sourceLink(e.source_url); if (link) row.append(link); table.append(row);
    }
    const nav = el('div',null,'profile-pagination'); const prev = el('button',t('上一页','Previous'),'options-secondary'); prev.disabled = pages.offset === 0; prev.onclick = () => { offset = Math.max(0,pages.offset-pages.limit); load(); }; const next = el('button',t('下一页','Next'),'options-secondary'); next.disabled = pages.offset+pages.limit >= pages.total; next.onclick = () => { offset = pages.offset+pages.limit; load(); }; nav.append(prev, el('span', `${pages.total ? pages.offset+1 : 0}–${Math.min(pages.offset+pages.limit,pages.total)} / ${pages.total}`), next); table.append(nav); root.append(table);
  }
  async function load() { const id = ++requestId; try { const params = new URLSearchParams({id:current,offset:String(offset),limit:'30'}); for (const [key,value] of Object.entries(filter)) if (value) params.set(key,value); const response = await fetch('/api/investors/profile?' + params); const data = await response.json(); if (id !== requestId) return; if (!response.ok) throw new Error(data.error || response.status); render(data); } catch (error) { if (id !== requestId) return; root.replaceChildren(); const back = el('a',t('← 返回关注名单','← Back to watchlist')); back.href='#investors'; root.append(back,el('p',t('无法加载详情：','Could not load details: ') + error.message)); } }
  function route() { const match = location.hash.match(/^#investors\/([^/]+)$/); dashboard.hidden = !!match; root.hidden = !match; if (!match) { current=''; return; } let id; try { id=decodeURIComponent(match[1]); } catch (_) { id=''; } if (id !== current) { current=id; filter={}; offset=0; root.replaceChildren(el('p',t('正在加载详情…','Loading details…'))); load(); } }
  window.addEventListener('hashchange',route); route();
})();
