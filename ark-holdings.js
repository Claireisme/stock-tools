(() => {
  const en = !/^\/zh(?:\/|$)/.test(location.pathname);
  const t = (zh, eng) => en ? eng : zh;
  const el = (tag, value, cls) => { const node = document.createElement(tag); if (value != null) node.textContent = value; if (cls) node.className = cls; return node; };
  const format = value => value == null ? '—' : new Intl.NumberFormat(en ? 'en-US' : 'zh-CN', { maximumFractionDigits: 4 }).format(Number(value));
  const signed = (value, suffix = '') => value == null ? '—' : `${Number(value) > 0 ? '+' : ''}${format(value)}${suffix}`;
  window.renderArkHoldings = function(container, initialFund) {
    let fund = initialFund || 'ARKK', query = '', page = 0, data, request = 0;
    const pageSize = 30;
    function draw() {
      if (!container.isConnected) return;
      container.replaceChildren();
      container.append(el('h2', t('ARK 基金每日持仓','ARK fund daily holdings')));
      container.append(el('p', t('官方收盘持仓快照；数量变化为两份快照之差，可能受基金申赎或公司行动影响，不直接等同于买卖。ARKY 的官方文件格式不同，暂不支持。','Official end-of-day holdings snapshots. Changes compare two snapshots and may reflect fund flows or corporate actions, not just trades. ARKY uses a different file format and is not yet supported.'), 'profile-muted'));
      const controls = el('div', null, 'holdings-controls'); const fundLabel = el('label'); fundLabel.append(el('span', t('选择基金','Fund'))); const choice = el('select');
      for (const f of data.funds || []) { const option = el('option',f); option.value = f; option.selected = f === fund; choice.append(option); } choice.addEventListener('change', () => { fund=choice.value; page=0; query=''; load(); }); fundLabel.append(choice); controls.append(fundLabel);
      const searchLabel = el('label'); searchLabel.append(el('span',t('搜索持仓','Search holdings'))); const search = el('input'); search.type='search'; search.placeholder=t('代码或名称','Ticker or name'); search.value=query; search.addEventListener('input', () => {query=search.value;page=0;drawRows();}); searchLabel.append(search); controls.append(searchLabel); container.append(controls);
      const asOf = data.as_of || '—', prev = data.previous_as_of;
      container.append(el('p', `${t('持仓日期','Holdings date')}: ${asOf} · ${prev ? `${t('比较日期','Compared with')}: ${prev}` : t('尚无可比较的历史快照，后续采集后显示变化。','No earlier snapshot yet; changes appear after a later collection.')}`, 'profile-coverage'));
      if (data.source_url) { try { const url = new URL(data.source_url); if (url.protocol === 'https:') { const link=el('a',t('查看官方持仓文件 ↗','Official holdings file ↗'),'profile-back'); link.href=url.href; link.target='_blank'; link.rel='noopener noreferrer'; container.append(link); } } catch (_) {} }
      const chart = el('div', null, 'position-chart'); chart.hidden = true; container.append(chart);
      const rows = el('div', null, 'holdings-rows'); container.append(rows);
      function drawRows() {
        rows.replaceChildren();
        const match = item => !query || [item.ticker,item.name,item.cusip].some(v=>String(v || '').toLowerCase().includes(query.toLowerCase()));
        const current = (data.holdings || []).filter(match); const closed = (data.closed || []).filter(match).map(item=>({...item,status:'closed'})); const all = [...current, ...closed];
        if (!all.length) {rows.append(el('p', data.as_of ? t('没有匹配的持仓记录。','No matching holdings.') : t('暂未采集此基金的持仓，请点击“检查更新”后重试。','No snapshot collected for this fund yet. Check for updates and try again.'),'investor-empty'));return;}
        const wrap=el('div',null,'holdings-scroll'); const table=el('table',null,'holdings-table'); const head=el('thead'); const tr=el('tr');
        for (const label of [t('证券','Security'),t('持仓数量','Shares'),t('基金占比','Fund weight'),t('持仓市值','Market value'),t('数量变化','Share change'),t('占比变化','Weight change'),t('状态','Status')]) tr.append(el('th',label)); head.append(tr);table.append(head); const body=el('tbody');
        const statuses={new:t('新进入','New'),increased:t('数量增加','Increased'),decreased:t('数量减少','Decreased'),unchanged:t('数量不变','Unchanged'),closed:t('不再持有','No longer held')};
        for(const item of all.slice(page*pageSize,(page+1)*pageSize)) { const row=el('tr'), security=el('td'), title=el('button',item.ticker || item.name || '—','holdings-security-button'); title.type='button'; title.setAttribute('aria-label',`${t('查看持仓和股价走势','View holdings and price chart')}: ${item.ticker || item.name}`); title.addEventListener('click',()=>window.renderArkPositionChart(chart,fund,item.security_id));security.append(title);if (item.ticker && item.name) security.append(el('small',item.name));row.append(security,el('td',format(item.shares)),el('td',item.weight == null ? '—' : `${format(item.weight)}%`),el('td',item.market_value == null ? '—' : `$${format(item.market_value)}`),el('td',signed(item.shares_change)),el('td',signed(item.weight_change,t(' 个百分点',' pp'))),el('td',statuses[item.status] || '—'));body.append(row); }
        table.append(body);wrap.append(table);rows.append(wrap); const nav=el('div',null,'profile-pagination');const prevBtn=el('button',t('上一页','Previous'),'options-secondary'),nextBtn=el('button',t('下一页','Next'),'options-secondary');prevBtn.disabled=page===0;nextBtn.disabled=(page+1)*pageSize>=all.length;prevBtn.onclick=()=>{page--;drawRows();};nextBtn.onclick=()=>{page++;drawRows();};nav.append(prevBtn,el('span',`${page*pageSize+1}–${Math.min((page+1)*pageSize,all.length)} / ${all.length}`),nextBtn);rows.append(nav);
      }
      drawRows();
    }
    async function load() {const id=++request; container.replaceChildren(el('p',t('正在加载基金持仓…','Loading fund holdings…')));try { const response=await fetch('/api/investors/ark-holdings?' + new URLSearchParams({fund})); const result=await response.json();if(id!==request || !container.isConnected)return;if(!response.ok)throw new Error(result.error || response.status);data=result;draw();} catch(error) {if(id!==request || !container.isConnected)return;container.replaceChildren(el('h2',t('ARK 基金每日持仓','ARK fund daily holdings')),el('p',t('持仓暂不可用：','Holdings unavailable: ') + error.message));} }
    load();
  };
})();
