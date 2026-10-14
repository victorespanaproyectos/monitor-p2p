const escapeName=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const $=id=>document.getElementById(id),money=value=>new Intl.NumberFormat('es-UY',{style:'currency',currency:'UYU'}).format(value);
let busy=false,timer;
async function refresh(){
  if(busy)return;busy=true;
  try{const response=await fetch('/api/profits',{cache:'no-store',signal:AbortSignal.timeout(10000)}),data=await response.json();if(!response.ok)throw new Error(data.error || 'No se pudo consultar la ganancia.');
    $('combined-total').textContent=money(data.total);$('combined-total').className=data.total<0?'negative':'positive';
    if($('combined-reserve-total')){
      $('combined-reserve-total').textContent=money(Math.max(0,data.total)*0.1);
      $('combined-reserve-note').textContent=(data.missing>1e-9?'Estimación parcial: faltan compras con costo registrado. ':'')+'10 % de la ganancia total positiva en UYU; cero si hay pérdida. USD/Airtm se informa por separado.';
    }
    $('combined-details').innerHTML=data.operators.map(operator=>`<div><span>${escapeName(operator.name)}</span><b class="${operator.profit<0?'negative':'positive'}">${money(operator.profit)}${operator.missing>1e-9?' *':''}</b></div>`).join('');
    $('combined-note').textContent=(data.missing>1e-9?'* Ganancia UYU parcial. ':'Ganancia UYU · historial completo. ')+`USD/Airtm: ${new Intl.NumberFormat('es-UY',{style:'currency',currency:'USD'}).format(data.totalUSD || 0)}${data.operators.some(o=>o.missingUSD>1e-9)?' (parcial)':''}. Informes por moneda.`;
    const inventoryTotal=$('combined-inventory-total');
    if(inventoryTotal){
      inventoryTotal.textContent=data.inventoryTotal===null?'Pendiente':money(data.inventoryTotal);
      inventoryTotal.className=data.inventoryTotal<0?'negative':'';
      if($('combined-previous-total')){
        const info=data.inventoryComparison,previous=info?.previous;
        $('combined-previous-date').textContent=`Día anterior${info?.yesterday?' · '+info.yesterday.split('-').reverse().join('/'):''}`;
        $('combined-previous-total').textContent=!previous?'Sin registro':previous.total===null?'Pendiente':money(previous.total);
        $('combined-previous-time').textContent=previous?`Último saldo registrado: ${new Date(previous.updatedAt).toLocaleTimeString('es-UY',{timeZone:'America/Montevideo'})}`:'Se guarda automáticamente mientras el servidor está abierto.';
        const change=$('combined-inventory-change');
        change.className='inventory-change';
        change.textContent=info?.change==null?'Variación del inventario: sin comparación':`Variación del inventario: ${info.change>0?'↑ + ':info.change<0?'↓ ':''}${money(info.change)}${info.percent===null?'':' · '+(info.percent>0?'+':'')+new Intl.NumberFormat('es-UY',{maximumFractionDigits:2}).format(info.percent)+' %'} respecto a ayer`;
      }

      if($('combined-withdrawals-total')){
        const info=data.inventoryComparison,amount=info?.withdrawalsEquivalent,adjusted=info?.adjustedChange;
        $('combined-withdrawals-total').textContent=amount==null?info?.previous?'Pendiente':'Sin registro':money(amount);
        const usd=info?.withdrawalsUSD || 0;
        $('combined-withdrawals-note').textContent=(usd?`Airtm: ${new Intl.NumberFormat('es-UY',{style:'currency',currency:'USD'}).format(usd)} · equivalente UYU estimado con los promedios del inventario. `:'')+(info?.withdrawalBasis==='snapshots'?'Retiros netos, incluidas correcciones y eliminaciones desde el saldo guardado.':info?.previous?'Según las fechas de los retiros posteriores al saldo guardado.':'Necesita un saldo del día anterior.');
        const label=$('combined-adjusted-change');label.className='inventory-change'+(adjusted>0?' change-up':adjusted<0?' change-down':'');
        label.textContent=adjusted==null?'Variación ajustada por retiros: pendiente':`Variación ajustada por retiros: ${adjusted>0?'+ ':''}${money(adjusted)}`;
      }
      $('combined-inventory-details').innerHTML=data.operators.map(operator=>`<div><span>${escapeName(operator.name)}</span><b>${operator.inventoryTotal===null?'Pendiente':money(operator.inventoryTotal)}</b></div>`).join('');
      $('combined-inventory-note').textContent=(data.inventoryTotal===null?'Faltan precios promedio para convertir saldos de algún operador. ':'Los retiros reducen el inventario. La variación ajustada no equivale necesariamente a ganancia. ')+(data.operators.some(o=>o.inventoryNeedsReview)?'Hay saldos negativos: revisa el inventario. ':'')+`Actualizado: ${new Date(data.updatedAt).toLocaleTimeString('es-UY',{timeZone:'America/Montevideo'})}.`;
    }
  }catch(error){if($('combined-reserve-note'))$('combined-reserve-note').textContent='10 % no disponible o desactualizado. '+error.message;$('combined-note').textContent='Ganancias no disponibles o desactualizadas. '+error.message;if($('combined-inventory-note'))$('combined-inventory-note').textContent='Inventario no disponible o desactualizado. '+error.message;}
  finally{busy=false;}
}
function schedule(){clearInterval(timer);if($('auto').checked)timer=setInterval(()=>{if(document.visibilityState==='visible')void refresh();},Number($('refresh-seconds').value)*1000);}
$('auto').addEventListener('change',schedule);$('refresh-seconds').addEventListener('change',schedule);
window.addEventListener('focus',()=>void refresh());
schedule();void refresh();
