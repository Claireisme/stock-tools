(() => {
  const $ = id => document.getElementById(id);
  const translations = {
    nav:['期权工具','Options'],title:['期权收益计算器','Options Profit Calculator'],home:['首页','Home'],open:['打开工具','Open tool'],homeDescription:['组合多个期权头寸，探索不同价格和日期下的盈亏。','Combine option positions and explore profit and loss across prices and dates.'],intro:['输入期权头寸，查看不同股价和日期的预估盈亏。','Enter positions to estimate profit and loss across prices and dates.'],position:['设置持仓','Position'],spot:['当前股价','Current stock price'],expiry:['到期日','Expiration date'],rate:['无风险利率 (%)','Risk-free rate (%)'],dividend:['股息率 (%)','Dividend yield (%)'],legs:['期权头寸','Option legs'],legsHelp:['每张合约按 100 股计算；所有头寸使用同一到期日。','Each contract represents 100 shares; all legs share one expiration date.'],add:['＋ 添加头寸','＋ Add leg'],stock:['股票持仓（可选）','Stock position (optional)'],stockHelp:['负数表示卖空股票。','Use a negative number for a short stock position.'],shares:['股票数量','Number of shares'],entry:['股票买入价 / 卖空价','Stock entry price'],low:['最低情景股价','Minimum scenario price'],high:['最高情景股价','Maximum scenario price'],calculate:['计算收益 →','Calculate →'],reset:['重置','Reset'],result:['到期收益分析','Expiration analysis'],cost:['期权净支出','Net option debit'],maxProfit:['最大收益','Maximum profit'],maxLoss:['最大亏损','Maximum loss'],breakEven:['到期盈亏平衡价','Expiration break-even'],chart:['到期损益曲线','Profit / loss at expiration'],chartHint:['横轴：股价 · 纵轴：盈亏','Horizontal: stock price · Vertical: profit / loss'],disclaimer:['期权价格可以修改。到期前估值采用 Black–Scholes 模型，假设隐含波动率不变；未计手续费、买卖价差、提前行权及税费。结果仅供参考。','Option premiums can be edited. Estimates before expiration use Black–Scholes with constant implied volatility; fees, bid-ask spreads, early exercise and taxes are excluded. Results are estimates only.'],scenarios:['价格与日期情景','Price and date scenarios'],scenarioHelp:['每格为该日期、该股价下的预估总盈亏；最后一列为到期损益。','Each cell shows estimated total profit / loss at that price and date; the last column is expiration.'],direction:['方向','Side'],type:['类型','Type'],strike:['行权价','Strike'],premium:['权利金 / 股','Premium / share'],contracts:['合约数','Contracts'],volatility:['隐含波动率 (%)','Implied volatility (%)'],buy:['买入','Buy'],sell:['卖出','Sell'],call:['看涨 Call','Call'],put:['看跌 Put','Put'],remove:['删除','Remove'],price:['股价','Stock price'],unlimited:['无上限','Unlimited'],none:['无','None'],all:['所有价格','All prices'],invalid:['请检查输入：股价及行权价须大于 0，权利金和情景价格不能为负，合约数须为正整数，波动率须大于 0；到期日不得早于今天。','Check the inputs: spot and strikes must be positive; premiums and scenario prices nonnegative; contracts positive integers; volatility positive; expiration today or later.'],rangeError:['最高情景股价必须大于最低情景股价。','The maximum scenario price must exceed the minimum.'],limit:['最多支持 8 个头寸。','Up to 8 legs are supported.']
  };
  Object.assign(translations, {
    chartProfit:['到期盈亏','Profit / loss'], chartControls:['使用左右方向键查看不同股价','Use left and right arrow keys to explore prices'],
    chainTitle:['期权链','Option chain'], chainHelp:['点击任一报价，填入所选头寸。无行情显示为 —。','Select any quote to fill the chosen leg. Missing values are shown as —.'], applyTo:['填入头寸','Apply to'], addNewLeg:['添加新头寸','Add a new leg'], bid:['买价','Bid'], ask:['卖价','Ask'], last:['最新价','Last'], chainApplied:['已填入','Applied to'], quoteTime:['报价时间','Quote time'], ivTime:['波动率时间','IV time'], optionSource:['期权数据源','Option data source'], configureAlpaca:['请在服务端运行 python3 configure_alpaca.py 配置密钥后重启服务。','Run python3 configure_alpaca.py on the server to configure keys, then restart.'], quoteNoteTradier:['Tradier 行情可能延迟。价格优先使用买卖中间价，否则使用最近成交价；价格和隐含波动率均可修改。','Tradier quotes may be delayed. Premium uses the bid/ask midpoint when available, otherwise the last trade. Premium and implied volatility can be edited.'],
    lookupTitle:['股票与期权行情','Stock and option quotes'],lookupHelp:['搜索美股并选择到期日，为每个头寸选择合约。也可以手动输入。','Search US stocks and choose an expiration, then select a contract for each leg. Manual entry remains available.'],ticker:['股票名称或代码','Stock name or ticker'],search:['搜索股票','Search'],chooseExpiry:['期权到期日','Option expiration'],chooseStock:['请先选择股票','Select a stock first'],refresh:['刷新期权链','Refresh chain'],quoteNote:['Alpaca Indicative 提供经过调整的参考报价，并非实际 OPRA 报价；成交数据延迟 15 分钟，非实时可交易报价。价格优先使用买卖中间价，否则使用最近成交价；价格和隐含波动率均可修改。','Alpaca Indicative quotes are modified rather than actual OPRA quotes; trades are delayed by 15 minutes. These are not live, executable quotes. Premium uses the bid/ask midpoint when available, otherwise the last trade. Premium and implied volatility can be edited.'],contract:['选择期权合约','Select option contract'],manual:['手动输入','Manual entry'],loading:['正在获取行情…','Loading quotes…'],noStocks:['没有找到匹配的美股。','No matching US stocks found.'],searchFailed:['股票搜索失败，请稍后重试。','Stock search failed. Please try again.'],chooseResult:['请选择一只股票。','Select a stock.'],noExpiries:['此股票没有可用的期权到期日。','No option expirations are available for this stock.'],noContracts:['该到期日没有可用合约。','No contracts available for this expiration.'],chainFailed:['期权行情不可用。请检查服务配置和网络后重试。','Option quotes are unavailable. Check the service configuration and connection, then retry.'],emptyTicker:['请输入股票名称或代码。','Enter a stock name or ticker.'],chooseContract:['已加载期权链，请为每个头寸选择合约。','Option chain loaded. Select a contract for each leg.'],missingPrice:['无有效价格，请手动填写','No price available; enter it manually'],missingIV:['无隐含波动率，请手动填写','No implied volatility available; enter it manually'],midpoint:['买卖中间价','Bid/ask midpoint'],lastTrade:['最近成交价','Last trade'],selected:['已选择','Selected'],quoteUnavailable:['股价不可用，请手动输入。','Stock quote unavailable; enter the stock price manually.'],configure:['请在服务端设置 TRADIER_API_TOKEN 后重启服务。','Set TRADIER_API_TOKEN on the server and restart it.']
  });
  const lang = () => $('language').value === 'en' ? 1 : 0;
  const stockLabel = item => lang() && /[\u3400-\u9fff]/u.test(item.name || '') ? item.code : `${item.name} (${item.code})`;
  const t = key => translations[key][lang()];
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  const day = date => new Date(`${date}T00:00:00Z`).getTime();
  const dateString = ms => new Date(ms).toISOString().slice(0, 10);
  const fmt = n => new Intl.NumberFormat(lang() ? 'en-US' : 'zh-CN', {maximumFractionDigits: 2, minimumFractionDigits: 2}).format(n);
  const signed = n => `${n > 0 ? '+' : ''}${fmt(n)}`;
  const legsContainer = $('opt-legs');
  function addLeg(data = {}) {
    if (legsContainer.children.length >= 8) { $('opt-error').textContent = t('limit'); return; }
    const leg = document.createElement('div'); leg.className = 'options-leg';
    leg.innerHTML = `<div class="options-leg-top"><span class="options-leg-number"></span><button type="button" class="opt-remove" data-opt="remove"></button></div><label class="options-contract-label"><span data-opt="contract"></span><select class="leg-contract"><option value="" data-opt="manual"></option></select></label><p class="options-contract-status" aria-live="polite"></p><div class="options-leg-grid"><label><span data-opt="direction"></span><select class="leg-side"><option value="buy" data-opt="buy"></option><option value="sell" data-opt="sell"></option></select></label><label><span data-opt="type"></span><select class="leg-type"><option value="call" data-opt="call"></option><option value="put" data-opt="put"></option></select></label><label><span data-opt="strike"></span><input class="leg-strike" type="number" min="0.01" step="any" required></label><label><span data-opt="premium"></span><input class="leg-premium" type="number" min="0" step="any" required></label><label><span data-opt="contracts"></span><input class="leg-contracts" type="number" min="1" step="1" required></label><label><span data-opt="volatility"></span><input class="leg-volatility" type="number" min="0.01" max="1000" step="any" required></label></div>`;
    legsContainer.appendChild(leg);
    for (const [field, value] of Object.entries({side:'buy',type:'call',strike:100,premium:5,contracts:1,volatility:30,...data})) leg.querySelector(`.leg-${field}`).value = value;
    leg.querySelector('.opt-remove').addEventListener('click', () => { if (legsContainer.children.length > 1) { leg.remove(); numberLegs(); clear(); } });
    leg.querySelector('.leg-contract').addEventListener('change', () => selectContract(leg));
    leg.querySelectorAll('.leg-type, .leg-strike, .leg-premium, .leg-volatility').forEach(input => input.addEventListener('input', () => { const field = [...input.classList].find(name => name.startsWith('leg-')).slice(4); if (leg._auto) leg._auto[field] = false; leg.querySelector('.leg-contract').value = ''; leg._quoteInfo = null; renderContractStatus(leg); }));
    populateContracts(leg); numberLegs(); translate();
  }
  function numberLegs() { [...legsContainer.children].forEach((el, i) => { el.querySelector('.options-leg-number').textContent = `LEG ${String(i + 1).padStart(2, '0')}`; el.querySelector('.opt-remove').disabled = legsContainer.children.length === 1; }); renderTargets(); }
  function translate() { document.querySelectorAll('[data-opt]').forEach(el => { el.textContent = t(el.dataset.opt); }); renderLookupStatus(); renderTargets(); renderExpiryTabs(); renderChain(); for (const leg of legsContainer.children) renderContractStatus(leg); if (lastResult) render(lastResult); }
  function clear() { lastResult = null; ['opt-cost','opt-max-profit','opt-max-loss','opt-breakeven'].forEach(id => $(id).textContent = '—'); $('opt-chart').innerHTML = ''; $('opt-table').innerHTML = ''; $('opt-error').textContent = ''; }
  function reset() { resetLookup(); $('opt-spot').value = 100; $('opt-expiry').value = dateString(day(today()) + 30 * 86400000); $('opt-rate').value = 4; $('opt-dividend').value = 0; $('opt-shares').value = 0; $('opt-entry').value = 100; $('opt-low').value = 50; $('opt-high').value = 150; legsContainer.innerHTML = ''; addLeg(); clear(); }
  let lookupGeneration = 0, selectedStock = null, selectedStockName = '', chain = [], stockAuto = {}, stockRevision = {}, lookupStatus = {key:'', detail:''}, pendingChainCenter = false;
  function clearAutoStock() { for (const id of Object.keys(stockAuto)) if (stockAuto[id]) $(id).value = ''; stockAuto = {}; }
  function setLookupStatus(key, detail = '') { lookupStatus = {key, detail}; renderLookupStatus(); }
  function renderLookupStatus() { $('opt-lookup-status').textContent = [lookupStatus.key ? t(lookupStatus.key) : '', lookupStatus.detail].filter(Boolean).join(' · '); }
  function renderContractStatus(leg) {
    const info = leg._quoteInfo;
    leg.querySelector('.options-contract-status').textContent = info ? [t('selected') + ': ' + info.symbol, info.priceKey ? t(info.priceKey) : t('missingPrice'), info.hasIV ? `IV ${fmt(info.iv * 100)}%` : t('missingIV'), info.time ? `${t('quoteTime')}: ${info.time}` : '', info.ivTime ? `${t('ivTime')}: ${info.ivTime}` : ''].filter(Boolean).join(' · ') : '';
  }
  function populateContracts(leg) {
    const select = leg.querySelector('.leg-contract');
    select.replaceChildren();
    const manual = document.createElement('option'); manual.value = ''; manual.dataset.opt = 'manual'; manual.textContent = t('manual'); select.appendChild(manual);
    chain.forEach((item, index) => { const option = document.createElement('option'); option.value = String(index + 1); option.textContent = `${item.type === 'call' ? 'CALL' : 'PUT'} · ${fmt(item.strike)} · ${item.symbol}`; select.appendChild(option); });
    leg._quoteInfo = null; renderContractStatus(leg);
  }
  function renderTargets() {
    const select = $('opt-chain-target'); if (!select) return;
    const prior = select.value; select.replaceChildren();
    [...legsContainer.children].forEach((_, i) => { const option = document.createElement('option'); option.value = String(i); option.textContent = `LEG ${String(i + 1).padStart(2, '0')}`; select.appendChild(option); });
    const option = document.createElement('option'); option.value = 'new'; option.textContent = t('addNewLeg'); select.appendChild(option);
    select.value = [...select.options].some(o => o.value === prior) ? prior : '0';
  }
  function renderExpiryTabs() {
    const container = $('opt-expiry-tabs'), select = $('opt-expirations'); container.replaceChildren();
    if (select.disabled) return;
    for (const option of select.options) {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = option.value; button.setAttribute('aria-pressed', String(option.value === select.value));
      button.addEventListener('click', () => { if (select.value !== option.value) { select.value = option.value; loadChain(); } }); container.appendChild(button);
    }
  }
  function renderChain() {
    const body = $('opt-chain-body'), scroll = $('opt-chain-panel').querySelector('.opt-chain-scroll'), previousScrollTop = scroll.scrollTop;
    body.replaceChildren(); $('opt-chain-panel').hidden = !chain.length; if (!chain.length) return;
    const groups = new Map(); chain.forEach((item, index) => { const strike = Number(item.strike); if (!groups.has(strike)) groups.set(strike, {call:[], put:[]}); groups.get(strike)[item.type].push({item,index}); });
    const spot = Number($('opt-spot').value), spotValid = $('opt-spot').value !== '' && Number.isFinite(spot) && spot > 0;
    const display = (value, pct = false) => value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) || Number(value) < 0 ? '—' : `${fmt(Number(value) * (pct ? 100 : 1))}${pct ? '%' : ''}`;
    const cell = (entry, field, strike, type) => {
      const td = document.createElement('td'); if (!entry) { td.textContent = '—'; return td; }
      if (spotValid && (type === 'call' ? spot > strike : spot < strike)) td.classList.add('opt-in-money');
      const button = document.createElement('button'); button.type = 'button'; button.textContent = display(entry.item[field], field === 'iv');
      const label = field === 'iv' ? 'IV' : t(field); button.setAttribute('aria-label', `${type === 'call' ? t('call') : t('put')} ${fmt(strike)} · ${label}: ${button.textContent} · ${entry.item.symbol}`);
      button.addEventListener('click', () => applyChainContract(entry.index)); td.appendChild(button); return td;
    };
    for (const strike of [...groups.keys()].sort((a,b) => a-b)) {
      const group = groups.get(strike), count = Math.max(group.call.length, group.put.length);
      for (let i = 0; i < count; i++) {
        const row = document.createElement('tr'); row.dataset.strike = strike; for (const field of ['bid','ask','last','iv']) row.appendChild(cell(group.call[i], field, strike, 'call'));
        const strikeCell = document.createElement('th'); strikeCell.scope = 'row'; strikeCell.textContent = fmt(strike); row.appendChild(strikeCell);
        for (const field of ['bid','ask','last','iv']) row.appendChild(cell(group.put[i], field, strike, 'put')); body.appendChild(row);
      }
    }
    scroll.scrollTop = previousScrollTop;
  }
  function centerChain() {
    const spotField = $('opt-spot'), spot = Number(spotField.value);
    const scroll = $('opt-chain-panel').querySelector('.opt-chain-scroll');
    if (!spotField.value.trim() || !Number.isFinite(spot) || spot <= 0 || !chain.length) { pendingChainCenter = false; return; }
    if (!scroll.clientHeight) { pendingChainCenter = true; return; }
    const rows = [...$('opt-chain-body').rows];
    const nearest = rows.reduce((best, row) => !best || Math.abs(Number(row.dataset.strike) - spot) < Math.abs(Number(best.dataset.strike) - spot) ? row : best, null);
    if (nearest) {
      const headerHeight = scroll.querySelector('thead').getBoundingClientRect().height;
      const rowRect = nearest.getBoundingClientRect(), scrollRect = scroll.getBoundingClientRect();
      scroll.scrollTop += rowRect.top - scrollRect.top - scroll.clientTop + rowRect.height / 2 - (scroll.clientHeight + headerHeight) / 2;
    }
    pendingChainCenter = false;
  }
  function applyChainContract(index) {
    const target = $('opt-chain-target').value; let leg;
    if (target === 'new') { if (legsContainer.children.length >= 8) { $('opt-chain-selection').textContent = t('limit'); return; } addLeg(); leg = legsContainer.lastElementChild; }
    else leg = legsContainer.children[Number(target)];
    if (!leg || !chain[index]) return;
    leg.querySelector('.leg-side').value = $('opt-chain-side').value; leg.querySelector('.leg-contract').value = String(index + 1); selectContract(leg);
    const n = [...legsContainer.children].indexOf(leg) + 1; $('opt-chain-selection').textContent = `${t('chainApplied')} LEG ${String(n).padStart(2, '0')} · ${chain[index].symbol}${!leg._quoteInfo.priceKey ? ` · ${t('missingPrice')}` : ''}${!leg._quoteInfo.hasIV ? ` · ${t('missingIV')}` : ''}`;
    $('opt-chain-target').value = 'new';
  }
  function clearAutoFields(leg) { for (const field of ['strike', 'premium', 'volatility']) if (leg._auto && leg._auto[field]) leg.querySelector(`.leg-${field}`).value = ''; leg._auto = {}; }
  function clearChain() { pendingChainCenter = false; chain = []; $('opt-chain-panel').hidden = true; $('opt-chain-body').replaceChildren(); $('opt-chain-selection').textContent = '';  [...legsContainer.children].forEach(leg => { clearAutoFields(leg); populateContracts(leg); }); clear(); }
  function resetLookup() {
    lookupGeneration++; selectedStock = null; clearChain(); stockAuto = {}; $('opt-symbol').value = ''; $('opt-stock-results').replaceChildren(); $('opt-stock-results').hidden = true;
    $('opt-expiry-tabs').replaceChildren(); const select = $('opt-expirations'); select.replaceChildren(); const option = document.createElement('option'); option.value = ''; option.dataset.opt = 'chooseStock'; option.textContent = t('chooseStock'); select.appendChild(option); select.disabled = true; $('opt-refresh').disabled = true; setLookupStatus('');
  }
  function configurationKey(error) { return /missing|credential|token/i.test(error.code || '') || /TRADIER_API_TOKEN|ALPACA_API_KEY/.test(error.message || '') ? 'configureAlpaca' : 'chainFailed'; }
  async function getJSON(path, params) {
    const response = await fetch(`${path}?${new URLSearchParams(params)}`, {cache:'no-store'});
    let data; try { data = await response.json(); } catch (_) { throw new Error('request'); }
    if (!response.ok || data.error) { const error = new Error(data.error || 'request'); error.code = data.code; throw error; }
    return data;
  }
  async function searchStocks() {
    const query = $('opt-symbol').value.trim(); const generation = ++lookupGeneration;
    selectedStock = null; clearAutoStock(); clearChain(); $('opt-expirations').disabled = true; $('opt-refresh').disabled = true; $('opt-stock-results').replaceChildren(); $('opt-stock-results').hidden = true;
    if (!query) { setLookupStatus('emptyTicker'); return; }
    setLookupStatus('loading');
    try {
      const data = await getJSON('/api/search', {q:query, market:'us', source:'sina'}); if (generation !== lookupGeneration) return;
      const results = Array.isArray(data.results) ? data.results.filter(item => item.market === 'us' && item.code && item.name) : [];
      for (const item of results) { const button = document.createElement('button'); button.type = 'button'; button.textContent = stockLabel(item); button.addEventListener('click', () => selectStock(item)); $('opt-stock-results').appendChild(button); }
      $('opt-stock-results').hidden = !results.length; setLookupStatus(results.length ? 'chooseResult' : 'noStocks');
    } catch (_) { if (generation === lookupGeneration) setLookupStatus('searchFailed'); }
  }
  async function selectStock(item) {
    const generation = ++lookupGeneration; selectedStock = item.code; selectedStockName = item.name; clearAutoStock(); clearChain(); $('opt-symbol').value = stockLabel(item); $('opt-stock-results').hidden = true; $('opt-stock-results').replaceChildren(); $('opt-expirations').disabled = true; $('opt-refresh').disabled = true; setLookupStatus('loading');
    const before = Object.fromEntries(['opt-spot','opt-entry','opt-low','opt-high'].map(id => [id, stockRevision[id] || 0]));
    const [expirations, quote] = await Promise.allSettled([getJSON('/api/options/expirations', {symbol:item.code, source:'alpaca'}), getJSON('/api/quote', {market:'us', code:item.code, source:'sina'})]);
    if (generation !== lookupGeneration) return;
    let stockNote = '';
    if (quote.status === 'fulfilled' && Number.isFinite(Number(quote.value.price)) && Number(quote.value.price) > 0) {
      const price = Number(quote.value.price); const updates = {'opt-spot':price, 'opt-entry':price, 'opt-low':(price * .5).toFixed(2), 'opt-high':(price * 1.5).toFixed(2)}; for (const [id, value] of Object.entries(updates)) if ((stockRevision[id] || 0) === before[id]) { $(id).value = value; stockAuto[id] = true; } clear();
      const source = lang() ? ({'新浪财经':'Sina Finance', '新浪行情':'Sina', '腾讯行情':'Tencent'}[quote.value.source] || quote.value.source || 'Stock') : (quote.value.source || '股票');
      const time = quote.value.time && (!lang() || !/[\u3400-\u9fff]/u.test(quote.value.time)) ? ` · ${quote.value.time}` : '';
      stockNote = `${source}: ${price} ${quote.value.currency || ''}${time}`;
    } else stockNote = t('quoteUnavailable');
    if (expirations.status === 'rejected') { setLookupStatus(configurationKey(expirations.reason), stockNote); return; }
    const dates = Array.isArray(expirations.value.expirations) ? expirations.value.expirations.filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d)) : [];
    const select = $('opt-expirations'); select.replaceChildren();
    if (!dates.length) { setLookupStatus('noExpiries', stockNote); return; }
    for (const date of dates) { const option = document.createElement('option'); option.value = date; option.textContent = date; select.appendChild(option); }
    select.disabled = false; $('opt-refresh').disabled = false; $('opt-expiry').value = dates[0]; renderExpiryTabs(); clear(); await loadChain(stockNote);
  }
  async function loadChain(stockNote = '') {
    if (!selectedStock || !$('opt-expirations').value) return;
    const generation = ++lookupGeneration, expiration = $('opt-expirations').value, symbol = selectedStock; clearChain(); renderExpiryTabs(); $('opt-expiry').value = expiration; clear(); setLookupStatus('loading');
    try {
      const data = await getJSON('/api/options/chain', {symbol, expiration, source:'alpaca'}); if (generation !== lookupGeneration) return;
      chain = (Array.isArray(data.options) ? data.options : []).filter(item => item && ['call','put'].includes(item.type) && Number.isFinite(Number(item.strike)) && Number(item.strike) > 0 && item.symbol);
      [...legsContainer.children].forEach(populateContracts);
      renderChain(); centerChain();
      setLookupStatus(chain.length ? 'chooseContract' : 'noContracts', [data.source || 'Alpaca indicative', stockNote].filter(Boolean).join(' · '));
    } catch (error) { if (generation === lookupGeneration) setLookupStatus(configurationKey(error)); }
  }
  function selectContract(leg) {
    const index = Number(leg.querySelector('.leg-contract').value) - 1, contract = chain[index];
    if (!contract) { clearAutoFields(leg); leg._quoteInfo = null; renderContractStatus(leg); clear(); return; }
    clearAutoFields(leg);
    leg.querySelector('.leg-type').value = contract.type; leg.querySelector('.leg-strike').value = contract.strike;
    const valid = x => x !== null && x !== undefined && x !== '' && Number.isFinite(Number(x)) && Number(x) >= 0;
    const bid = valid(contract.bid) ? Number(contract.bid) : null, ask = valid(contract.ask) ? Number(contract.ask) : null, last = valid(contract.last) ? Number(contract.last) : null;
    const priceKey = bid !== null && ask !== null && ask >= bid && ask > 0 ? 'midpoint' : last !== null && last > 0 ? 'lastTrade' : '';
    leg.querySelector('.leg-premium').value = priceKey ? String(priceKey === 'midpoint' ? Number(((bid + ask) / 2).toFixed(4)) : last) : ''; 
    const iv = Number(contract.iv), hasIV = contract.iv !== null && contract.iv !== undefined && Number.isFinite(iv) && iv > 0 && iv <= 10;
    leg.querySelector('.leg-volatility').value = hasIV ? String(Number((iv * 100).toFixed(4))) : '';
    leg._auto = {strike:true, premium:!!priceKey, volatility:hasIV};
    const toTime = value => { if (value == null || value === '') return 0; const numeric = Number(value); const timestamp = Number.isFinite(numeric) ? (numeric < 1e12 ? numeric * 1000 : numeric) : Date.parse(value); return Number.isFinite(timestamp) ? timestamp : 0; };
    const quoteTimes = (priceKey === 'midpoint' ? [contract.bid_time, contract.ask_time] : [contract.trade_time]).map(toTime).filter(Boolean);
    const timestamp = quoteTimes.length ? Math.min(...quoteTimes) : 0, ivTimestamp = toTime(contract.iv_time);
    const time = timestamp ? new Date(timestamp).toLocaleString() : '', ivTime = ivTimestamp ? new Date(ivTimestamp).toLocaleString() : '';
    leg._quoteInfo = {symbol:contract.symbol, priceKey, hasIV, iv, time, ivTime}; renderContractStatus(leg); clear();
  }
  let lastResult = null;
  function calculate(event) {
    event.preventDefault();
    const num = id => $(id).value.trim() === '' ? NaN : Number($(id).value);
    const spot = num('opt-spot'), rate = num('opt-rate') / 100, dividend = num('opt-dividend') / 100, shares = num('opt-shares'), stockEntry = num('opt-entry'), low = num('opt-low'), high = num('opt-high'), expiry = $('opt-expiry').value;
    const legs = [...legsContainer.children].map(el => { const val = name => el.querySelector(`.leg-${name}`).value; const n = name => val(name).trim() === '' ? NaN : Number(val(name)); return {side:val('side'),type:val('type'),strike:n('strike'),premium:n('premium'),contracts:n('contracts'),volatility:n('volatility') / 100,expiry}; });
    if (![spot,rate,dividend,shares,stockEntry,low,high].every(n => Number.isFinite(n) && Math.abs(n) <= 1e9) || spot <= 0 || rate < -1 || rate > 1 || dividend < 0 || dividend > 1 || !Number.isInteger(shares) || stockEntry < 0 || low < 0 || high < 0 || !expiry || !Number.isFinite(day(expiry)) || day(expiry) < day(today()) || legs.some(l => ![l.strike,l.premium,l.contracts,l.volatility].every(n => Number.isFinite(n) && Math.abs(n) <= 1e9) || l.strike <= 0 || l.premium < 0 || !Number.isInteger(l.contracts) || l.contracts < 1 || l.volatility <= 0 || l.volatility > 10)) { clear(); $('opt-error').textContent = t('invalid'); return; }
    if (high <= low) { clear(); $('opt-error').textContent = t('rangeError'); return; }
    $('opt-error').textContent = '';
    const args = {legs,shares,stockEntry,rate,dividend};
    const analysis = OptionsMath.expiryAnalysis(args);
    const dates = [...new Set(Array.from({length:5}, (_, i) => dateString(day(today()) + Math.round((day(expiry) - day(today())) / 86400000 * i / 4) * 86400000)))];
    const values = Array.from({length:11}, (_, i) => { const s = low + (high - low) * i / 10; return {spot:s, profits:dates.map(date => OptionsMath.profit({...args,spot:s,date}))}; });
    const curveSpots = [...new Set([...Array.from({length:101}, (_, i) => low + (high - low) * i / 100), ...legs.map(leg => leg.strike).filter(strike => strike > low && strike < high)])].sort((a,b) => a-b);
    const curve = curveSpots.map(spot => ({spot, profit:OptionsMath.profit({...args,spot,date:expiry})}));
    const debit = legs.reduce((sum,l) => sum + (l.side === 'buy' ? 1 : -1) * l.premium * l.contracts * 100, 0);
    lastResult = {analysis,dates,values,curve,debit,args,expiry}; render(lastResult);
  }
  function render({analysis,dates,values,curve,debit,args,expiry}) {
    $('opt-cost').textContent = signed(debit);
    $('opt-max-profit').textContent = analysis.maxProfit === Infinity ? t('unlimited') : signed(analysis.maxProfit);
    $('opt-max-loss').textContent = analysis.maxLoss === Infinity ? t('unlimited') : fmt(analysis.maxLoss);
    const breakevens = [...analysis.breakevens.map(fmt), ...analysis.breakevenRanges.map(([start, end]) => `${fmt(start)} – ${end === Infinity ? '∞' : fmt(end)}`)];
    $('opt-breakeven').textContent = breakevens.length ? breakevens.join(' / ') : t('none');
    const min = Math.min(0,...curve.map(p => p.profit)), max = Math.max(0,...curve.map(p => p.profit)), span = max-min || 1;
    const low = curve[0].spot, high = curve[curve.length-1].spot;
    const y = v => 160 - (v-min)/span*140, x = spot => 45+(spot-low)/(high-low)*510;
    const points = curve.map(p => `${x(p.spot).toFixed(1)},${y(p.profit).toFixed(1)}`).join(' ');
    $('opt-chart').innerHTML = `<svg viewBox="0 0 590 205" role="slider" tabindex="0" aria-label="${t('chart')}. ${t('chartControls')}" aria-valuemin="${low}" aria-valuemax="${high}"><line x1="45" x2="555" y1="${y(0)}" y2="${y(0)}" stroke="#afbdd2" stroke-dasharray="4 4"/><polyline points="${points}" fill="none" stroke="#1556e8" stroke-width="3"/><text x="45" y="195">${fmt(low)}</text><text x="555" y="195" text-anchor="end">${fmt(high)}</text><text x="45" y="12">${signed(max)}</text><text x="45" y="176">${signed(min)}</text><g class="chart-guide" visibility="hidden" aria-hidden="true"><line class="chart-guide-x" y1="20" y2="160"/><line class="chart-guide-y" x1="45" x2="555"/><circle r="4"/><g class="chart-tooltip"><rect width="158" height="42" rx="5"/><text class="chart-tooltip-spot" x="9" y="16"></text><text class="chart-tooltip-profit" x="9" y="32"></text></g></g></svg>`;
    const svg = $('opt-chart').querySelector('svg'), guide = svg.querySelector('.chart-guide');
    let selected = (low + high) / 2;
    function show(spot) {
      selected = Math.max(low, Math.min(high, spot));
      const profit = OptionsMath.profit({...args, spot:selected, date:expiry}), px = x(selected), py = y(profit);
      const vertical = guide.querySelector('.chart-guide-x'), horizontal = guide.querySelector('.chart-guide-y'), marker = guide.querySelector('circle');
      vertical.setAttribute('x1', px); vertical.setAttribute('x2', px);
      horizontal.setAttribute('y1', py); horizontal.setAttribute('y2', py);
      marker.setAttribute('cx', px); marker.setAttribute('cy', py);
      guide.querySelector('.chart-tooltip').setAttribute('transform', `translate(${Math.max(45, Math.min(397, px + 10))} ${py < 70 ? py + 10 : py - 50})`);
      guide.querySelector('.chart-tooltip-spot').textContent = `${t('price')}: ${fmt(selected)}`;
      guide.querySelector('.chart-tooltip-profit').textContent = `${t('chartProfit')}: ${signed(profit)}`;
      svg.setAttribute('aria-valuenow', selected.toFixed(2));
      svg.setAttribute('aria-valuetext', `${t('price')}: ${fmt(selected)}, ${t('chartProfit')}: ${signed(profit)}`);
      guide.setAttribute('visibility', 'visible');
    }
    function move(event) {
      const rect = svg.getBoundingClientRect();
      if (!rect.width) return;
      show(low + Math.max(0, Math.min(1, ((event.clientX - rect.left) / rect.width * 590 - 45) / 510)) * (high - low));
    }
    show(selected);
    guide.setAttribute('visibility', 'hidden');
    svg.addEventListener('pointermove', move);
    svg.addEventListener('pointerdown', move);
    svg.addEventListener('pointerleave', event => { if (event.pointerType !== 'touch' && document.activeElement !== svg) guide.setAttribute('visibility', 'hidden'); });
    svg.addEventListener('focus', () => show(selected));
    svg.addEventListener('blur', () => guide.setAttribute('visibility', 'hidden'));
    svg.addEventListener('keydown', event => {
      if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
      event.preventDefault();
      show(event.key === 'Home' ? low : event.key === 'End' ? high : selected + (event.key === 'ArrowRight' ? 1 : -1) * (high - low) / 100);
    });
    $('opt-table').innerHTML = `<thead><tr><th>${t('price')}</th>${dates.map(date => `<th>${date}</th>`).join('')}</tr></thead><tbody>${values.slice().reverse().map(row => `<tr><th>${fmt(row.spot)}</th>${row.profits.map(value => `<td class="${value >= 0 ? 'profit' : 'loss'}">${signed(value)}</td>`).join('')}</tr>`).join('')}</tbody>`;
  }
  $('opt-search').addEventListener('click', searchStocks);
  $('opt-symbol').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); searchStocks(); } });
  $('opt-symbol').addEventListener('input', () => { lookupGeneration++; selectedStock = null; clearAutoStock(); clearChain(); $('opt-expirations').disabled = true; $('opt-refresh').disabled = true; $('opt-stock-results').replaceChildren(); $('opt-stock-results').hidden = true; setLookupStatus(''); });
  $('opt-expirations').addEventListener('change', () => loadChain());
  window.addEventListener('hashchange', () => { if (location.hash === '#options' && pendingChainCenter) centerChain(); });
  $('opt-refresh').addEventListener('click', () => loadChain());
  $('opt-expiry').addEventListener('input', () => { lookupGeneration++; clearChain(); });
  for (const id of ['opt-spot','opt-entry','opt-low','opt-high']) $(id).addEventListener('input', () => { stockAuto[id] = false; stockRevision[id] = (stockRevision[id] || 0) + 1; if (id === 'opt-spot' && chain.length) renderChain(); });
  $('opt-add').addEventListener('click', () => { clear(); addLeg(); });
  $('opt-reset').addEventListener('click', reset);
  $('options-form').addEventListener('submit', calculate);
  $('options-form').addEventListener('input', clear);
  $('language').addEventListener('change', translate);
  reset(); translate();
})();
