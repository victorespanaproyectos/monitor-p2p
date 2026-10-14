import { BINANCE_USERNAME } from './operator.js?v=market-1.4.2';
import { profit, spreadScenarios, myPositions, minimumMatches, recommendedSpread, rankedSpreads } from './profit.js?v=market-1.4.2';
const FIAT=document.body.dataset.fiat || 'UYU';
const MONEY=FIAT==='USD'?'USD':'$U';
const MIN_FALLBACK=null;
const banks = FIAT==='USD'?[{key:'airtm',name:'Airtm',mark:'A',color:'#1868e5',match:/airtm/i}]:[
  { key:'santander',name:'Santander',mark:'S',color:'#d52832',match:/santander/i },
  { key:'itau',name:'Itaú',mark:'i',color:'#df650e',match:/itau/i },
  { key:'oca',name:'OCA Blue',mark:'O',color:'#1684b3',match:/ocablue/i },
  { key:'mercadopago',name:'MercadoPago',mark:'M',color:'#1689c4',match:/mercadopago/i },
  { key:'prex',name:'Prex',mark:'P',color:'#6c39b9',match:/prex/i },
  { key:'brou',name:'BROU',mark:'B',color:'#194b8a',match:/bankrepublicuruguay|brou/i },
];
let marketAmount='',marketAmountUnit='fiat',refreshSequence=0,advertiserSequence=0,advertiserUser='';
const recommendationState={data:null,error:null,busy:false,lastFetch:0};
const state = { groups:new Map(),bank:FIAT==='USD'?'airtm':'santander',extra:null,methods:[],methodsLoading:false,loading:false,error:null };
state.selected=new Set([state.bank]);state.extras=new Map();
const choices=()=>[...banks,...state.extras.values()];
const $ = id => document.getElementById(id);
const escape = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const fmt = (n,decimals=2) => n == null ? '—' : new Intl.NumberFormat('es-UY',{minimumFractionDigits:decimals,maximumFractionDigits:decimals}).format(n);
const time = value => value ? new Date(value).toLocaleTimeString('es-UY',{timeZone:'America/Montevideo',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—';
const priceFmt=n=>fmt(n,FIAT==='USD'?4:2);
const mark = (b,large=false) => `<span class="bank-mark bank-icon ${large?'large':''}" style="--bank-color:${b.color}">${['santander','itau','oca','mercadopago','prex','brou','airtm'].includes(b.key)?`<img src="/static/banks/${b.key}.${b.key==='mercadopago'?'svg':'png'}" alt="" width="30" height="30">`:'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M3 10h18L12 3 3 10Zm2 2v7m5-7v7m4-7v7m5-7v7M2 21h20"/></svg>'}</span>`;
const fields = ['calc-buy','calc-sell','calc-amount','refresh-seconds','calc-buy-percent','calc-sell-percent','calc-buy-fixed','calc-sell-fixed'];
try {
  const saved=JSON.parse(localStorage.getItem('p2p-'+FIAT.toLowerCase()+'-preferences-v3') || '{}');
  fields.forEach(id => {if(typeof saved[id]==='string') $(id).value=saved[id];});
} catch {}
if (!['3','6','10','30','60'].includes($('refresh-seconds').value)) $('refresh-seconds').value='60';
if (!$('calc-amount').value) $('calc-amount').value='1000';
function save() {try {localStorage.setItem('p2p-'+FIAT.toLowerCase()+'-preferences-v3',JSON.stringify(Object.fromEntries(fields.map(id=>[id,$(id).value]))));}catch{}}
function inputs() {return {buy:$('calc-buy').valueAsNumber,sell:$('calc-sell').valueAsNumber,amount:$('calc-amount').valueAsNumber,unit:'USDT',buyExpenseRate:(Number($('calc-buy-percent').value)/100).toFixed(6),sellExpenseRate:(Number($('calc-sell-percent').value)/100).toFixed(6),buyFixed:Number($('calc-buy-fixed').value),sellFixed:Number($('calc-sell-fixed').value)};}
const netClass = n => n>=0?'positive':'negative';
function resultHTML(r) {
  return `<div class="result-main"><span>Ganancia neta estimada</span><strong class="${netClass(r.net)}">${MONEY} ${fmt(r.net)}</strong><span>${fmt(r.roi)}% sobre el costo total</span></div><div class="result-detail"><span>Ganancia bruta <b>${MONEY} ${fmt(r.gross)}</b></span><span>Comisiones <b>${fmt(r.fees,6)} USDT</b></span><span>Gastos adicionales <b>${MONEY} ${fmt(r.extraCosts || 0)}</b></span><span>Costo de compra <b>${MONEY} ${fmt(r.cost)}</b></span><span>Ingreso de venta <b>${MONEY} ${fmt(r.proceeds)}</b></span><span>Compra nominal <b>${fmt(r.quantity)} USDT</b></span><span>Venta nominal <b>${fmt(r.sellQuantity,6)} USDT</b></span><span>Spread <b>${priceFmt(r.spread)} ${FIAT}/USDT</b></span></div>`;
}
let calcSequence=0,calcKey='';
function renderCalc() {
  const values=inputs(),key=JSON.stringify(values);if(key===calcKey)return;calcKey=key;
  const sequence=++calcSequence;const valid=profit(values);if(!valid){$('calc-result').innerHTML='<p>Ingresa precios de compra, venta y un monto válido.</p>';return;}
  $('calc-result').textContent='Calculando en Python…';
  fetch('/api/calculate?operator='+encodeURIComponent(window.P2P_CONTEXT.operator)+'&buy='+values.buy+'&sell='+values.sell+'&amount='+values.amount+'&buyExpenseRate='+values.buyExpenseRate+'&sellExpenseRate='+values.sellExpenseRate+'&buyFixed='+values.buyFixed+'&sellFixed='+values.sellFixed).then(async response=>{const data=await response.json();if(!response.ok)throw Error(data.error||'No se pudo calcular.');if(sequence===calcSequence)$('calc-result').innerHTML=resultHTML(data.result);}).catch(error=>{if(sequence===calcSequence){$('calc-result').textContent=error.message;calcKey='';}});
}

function renderSpread(group,key=state.bank) {
  const scenarios=!group?.queryError?spreadScenarios(group):null;
  if(!scenarios) return '<section class="spread-unavailable">El spread estará disponible cuando haya cotizaciones válidas en ambos lados.</section>';
  return `<section class="spread-grid" aria-label="Spread del medio seleccionado">${scenarios.map(s=>{
    const r=profit({...inputs(),buy:s.buy,sell:s.sell});
    const spread=s.sell-s.buy;
    return `<article class="spread-card"><div class="tool-heading"><h3>${s.name}</h3><span>${fmt(spread/s.buy*100)}% bruto</span></div><div class="spread-value ${netClass(spread)}">${priceFmt(spread)} <small>${FIAT} por USDT</small></div><p>${s.note}</p><div class="spread-prices">Compra: <b>${priceFmt(s.buy)}</b> · Venta: <b>${priceFmt(s.sell)}</b> ${FIAT}</div><div class="spread-estimate">${r?`Para ${fmt(inputs().amount)} ${inputs().unit}:<br><b class="${netClass(r.net)}">${MONEY} ${fmt(r.net)} netos estimados</b><span>Bruto: ${MONEY} ${fmt(r.gross)} · Comisiones: ${fmt(r.fees,6)} USDT</span>`:'Ingresa un monto válido para estimar la ganancia.'}</div><button type="button" class="use-prices" data-scenario="${s.key}" data-market="${escape(key)}" title="Usar precios en la calculadora" aria-label="Usar precios de ${s.name} en la calculadora"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="4" y="3" width="12" height="18" rx="2"/><path d="M7 7h6M7 11h2m2 0h2m-6 4h2m2 0h2m-6 3h2m11-9 3 3-3 3m-5-3h8"/></svg></button></article>`;
  }).join('')}<p class="spread-note">Estos escenarios usan los precios publicados como referencia. La estimación usa el monto y las comisiones de la calculadora; no comprueba que los límites o la disponibilidad cubran el monto. Un spread mayor no garantiza que se completen tus anuncios.</p></section>`;
}
function renderRecommendations(){
  const data=recommendationState.data;
  const icon='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="4" y="3" width="12" height="18" rx="2"/><path d="M7 7h6M7 11h2m2 0h2m-6 4h2m2 0h2m-6 3h2m11-9 3 3-3 3m-5-3h8"/></svg>';
  const tile=(scope,label)=>{
    const best=data?recommendedSpread(data.quotes,inputs().amount,scope==='defaults'):null;
    const tested=scope==='defaults'?data?.defaultConsulted:data?.consulted,total=scope==='defaults'?data?.defaultTotal:data?.total;
    let status=!data?'Consultando medios…':`${tested} / ${total} medios consultados`;
    if(data && scope==='defaults' && data.defaultAvailable<data.defaultTotal)status+=` · ${data.defaultTotal-data.defaultAvailable} no disponibles`;
    if(best){const estimate=best.estimate;return `<article class="recommendation-tile recommendation-${scope}"><div class="recommendation-label">${label}</div><div class="recommendation-method">${escape(best.name)}<button type="button" class="recommendation-use" data-recommendation="${scope}" title="Usar precios de ${escape(best.name)} en la calculadora" aria-label="Usar precios de ${escape(best.name)} en la calculadora">${icon}</button></div><div class="recommendation-profit ${netClass(estimate.net)}">${MONEY} ${fmt(estimate.net)} <small>netos estimados</small></div><p class="recommendation-prices">Compra <b>${priceFmt(best.buy)}</b> · Venta <b>${priceFmt(best.sell)}</b> ${FIAT}</p><p class="recommendation-metrics">Spread ${priceFmt(estimate.spread)} ${FIAT}/USDT · ${fmt(estimate.roi)} % neto</p>${estimate.net<=0?'<p class="recommendation-loss">Sin spread neto positivo: esta es la mejor referencia consultada, pero no genera ganancia.</p>':''}<small class="recommendation-coverage">${status} · Cotización ${time(best.updatedAt)}</small></article>`;}
    return `<article class="recommendation-tile recommendation-${scope}"><div class="recommendation-label">${label}</div><p class="recommendation-empty">${!Number.isFinite(inputs().amount)||inputs().amount<=0?'Ingresa un monto válido en la calculadora.':data?.complete?'Sin precios válidos en ambos lados.':'Buscando precios de compra y venta…'}</p><small class="recommendation-coverage">${status}</small></article>`;
  };
  const top=data?rankedSpreads(data.quotes,inputs().amount).slice(0,5):[];
  const ranking=`<article class="recommendation-ranking"><div class="recommendation-ranking-heading"><div><span class="recommendation-label">RANKING GLOBAL</span><h3>Top 5 · mejores spreads</h3></div><span class="ranking-count">${top.length} / 5</span></div><p class="ranking-description">Todos los medios consultados · ordenados por ganancia neta para el monto de la calculadora.</p>${top.length?`<ol class="spread-ranking-list">${top.map((item,index)=>`<li class="spread-ranking-row podium-${index+1}"><span class="spread-rank-number" aria-label="Posición ${index+1}">${index+1}</span><div class="spread-ranking-name"><b>${escape(item.name)}</b><small>${item.defaultKey?'Medio por defecto':'Otro medio'} · ${time(item.updatedAt)}</small></div><div class="spread-ranking-prices"><span>Compra <b>${priceFmt(item.buy)}</b> · Venta <b>${priceFmt(item.sell)}</b> ${FIAT}</span><small>Spread ${priceFmt(item.estimate.spread)} ${FIAT}/USDT</small></div><div class="spread-ranking-net"><strong class="${netClass(item.estimate.net)}">${MONEY} ${fmt(item.estimate.net)}</strong><small>${item.estimate.net>0?'netos estimados':'sin ganancia neta'} · ${fmt(item.estimate.roi)} %</small></div><button type="button" class="recommendation-use" data-recommendation="ranked" data-method-key="${escape(item.key)}" title="Usar precios de ${escape(item.name)}" aria-label="Usar precios del puesto ${index+1}: ${escape(item.name)} en la calculadora">${icon}</button></li>`).join('')}</ol>${top.length<5?`<p class="ranking-description">Hay ${top.length} medios con precios válidos en ambos lados. Se muestran los disponibles.</p>`:''}`:`<p class="recommendation-empty">${!Number.isFinite(inputs().amount)||inputs().amount<=0?'Ingresa un monto válido en la calculadora.':data?.complete?'No hay medios con precios válidos en ambos lados.':'El ranking aparecerá mientras se consultan los medios.'}</p>`}</article>`;
  const coverage=data?`${data.consulted}/${data.total}`:'—';
  const complete=data?.complete && data.consulted===data.total && !data.failed && !data.error;
  const note=recommendationState.error?`Comparación no disponible o desactualizada: ${escape(recommendationState.error)}`:data?.limited?'Binance limitó las consultas: comparación parcial; se reintentará en la próxima revisión.':data?.error?`Comparación parcial: ${escape(data.error)}`:data?.complete?`${complete?'Revisión completa':'Revisión parcial'} · ${coverage} consultados${data.failed?` · ${data.failed} consultas fallidas`:''}.`:`Revisando catálogo: ${coverage} medios. Los resultados pueden cambiar al completar la revisión.`;
  return `<section class="recommendations-section" aria-label="Spreads recomendados"><div class="recommendations-heading"><div><span class="eyebrow">COMPARACIÓN ENTRE MEDIOS</span><h2>Spread recomendado</h2></div><span class="recommendation-status">${complete?'Revisión completa':'Comparación en curso / parcial'}</span></div><div class="recommendation-grid">${tile('defaults','Medios por defecto')}${tile('all','Todos los medios de pago')}</div>${ranking}<p class="recommendation-note" aria-live="polite">${note}</p><p class="recommendation-help">Para ${fmt(inputs().amount)} USDT nominales a comprar. Se compara el spread competitivo del mismo medio, con ${fmt(Number(window.P2P_CONTEXT.commission)*100,4)} % en USDT por lado. Mejor = mayor ganancia neta estimada entre los precios válidos consultados. No comprueba demanda, disponibilidad ni límites para tu monto. No incluye cargos adicionales del medio. Revisión global cada 60 s al terminar; las cotizaciones del listado mantienen su intervalo.</p></section>`;
}
async function refreshRecommendations(){
  if(recommendationState.busy)return;recommendationState.busy=true;
  try{
    const response=await fetch('/api/recommendations?fiat='+FIAT,{cache:'no-store',signal:AbortSignal.timeout(20000)}),data=await response.json();
    if(!response.ok || !Array.isArray(data.quotes))throw new Error(data.error || 'No se pudieron comparar los medios.');
    recommendationState.data=data;recommendationState.error=null;
  }catch(error){recommendationState.error=error.message;}
  finally{recommendationState.busy=false;recommendationState.lastFetch=Date.now();render();}
}
function paymentNames(ad) {
  const details=ad.methodDetails || [];
  return [...new Set((ad.methods || []).map(id=>{
    const bank=banks.find(b=>b.match.test(id));
    return bank?.name || details.find(m=>m.identifier===id)?.name || state.methods.find(m=>m.identifier===id)?.name || id;
  }))];
}
function book(side,makerBuy) {
  const ads=side?.ads || [], username=BINANCE_USERNAME;
  const positions=myPositions(ads,username);
  const minimumInfo=minimumMatches(ads,username,MIN_FALLBACK);
  let body;
  if(state.loading&&!side) body=`<div class="loading-rows" aria-label="Consultando anuncios">${Array.from({length:5},()=>'<div class="loading-line"></div>').join('')}</div>`;
  else if(side?.error||(state.error&&!side)) body=`<div class="empty"><strong>Sin cotizaciones actuales</strong><p>${escape(side?.error||state.error)}</p></div>`;
  else if(!ads.length) body=`<div class="empty"><strong>No hay anuncios disponibles</strong><p>${marketAmount?'No se encontraron anuncios compatibles en la muestra consultada. Prueba otro monto o medio.':'Binance no devolvió anuncios para este medio de pago.'}</p></div>`;
  else body=`<div class="table-scroll"><table class="order-table"><thead><tr><th># / Anunciante</th><th>Precio ${FIAT}</th><th>Disponible / Límites</th><th>Medios de pago</th></tr></thead><tbody>${ads.map((ad,i)=>`<tr class="${positions.includes(i+1)?'my-ad':minimumInfo.positions.includes(i+1)?'same-minimum':''}">
    <td><div class="trader-info"><span class="rank">${String(i+1).padStart(2,'0')}</span><div><div class="trader-name">${ad.userNo?`<button type="button" class="advertiser-link" data-advertiser="${escape(ad.userNo)}" data-nickname="${escape(ad.nickname)}" aria-label="Ver anuncios de ${escape(ad.nickname)}">${escape(ad.nickname)}</button>`:escape(ad.nickname)}${positions.includes(i+1)?'<span class="my-badge">Tu anuncio</span>':minimumInfo.positions.includes(i+1)?'<span class="minimum-badge">Mismo mínimo</span>':ad.merchant?'<span title="Comerciante">✓</span>':''}</div><span class="connection-state ${ad.online===true?'connection-online':ad.online===false?'connection-offline':'connection-unknown'}"><i aria-hidden="true"></i>${ad.online===true?'Conectado':ad.online===false?'Desconectado':'Estado no disponible'}</span><span class="muted">${fmt(ad.completion,1)}% completado · ${fmt(ad.orders,0)} órdenes</span></div></div></td>
    <td><strong class="price">${priceFmt(ad.price)}</strong><small class="muted">por USDT</small></td>
    <td><span class="available">${fmt(ad.available)} USDT</span><span class="limits">${fmt(ad.minFiat)} – ${fmt(ad.effectiveMaxFiat ?? ad.maxFiat)} <small>${FIAT}</small></span>${ad.min!=null&&ad.max!=null?`<small class="muted">${fmt(ad.min)} – ${fmt(ad.max)} USDT</small>`:''}<small class="muted">${ad.minutes??'—'} min para pagar</small></td>
    <td class="payment-cell"><div class="payment-list">${paymentNames(ad).map(name=>`<span class="payment-chip">${escape(name)}</span>`).join('') || '<span class="muted">Medios no informados</span>'}</div><a class="offer-link" target="_blank" rel="noreferrer" href="https://c2c.binance.com/es/adv?adNo=${encodeURIComponent(ad.id)}" aria-label="Ver anuncio de ${escape(ad.nickname)}">Ver en Binance ↗</a></td>
  </tr>`).join('')}</tbody></table></div>`;
  return `<section class="book ${makerBuy?'buy':'sell'}"><div class="book-top"><div><div class="book-title"><h2>${makerBuy?'Otros compran USDT':'Otros venden USDT'}</h2></div><p>Competencia de tu anuncio de ${makerBuy?'compra':'venta'}</p></div><span class="count">${state.loading&&!side?'…':ads.length} / 10${marketAmount?' compatibles':''}</span></div><div class="book-meta"><span>${makerBuy?'Precio mayor a menor':'Precio menor a mayor'} · orden de Binance</span><span>Consulta: ${time(side?.updatedAt)}</span></div>${body}<div class="book-bottom">${!marketAmount&&ads.length>0&&ads.length<10?`Binance devolvió ${ads.length} anuncios disponibles.`:marketAmount?'Muestra filtrada: no garantiza que hayas visto todos los anuncios compatibles. Precios antes de comisiones.':'Precios por 1 USDT, antes de comisiones.'}</div></section>`;
}
function renderTabs() {
  $('banks').innerHTML=choices().map(b=>`<button type="button" class="bank-tab" id="tab-${escape(b.key)}" data-bank="${escape(b.key)}" aria-controls="content" aria-pressed="${state.selected.has(b.key)}"><span class="selection-check" aria-hidden="true">${state.selected.has(b.key)?'✓':'+'}</span>${mark(b)}${escape(b.name)}</button>`).join('');
}
function select(key,focus=false,addOnly=false) {
  if(!choices().some(b=>b.key===key))return;
  if(!addOnly && state.selected.has(key))state.selected.delete(key);else state.selected.add(key);
  state.bank=state.selected.has(key)?key:[...state.selected][0];state.error=null;renderTabs();render();
  if(focus)Array.from(document.querySelectorAll('[data-bank]')).find(b=>b.dataset.bank===key)?.focus();
  if(state.selected.has(key) && !state.groups.has(key))void refresh();
}
$('banks').addEventListener('click',event=>{const button=event.target.closest('[data-bank]');if(button&&!state.loading)select(button.dataset.bank);});
$('banks').addEventListener('keydown',event=>{
  if(state.loading||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();const list=choices(),key=event.target.closest('[data-bank]')?.dataset.bank,index=Math.max(0,list.findIndex(b=>b.key===key));
  const next=event.key==='Home'?0:event.key==='End'?list.length-1:(index+(event.key==='ArrowRight'?1:-1)+list.length)%list.length;
  Array.from(document.querySelectorAll('[data-bank]')).find(b=>b.dataset.bank===list[next].key)?.focus();
});
$('selection-defaults').addEventListener('click',()=>{if(state.loading)return;banks.forEach(b=>state.selected.add(b.key));state.bank=[...state.selected][0];renderTabs();render();void refresh();});
$('selection-clear').addEventListener('click',()=>{if(state.loading)return;state.selected.clear();state.bank=null;renderTabs();render();});
function positionHTML(group,name) {
  const username=BINANCE_USERNAME;
  $('binance-username').textContent=BINANCE_USERNAME;
  return `<div class="method-positions"><b>${escape(name)}</b><div>`+[['Compra',group?.sell],['Venta',group?.buy]].map(([name,side])=>{
    if(!side||side.error) return `<span>${name}: sin datos disponibles.</span>`;
    const found=myPositions(side.ads,username), minimumInfo=minimumMatches(side.ads,username,MIN_FALLBACK);
    return `<span>${name}: <b>${found.length?'posición en la muestra '+found.join(', '):'no aparece entre los '+side.ads.length}</b>${state.error?' (última consulta, desactualizada)':''}<small>Mínimo${minimumInfo.minima.length>1?'s':''}: ${MONEY} ${minimumInfo.minima.length?minimumInfo.minima.map(n=>fmt(n)).join(' / '):'sin referencia'}${minimumInfo.fromOwn?' (tu anuncio)':minimumInfo.minima.length?' (referencia: tu anuncio no aparece en estos 10)':' (tu anuncio no aparece en estos 10)'}</small></span>`;
  }).join('')+'</div></div>';
}
function render() {
  const selected=choices().filter(b=>state.selected.has(b.key));
  document.querySelectorAll('[data-bank]').forEach(button=>{
    const active=state.selected.has(button.dataset.bank);button.dataset.state=active?'active':'inactive';button.setAttribute('aria-pressed',String(active));button.disabled=state.loading;
  });
  $('other-method').disabled=state.loading||!state.methods.length;
  $('selection-defaults').disabled=state.loading;$('selection-clear').disabled=state.loading;
  $('content').setAttribute('aria-busy',String(state.loading));
  const refreshButton=$('refresh');if(refreshButton){refreshButton.disabled=state.loading;refreshButton.textContent=state.loading?'Consultando…':'Actualizar';}
  const timestamps=selected.flatMap(b=>{const g=state.groups.get(b.key);return [g?.buy.updatedAt,g?.sell.updatedAt].filter(Boolean);}).sort();
  $('timestamp').textContent=timestamps.length?`Última consulta ${time(timestamps.at(-1))}`:'Esperando cotizaciones';
  $('status').textContent=state.error?'Consulta parcial / fallida':state.loading?'Consultando Binance':`${selected.length} medios seleccionados · cotizaciones de Binance`;
  $('error').hidden=!state.error;$('error').innerHTML=state.error?`<div><strong>${escape(state.error)}</strong><p>Los datos anteriores del medio que falló pueden estar desactualizados.</p></div>`:'';
  const marketHTML=b=>{
    const group=state.groups.get(b.key),scenarios=group?.queryError?null:spreadScenarios(group);
    return `<section class="selected-market" aria-label="Mercado de ${escape(b.name)}"><div class="market-strip"><div class="selected-bank">${mark(b,true)}<div><h2>${escape(b.name)}</h2><span>Hasta 10 anuncios por lado · ${FIAT}${marketAmount?' · monto '+escape(marketAmount)+' '+(marketAmountUnit==='fiat'?FIAT:'USDT'):''}</span></div></div><div class="quote buy-quote"><span>Mayor precio de otros compradores</span><strong>${priceFmt(scenarios?.[0]?.buy)} <small>${FIAT}</small></strong></div><div class="quote sell-quote"><span>Menor precio de otros vendedores</span><strong>${priceFmt(scenarios?.[0]?.sell)} <small>${FIAT}</small></strong></div></div><div class="books">${book(group?.sell,true)}${book(group?.buy,false)}</div></section>`;
  };
  $('spreads-content').innerHTML=renderRecommendations()+selected.map(b=>`<section class="selected-spread"><h2>${escape(b.name)}</h2>${renderSpread(state.groups.get(b.key),b.key)}</section>`).join('');
  $('content').innerHTML=(selected.length?selected.map(marketHTML).join(''):'<div class="empty selection-empty"><strong>Selecciona uno o varios medios de pago</strong><p>Puedes marcar varios bancos arriba o agregar otros medios desde el selector.</p></div>');
  renderCalc();$('binance-username').textContent=BINANCE_USERNAME;
  $('positions').innerHTML=selected.map(b=>positionHTML(state.groups.get(b.key),b.name)).join('')||'<span>Selecciona un medio para encontrar tus anuncios.</span>';
}
function useMarketPrices(event){
  const recommended=event.target.closest('[data-recommendation]');
  if(recommended){const best=!recommendationState.data?null:recommended.dataset.recommendation==='ranked'?rankedSpreads(recommendationState.data.quotes,inputs().amount).find(q=>q.key===recommended.dataset.methodKey):recommendedSpread(recommendationState.data.quotes,inputs().amount,recommended.dataset.recommendation==='defaults');if(!best)return;$('calc-buy').value=best.buy;$('calc-sell').value=best.sell;save();render();$('calculadora')?.scrollIntoView({behavior:'smooth',block:'start'});$('calc-buy').focus({preventScroll:true});return;}
  const button=event.target.closest('[data-scenario]');if(!button)return;
  const scenario=spreadScenarios(state.groups.get(button.dataset.market || state.bank))?.find(s=>s.key===button.dataset.scenario);if(!scenario)return;
  $('calc-buy').value=scenario.buy;$('calc-sell').value=scenario.sell;save();render();$('calculadora')?.scrollIntoView({behavior:'smooth',block:'start'});$('calc-buy').focus({preventScroll:true});
}
$('content').addEventListener('click',useMarketPrices);
$('spreads-content').addEventListener('click',useMarketPrices);
fields.filter(id=>id!=='refresh-seconds').forEach(id=>$(id).addEventListener('input',()=>{save();render();}));
$('other-method').addEventListener('change',()=>{
  const id=$('other-method').value;if(!id)return;
  const fixed=banks.find(b=>b.match.test(id));
  const method=state.methods.find(m=>m.identifier===id);if(!method)return;
  if(!fixed)state.extras.set(id,{key:id,name:method.name,mark:'+',color:'#596f86'});
  select(fixed?.key || id,false,true);$('other-method').value='';
});
async function loadMethods() {
  if(state.methodsLoading)return;state.methodsLoading=true;
  try {
    const response=await fetch('/api/methods?fiat='+FIAT,{signal:AbortSignal.timeout(20000)}),data=await response.json();
    if(!response.ok||!Array.isArray(data.methods))throw new Error(data.error||'No se pudieron cargar los medios de pago.');
    state.methods=data.methods;
    $('other-method').innerHTML='<option value="">Seleccionar otro medio…</option>'+data.methods.map(m=>`<option value="${escape(m.identifier)}">${escape(m.name)}</option>`).join('');
    $('methods-note').textContent='Medios disponibles en Binance para '+FIAT+'. Cada medio que agregues se mantiene en la selección. Marca o desmarca varios medios para compararlos.';
  } catch(error){$('other-method').innerHTML='<option value="">Medios no disponibles</option>';$('methods-note').textContent=error.message+' Se reintentará con la actualización automática.';}
  state.methodsLoading=false;render();
}
async function refresh() {
  if(state.loading||!state.selected.size)return;
  const selected=choices().filter(b=>state.selected.has(b.key));
  const sequence=++refreshSequence;const amountQuery=marketAmount?'&amount='+encodeURIComponent(marketAmount)+'&amountUnit='+encodeURIComponent(marketAmountUnit):'';
  state.loading=true;state.error=null;render();
  let defaultRequest;const errors=[];
  async function load(b){
    try{
      const identifier=banks.some(f=>f.key===b.key)?state.methods.find(m=>b.match.test(m.identifier))?.identifier:b.key;
      let data;
      if(identifier){
        const response=await fetch('/api/market?fiat='+FIAT+'&method='+encodeURIComponent(identifier)+amountQuery,{cache:'no-store',signal:AbortSignal.timeout(30000)});data=await response.json();
        if(!response.ok)throw new Error(data.error||'No se pudieron consultar las cotizaciones.');
      }else{
        // Until the catalog loads, one shared request resolves all defaults.
        defaultRequest ||= fetch('/api/market?fiat='+FIAT+amountQuery,{cache:'no-store',signal:AbortSignal.timeout(30000)}).then(async response=>{const data=await response.json();if(!response.ok)throw new Error(data.error||'No se pudieron consultar las cotizaciones.');return data;});
        data=await defaultRequest;
      }
      if(!Array.isArray(data.groups))throw new Error('Binance no devolvió una lista válida.');
      const group=identifier?data.groups[0]:data.groups.find(g=>g.key===b.key);if(!group)throw new Error('Medio no disponible.');
      if(sequence!==refreshSequence)return;
      state.groups.set(b.key,{...group,key:b.key,queryError:null});
    }catch(error){if(sequence!==refreshSequence)return;const message=error.name==='TimeoutError'?'La consulta demoró demasiado.':error.message;errors.push(`${b.name}: ${message}`);
      const old=state.groups.get(b.key);state.groups.set(b.key,{...old,key:b.key,queryError:message,buy:{...old?.buy,error:message},sell:{...old?.sell,error:message}});
    }
  }
  for(let offset=0;offset<selected.length;offset+=2){if(sequence!==refreshSequence)return;await Promise.all(selected.slice(offset,offset+2).map(load));}
  if(sequence!==refreshSequence)return;state.error=errors.join(' · ')||null;state.loading=false;render();
  window.dispatchEvent(new CustomEvent("p2p-market-result",{detail:{fiat:FIAT,error:state.error,groups:[...state.groups.values()]}}));
}
$('refresh')?.addEventListener('click',()=>{if(!state.methods.length)void loadMethods();void refresh();});
let refreshTimer;
function scheduleRefresh() {
  clearInterval(refreshTimer);
  if (!$('auto').checked) return;
  const seconds=Number($('refresh-seconds').value);
  if (![3,6,10,30,60].includes(seconds)) return;
  refreshTimer=setInterval(()=>{if(document.visibilityState==='visible'){if(!state.methods.length)void loadMethods();void refresh();}},seconds*1000);
}
$('auto').addEventListener('change',scheduleRefresh);
$('refresh-seconds').addEventListener('change',()=>{save();scheduleRefresh();});
setInterval(()=>{if(document.visibilityState==='visible' && (recommendationState.data && !recommendationState.data.complete || $('auto').checked && Date.now()-recommendationState.lastFetch>=60000))void refreshRecommendations();},3000);
scheduleRefresh();
renderTabs();void loadMethods();void refresh();void refreshRecommendations();

function applyAmount(clear=false){
 const input=$('market-amount');const value=clear?'':input.value.trim();
 if(value && (!Number.isFinite(Number(value)) || Number(value)<=0 || Number(value)>1e10)){ $('market-amount-status').textContent='Indica un monto positivo válido.';return;}
 if(clear)input.value='';marketAmount=value;marketAmountUnit=$('market-amount-unit').value;
 ++refreshSequence;state.loading=false;state.groups.clear();state.error=null;
 $('market-amount-status').textContent=marketAmount?`Filtro aplicado: ${fmt(Number(marketAmount),marketAmountUnit==='USDT'?8:2)} ${marketAmountUnit==='fiat'?FIAT:'USDT'}. Límites y disponibilidad antes de comisiones.`:'Sin filtro de monto.';
 render();void refresh();
}
$('market-amount-form').addEventListener('submit',event=>{event.preventDefault();applyAmount();});
$('clear-amount').addEventListener('click',()=>applyAmount(true));
const adNumber=(n,decimals=8)=>n==null?'—':new Intl.NumberFormat('es-UY',{maximumFractionDigits:decimals}).format(n);
function profileHTML(data){
 const ads=data.ads || [];
 if(!ads.length)return '<div class="empty"><strong>Sin anuncios públicos en esta consulta</strong><p>No implica que el usuario no tenga anuncios privados o restringidos.</p></div>';
 return `<p class="advertiser-table-hint">Desliza la tabla horizontalmente para ver todas las columnas.</p><div class="table-scroll"><table class="order-table"><thead><tr><th>Operación del anunciante</th><th>Activo / moneda</th><th>Precio</th><th>Disponible / límites efectivos</th><th>Medios y condiciones</th><th>Anuncio</th></tr></thead><tbody>${ads.map(ad=>`<tr><td>${ad.tradeType==='BUY'?'Compra (tú vendes)':'Vende (tú compras)'}</td><td>${escape(ad.asset)} / ${escape(ad.fiat)}</td><td><b>${adNumber(ad.price)} ${escape(ad.fiat)}</b><small>por ${escape(ad.asset)}</small></td><td>${adNumber(ad.available)} ${escape(ad.asset)}<span class="limits">${fmt(ad.minFiat)} - ${fmt(ad.effectiveMaxFiat)} ${escape(ad.fiat)}</span>${ad.tradable===false?'<small>No operable según esta consulta</small>':''}</td><td><div class="payment-list">${paymentNames(ad).map(name=>`<span class="payment-chip">${escape(name)}</span>`).join('')}</div>${ad.remarks?`<details><summary>Condiciones del anunciante</summary><p>${escape(ad.remarks)}</p></details>`:''}</td><td><a class="offer-link" target="_blank" rel="noreferrer" href="https://c2c.binance.com/es/adv?adNo=${encodeURIComponent(ad.id)}">Ver en Binance ↗</a></td></tr>`).join('')}</tbody></table></div>`;
}
async function loadAdvertiser(userNo,nickname){
 const sequence=++advertiserSequence;advertiserUser=userNo;
 $('advertiser-title').textContent=nickname?`Anuncios de ${nickname}`:'Anuncios del anunciante';$('advertiser-summary').textContent='';$('advertiser-time').textContent='';$('advertiser-content').textContent='Consultando anuncios públicos…';$('advertiser-retry').disabled=true;
 try{
  const response=await fetch('/api/advertiser?userNo='+encodeURIComponent(userNo),{cache:'no-store',signal:AbortSignal.timeout(20000)});const data=await response.json();
  if(!response.ok)throw new Error(data.error || 'No se pudo consultar el perfil.');if(sequence!==advertiserSequence)return;
  $('advertiser-title').textContent=`Anuncios de ${data.nickname}`;$('advertiser-summary').textContent=`${data.ads.length} anuncios públicos${data.limited?' · muestra limitada':''}${data.demo?' · DEMOSTRACIÓN':''}. Compras: ${data.ads.filter(a=>a.tradeType==='BUY').length} · ventas: ${data.ads.filter(a=>a.tradeType==='SELL').length}.`;
  $('advertiser-time').textContent=`Consultado: ${new Date(data.updatedAt).toLocaleString('es-UY',{timeZone:'America/Montevideo'})}. Caché de hasta 30 segundos.`;$('advertiser-content').innerHTML=profileHTML(data);
 }catch(error){if(sequence===advertiserSequence)$('advertiser-content').textContent=error.name==='TimeoutError'?'Binance demoró demasiado. Puedes intentar de nuevo.':error.message;}
 finally{if(sequence===advertiserSequence)$('advertiser-retry').disabled=false;}
}
$('content').addEventListener('click',event=>{const button=event.target.closest('[data-advertiser]');if(!button)return;$('advertiser-dialog').showModal();void loadAdvertiser(button.dataset.advertiser,button.dataset.nickname);});
$('advertiser-close').addEventListener('click',()=>{$('advertiser-dialog').close();++advertiserSequence;});
$('advertiser-dialog').addEventListener('cancel',()=>{++advertiserSequence;});
$('advertiser-retry').addEventListener('click',()=>void loadAdvertiser(advertiserUser));
