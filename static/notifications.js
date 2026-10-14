import {compareProfile} from './notification-rules.js?v=1.4.2';
const c=window.P2P_CONTEXT;
if(c?.operator){if(!document.getElementById('theme-control')&&document.readyState!=='complete')document.addEventListener('DOMContentLoaded',start,{once:true});else start();}
function start(){
 const scope=`p2p-alerts-v1:${c.username}:${c.operator}`,fmt=n=>Number(n).toLocaleString('es-UY',{maximumFractionDigits:8});
 const defaults={ads:true,pending:true,low:true,errors:true,pendingMinutes:30,limits:{},desktop:false,sound:false};
 let volatile={},storageOK=true,busy=false,stateBusy=false,profileHint='',watchStatus='Identificando tu perfil…',stateStatus='',marketFailures={};
 function read(){if(!storageOK)return volatile;try{return JSON.parse(localStorage.getItem(scope)||'{}');}catch{storageOK=false;return volatile;}}
 function write(data){volatile=data;try{localStorage.setItem(scope,JSON.stringify(data));}catch{storageOK=false;}}
 function prefs(){return {...defaults,...read().prefs};}
 const icons={bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',ads:'<path d="m3 17 6-6 4 4 8-10"/><path d="M15 5h6v6"/>',pending:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',low:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/>',errors:'<circle cx="12" cy="12" r="9"/><path d="M12 7v6m0 4h.01"/>'};
 const icon=type=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[type]||icons.bell}</svg>`;
 const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
 const button=document.createElement('button');button.id='notification-bell';button.type='button';button.className='notification-bell';button.setAttribute('aria-label','Abrir notificaciones');button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls','notification-panel');button.title='Notificaciones';
 const theme=document.querySelector('.theme-control');
 const host=theme?.parentElement||document.querySelector('header')||document.body;
 const binance=document.querySelector('.header-inner a[href*="binance.com"]');
 if(binance){binance.className='binance-icon-link';binance.title='Abrir Binance';binance.setAttribute('aria-label','Abrir Binance en otra pestaña');binance.rel='noopener noreferrer';binance.innerHTML='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="m12 0 5.5 5.5-2.1 2.1L12 4.2 8.6 7.6 6.5 5.5 12 0ZM2.1 9.9 4.2 12l-2.1 2.1L0 12l2.1-2.1Zm7.8 2.1 2.1-2.1 2.1 2.1-2.1 2.1-2.1-2.1Zm12-2.1L24 12l-2.1 2.1-2.1-2.1 2.1-2.1ZM8.6 16.4l3.4 3.4 3.4-3.4 2.1 2.1L12 24l-5.5-5.5 2.1-2.1ZM4.2 12l2.1-2.1 2.1 2.1-2.1 2.1L4.2 12Zm11.4 0 2.1-2.1 2.1 2.1-2.1 2.1-2.1-2.1Z"/></svg>';}
 if(theme){const actions=document.createElement('div');actions.className='notification-header-actions';theme.before(actions);if(binance)actions.append(binance);actions.append(button,theme);}else{if(binance)host.append(binance);host.append(button);}
 const panel=document.createElement('aside');panel.id='notification-panel';panel.className='notification-panel';panel.hidden=true;panel.setAttribute('aria-label','Notificaciones');document.body.append(panel);
 const toast=document.createElement('div');toast.className='notification-toast';toast.hidden=true;toast.setAttribute('role','status');document.body.append(toast);let toastTimer;
 const dialog=document.createElement('dialog');dialog.id='notification-settings';dialog.className='notification-settings';document.body.append(dialog);
 let accounts=[];
 function sound(){try{const A=window.AudioContext||window.webkitAudioContext,a=new A(),o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);g.gain.setValueAtTime(.06,a.currentTime);o.frequency.value=660;o.start();o.stop(a.currentTime+.15);o.onended=()=>a.close();}catch{}}
 function push(type,key,title,body,href){
  const d=read(),p={...defaults,...d.prefs};if(!p[type])return;
  d.seen ||= {}; if(d.seen[key])return;d.seen[key]=Date.now();
  const sorted=Object.entries(d.seen).sort((a,b)=>b[1]-a[1]);d.seen=Object.fromEntries(sorted.slice(0,500));
  d.items=[{id:crypto.randomUUID?.()||`${Date.now()}-${Math.random().toString(36).slice(2)}`,type,title,body,href,time:Date.now(),read:false},...(d.items||[])].slice(0,60);write(d);render();
  toast.innerHTML=`<strong>${esc(title)}</strong><p>${esc(body)}</p><button type="button" aria-label="Cerrar aviso">×</button>`;toast.hidden=false;toast.querySelector('button').onclick=()=>toast.hidden=true;clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.hidden=true,8000);
  if(p.sound)sound();
  if(p.desktop && 'Notification' in window && Notification.permission==='granted')try{const n=new Notification(title,{body:`${c.name}: ${body}`,tag:key});n.onclick=()=>{window.focus();n.close();};}catch{}
 }
 function render(){
  const items=(read().items||[]).filter(i=>!i.read),unread=items.length;
  button.innerHTML=`${icon('bell')}${unread?`<b>${unread}</b>`:''}`;button.setAttribute('aria-label',`Notificaciones: ${unread} sin leer`);
  panel.innerHTML=`<div class="notification-heading"><h2>Notificaciones</h2><button data-close type="button" aria-label="Cerrar notificaciones">×</button></div><div class="notification-subheading"><span>Operador: <strong>${esc(c.name)}</strong></span><button data-read type="button">Marcar como leídas</button></div><div class="notification-list">${items.length?items.map(i=>`<article class="notification-card ${esc(i.type)} ${i.read?'read':''}"><span class="notification-card-icon">${icon(i.type)}</span><div class="notification-card-content"><div class="notification-card-heading"><strong>${esc(i.title)}</strong><small>${new Date(i.time).toLocaleTimeString('es-UY',{hour:'2-digit',minute:'2-digit'})}</small></div><div class="notification-card-body">${i.body.split(' · ').map(line=>`<p>${esc(line)}</p>`).join('')}</div><a data-notification-id="${esc(i.id)}" href="${esc(i.href)}" ${i.type==='ads'?'target="_blank" rel="noopener noreferrer"':''}>${i.type==='ads'?'Ver anuncio ↗':i.type==='pending'?'Ver orden':i.type==='low'?'Ver inventario':'Revisar'}</a><time datetime="${new Date(i.time).toISOString()}" class="notification-date">${new Date(i.time).toLocaleDateString('es-UY')}</time></div></article>`).join(''):'<p class="notification-empty">No tienes notificaciones sin leer.</p>'}</div><div class="notification-footer"><button data-settings type="button">⚙ Configurar notificaciones <span aria-hidden="true">›</span></button><details><summary>Estado de las consultas</summary><p class="notification-status">${esc(watchStatus)}${stateStatus?' · '+esc(stateStatus):''}${storageOK?'':' · El navegador no permite guardar los avisos.'}</p><button data-clear type="button">Borrar historial</button></details></div>`;
  panel.querySelector('[data-close]').onclick=()=>toggle(false);
  function markRead(ids){const d=read();for(const i of d.items||[])if(ids.has(i.id))i.read=true;write(d);toast.hidden=true;render();}
  panel.querySelector('[data-read]').onclick=()=>markRead(new Set(items.map(i=>i.id)));
  for(const link of panel.querySelectorAll('[data-notification-id]'))link.addEventListener('click',()=>markRead(new Set([link.dataset.notificationId])));
  panel.querySelector('[data-clear]').onclick=()=>{const d=read();d.items=[];write(d);render();};
  panel.querySelector('[data-settings]').onclick=settings;
 }
 function positionPanel(){if(panel.hidden)return;const rect=button.getBoundingClientRect(),width=Math.min(480,innerWidth-24),top=Math.max(12,Math.min(rect.bottom+12,innerHeight-180));panel.style.width=width+'px';panel.style.left=Math.max(12,Math.min(rect.right-width,innerWidth-width-12))+'px';panel.style.top=top+'px';panel.style.maxHeight=Math.max(160,innerHeight-top-12)+'px';}
 function toggle(open){panel.hidden=!open;button.setAttribute('aria-expanded',String(open));if(open){render();positionPanel();}else button.focus();}
 window.addEventListener('resize',positionPanel);window.addEventListener('scroll',positionPanel,{passive:true});
 button.onclick=()=>toggle(panel.hidden);
 document.addEventListener('keydown',e=>{if(e.key==='Escape' && !panel.hidden)toggle(false);});
 document.addEventListener('click',e=>{if(!panel.hidden&&!e.composedPath().includes(panel)&&!e.composedPath().includes(button)&&!dialog.open)toggle(false);});
 function settings(){
  const p=prefs(),rows=[{key:'binance',name:'Binance',currency:'USDT'},...accounts.filter(a=>a.active)];
  dialog.innerHTML=`<form><div class="notification-heading"><h2>Configurar avisos</h2><button type="button" data-cancel aria-label="Cerrar configuración">×</button></div><p>Operador: ${esc(c.name)}</p>${[['ads','Cambios en tus anuncios'],['pending','Órdenes pendientes'],['low','Saldo disponible bajo'],['errors','Fallos de actualización'],['sound','Sonido opcional'],['desktop','Notificaciones del navegador']].map(([key,label])=>`<label class="notification-check"><input type="checkbox" name="${key}" ${p[key]?'checked':''}>${label}</label>`).join('')}<label>Minutos para una orden pendiente<input type="number" name="pendingMinutes" min="1" max="10080" step="1" value="${p.pendingMinutes}" required></label><h3>Mínimos de saldo disponible</h3><p>Deja el campo vacío para no vigilar esa cuenta. Los saldos reservados no están disponibles.</p>${rows.map(a=>`<label>${esc(a.name)} (${esc(a.currency)})<input type="number" data-limit="${esc(a.key)}" min="0" max="10000000000" step="any" value="${esc(p.limits[a.key]??'')}" placeholder="Sin alerta"></label>`).join('')}<p>Los avisos y ajustes se guardan en este navegador por usuario y operador. Se revisan cada 30 segundos mientras la aplicación esté abierta y visible. Binance puede tardar en reflejar cambios; su perfil tiene una caché de hasta 30 segundos.</p><p>No se confirma ni se crea una orden automáticamente. Si no se encuentra tu perfil, abre un mercado donde aparezca tu anuncio.</p><p id="notification-permission" role="status"></p><button type="submit">Guardar configuración</button></form>`;
  dialog.querySelector('[data-cancel]').onclick=()=>dialog.close();
  dialog.querySelector('form').onsubmit=async e=>{e.preventDefault();const f=e.target,np={...p,limits:{}};
   for(const k of ['ads','pending','low','errors','sound','desktop'])np[k]=f.elements[k].checked;
   np.pendingMinutes=Number(f.elements.pendingMinutes.value);
   if(!Number.isInteger(np.pendingMinutes)||np.pendingMinutes<1||np.pendingMinutes>10080)return;
   for(const input of f.querySelectorAll('[data-limit]'))if(input.value!==''){const n=Number(input.value);if(!Number.isFinite(n)||n<0||n>1e10)return;np.limits[input.dataset.limit]=n;}
   if(np.desktop){if(!('Notification' in window)){np.desktop=false;dialog.querySelector('#notification-permission').textContent='Este navegador no admite avisos de escritorio. Los avisos internos siguen activos.';}else{const permission=Notification.permission==='default'?await Notification.requestPermission():Notification.permission;if(permission!=='granted'){np.desktop=false;dialog.querySelector('#notification-permission').textContent='Permiso no concedido. Los avisos internos siguen activos.';}}}
   const d=read();d.prefs=np;d.lowState={};d.pendingSeen={};d.stateInitialized=false;
   // Re-enabling ad monitoring starts with a fresh reference.
   if(np.ads!==p.ads)d.profile=null;
   write(d);if(np.sound)sound();render();
   if(f.elements.desktop.checked&&!np.desktop){f.elements.desktop.checked=false;return;}
   dialog.close();void poll();
  };dialog.showModal();
 }
 async function get(path){const r=await fetch(`${path}${path.includes('?')?'&':'?'}operator=${encodeURIComponent(c.operator)}`,{cache:'no-store',signal:AbortSignal.timeout(60000)});if(r.status===401||r.status===403){throw Error('Sesión vencida o sin acceso. Recarga e inicia sesión.');}const d=await r.json();if(!r.ok)throw Error(d.error||'No se pudo consultar.');return d;}
 function failure(source,error){marketFailures[source]||={count:0,last:0};const f=marketFailures[source];f.count++;
  if(f.count>=2)push('errors','failure:'+source+':'+f.episode,'No se pudo actualizar '+source,`${error}. Última actualización correcta: ${f.last?new Date(f.last).toLocaleTimeString('es-UY'):'sin datos'}.`,'/?operator='+c.operator);
 }
 function success(source){const f=marketFailures[source]||{};marketFailures[source]={count:0,last:Date.now(),episode:(f.episode||0)+(f.count?1:0)};}
 async function pollProfile(){if(busy||!prefs().ads)return;busy=true;
  try{const data=await get('/api/own-ads'+(profileHint?'?userNo='+encodeURIComponent(profileHint):''));
   if(data.status!=='watching'){watchStatus=data.message||'Perfil aún no encontrado.';render();return;}
   success('tus anuncios');watchStatus=`Vigilando ${data.ads.length} anuncios públicos · ${new Date(data.updatedAt).toLocaleTimeString('es-UY')}${data.limited?' · Muestra limitada':''}`;
   const d=read(),result=compareProfile(d.profile,data,c.binanceUsername);d.profile=result.snapshot;write(d);
   for(const event of result.events){const a=event.ad;const details=event.diff.map(x=>`${x.label}: ${fmt(x.before)} → ${fmt(x.after)} ${x.key==='available'?a.asset:a.fiat}`).join(' · ');push('ads',`ad:${data.userNo}:${event.id}:${data.updatedAt}`,`Tu anuncio de ${a.tradeType==='SELL'?'venta':'compra'} cambió`,`${a.asset} / ${a.fiat} · ${details}`,'https://c2c.binance.com/es/adv?adNo='+encodeURIComponent(a.id));}
  }catch(e){watchStatus='No se pudo vigilar tus anuncios: '+e.message;failure('tus anuncios',e.message);}finally{busy=false;render();}
 }
 async function pollState(){if(stateBusy)return;stateBusy=true;
  try{const data=await get('/api/notification-state');accounts=data.accounts;stateStatus='Saldos y órdenes actualizados';
   const d=read(),p=prefs(),now=Date.now();d.lowState ||= {};d.pendingSeen ||= {};const events=[];
   const balances={...data.availableAccounts,binance:data.availableBinance};
   for(const [key,limit] of Object.entries(p.limits)){if(key!=='binance'&&!accounts.some(a=>a.active&&a.key===key))continue;const value=balances[key];if(typeof value!=='number')continue;const low=value<limit,previous=d.lowState[key];
    if(p.low&&d.stateInitialized&&low&&previous===false){const a=accounts.find(a=>a.key===key),label=a?.name||'Binance',unit=a?.currency||'USDT';events.push(['low',`low:${key}:${now}`,'Saldo disponible bajo',`${label}: ${fmt(value)} ${unit} · Mínimo: ${fmt(limit)} ${unit}`,'/inventario?operator='+c.operator]);}d.lowState[key]=low;
   }
   const ids=new Set(data.pending.map(o=>o.id));for(const id of Object.keys(d.pendingSeen))if(!ids.has(id))delete d.pendingSeen[id];
   for(const o of data.pending){const age=now-Date.parse(o.date),eligible=Number.isFinite(age)&&age>=p.pendingMinutes*60000;if(!eligible){delete d.pendingSeen[o.id];continue;}
    if(p.pending&&d.stateInitialized&&!d.pendingSeen[o.id]){events.push(['pending',`pending:${o.id}:${p.pendingMinutes}`,'Orden pendiente',`Orden ${o.number} · Lleva ${Math.floor(age/60000)} minutos pendiente.`,'/ordenes?operator='+c.operator]);d.pendingSeen[o.id]=true;}}
   d.stateInitialized=true;write(d);for(const event of events)push(...event);render();
  }catch(e){stateStatus='Saldos y órdenes sin actualizar: '+e.message;render();}finally{stateBusy=false;}
 }
 function poll(){if(document.visibilityState!=='visible')return;void pollState();void pollProfile();}
 window.addEventListener('p2p-market-result',e=>{const {groups,error,fiat}=e.detail,source='el mercado '+fiat;
  const sideError=groups.map(g=>g.buy?.error||g.sell?.error).find(Boolean);if(error||sideError)failure(source,error||sideError);else success(source);
  for(const group of groups)for(const side of [group.buy,group.sell])for(const a of side?.ads||[])if(a.nickname?.trim().toLowerCase()===c.binanceUsername.trim().toLowerCase()&&a.userNo){if(profileHint!==a.userNo){profileHint=a.userNo;void pollProfile();}}
 });
 window.addEventListener('p2p-data-changed',()=>void pollState());window.addEventListener('storage',e=>{if(e.key===scope)render();});
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')poll();});
 render();poll();setInterval(poll,30000);
}
