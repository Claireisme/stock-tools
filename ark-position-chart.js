(() => {
  const en = !/^\/zh(?:\/|$)/.test(location.pathname);
  const t = (zh, eng) => en ? eng : zh;
  const el = (tag, value, cls) => { const n=document.createElement(tag); if(value!=null)n.textContent=value; if(cls)n.className=cls; return n; };
  const ns='http://www.w3.org/2000/svg';
  const svgEl = (name, attrs={}) => { const n=document.createElementNS(ns,name); for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v)); return n; };
  const fmt = v => v == null ? '—' : new Intl.NumberFormat(en?'en-US':'zh-CN',{maximumFractionDigits:2}).format(v);
  const timestamp = d => Date.parse(`${d}T00:00:00Z`);
  window.renderArkPositionChart = async function(container, fund, securityId) {
    const token = container._chartToken = Symbol();
    container.hidden=false; container.replaceChildren(el('p',t('正在加载持仓与股价…','Loading holdings and price…')));
    try {
      const response=await fetch('/api/investors/ark-holdings/history?' + new URLSearchParams({fund,security_id:securityId}));
      const data=await response.json(); if(!container.isConnected || container._chartToken !== token)return; if(!response.ok)throw new Error(data.error || response.status);
      let metric='weight';
      function render() {
        container.replaceChildren();
        const head=el('div',null,'position-chart-head'), title=el('div'); title.append(el('h3',`${fund} · ${data.security.ticker || data.security.name}`),el('p',data.security.name,'profile-muted'));
        const close=el('button',t('关闭图表','Close chart'),'options-secondary'); close.onclick=()=>{container._chartToken = null; container.hidden=true;container.replaceChildren();}; head.append(title,close);container.append(head);
        const controls=el('div',null,'position-chart-controls');
        for(const [key,label] of [['weight',t('基金占比','Fund weight')],['shares',t('持仓数量','Shares held')]]) { const button=el('button',label,'options-secondary'); button.type='button'; button.setAttribute('aria-pressed',String(metric===key)); button.onclick=()=>{metric=key;render();}; controls.append(button); }
        container.append(controls);
        let segment = 0; const hp=[]; for (const p of (data.holdings || [])) { if (p.reported === false || p[metric] == null || !Number.isFinite(Number(p[metric])) || !Number.isFinite(timestamp(p.date))) { segment++; continue; } hp.push({date:p.date,value:Number(p[metric]),segment}); } hp.sort((a,b)=>a.date.localeCompare(b.date));
        const pp=(data.price?.points || []).filter(p=>p.close!=null && Number.isFinite(Number(p.close)) && Number.isFinite(timestamp(p.date))).map(p=>({date:p.date,value:Number(p.close)})).sort((a,b)=>a.date.localeCompare(b.date));
        const note=t('持仓来自 ARK 已保存的收盘快照，仅显示实际采集日期；缺失日期不补值。','Holdings are saved ARK closing snapshots; only collected dates are shown, without filling gaps.');
        container.append(el('p', note, 'profile-muted'));
        if(hp.length===1)container.append(el('p',t('目前仅有一个持仓数据点；以后采集到更多日期才能形成趋势。','Only one holdings snapshot is available; a trend requires more dates.'),'position-chart-note'));
        if(data.price?.error) container.append(el('p',`${t('股价暂不可用','Price unavailable')}: ${data.price.error}`,'position-chart-note'));
        else if(!pp.length) container.append(el('p',t('没有可用的历史股价。','No historical price is available.'),'position-chart-note'));
        const axis=el('p',`${t('绿色：','Green: ')}${metric==='weight'?t('基金占比（左轴）','fund weight (left axis)'):t('持仓数量（左轴）','shares held (left axis)')}　 ${t('蓝色：股价（右轴）','Blue: price (right axis)')}`, 'position-chart-legend'); container.append(axis);
        if(!hp.length && !pp.length){container.append(el('p',t('暂无图表数据。','No chart data available.'),'investor-empty'));return;}
        const W=900,H=300,L=82,R=82,T=24,B=48,plotW=W-L-R,plotH=H-T-B;
        let allDates=[...hp,...pp].map(p=>timestamp(p.date)), min=Math.min(...allDates), max=Math.max(...allDates); if(min===max){min-=43200000;max+=43200000;}
        const extent=values=>{if(!values.length)return [0,1];let lo=Math.min(...values),hi=Math.max(...values);if(lo===hi){const pad=Math.max(Math.abs(lo)*.05,1);lo-=pad;hi+=pad;}else {const pad=(hi-lo)*.08;lo-=pad;hi+=pad;}return [lo,hi];};
        const [hlo,hhi]=extent(hp.map(x=>x.value)),[plo,phi]=extent(pp.map(x=>x.value));
        const x=d=>L+(timestamp(d)-min)/(max-min)*plotW, y=(v,lo,hi)=>T+(hi-v)/(hi-lo)*plotH;
        const chart=svgEl('svg',{viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':t('基金持仓及股票价格走势图','Fund holdings and stock price chart'),class:'position-chart-svg'});
        const txt=(xPos,yPos,value,anchor='start')=>{const node=svgEl('text',{x:xPos,y:yPos,'text-anchor':anchor,class:'position-chart-axis'});node.textContent=value;chart.append(node);};
        for(let i=0;i<4;i++){const yy=T+plotH*i/3;chart.append(svgEl('line',{x1:L,y1:yy,x2:W-R,y2:yy,class:'position-chart-grid'})); if(hp.length)txt(L-8,yy+4,fmt(hhi-(hhi-hlo)*i/3)+(metric==='weight'?'%':''),'end');if(pp.length)txt(W-R+8,yy+4,fmt(phi-(phi-plo)*i/3));}
        const addLine=(points,lo,hi,kind,gap)=>{let path='',last,lastSegment;for(const p of points){const xx=x(p.date),yy=y(p.value,lo,hi);path+=(last==null || timestamp(p.date)-last>gap || (p.segment != null && p.segment !== lastSegment)?'M':'L')+xx.toFixed(1)+' '+yy.toFixed(1)+' ';last=timestamp(p.date);lastSegment=p.segment;}if(path)chart.append(svgEl('path',{d:path,class:`position-line ${kind}`}));};
        addLine(pp,plo,phi,'price',7*86400000);addLine(hp,hlo,hhi,'holding',5*86400000);
        if(pp.length===1)chart.append(svgEl('circle',{cx:x(pp[0].date),cy:y(pp[0].value,plo,phi),r:4,fill:'#4e79b6'}));
        for(const p of hp){const circle=svgEl('circle',{cx:x(p.date),cy:y(p.value,hlo,hhi),r:5,class:'position-dot'});const tip=svgEl('title');tip.textContent=`${p.date}: ${fmt(p.value)}${metric==='weight'?'%':''}`;circle.append(tip);chart.append(circle);}
        const dateText = ms => new Date(ms).toISOString().slice(0,10);txt(L,H-12,dateText(min));txt(W-R,H-12,dateText(max),'end');container.append(chart);
        if(pp.length)container.append(el('p',t('股价来源：Alpaca IEX 日收盘价（未复权，仅代表 IEX 交易所，可能不等于全市场收盘价）。','Price: Alpaca IEX daily close, unadjusted, reflecting IEX only rather than the consolidated market.'),'profile-muted'));
        const more=el('details',null,'position-chart-data'); more.append(el('summary',t('查看持仓数据点','View holdings data points'))); const list=el('ul');for(const p of hp)list.append(el('li',`${p.date} · ${fmt(p.value)}${metric==='weight'?'%':''}`));if(!hp.length)list.append(el('li',t('暂无持仓数据','No holdings data')));more.append(list);container.append(more);
      }
      render();container.scrollIntoView({behavior:'smooth',block:'nearest'});
    } catch(error) { if(!container.isConnected || container._chartToken !== token)return; container.replaceChildren(el('p',t('无法加载走势图：','Could not load chart: ')+error.message)); }
  };
})();
