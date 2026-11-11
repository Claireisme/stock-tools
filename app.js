(() => {
  const $ = id => document.getElementById(id);
  const translations = {
    '数值工具箱':'Number Toolkit','工具导航':'Tools','股票工具':'Stock Tools','简单计算，清晰决策':'Simple calculations, clearer decisions','简单计算，清晰决策。':'Simple calculations, clearer decisions.',
    '让每个数字':'Make every number','都有答案。':'make sense.','好用的工具，放在一个地方。':'Useful tools, all in one place.','为日常计算节省时间，让每个决定更清晰。':'Save time on everyday calculations and make clearer decisions.','探索工具':'Explore tools',
    '选择一个工具，开始简单计算。':'Choose a tool and start calculating.','/ 持续更新':'/ Growing collection', '股价涨跌幅计算器':'Stock Price Change Calculator',
    '搜索股票，计算价格变化的百分比，或根据涨跌幅推算目标价。':'Search stocks, calculate a price change, or estimate a target price.','打开工具':'Open tool','计算示例':'Example','当前价格':'Current price','目标价格':'Target price','涨跌幅':'Price change',
    '更多工具':'More tools','更多实用工具，持续收录中。':'More useful tools are on the way.','新的工具正在规划中，敬请期待。':'More tools are being planned.','即将推出':'Coming soon','首页':'Home',
    '输入股票名称或代码，快速看清价格变化。':'Enter a stock name or ticker to explore price changes.','开始计算':'Start calculating','股票行情查询':'Stock lookup','可选，也可手动输入价格':'Optional: you can also enter a price manually','市场':'Market','全部市场':'All markets','A 股':'China A shares','港股':'Hong Kong','美股':'US',
    '检测数据源':'Check sources','数据源':'Data source','腾讯行情':'Tencent','新浪行情':'Sina','新浪财经':'Sina Finance','股票名称 / 代码':'Stock name / ticker','搜索':'Search','匹配的股票':'Matching stocks','计算方式':'Calculation mode','计算涨跌幅':'Calculate change','计算目标价':'Calculate target price',
    '基准价格':'Base price','变化后的价格':'Price after change','输入负数表示下跌':'Use a negative number for a decline','输入你想比较的目标价格。':'Enter the target price to compare.','上涨输入正数，下跌输入负数。':'Use a positive number for a rise and a negative number for a decline.',
    '计算结果':'Calculate','重置':'Reset','还没有数据？':'Need an example?','填入示例数据':'Use example','填入示例数据 →':'Use example →','输入价格后，结果将在这里显示。':'Enter prices to see the result.','ⓘ  计算公式':'ⓘ  Formula','小提示':'Note','正数表示上涨，负数表示下跌。行情可能延迟，休市时显示最近价格。计算结果仅供参考。':'Positive means a rise; negative means a decline. Quotes may be delayed and show the latest price when markets are closed. Results are for reference only.',
    '为日常计算，留一处简单。':'Making everyday calculations simpler.','设计与开发':'Designed and developed by','数值工具箱首页':'Number Toolkit home','主导航':'Main navigation',
    '输入股票名称或代码':'Enter stock name or ticker','搜索股票名称或代码':'Search by stock name or ticker','输入股票名称或代码，选择匹配的股票。':'Enter a stock name or ticker and select a match.','例如 贵州茅台或 600519':'e.g. Kweichow Moutai or 600519','输入 A 股名称或代码。':'Enter an A-share name or ticker.','例如 腾讯控股或 00700':'e.g. Tencent or 00700','输入港股名称或代码。':'Enter a Hong Kong stock name or ticker.','例如 苹果或 AAPL':'e.g. Apple or AAPL','输入美股名称或代码。':'Enter a US stock name or ticker.','例如 100':'e.g. 100','例如 110':'e.g. 110','例如 10 或 -10':'e.g. 10 or -10',
    '（目标价格 − 当前价格）÷ 当前价格 × 100%':'(Target price − Current price) ÷ Current price × 100%','当前价格 ×（1 + 涨跌幅 ÷ 100）':'Current price × (1 + Change ÷ 100)',
    '请填写两个数值后再计算。':'Enter both values to calculate.','当前价格必须大于 0。':'Current price must be greater than zero.','请输入大于或等于 0 的目标价格。':'Target price must be zero or greater.','跌幅不能低于 -100%。':'A decline cannot exceed 100%.','数值过大，请输入较小的数值。':'Values are too large; enter smaller numbers.',
    '请输入股票名称或代码。':'Enter a stock name or ticker.','正在搜索股票…':'Searching stocks…','未找到匹配的股票，请更换关键词或市场。':'No matches. Try a different search or market.','股票搜索失败，请稍后重试。':'Stock search failed. Please try again.','无法连接搜索服务，请确认本地服务已启动。':'Cannot connect to search. Make sure the local server is running.','查询中…':'Loading…','正在获取行情…':'Fetching quote…','行情查询失败，请稍后重试。':'Quote lookup failed. Please try again.','数据源未返回有效价格，请稍后重试。':'The data source returned no valid price. Please try again.','行情服务返回了无效数据，请确认本地服务已启动。':'Invalid quote response. Make sure the local server is running.','无法连接行情服务，请确认本地服务已启动。':'Cannot connect to the quote service. Make sure the local server is running.',
    '未找到该股票，请检查代码和市场。':'Stock not found. Check the ticker and market.','行情暂不可用，请稍后重试。':'Quote unavailable. Please try again.','行情服务暂时不可用，请检查网络后重试。':'Quote service unavailable. Check your connection and try again.','搜索服务暂时不可用，请检查网络后重试。':'Search service unavailable. Check your connection and try again.','该股票暂无有效价格。':'No valid price is available for this stock.'
  };
  const language = /^\/zh(?:\/|$)/.test(location.pathname) ? 'zh' : 'en';
  const tr = text => language === 'en' ? (translations[text] || text) : text;
  const staticNodes = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode, original = node.nodeValue, trimmed = original.trim();
    if (translations[trimmed]) staticNodes.push({node, original, trimmed});
  }
  const attrs = [];
  document.querySelectorAll('[aria-label], [placeholder]').forEach(node => ['aria-label', 'placeholder'].forEach(attr => {
    const value = node.getAttribute(attr);
    if (value && translations[value]) attrs.push({node, attr, value});
  }));
  function translateStatic() {
    document.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
    staticNodes.forEach(({node, original, trimmed}) => { if (node.isConnected) node.nodeValue = original.replace(trimmed, tr(trimmed)); });
    attrs.forEach(({node, attr, value}) => node.setAttribute(attr, tr(value)));
    $('language').value = language;
    $('language').setAttribute('aria-label', language === 'en' ? 'Language' : '语言');
    $('language').previousElementSibling.textContent = language === 'en' ? 'Language' : '语言';
    $('language').querySelector('[value="en"]').textContent = language === 'en' ? 'English' : '英文';
    $('language').querySelector('[value="zh"]').textContent = language === 'en' ? 'Chinese' : '中文';
    document.querySelector('meta[name="description"]').content = language === 'en' ? 'Number Toolkit for everyday calculations.' : '数值工具箱，方便日常计算。';
  }

  const home = $('home-view'), calculator = $('calculator-view');
  const current = $('current'), second = $('second'), form = $('calc-form');
  let mode = 'change', currency = 'CNY', quoteRequest = 0;
  const marketHints = { all: ['搜索股票名称或代码', '输入股票名称或代码，选择匹配的股票。'], cn: ['例如 贵州茅台或 600519', '输入 A 股名称或代码。'], hk: ['例如 腾讯控股或 00700', '输入港股名称或代码。'], us: ['例如 苹果或 AAPL', '输入美股名称或代码。'] };
  const unit = () => language === 'en' ? `${currency} / share` : `${({CNY:'元', HKD:'港元', USD:'美元'})[currency] || currency} / 股`;
  function refreshUnits() {
    $('current-unit').textContent = unit();
    $('second-unit').textContent = mode === 'change' ? unit() : '%';
  }
  const format = value => new Intl.NumberFormat(language === 'en' ? 'en-US' : 'zh-CN', { maximumFractionDigits: 4 }).format(Object.is(value, -0) ? 0 : value);
  const signed = value => `${value > 0 ? '+' : ''}${format(value)}`;

  function route() {
    const isCalculator = location.hash === '#price';
    const isOptions = location.hash === '#options';
    home.hidden = isCalculator || isOptions;
    calculator.hidden = !isCalculator;
    $('options-view').hidden = !isOptions;
    document.title = language === 'en' ? (isOptions ? 'Options Profit Calculator · Number Toolkit' : isCalculator ? 'Stock Price Change Calculator · Number Toolkit' : 'Number Toolkit') : (isOptions ? '期权收益计算器 · 数值工具箱' : isCalculator ? '股价涨跌幅计算器 · 数值工具箱' : '数值工具箱 · 让计算简单一点');
    if (location.hash !== '#tools') window.scrollTo(0, 0);
  }
  function clearResult() {
    $('error').textContent = '';
    $('result-value').innerHTML = mode === 'change' ? '— <small>%</small>' : `— <small>${unit()}</small>`;
    $('result-value').classList.remove('positive', 'negative');
    $('result-detail').textContent = tr('输入价格后，结果将在这里显示。');
  }
  function setMode(next, preserve = false) {
    mode = next;
    const change = mode === 'change';
    $('tab-change').classList.toggle('active', change);
    $('tab-target').classList.toggle('active', !change);
    $('tab-change').setAttribute('aria-selected', String(change));
    $('tab-target').setAttribute('aria-selected', String(!change));
    $('second-label').textContent = change ? tr('目标价格') : tr('涨跌幅');
    $('second-hint').textContent = change ? tr('变化后的价格') : tr('输入负数表示下跌');
    refreshUnits();
    $('second').placeholder = change ? tr('例如 110') : tr('例如 10 或 -10');
    $('field-note').textContent = change ? tr('输入你想比较的目标价格。') : tr('上涨输入正数，下跌输入负数。');
    $('result-label').textContent = change ? tr('涨跌幅') : tr('目标价格');
    $('formula-text').textContent = change ? tr('（目标价格 − 当前价格）÷ 当前价格 × 100%') : tr('当前价格 ×（1 + 涨跌幅 ÷ 100）');
    if (!preserve) second.value = '';
    clearResult();
    if (preserve && current.value.trim() && second.value.trim()) calculate();
  }
  function calculate() {
    $('error').textContent = '';
    if (current.value.trim() === '' || second.value.trim() === '') { $('error').textContent = tr('请填写两个数值后再计算。'); return; }
    const base = Number(current.value), value = Number(second.value);
    if (!Number.isFinite(base) || base <= 0) { $('error').textContent = tr('当前价格必须大于 0。'); return; }
    if (!Number.isFinite(value) || (mode === 'change' && value < 0)) { $('error').textContent = tr('请输入大于或等于 0 的目标价格。'); return; }
    if (mode === 'target' && value < -100) { $('error').textContent = tr('跌幅不能低于 -100%。'); return; }
    const result = mode === 'change' ? (value - base) / base * 100 : base * (1 + value / 100);
    const difference = mode === 'change' ? value - base : result - base;
    if (!Number.isFinite(result) || !Number.isFinite(difference)) { $('error').textContent = tr('数值过大，请输入较小的数值。'); return; }
    $('result-value').innerHTML = `${mode === 'change' ? signed(result) : format(result)} <small>${mode === 'change' ? '%' : unit()}</small>`;
    $('result-value').classList.toggle('positive', difference > 0);
    $('result-value').classList.toggle('negative', difference < 0);
    $('result-detail').textContent = language === 'en' ? `Price ${difference > 0 ? 'rose' : difference < 0 ? 'fell' : 'unchanged'} ${format(Math.abs(difference))} ${unit()}` : `价格${difference > 0 ? '上涨' : difference < 0 ? '下跌' : '持平'} ${format(Math.abs(difference))} ${unit()}`;
  }
  const quoteCode = $('quote-code'), quoteMarket = $('quote-market');
  const sourceNames = {sina: ['新浪行情', 'Sina'], tencent: ['腾讯行情', 'Tencent'], yahoo: ['Yahoo Finance', 'Yahoo Finance']};
  let savedHealth = {};
  try { savedHealth = JSON.parse(localStorage.getItem('toolkit-source-health') || '{}') || {}; } catch (_) {}
  const health = typeof savedHealth === 'object' && !Array.isArray(savedHealth) ? savedHealth : {};
  let fallbackNotice = null, healthRequest = 0;
  const sourceName = id => sourceNames[id] ? sourceNames[id][language === 'en' ? 1 : 0] : id;
  function renderSource() {
    const currentSource = sourceName($('quote-source').value);
    $('source-current').textContent = fallbackNotice
      ? (language === 'en' ? `${sourceName(fallbackNotice.from)} is unavailable. Automatically switched to ${currentSource}.` : `${sourceName(fallbackNotice.from)}不可用，已自动切换至${currentSource}。`)
      : (language === 'en' ? `Current source: ${currentSource}` : `当前使用：${currentSource}`);
    if ($('quote-source').value === 'yahoo') $('source-current').textContent += language === 'en' ? ' · Search by ticker or English name; Beijing Exchange is not supported.' : ' · 建议输入英文名称或代码搜索；暂不支持北交所。';
    $('source-health').replaceChildren();
    for (const id of Object.keys(sourceNames)) {
      const item = health[id];
      const span = document.createElement('span');
      if (!item) span.textContent = `${sourceName(id)} · ${language === 'en' ? 'Not checked' : '尚未检测'}`;
      else {
        const searchOK = item.search?.ok === true, quoteOK = item.quote?.ok === true;
        span.className = searchOK && quoteOK ? 'health-ok' : searchOK || quoteOK ? 'health-partial' : 'health-failed';
        const status = searchOK && quoteOK ? (language === 'en' ? 'Available' : '可用') : searchOK || quoteOK ? (language === 'en' ? 'Partially available' : '部分可用') : (language === 'en' ? 'Unavailable' : '不可用');
        const details = language === 'en' ? `Search ${searchOK ? 'OK' : 'failed'}, quote ${quoteOK ? 'OK' : 'failed'}` : `搜索${searchOK ? '可用' : '失败'}、行情${quoteOK ? '可用' : '失败'}`;
        const date = new Date(item.checked_at);
        const time = Number.isNaN(date.getTime()) ? '—' : date.toLocaleString(language === 'en' ? 'en-US' : 'zh-CN');
        span.textContent = `${sourceName(id)} · ${status} (${details}) · ${language === 'en' ? 'Checked' : '检测于'} ${time}`;
      }
      $('source-health').appendChild(span);
    }
  }
  function applyFallback(data) {
    if (!data.fallback || !$('quote-source').querySelector(`option[value="${data.fallback.to}"]`)) return;
    $('quote-source').value = data.fallback.to;
    fallbackNotice = {from: data.fallback.from, to: data.fallback.to};
    renderSource();
  }
  async function checkSources() {
    const request = ++healthRequest, button = $('check-sources');
    button.disabled = true;
    button.textContent = language === 'en' ? 'Checking…' : '检测中…';
    await Promise.all(Object.keys(sourceNames).map(async id => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 20000);
      try {
        const response = await fetch(`/api/health?${new URLSearchParams({source:id})}`, {signal: controller.signal, cache:'no-store'});
        const result = await response.json();
        if (!response.ok || !result.search || !result.quote) throw new Error('health check failed');
        if (request === healthRequest) health[id] = result;
      } catch (_) {
        if (request === healthRequest) health[id] = {checked_at:new Date().toISOString(), search:{ok:false}, quote:{ok:false}};
      } finally {
        clearTimeout(timer);
        if (request === healthRequest) {
          try { localStorage.setItem('toolkit-source-health', JSON.stringify(health)); } catch (_) {}
          renderSource();
        }
      }
    }));
    if (request === healthRequest) { button.disabled = false; button.textContent = tr('检测数据源'); }
  }
  $('check-sources').addEventListener('click', checkSources);
  const quoteResults = $('quote-results'), quoteStatus = $('quote-status');
  const marketNames = { cn: 'A 股', hk: '港股', us: '美股' };
  const displayName = (name, code) => language === 'en' && /[\u3400-\u9fff]/u.test(name || '') ? code : (name || code);
  const quoteDescription = (data, name, code, price) => {
    const ticker = data.code || code, label = displayName(data.name || name, ticker);
    const time = data.time && (language !== 'en' || !/[\u3400-\u9fff]/u.test(data.time)) ? ` · ${language === 'en' ? 'Source time' : '数据源时间'}: ${data.time}` : (language === 'en' ? ' · Time unavailable' : ' · 数据源未提供时间');
    const source = data.source ? ` · ${language === 'en' ? 'Source' : '来源'}: ${tr(data.source)}` : '';
    return `${label === ticker ? ticker : `${label} (${ticker})`} ${format(price)} ${unit()}${time}${source}`;
  };
  let searchRequest = 0, searchTimer, searchController, options = [], activeOption = -1, quoteAutofilled = false, lastQuote = null;

  function closeResults() {
    quoteResults.hidden = true;
    quoteResults.replaceChildren();
    quoteCode.setAttribute('aria-expanded', 'false');
    quoteCode.removeAttribute('aria-activedescendant');
    options = [];
    activeOption = -1;
  }
  function cancelSearch() {
    clearTimeout(searchTimer);
    searchRequest++;
    if (searchController) searchController.abort();
    closeResults();
  }
  function cancelQuote() {
    quoteRequest++;
    $('quote-search').disabled = false;
    $('quote-search').textContent = tr('搜索');
  }
  function discardQuote() {
    cancelQuote();
    quoteStatus.textContent = '';
    lastQuote = null;
    if (quoteAutofilled) {
      current.value = '';
      quoteAutofilled = false;
      clearResult();
    }
  }
  function updateQuoteHint() {
    const [placeholder, hint] = marketHints[quoteMarket.value] || marketHints.all;
    quoteCode.placeholder = tr(placeholder);
    $('quote-hint').textContent = tr(hint);
    cancelSearch();
    discardQuote();
    if (quoteCode.value.trim()) scheduleSearch();
  }
  function renderResults(results) {
    closeResults();
    options = results;
    results.forEach((item, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'quote-option';
      button.id = `quote-option-${index}`;
      button.setAttribute('role', 'option');
      button.setAttribute('aria-selected', 'false');
      button.tabIndex = -1;
      for (const [className, value] of [['quote-option-name', displayName(item.name, item.code) === item.code ? '' : displayName(item.name, item.code)], ['quote-option-code', item.code], ['quote-option-market', tr(marketNames[item.market]) || item.market]]) {
        const span = document.createElement('span');
        span.className = className;
        span.textContent = value;
        button.appendChild(span);
      }
      button.addEventListener('mousedown', event => event.preventDefault());
      button.addEventListener('click', () => selectOption(index));
      quoteResults.appendChild(button);
    });
    quoteResults.hidden = !results.length;
    quoteCode.setAttribute('aria-expanded', String(Boolean(results.length)));
  }
  function setActive(index) {
    if (!options.length) return;
    activeOption = (index + options.length) % options.length;
    [...quoteResults.children].forEach((child, i) => {
      child.classList.toggle('active', i === activeOption);
      child.setAttribute('aria-selected', String(i === activeOption));
    });
    const active = quoteResults.children[activeOption];
    quoteCode.setAttribute('aria-activedescendant', active.id);
    active.scrollIntoView({ block: 'nearest' });
  }
  async function searchStocks() {
    clearTimeout(searchTimer);
    const q = quoteCode.value.trim();
    cancelSearch();
    if (!q) { quoteStatus.textContent = tr('请输入股票名称或代码。'); return; }
    const request = searchRequest;
    const controller = new AbortController();
    searchController = controller;
    quoteStatus.textContent = tr('正在搜索股票…');
    try {
      const params = new URLSearchParams({ q, market: quoteMarket.value, source: $('quote-source').value });
      const response = await fetch(`/api/search?${params}`, { signal: controller.signal });
      const data = await response.json();
      if (request !== searchRequest) return;
      if (!response.ok || data.error) throw new Error(data.error || tr('股票搜索失败，请稍后重试。'));
      applyFallback(data);
      const results = Array.isArray(data.results) ? data.results.filter(item => item && item.name && item.code && marketNames[item.market]) : [];
      renderResults(results);
      quoteStatus.textContent = results.length ? (language === 'en' ? `${results.length} stocks found. Select one.` : `找到 ${results.length} 只股票，请选择。`) : tr('未找到匹配的股票，请更换关键词或市场。');
    } catch (error) {
      if (request !== searchRequest || error.name === 'AbortError') return;
      quoteStatus.textContent = error instanceof TypeError ? tr('无法连接搜索服务，请确认本地服务已启动。') : (language === 'en' && !translations[error.message] ? tr('股票搜索失败，请稍后重试。') : (tr(error.message) || tr('股票搜索失败，请稍后重试。')));
    }
  }
  function scheduleSearch() {
    clearTimeout(searchTimer);
    if (!quoteCode.value.trim()) return;
    searchTimer = setTimeout(searchStocks, 300);
  }
  async function selectOption(index) {
    const item = options[index];
    if (!item) return;
    cancelSearch();
    const label = displayName(item.name, item.code);
    quoteCode.value = label === item.code ? item.code : `${label} (${item.code})`;
    await lookupQuote(item.market, item.code, item.name);
  }
  async function lookupQuote(market, code, name) {
    const request = ++quoteRequest;
    const button = $('quote-search');
    button.disabled = true;
    button.textContent = tr('查询中…');
    quoteStatus.textContent = tr('正在获取行情…');
    try {
      const params = new URLSearchParams({ market, code, source: $('quote-source').value });
      const response = await fetch(`/api/quote?${params}`);
      const data = await response.json();
      if (request !== quoteRequest) return;
      if (!response.ok || data.error) throw new Error(data.error || tr('行情查询失败，请稍后重试。'));
      applyFallback(data);
      const price = Number(data.price);
      if (!Number.isFinite(price) || price <= 0) throw new Error(tr('数据源未返回有效价格，请稍后重试。'));
      currency = ({CNY:'CNY', HKD:'HKD', USD:'USD', '元':'CNY', '港元':'HKD', '美元':'USD'})[data.currency] || ({cn:'CNY', hk:'HKD', us:'USD'})[market];
      current.value = String(price);
      quoteAutofilled = true;
      refreshUnits();
      clearResult();
      if (second.value.trim() !== '') calculate();
      lastQuote = {data, name, code, price};
      quoteStatus.textContent = quoteDescription(data, name, code, price);
    } catch (error) {
      if (request !== quoteRequest) return;
      quoteStatus.textContent = error instanceof SyntaxError ? tr('行情服务返回了无效数据，请确认本地服务已启动。') : error instanceof TypeError ? tr('无法连接行情服务，请确认本地服务已启动。') : (language === 'en' && !translations[error.message] ? tr('行情查询失败，请稍后重试。') : (tr(error.message) || tr('行情查询失败，请稍后重试。')));
    } finally {
      if (request === quoteRequest) { button.disabled = false; button.textContent = tr('搜索'); }
    }
  }
  quoteCode.setAttribute('role', 'combobox');
  quoteCode.setAttribute('aria-autocomplete', 'list');
  quoteCode.setAttribute('aria-controls', 'quote-results');
  quoteCode.setAttribute('aria-expanded', 'false');
  quoteMarket.addEventListener('change', updateQuoteHint);
  $('quote-source').addEventListener('change', () => {
    fallbackNotice = null;
    renderSource();
    const selected = lastQuote;
    cancelSearch();
    discardQuote();
    if (selected) lookupQuote(selected.data.currency === 'CNY' ? 'cn' : selected.data.currency === 'HKD' ? 'hk' : 'us', selected.code, selected.name);
    else if (quoteCode.value.trim()) scheduleSearch();
  });
  quoteCode.addEventListener('input', () => { cancelSearch(); discardQuote(); scheduleSearch(); });
  quoteCode.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown' && options.length) { event.preventDefault(); setActive(activeOption + 1); }
    else if (event.key === 'ArrowUp' && options.length) { event.preventDefault(); setActive(activeOption < 0 ? options.length - 1 : activeOption - 1); }
    else if (event.key === 'Enter') { event.preventDefault(); if (activeOption >= 0) selectOption(activeOption); else searchStocks(); }
    else if (event.key === 'Escape') { cancelSearch(); }
  });
  document.addEventListener('click', event => {
    if (!quoteResults.contains(event.target) && event.target !== quoteCode && !$('quote-search').contains(event.target)) cancelSearch();
  });
  $('quote-search').addEventListener('click', searchStocks);
  $('tab-change').addEventListener('click', () => setMode('change'));
  $('tab-target').addEventListener('click', () => setMode('target'));
  form.addEventListener('submit', event => { event.preventDefault(); calculate(); });
  $('reset').addEventListener('click', () => { cancelSearch(); cancelQuote(); quoteCode.value = ''; quoteStatus.textContent = ''; quoteAutofilled = false; currency = 'CNY'; refreshUnits(); form.reset(); clearResult(); current.focus(); });
  $('example').addEventListener('click', () => { current.value = '100'; second.value = mode === 'change' ? '110' : '10'; calculate(); });
  current.addEventListener('input', () => {
    cancelQuote();
    quoteAutofilled = false;
    quoteStatus.textContent = '';
  });
  for (const input of [current, second]) input.addEventListener('input', () => {
    clearResult();
    if (current.value.trim() !== '' && second.value.trim() !== '') calculate();
  });
  $('language').addEventListener('change', event => {
    const path = event.target.value === 'zh' ? '/zh/' : '/';
    location.assign(path + location.search + location.hash);
  });
  translateStatic();
  renderSource();
  setMode(mode, true);
  window.addEventListener('hashchange', route);
  route();
})();
