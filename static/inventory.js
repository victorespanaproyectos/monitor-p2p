import { OPERATOR,OPERATOR_NAME,operatorURL } from './operator.js?v=market-1.4.2';
import { banksFor } from './inventory-calculations.js?v=market-1.4.2';
const $=id=>document.getElementById(id),allBanks=banksFor(OPERATOR),banks=allBanks.filter(a=>a.active);
const money=value=>value===null?'Pendiente':new Intl.NumberFormat('es-UY',{style:'currency',currency:'UYU'}).format(value);
const currencyMoney=(value,currency='UYU')=>value===null?'Pendiente':new Intl.NumberFormat('es-UY',{style:'currency',currency}).format(value);
const price=value=>new Intl.NumberFormat('es-UY',{style:'currency',currency:'UYU',maximumFractionDigits:6}).format(value);
const qty=value=>value===null?'Pendiente':new Intl.NumberFormat('es-UY',{maximumFractionDigits:6}).format(value);
let reconciliationRecords=[];
let serverInventory=null,serverValues=null,averages=null,revision=null,withdrawals=[],withdrawalEditing=null,dirty=false,loading=false,saving=false;
const esc=value=>String(value).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
$('withdrawal-account').innerHTML=banks.map(bank=>`<option value="${bank.key}">${esc(bank.name)}</option>`).join('');
$('bank-inputs').innerHTML=banks.map(bank=>`<div class="inventory-account-entry"><label>${esc(bank.name)} (${bank.currency || 'UYU'})<input id="balance-${bank.key}" type="number" min="0" max="10000000000" step="0.01" required inputmode="decimal" value="0"></label><button type="button" class="account-hide" data-archive-account="${esc(bank.key)}">Quitar del inventario</button></div>`).join('');
$('account-empty').hidden=banks.length>0;
$('create-movement').disabled=banks.length===0;
if(!banks.length)$('create-movement').title='Primero agrega una cuenta en Inventario.';
$('archived-accounts').innerHTML=allBanks.some(a=>!a.active)?`<details><summary>Cuentas quitadas</summary>${allBanks.filter(a=>!a.active).map(a=>`<p>${esc(a.name)} (${a.currency}) <button type="button" class="secondary-button" data-activate-account="${esc(a.key)}">Volver a usar</button></p>`).join('')}</details>`:'';
$('inventory-save').textContent=`Conciliar saldos · ${esc(OPERATOR_NAME)}`;
function draft(){
  const number=id=>{const input=$(id);if(!input.value || !Number.isFinite(Number(input.value)) || Number(input.value)<0)throw new Error('Completa todos los saldos con importes no negativos.');return Number(input.value);};
  return {accounts:Object.fromEntries(banks.map(bank=>[bank.key,number(`balance-${bank.key}`)])),binance:number('binance')};
}
function fill(inventory){for(const bank of banks)$(`balance-${bank.key}`).value=inventory.accounts[bank.key] || 0;$('binance').value=inventory.binance ?? Math.round(((inventory.funds || 0)+(inventory.earn || 0))*1e6)/1e6;
  $('inventory-saved-at').textContent=inventory.updatedAt?`Saldo base corregido: ${new Date(inventory.updatedAt).toLocaleString('es-UY',{timeZone:'America/Montevideo'})}.`:'Todavía no hay un inventario guardado para este operador.';
}
function renderDifferences(){
  if(!serverInventory)return;
  try{const input=draft();$('reconcile-diff').innerHTML=banks.map(a=>{const delta=input.accounts[a.key]-serverInventory.accounts[a.key];return `<div>${esc(a.name)}: diferencia <b>${currencyMoney(delta,a.currency)}</b></div>`;}).join('')+`<div>Binance: diferencia <b>${qty(input.binance-serverInventory.binance)} USDT</b></div>`;}catch{$('reconcile-diff').textContent='Completa los saldos reales para comparar.';}
}
function render(){
  if(!averages)return;
  renderDifferences();
  const inv=serverInventory;
  $('reservation-summary').innerHTML=`<p>${inv.pendingCount} órdenes pendientes.</p><div class="table-scroll"><table class="ranking-table"><thead><tr><th>Cuenta / moneda</th><th>Total</th><th>Reservado</th><th>Disponible</th></tr></thead><tbody>${banks.map(a=>`<tr><td>${esc(a.name)} (${a.currency})</td><td>${currencyMoney(inv.accounts[a.key],a.currency)}</td><td>${currencyMoney(inv.reservedAccounts[a.key],a.currency)}</td><td>${currencyMoney(inv.availableAccounts[a.key],a.currency)}</td></tr>`).join('')}<tr><td>Binance (USDT)</td><td>${qty(inv.binance)}</td><td>${qty(inv.reservedBinance)}</td><td>${qty(inv.availableBinance)}</td></tr></tbody></table></div>`;
  $('reconcile-history').innerHTML=reconciliationRecords.length?reconciliationRecords.map(r=>`<details class="reconciliation-entry"><summary>${esc(new Date(r.date).toLocaleString('es-UY'))} · ${esc(r.user)} · ${esc(r.detail.reason || 'Conciliación anterior')}</summary><p>${esc(r.detail.reason || 'Sin motivo en esta versión anterior')}</p>${Object.entries(r.detail.differences || {}).map(([key,value])=>`<p>${esc(banks.find(a=>a.key===key)?.name || key)}: ${currencyMoney(value,banks.find(a=>a.key===key)?.currency)}</p>`).join('')}<p>Binance: ${qty(r.detail.binanceDifference || 0)} USDT</p></details>`).join(''):'<p class="tool-note">No hay conciliaciones registradas.</p>';
  $('inventory-averages').innerHTML=['buy','sell'].map(type=>{const data=averages[type];return `<div class="inventory-average"><span>Promedio de ${type==='buy'?'compra':'venta'}</span><strong>${data.price===null?'Sin registros':price(data.price)}</strong><small>UYU por USDT · ${data.count} órdenes · ${qty(data.quantity)} USDT</small></div>`;}).join('');
  if(averages.usd)$('inventory-averages').innerHTML+=['buy','sell'].map(type=>{const data=averages.usd[type];return `<div class="inventory-average"><span>Airtm · promedio de ${type==='buy'?'compra':'venta'}</span><strong>${data.price===null?'Sin registros':new Intl.NumberFormat('es-UY',{style:'currency',currency:'USD',maximumFractionDigits:6}).format(data.price)}</strong><small>USD por USDT · ${data.count} órdenes</small></div>`;}).join('');
  const inventory=serverInventory;
  const values=serverValues;
  $('inventory-values').innerHTML=`<div class="summary-item"><span>Total en cuentas UYU</span><strong>${money(values.bankTotal)}</strong><small>Saldos bancarios en pesos de ${esc(OPERATOR_NAME)}</small></div><div class="summary-item"><span>USDT que puedes comprar · netos</span><strong>${qty(values.availableBuyNet)}${values.availableBuyNet===null?'':' USDT'}</strong><small>${values.availableBuyNet===null?'Faltan compras completadas para calcular un promedio.':'Capacidad disponible tras reservas, con comisión Binance. No incluye cargos adicionales de la billetera.'}</small></div><div class="summary-item"><span>Saldo total en Binance</span><strong>${qty(values.binanceTotal)} USDT</strong><small>Saldo único en USDT</small></div><div class="summary-item"><span>Valor neto de Binance en UYU</span><strong>${money(values.binancePesos)}</strong><small>${values.binancePesos===null?'Faltan ventas registradas para calcular un promedio.':`Comisión estimada al convertir: ${qty(values.binanceFee)} USDT`}</small></div>${banks.some(a=>a.currency==='USD')?`<div class="summary-item"><span>Cuentas · saldo USD</span><strong>${currencyMoney(values.accounts.filter(a=>a.currency==='USD').reduce((sum,a)=>sum+a.amount,0),'USD')}</strong><small>Valor estimado UYU: ${money(values.airtmPesos)} · conversión USD → USDT → UYU</small></div>`:''}<div class="summary-item inventory-total"><span>Inventario total en pesos uruguayos</span><strong>${money(values.totalPesos)}</strong><small>${values.totalPesos===null?`Total incompleto: cuentas ${money(values.bankTotal)} + Binance pendiente de valorar.`:'Cuentas UYU + Airtm convertido + Binance neto. Cada saldo se incluye una sola vez.'}</small></div>`;
  $('inventory-bank-rows').innerHTML=values.accounts.filter(a=>allBanks.find(b=>b.key===a.key)?.active || a.amount!==0).map(account=>`<tr><td><b>${esc(account.name)}</b></td><td>${currencyMoney(account.amount,account.currency)}</td><td>${qty(account.gross)}</td><td>${qty(account.fee)}</td><td><b>${qty(account.net)}</b></td></tr>`).join('')+`<tr><td><b>Total de capacidad</b></td><td>Cuentas UYU + Airtm USD</td><td>${qty(values.buyGross)}</td><td>${qty(values.buyFee)}</td><td><b>${qty(values.buyNet)}</b></td></tr>`;
  $('binance-detail').innerHTML=`<div class="binance-valuation binance-unified"><div><span>Binance · ${qty(values.binanceTotal)} USDT</span><b>${money(values.binancePesos)}</b><small>Comisión estimada al convertir: ${qty(values.binanceFee)} USDT</small></div></div>`;
}
async function request(options){const response=await fetch(operatorURL('/api/inventory'),options),data=await response.json();if(!response.ok)throw new Error(data.error || 'No se pudo acceder al inventario.');if(data.operator!==OPERATOR)throw new Error('La respuesta no corresponde al operador activo.');return data;}
function error(message){$('inventory-error').hidden=!message;$('inventory-error').textContent=message;}
async function load(quiet=false){
  if(loading || quiet && (dirty || saving))return;
  loading=true;if(!quiet)$('inventory-fields').disabled=true;$('inventory-reload').disabled=true;if(!quiet)error('');
  try{const data=await request();const auditResponse=await fetch(operatorURL('/api/audit'));if(!auditResponse.ok)throw new Error('No se pudo cargar el historial de conciliaciones.');const auditData=await auditResponse.json();reconciliationRecords=(auditData.records || []).filter(r=>r.action==='inventory.reconcile');if(quiet && dirty)return;serverInventory=data.inventory;serverValues=data.values;averages=data.averages;revision=data.revision;withdrawals=data.withdrawals || [];fill(data.inventory);$('inventory-review').hidden=!data.inventory.needsReview;$('inventory-fields').disabled=false;if(!quiet){dirty=false;$('inventory-message').textContent='';}render();renderWithdrawals();}
  catch(problem){error(problem.message);}
  finally{loading=false;$('inventory-reload').disabled=false;}
}
$('inventory-form').addEventListener('input',()=>{dirty=true;$('inventory-message').textContent='Cambios sin guardar. La valoración se actualizará al guardar.';$('inventory-message').className='';render();});
$('inventory-form').addEventListener('submit',async event=>{
  event.preventDefault();if($('inventory-fields').disabled || loading || saving)return;
  let input;try{input=draft();input.reason=$('reconcile-reason').value.trim();const changed=input.binance!==serverInventory.binance || banks.some(a=>input.accounts[a.key]!==serverInventory.accounts[a.key]);if(changed&&!input.reason)throw new Error('Indica el motivo de la conciliación.');if(!confirm('¿Conciliar los saldos reales? Revisa las diferencias mostradas. El ajuste no se cuenta como ganancia.'))return;}catch(problem){error(problem.message);return;}
  saving=true;$('inventory-fields').disabled=true;$('inventory-reload').disabled=true;lockOperator(true);error('');$('inventory-message').textContent='Guardando…';
  try{const data=await request({method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({operator:OPERATOR,expectedRevision:revision,...input})});serverInventory=data.inventory;serverValues=data.values;averages=data.averages;revision=data.revision;withdrawals=data.withdrawals || [];dirty=false;$('reconcile-reason').value='';const auditResponse=await fetch(operatorURL('/api/audit'));if(auditResponse.ok)reconciliationRecords=((await auditResponse.json()).records || []).filter(r=>r.action==='inventory.reconcile');fill(data.inventory);$('inventory-review').hidden=!data.inventory.needsReview;render();renderWithdrawals();$('inventory-message').textContent=`Inventario de ${esc(OPERATOR_NAME)} guardado.`;$('inventory-message').className='positive';}
  catch(problem){error(problem.message);$('inventory-message').textContent='No se pudo guardar el inventario.';$('inventory-message').className='negative';}
  finally{saving=false;$('inventory-fields').disabled=false;$('inventory-reload').disabled=false;lockOperator(false);}
});
$('inventory-reload').addEventListener('click',()=>void load());

function localDate(value=new Date()){const date=new Date(value);return new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16);}
function movementLabels(){const currency=banks.find(a=>a.key===$('withdrawal-account').value)?.currency || 'UYU';$('withdrawal-amount-label').textContent=`Monto (${currency})`;$('withdrawal-save').textContent=withdrawalEditing?'Guardar cambios':$('withdrawal-kind').value==='deposit'?'Registrar depósito':'Registrar retiro';}
$('withdrawal-account').addEventListener('change',movementLabels);$('withdrawal-kind').addEventListener('change',movementLabels);
function resetWithdrawal(){withdrawalEditing=null;$('withdrawal-date').value=localDate();$('withdrawal-amount').value='';$('withdrawal-note').value='';$('withdrawal-save').textContent='Registrar retiro';$('withdrawal-cancel').hidden=true;movementLabels();}
function renderWithdrawals(){
  $('withdrawal-rows').innerHTML=withdrawals.length?[...withdrawals].sort((a,b)=>new Date(b.date)-new Date(a.date)).map(record=>`<tr><td>${esc(new Date(record.date).toLocaleString('es-UY',{timeZone:'America/Montevideo'}))}</td><td>${esc(banks.find(bank=>bank.key===record.accountKey)?.name || record.accountKey)}</td><td>${currencyMoney(record.amountCents/100,record.currency || banks.find(a=>a.key===record.accountKey)?.currency || 'UYU')}</td><td>${record.kind==='deposit'?'Depósito':'Retiro'} · ${esc(record.note || '—')}</td><td><div class="row-actions"><button type="button" data-withdraw-edit="${record.id}">Editar</button><button type="button" class="delete-order" data-withdraw-delete="${record.id}">Eliminar</button></div></td></tr>`).join(''):'<tr><td colspan="5" class="ledger-empty">No hay movimientos registrados.</td></tr>';
}
async function withdrawRequest(path,options){const response=await fetch(operatorURL(path),options),data=await response.json();if(!response.ok)throw new Error(data.error || 'No se pudo guardar el retiro.');if(data.operator!==OPERATOR)throw new Error('El retiro no corresponde al operador activo.');return data;}
$('withdrawal-form').addEventListener('submit',async event=>{
  event.preventDefault();if(saving || loading)return;
  if(dirty){$('withdrawal-message').textContent='Guarda o recarga los saldos que estás editando antes de registrar un movimiento.';return;}
  saving=true;$('withdrawal-save').disabled=true;lockOperator(true);$('withdrawal-message').textContent='Guardando…';
  try{await withdrawRequest(withdrawalEditing?`/api/withdrawals/${withdrawalEditing}`:'/api/withdrawals',{method:withdrawalEditing?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operator:OPERATOR,accountKey:$('withdrawal-account').value,kind:$('withdrawal-kind').value,amount:Number($('withdrawal-amount').value),date:new Date($('withdrawal-date').value).toISOString(),note:$('withdrawal-note').value})});resetWithdrawal();$('movement-dialog').close();$('movement-page-message').textContent='Movimiento guardado. Inventario actualizado.';$('withdrawal-message').textContent='Movimiento guardado. Inventario actualizado.';await load();}
  catch(problem){$('withdrawal-message').textContent=problem.message;}
  finally{saving=false;$('withdrawal-save').disabled=false;lockOperator(false);}
});
$('withdrawal-cancel').addEventListener('click',()=>{resetWithdrawal();$('movement-dialog').close();});
$('create-movement').addEventListener('click',()=>{if(saving)return;if(withdrawalEditing)resetWithdrawal();$('withdrawal-message').textContent='';$('movement-dialog').showModal();});
$('movement-close').addEventListener('click',()=>{if(!saving)$('movement-dialog').close();});
$('movement-dialog').addEventListener('cancel',event=>{if(saving)event.preventDefault();});
$('movement-dialog').addEventListener('click',event=>{if(event.target===$('movement-dialog') && !saving){const r=$('movement-dialog').getBoundingClientRect();if(event.clientX<r.left || event.clientX>r.right || event.clientY<r.top || event.clientY>r.bottom)$('movement-dialog').close();}});
$('withdrawal-rows').addEventListener('click',async event=>{
  const button=event.target.closest('button');if(!button || saving || loading)return;
  const record=withdrawals.find(item=>item.id===(button.dataset.withdrawEdit || button.dataset.withdrawDelete));if(!record)return;
  if(button.dataset.withdrawEdit){withdrawalEditing=record.id;$('withdrawal-kind').value=record.kind || 'withdrawal';$('withdrawal-account').value=record.accountKey;$('withdrawal-date').value=localDate(record.date);$('withdrawal-amount').value=record.amountCents/100;$('withdrawal-note').value=record.note || '';$('withdrawal-save').textContent='Guardar cambios';$('withdrawal-cancel').hidden=false;movementLabels();$('movement-dialog').showModal();$('withdrawal-amount').focus();return;}
  if(dirty){$('movement-page-message').textContent='Guarda o recarga los saldos que estás editando antes de eliminar un retiro.';return;}
  if(!confirm('¿Eliminar este movimiento y revertir su efecto en el saldo de la cuenta?'))return;
  saving=true;button.disabled=true;
  try{await withdrawRequest(`/api/withdrawals/${record.id}`,{method:'DELETE'});if(withdrawalEditing===record.id)resetWithdrawal();$('movement-page-message').textContent='Movimiento eliminado. Saldo actualizado.';await load();}
  catch(problem){$('movement-page-message').textContent=problem.message;}
  finally{saving=false;button.disabled=false;}
});
window.addEventListener('focus',()=>void load(true));
setInterval(()=>{if(document.visibilityState==='visible')void load(true);},15000);
resetWithdrawal();void load();

async function accountRequest(data,method='POST'){
 const response=await fetch(operatorURL('/api/accounts'),{method,headers:{'Content-Type':'application/json'},body:JSON.stringify({operator:OPERATOR,...data})});const result=await response.json();if(!response.ok)throw new Error(result.error || 'No se pudo guardar la cuenta.');return result;
}
$('create-account').addEventListener('click',()=>{if(loading || saving)return;if(dirty){$('account-page-message').textContent='Guarda o recarga los saldos que estás editando antes de crear una cuenta.';return;}$('inventory-account-form').reset();$('account-form-message').textContent='';$('account-dialog').showModal();$('account-name').focus();});
$('account-close').addEventListener('click',()=>{if(!saving)$('account-dialog').close();});
$('account-dialog').addEventListener('cancel',event=>{if(saving)event.preventDefault();});
$('account-institution').addEventListener('change',()=>{$('account-name').value=$('account-institution').value;if($('account-institution').value==='Airtm')$('account-currency').value='USD';});
$('inventory-account-form').addEventListener('submit',async event=>{event.preventDefault();if(saving)return;saving=true;$('account-save').disabled=true;lockOperator(true);try{await accountRequest({name:$('account-name').value.trim(),currency:$('account-currency').value});location.reload();}catch(e){$('account-form-message').textContent=e.message;}finally{saving=false;$('account-save').disabled=false;lockOperator(false);}});
$('inventory-fields').addEventListener('click',async event=>{const button=event.target.closest('[data-archive-account],[data-activate-account]');if(!button || saving || loading)return;if(dirty){$('account-page-message').textContent='Guarda o recarga tus cambios de saldo antes de modificar las cuentas.';return;}const key=button.dataset.archiveAccount || button.dataset.activateAccount;const archive=Boolean(button.dataset.archiveAccount);if(archive&&!confirm('¿Quitar esta cuenta del inventario? Debe tener saldo cero y no tener órdenes pendientes. Su historial se conserva.'))return;saving=true;button.disabled=true;try{await accountRequest({key,action:archive?'archive':'activate'},'PUT');location.reload();}catch(e){$('account-page-message').textContent=e.message;}finally{saving=false;button.disabled=false;}});
function lockOperator(disabled){const select=$('operator-select');if(select)select.disabled=disabled;}
