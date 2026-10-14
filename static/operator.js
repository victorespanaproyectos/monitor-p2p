const c=window.P2P_CONTEXT;
export const OPERATOR=c.operator;
export const BINANCE_USERNAME=c.binanceUsername;
export const OPERATOR_NAME=c.name;
export function operatorURL(path){const url=new URL(path,location.origin);url.searchParams.set('operator',OPERATOR);return url.pathname+url.search;}
const select=document.getElementById('operator-select');
if(select){select.replaceChildren(...Object.entries(c.operators).map(([id,name])=>new Option(name,id)));select.value=OPERATOR;select.addEventListener('change',()=>location.assign('/?operator='+select.value));}
for(const link of document.querySelectorAll('[data-operator-context]'))link.href=operatorURL(link.getAttribute('href'));
for(const label of document.querySelectorAll('[data-operator-name]'))label.textContent=OPERATOR_NAME;
const nav=document.querySelector('.market-navigation');
if(nav){if(c.isAdmin){const link=document.createElement('a');link.href=operatorURL('/operadores');link.textContent='Operadores y cuentas';nav.append(link);}const password=document.createElement('a');password.href='/password/';password.textContent='Contraseña';nav.append(password);const form=document.createElement('form');form.method='post';form.action='/logout/';const token=document.createElement('input');token.type='hidden';token.name='csrfmiddlewaretoken';token.value=decodeURIComponent(document.cookie.split('; ').find(v=>v.startsWith('csrftoken='))?.split('=').slice(1).join('=')||'');const button=document.createElement('button');button.type='submit';button.className='secondary-button';button.textContent='Salir · '+c.username;form.append(token,button);nav.append(form);}
if(c.demo){const banner=document.createElement('div');banner.className='operator-banner';banner.textContent='DEMOSTRACIÓN · Anuncios simulados y datos ficticios';document.querySelector('main')?.prepend(banner);}

for(const note of document.querySelectorAll('.tool-note,.recommendation-help')){if(note.textContent.includes('0,2 %')||note.textContent.includes('0,998')||note.textContent.includes('1,002')){const rate=Number(c.commission),text=note.textContent.replaceAll('0,2 %',(rate*100).toLocaleString('es-UY')+' %').replaceAll('0,998',(1-rate).toLocaleString('es-UY',{maximumFractionDigits:6})).replaceAll('1,002',(1+rate).toLocaleString('es-UY',{maximumFractionDigits:6}));note.textContent=text;}}
