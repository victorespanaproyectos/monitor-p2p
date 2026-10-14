import { banksFor } from './inventory-calculations.js?v=market-1.4.2';
import { OPERATOR, OPERATOR_NAME, operatorURL } from './operator.js?v=market-1.4.2';
import { dayKey, paymentMethod, chartBuckets } from './order-analytics.js?v=market-1.4.2';
const $ = id => document.getElementById(id);
const accountBanks=banksFor(OPERATOR);
$('account-key').replaceChildren(...accountBanks.filter(a=>a.active).map(a=>new Option(a.name,a.key)));
if(!accountBanks.some(a=>a.active))$('order-page-message').textContent='Todavía no tienes cuentas activas para este operador. Abre Crear Orden para agregar una cuenta desde Inventario.';
const orderCurrency=()=>accountBanks.find(a=>a.key===$('account-key').value)?.currency || (paymentMethod($('payment-method').value)==='Airtm'?'USD':'UYU');
const reportCurrency=()=>$('report-currency').value || 'UYU';
const money=(value,currency=(reportCurrency()==='ALL'?'UYU':reportCurrency()))=>new Intl.NumberFormat('es-UY',{style:'currency',currency}).format(value);
const statusLabel=value=>({pending:'Pendiente',completed:'Completada',cancelled:'Cancelada'}[value] || 'Completada');
const qty = value => new Intl.NumberFormat('es-UY',{ maximumFractionDigits:6 }).format(value);
const esc = value => String(value).replace(/[&<>"']/g, character => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[character]));
let reportCache=null,reportSequence=0;
function report(_orders,_from,_to,_withdrawals,currency='UYU'){return reportCache?.[currency] || {currency,selected:[],totals:{},methods:[],withdrawals:[],days:[]};}
async function updateReports(){const seq=++reportSequence;const url=operatorURL('/api/report')+'&from='+$('range-from').value+'&to='+$('range-to').value;const data=await request(url);if(seq!==reportSequence)return;for(const dataReport of Object.values(data.reports)){for(const day of dataReport.days)day.methods=new Map(Object.entries(day.methods));}reportCache=data.reports;}
async function reloadReport(){if(!validRange())return;try{await updateReports();render();}catch(e){$('history-status').textContent=e.message;}}
let orders = [], withdrawals=[], editing = null, busy = false;
function localDate(value = new Date()) {
  const date = new Date(value); return new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16);
}
function preview() {
  const currency=orderCurrency();
  $('price-label').textContent=`Precio (${currency} por USDT)`;
  $('amount-label').textContent=`Monto de la orden (${currency})`;
  const price=Number($('price').value),amount=Number($('amount').value);
  if(!(price>0 && amount>0)){$('preview').textContent='Ingresa el precio y monto para calcular los USDT y la comisión.';return;}
  const quantity=Math.round(amount*100)/100/price,rate=Number(orders.find(o=>o.id===editing)?.feeRate ?? window.P2P_CONTEXT.commission),fee=quantity*rate,buy=$('type').value==='buy';
  const extra=Math.round((amount*Number($('expense-percent').value)/100+Number($('expense-fixed').value)+Number.EPSILON)*100)/100;
  $('preview').innerHTML=`<div>Estado: <b>${statusLabel($('order-status').value)}</b></div><div>Cargos adicionales: <b>${money(extra,currency)}</b></div><div>${buy?'Desembolso total':'Ingreso neto'}: <b>${money(buy?amount+extra:amount-extra,currency)}</b></div><div>Importe ${currency}: <b>${money(amount,currency)}</b></div><div>USDT nominales: <b>${qty(quantity)}</b></div><div>Comisión (${rate*100} %): <b>${qty(fee)} USDT</b></div><div>${buy?'USDT recibidos netos':'USDT descontados de Binance'}: <b>${qty(quantity*(buy?1-rate:1+rate))} USDT</b></div>`;
}
function notice(message,error=false) { $('form-message').textContent=message; $('form-message').className = error ? 'negative' : 'positive'; if(!$('order-dialog').open){$('order-page-message').textContent=message;$('order-page-message').className=error?'negative':'positive';} }
function reset() {
  editing=null; $('order-form').reset(); $('date').value=localDate(); $('form-title').textContent=`Cargar una orden · ${OPERATOR_NAME}`; $('save').textContent=`Guardar orden · ${OPERATOR_NAME}`; $('cancel').hidden=true; $('existing-receipt').hidden=true; preview();
}
async function request(path, options) {
  const response = await fetch(operatorURL(path),options); const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'No se pudo completar la solicitud.'); return data;
}
function visibleOrders(selected) {
  const search=$('search').value.trim().toLowerCase(),filter=$('filter-type').value,status=$('filter-status').value;
  return selected.filter(o=>(!filter||o.type===filter)&&(!status||o.status===status)&&o.number.toLowerCase().includes(search)).sort((a,b)=>new Date(b.date)-new Date(a.date));
}
function selectedReport() {
  const currency=reportCurrency(),from=$('range-from').value,to=$('range-to').value;
  if(currency==='ALL')return {currency,selected:['UYU','USD'].flatMap(unit=>report(orders,from,to,withdrawals,unit).selected)};
  return report(orders,from,to,withdrawals,currency);
}
function renderAllAnalytics() {
  const snapshots=['UYU','USD'].map(currency=>{
    renderAnalytics(report(orders,$('range-from').value,$('range-to').value,withdrawals,currency));
    return {currency,...Object.fromEntries(['summary','gain-note','ranking-head','ranking','period-withdrawals','chart-legend','activity-chart','chart-note'].map(id=>[id,$(id).innerHTML]))};
  });
  const title=currency=>currency==='UYU'?'UYU · bancos':'USD · Airtm';
  $('summary').innerHTML=snapshots.map(item=>`<section class="currency-summary"><h3>${title(item.currency)}</h3><div class="ledger-summary">${item.summary}</div></section>`).join('');
  $('gain-note').className='gain-note';
  $('gain-note').textContent='Los totales y las ganancias se calculan por separado en UYU y USD. No se suman monedas ni se convierten costos entre ellas. Una venta sin compras previas de la misma moneda puede mostrar ganancia parcial; las órdenes antiguas de Airtm requieren revisión.';
  $('ranking-head').innerHTML='';
  $('ranking').innerHTML=snapshots.map(item=>`<tr><td colspan="6"><h3>${title(item.currency)}</h3><div class="table-scroll"><table class="ranking-table"><thead>${item['ranking-head']}</thead><tbody>${item.ranking}</tbody></table></div></td></tr>`).join('');
  $('period-withdrawals').innerHTML=snapshots.map(item=>`<section><h3>${title(item.currency)}</h3>${item['period-withdrawals']}</section>`).join('');
  $('chart-legend').innerHTML='';
  $('activity-chart').innerHTML=snapshots.map(item=>`<section><h3>${title(item.currency)}</h3><div class="chart-legend">${item['chart-legend']}</div><div class="chart-scroll">${item['activity-chart']}</div><p class="tool-note">${item['chart-note']}</p></section>`).join('');
  $('chart-note').textContent='Gráficas separadas por moneda; cada una usa su propia escala.';
  $('range-label').textContent=`${$('range-from').value || 'Desde la primera orden'} → ${$('range-to').value || 'hasta la última orden'} · ${selectedReport().selected.length} órdenes del período · todas las monedas. Totales separados en UYU y USD.`;
}
function validRange() {
  const invalid=$('range-from').value && $('range-to').value && $('range-from').value>$('range-to').value;
  $('range-error').hidden=!invalid;
  for(const id of ['summary','gain-note','analytics-details','period-withdrawals','chart-panel'])$(id).hidden=Boolean(invalid);
  $('csv').disabled=Boolean(invalid);
  if(invalid){$('rows').innerHTML='';$('history-status').textContent='Corrige el rango de fechas para ver las órdenes.';}
  return !invalid;
}
const palette=['#2563a8','#dd7c20','#237b60','#9651a1','#ba405b','#657c23','#25828c','#715dca','#906448','#59677a','#bc9b17','#3487bf'];
function methodColors() {
  const names=[...new Set(orders.map(o=>paymentMethod(o.paymentMethod).normalize('NFC').toLocaleLowerCase('es-UY')))].sort();
  return new Map(names.map((name,index)=>[name,palette[index] || `hsl(${index*137.5%360} 55% 40%)`]));
}
function chart(data,colors) {
  const {buckets,unit}=chartBuckets(data,$('range-from').value,$('range-to').value);
  $('chart-legend').innerHTML=data.methods.map(method=>`<span><i style="background:${colors.get(method.key)}"></i>${esc(method.name)}</span>`).join('');
  if(!buckets.length){$('activity-chart').innerHTML='<p class="chart-empty">No hay operaciones en este rango de fechas.</p>';$('chart-note').textContent='';return;}
  const width=Math.max(720,buckets.length*46+90),height=315,left=76,top=25,bottom=55,plotHeight=height-top-bottom,step=(width-left-20)/buckets.length;
  const peak=Math.max(...buckets.flatMap(bucket=>[bucket.buy,bucket.sell]));
  const magnitude=10**Math.floor(Math.log10(peak || 1)),max=Math.ceil(peak/magnitude)*magnitude || 1;
  let svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" style="min-width:${width}px" role="img" aria-labelledby="chart-title-${data.currency} chart-description-${data.currency}"><title id="chart-title-${data.currency}">Volumen bruto de compras y ventas en ${data.currency} por medio de pago</title><desc id="chart-description-${data.currency}">Barras agrupadas por ${unit}. C significa compra y V venta. El ranking superior contiene los importes exactos por medio de pago.</desc>`;
  for(let tick=0;tick<=4;tick++){
    const value=max*tick/4,y=top+plotHeight*(1-value/max);
    svg+=`<line x1="${left}" y1="${y}" x2="${width-10}" y2="${y}" stroke="var(--line)"/><text x="${left-8}" y="${y+4}" text-anchor="end" font-size="11" fill="var(--muted)">${esc(new Intl.NumberFormat('es-UY',{notation:'compact',maximumFractionDigits:1}).format(value))}</text>`;
  }
  const barWidth=Math.min(15,step*.27),ordered=[...data.methods].sort((a,b)=>a.name.localeCompare(b.name));
  buckets.forEach((bucket,index)=>{
    const center=left+(index+.5)*step;
    ['buy','sell'].forEach((side,sideIndex)=>{
      const x=center+(sideIndex===0?-barWidth-2:2);let stacked=0;
      for(const method of ordered){
        const amount=bucket.methods.get(method.key)?.[side] || 0;if(!amount)continue;
        const barHeight=amount/max*plotHeight,y=top+plotHeight-(stacked+amount)/max*plotHeight;
        const label=`${bucket.label} · ${side==='buy'?'Compra':'Venta'} · ${method.name}: ${money(amount,data.currency)}`;
        svg+=`<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${colors.get(method.key)}" tabindex="0" role="img" aria-label="${esc(label)}"><title>${esc(label)}</title></rect>`;
        stacked+=amount;
      }
      svg+=`<text x="${x+barWidth/2}" y="${top+plotHeight+14}" text-anchor="middle" font-size="10" fill="var(--muted)">${sideIndex===0?'C':'V'}</text>`;
    });
    if(index%Math.max(1,Math.ceil(buckets.length/12))===0||index===buckets.length-1){
      const label=unit==='mes'?bucket.label.slice(5)+'/'+bucket.label.slice(0,4):unit==='año'?bucket.label:bucket.label.slice(8)+'/'+bucket.label.slice(5,7);
      svg+=`<text x="${center}" y="${height-12}" text-anchor="middle" font-size="11" fill="var(--muted)">${esc(label)}</text>`;
    }
  });
  $('activity-chart').innerHTML=svg+'</svg>';
  $('chart-note').textContent=`Importes brutos antes de comisión · agrupación por ${unit}${unit==='semana'?' (bloques de 7 días desde el inicio del rango)':''}. Desliza horizontalmente para ver todo el período.`;
}
function renderAnalytics(data) {
  const t=data.totals,colors=methodColors(),formatMoney=value=>money(value,data.currency);
  $('ranking-head').innerHTML=`<tr><th>Medio / participación</th><th>Compras ${data.currency}</th><th>Ventas ${data.currency}</th><th>Operado ${data.currency}</th><th>Comisiones USDT</th><th>Ganancia ${data.currency}</th></tr>`;
  const breakdown=side=>data.methods.filter(method=>method[side]>0).map(method=>`<li><span>${esc(method.name)}</span><b>${formatMoney(method[side])}</b></li>`).join('');
  $('range-label').textContent=`${$('range-from').value || 'Desde la primera orden'} → ${$('range-to').value || 'hasta la última orden'} · ${t.count} órdenes completadas del período. Pendientes: ${data.statusCounts?.pending || 0} · canceladas: ${data.statusCounts?.cancelled || 0}. La gráfica y los totales incluyen solo completadas.`;
  $('summary').innerHTML=`<div class="summary-item"><span>Compras · monto bruto</span><strong>${formatMoney(t.buy)}</strong><small>${qty(t.buyQuantity)} USDT · importe pagado: ${formatMoney(t.buyTotal)}</small><ul class="method-breakdown">${breakdown('buy')}</ul></div><div class="summary-item"><span>Ventas · monto bruto</span><strong>${formatMoney(t.sell)}</strong><small>${qty(t.sellQuantity)} USDT · importe cobrado: ${formatMoney(t.sellTotal)}</small><ul class="method-breakdown">${breakdown('sell')}</ul></div><div class="summary-item"><span>Volumen operado · compra + venta</span><strong>${formatMoney(t.volume)}</strong><small>Comisiones de las órdenes del período: ${qty(t.fees)} USDT</small><small>Gastos adicionales: ${formatMoney(t.expenses || 0)}</small><small>Flujo bancario: ${formatMoney(t.cash)}</small></div><div class="summary-item"><span>${t.missing>1e-9?'Ganancia parcial':'Ganancia realizada estimada'} · FIFO</span><strong class="${t.profit<0?'negative':'positive'}">${formatMoney(t.profit)}</strong><small>${qty(t.matched)} USDT entregados con costo registrado, incluida comisión</small><small>${t.missing>1e-9?`${qty(t.missing)} USDT entregados sin costo registrado`:'Comisiones descontadas del saldo USDT'}</small></div><div class="summary-item"><span>10 % de las ganancias${t.missing>1e-9?' · parcial':''}</span><strong>${formatMoney(t.reserve)}</strong><small>10 % de la ganancia positiva del período; cero si hay pérdida.</small></div><div class="summary-item"><span>Retiros del período</span><strong>${formatMoney(t.withdrawals)}</strong><small>Ganancia menos retiros (referencia): ${formatMoney(t.afterWithdrawals)}</small><small>Flujo bancario tras retiros: ${formatMoney(t.cashAfterWithdrawals)}</small></div>`;
  $('gain-note').className=t.missing>1e-9?'gain-note incomplete-gain':'gain-note';
  $('gain-note').textContent=(t.missing>1e-9?`Resultado parcial: faltan compras anteriores para ${qty(t.missing)} USDT vendidos en el período. Esas unidades se excluyen de la ganancia, no se les asigna costo cero. Registra las compras que faltan para completar el cálculo. `:'')+`FIFO en ${data.currency}: las compras aportan USDT netos de su comisión; las ventas consumen nominales más su comisión. Los cargos de compra se incorporan al costo de las unidades recibidas; los de venta reducen el ingreso. No se restan dos veces. Se usan compras anteriores de la misma moneda, incluso fuera del período. No se mezclan costos UYU y USD: una venta financiada con compras en otra moneda puede quedar parcial. Las órdenes antiguas de Airtm sin moneda requieren revisión y se excluyen hasta corregirlas.`;
  $('ranking').innerHTML=data.methods.length?data.methods.map((method,index)=>`<tr><td><div class="ranking-name"><i style="background:${colors.get(method.key)}"></i><b>${index+1}. ${esc(method.name)}</b></div><small>${method.count} órdenes · ${qty(t.volume?method.volume/t.volume*100:0)} %</small><div class="rank-track"><span style="width:${t.volume?method.volume/t.volume*100:0}%;background:${colors.get(method.key)}"></span></div></td><td>${formatMoney(method.buy)}<small>Pagado: ${formatMoney(method.buyTotal)}</small></td><td>${formatMoney(method.sell)}<small>Cobrado: ${formatMoney(method.sellTotal)}</small></td><td><b>${formatMoney(method.volume)}</b></td><td>${qty(method.fees)} USDT</td><td class="${method.profit<0?'negative':'positive'}">${formatMoney(method.profit)}${method.missing>1e-9?`<small>Parcial · faltan ${qty(method.missing)} USDT</small>`:''}</td></tr>`).join(''):`<tr><td colspan="6" class="ledger-empty">No hay medios de pago para mostrar.</td></tr>`;
  $('period-withdrawals').innerHTML=data.withdrawals.length?`<div class="table-scroll"><table class="ranking-table"><thead><tr><th>Fecha</th><th>Cuenta</th><th>Monto ${data.currency}</th><th>Descripción</th></tr></thead><tbody>${data.withdrawals.map(record=>`<tr><td>${esc(new Date(record.date).toLocaleString('es-UY',{timeZone:'America/Montevideo'}))}</td><td>${esc(accountBanks.find(bank=>bank.key===record.accountKey)?.name || record.accountKey)}</td><td>${formatMoney(record.amountCents/100)}</td><td>${esc(record.note || '—')}</td></tr>`).join('')}</tbody></table></div>`:'<p class="tool-note">No hay retiros en este período.</p>';
  chart(data,colors);
}
function render() {
  if(!validRange())return;
  const data=selectedReport();if(data.currency==='ALL')renderAllAnalytics();else renderAnalytics(data);
  const legacy=orders.filter(o=>o.legacyCurrencyReview && (!$('range-from').value || dayKey(o.date)>=$('range-from').value) && (!$('range-to').value || dayKey(o.date)<=$('range-to').value));
  const visible=visibleOrders([...data.selected,...legacy]);
  $('rows').innerHTML = visible.length ? visible.map(o=>`<tr><td>${esc(new Date(o.date).toLocaleString('es-UY',{timeZone:'America/Montevideo'}))}<small>Orden ${esc(o.number)}</small></td><td class="ledger-type ${o.type==='buy'?'positive':''}">${o.type==='buy'?'Compra':'Venta'}<small class="status-badge status-${esc(o.status)}">${statusLabel(o.status)}</small><small>${esc(paymentMethod(o.paymentMethod))}${o.legacyCurrencyReview?' · Revisar moneda antigua':''}</small></td><td>${qty(o.price)} ${o.currency}</td><td>${money(o.amount,o.currency)}<small>Gastos: ${money(o.expenses || 0,o.currency)}</small><small>${o.status==='completed'?'Efectivo neto':'Estimado'}: ${money(o.cashTotal ?? o.amount,o.currency)}</small></td><td>${qty(o.quantity)}</td><td>${qty(o.commission)} USDT</td><td><b>${qty(o.netQuantity)} USDT</b><small>${o.status==='cancelled'?'Sin efecto en saldo':o.status==='pending'?'Estimado · aún no aplicado':o.type==='buy'?'Recibidos netos':'Descontados de Binance'}</small></td><td>${o.receipt?`<a href="${operatorURL(`/api/orders/${o.id}/receipt`)}" target="_blank" rel="noopener" title="${esc(o.receipt.name)}">Ver comprobante ↗</a>`:'<small>Sin comprobante</small>'}<div class="row-actions"><button type="button" data-edit="${o.id}">Editar</button><button type="button" class="delete-order" data-delete="${o.id}">Eliminar</button></div></td></tr>`).join('') : '<tr><td colspan="8" class="ledger-empty">No hay órdenes para mostrar.</td></tr>';
  $('history-status').textContent=`${visible.length} órdenes visibles · ${data.selected.length} en ${data.currency==='ALL'?'todas las monedas':data.currency} del período · ${orders.length} en todo el historial.${legacy.length?` ${legacy.length} órdenes antiguas de Airtm requieren revisión.`:''} Más recientes primero.`;
  const customs=[...new Set(orders.map(o=>paymentMethod(o.paymentMethod)).concat(['Santander','Itaú','OCA Blue','MercadoPago','BROU','Prex','Airtm']))].sort();
  $('payment-options').innerHTML=customs.map(name=>`<option value="${esc(name)}"></option>`).join('');
}
async function refresh() {
  $('reload').disabled=true;
  try { const data=await request('/api/orders'); if(data.operator!==OPERATOR)throw new Error('La respuesta no corresponde al operador activo.'); orders=data.orders;withdrawals=data.withdrawals || [];await updateReports(); $('history-status').classList.remove('negative'); render(); }
  catch (error) { $('history-status').textContent=error.message; $('history-status').classList.add('negative'); throw error; }
  finally { $('reload').disabled=false; }
}
async function attachment(file) {
  if (file.size>10*1024*1024) throw new Error('El comprobante debe pesar como máximo 10 MB.');
  const data = await new Promise((resolve,reject)=>{ const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('No se pudo leer el comprobante.'));reader.readAsDataURL(file); });
  return { name:file.name, data };
}
$('order-form').addEventListener('submit',async event=>{
  event.preventDefault(); if(busy)return;if(!$('account-key').value){accountNotice();return;} busy=true; $('save').disabled=true; $('cancel').disabled=true; lockOperator(true); notice('Guardando…');
  let saved=false;
  try {
    const input={ operator:OPERATOR,type:$('type').value,status:$('order-status').value,expenseRate:(Number($('expense-percent').value)/100).toFixed(6),expenseFixed:Number($('expense-fixed').value),expenseNote:$('expense-note').value.trim(), date:new Date($('date').value).toISOString(), number:$('number').value.trim(),paymentMethod:$('payment-method').value.trim(),accountKey:$('account-key').value,currency:orderCurrency(),price:Number($('price').value), amount:Number($('amount').value), removeReceipt:$('remove-receipt').checked };
    if($('receipt').files[0])input.receipt=await attachment($('receipt').files[0]);
    await request(editing?`/api/orders/${editing}`:'/api/orders',{ method:editing?'PUT':'POST', headers:{ 'Content-Type':'application/json' },body:JSON.stringify(input) });
    saved=true; reset(); $('order-dialog').close(); $('order-page-message').textContent='Orden guardada.'; notice('Orden guardada.'); await refresh();
    if (!selectedReport().selected.some(order=>order.number===input.number)) notice('Orden guardada. Revisa la moneda del informe y usa Todo el historial para verla.');
  } catch(error){ notice(saved?`La orden se guardó, pero no se pudo actualizar el historial: ${error.message}`:error.message,true); }
  finally{busy=false;$('save').disabled=false;$('cancel').disabled=false; lockOperator(false);}
});
$('rows').addEventListener('click',async event=>{
  const button=event.target.closest('button'); if(!button||busy)return;
  const order=orders.find(o=>o.id===(button.dataset.edit||button.dataset.delete));if(!order)return;
  if(button.dataset.edit){
    editing=order.id;if(![...$('account-key').options].some(a=>a.value===order.accountKey)){const a=accountBanks.find(a=>a.key===order.accountKey);if(a)$('account-key').add(new Option(a.name+' (archivada)',a.key));} $('order-status').value=order.status || 'completed'; $('expense-percent').value=Number(order.expenseRate || 0)*100; $('expense-fixed').value=order.expenseFixed || 0; $('expense-note').value=order.expenseNote || ''; $('type').value=order.type; $('date').value=localDate(order.date); $('number').value=order.number; $('payment-method').value=paymentMethod(order.paymentMethod); $('account-key').value=order.accountKey || ''; $('price').value=order.price; $('amount').value=order.amount; $('receipt').value=''; $('remove-receipt').checked=false;
    $('form-title').textContent=`Editar orden · ${OPERATOR_NAME}`;$('save').textContent='Guardar cambios';$('cancel').hidden=false;$('existing-receipt').hidden=!order.receipt;
    if(order.receipt){$('current-receipt').href=operatorURL(`/api/orders/${order.id}/receipt`);$('current-receipt').textContent=`Ver ${order.receipt.name} ↗`;}
    accountNotice();notice(order.legacyCurrencyReview?'Orden antigua: confirma que el precio y monto sean USD y selecciona la cuenta Airtm antes de guardar.':''); preview(); $('order-dialog').showModal(); $('number').focus(); return;
  }
  if(!confirm(`¿Eliminar la orden ${order.number} y su comprobante?`))return;
  busy=true;button.disabled=true;
  try { await request(`/api/orders/${order.id}`,{method:'DELETE'});if(editing===order.id)reset();notice('Orden eliminada.');await refresh(); }
  catch(error){notice(error.message,true);}finally{busy=false;button.disabled=false;}
});
$('cancel').addEventListener('click',()=>{reset();notice('');$('order-dialog').close();});
let checkingAccounts=false;
function accountNotice(){
 const canSave=Boolean($('account-key').value);$('save').disabled=busy || !canSave;
 if(!canSave)$('form-message').innerHTML=`No hay una cuenta activa seleccionada para este operador. <a href="${operatorURL('/inventario')}" target="_blank" rel="noopener">Agregar cuenta en Inventario ↗</a>. Después vuelve a esta pestaña; se actualizará la lista.`;
 else if($('form-message').querySelector('a'))notice('');
}
async function syncAccounts(){
 const data=await request('/api/accounts',{signal:AbortSignal.timeout(15000)});
 if(!Array.isArray(data.accounts))throw new Error('No se pudieron cargar las cuentas.');
 const selected=$('account-key').value,existing=orders.find(o=>o.id===editing)?.accountKey;
 accountBanks.splice(0,accountBanks.length,...data.accounts);
 const choices=accountBanks.filter(a=>a.active || a.key===existing);
 $('account-key').replaceChildren(...choices.map(a=>new Option(a.name+(a.active?'':' (archivada)'),a.key)));
 if(choices.some(a=>a.key===(existing || selected)))$('account-key').value=existing || selected;
 accountNotice();preview();
}
$('create-order').addEventListener('click',async()=>{
 if(busy || checkingAccounts)return;checkingAccounts=true;
 const button=$('create-order');button.disabled=true;button.setAttribute('aria-busy','true');button.textContent='Comprobando cuentas…';
 try{reset();notice('');await syncAccounts();$('order-dialog').showModal();}
 catch(e){notice('No se pudieron comprobar las cuentas: '+e.message,true);}
 finally{checkingAccounts=false;button.disabled=false;button.removeAttribute('aria-busy');button.textContent='Crear Orden';}
});
window.addEventListener('focus',()=>{if(!busy&&!checkingAccounts)void syncAccounts().catch(e=>{if($('order-dialog').open)notice('No se pudieron actualizar las cuentas: '+e.message,true);});});
$('account-key').addEventListener('change',accountNotice);
$('order-close').addEventListener('click',()=>{if(!busy)$('order-dialog').close();});
$('order-dialog').addEventListener('cancel',event=>{if(busy)event.preventDefault();});
$('order-dialog').addEventListener('click',event=>{if(event.target===$('order-dialog') && !busy){const r=$('order-dialog').getBoundingClientRect();if(event.clientX<r.left || event.clientX>r.right || event.clientY<r.top || event.clientY>r.bottom)$('order-dialog').close();}});
for(const id of ['type','price','amount','payment-method','account-key','order-status','expense-percent','expense-fixed'])$(id).addEventListener('input',preview);
for(const id of ['search','filter-type','filter-status'])$(id).addEventListener('input',render);
$('reload').addEventListener('click',()=>refresh().catch(()=>{}));
$('csv').addEventListener('click',()=>{
  if(!validRange())return;
  const selected=visibleOrders(selectedReport().selected);
  const cell=value=>`"${String(value).replace(/^[=+\-@\t\r]/,"'$&").replace(/"/g,'""')}"`;
  const values=[['Fecha','Número de orden','Operación','Medio de pago','Moneda','Precio por USDT','Monto fiat','USDT nominales','Comisión USDT','USDT recibidos o descontados','Comprobante','Estado','Gastos adicionales','Efectivo neto','Descripción del gasto'],...selected.map(o=>[new Date(o.date).toISOString(),o.number,o.type==='buy'?'Compra':'Venta',paymentMethod(o.paymentMethod),o.currency,o.price,o.amount,o.quantity,o.commission,o.netQuantity,o.receipt?.name||'',statusLabel(o.status),o.expenses || 0,o.cashTotal ?? o.amount,o.expenseNote || ''])];
  const blob=new Blob(['\uFEFF'+values.map(row=>row.map(cell).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`ordenes-${OPERATOR}-p2p.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
function monthRange(){const today=dayKey(new Date());$('range-from').value=today.slice(0,7)+'-01';$('range-to').value=today;}
for(const id of ['range-from','range-to','report-currency'])$(id).addEventListener('change',()=>void reloadReport());
$('this-month').addEventListener('click',()=>{monthRange();void reloadReport();});
$('all-dates').addEventListener('click',()=>{$('range-from').value='';$('range-to').value='';void reloadReport();});
monthRange();reset();refresh().catch(()=>{});

function lockOperator(disabled){const select=$('operator-select');if(select)select.disabled=disabled;}
