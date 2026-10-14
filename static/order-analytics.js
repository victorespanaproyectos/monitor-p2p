import { currencyOf } from './inventory-calculations.js?v=market-1.4.2';
// FIFO por moneda: compras aportan USDT netos; ventas consumen nominal + comisión USDT.
const dayFormatter = new Intl.DateTimeFormat('en-CA',{ timeZone:'America/Montevideo', year:'numeric',month:'2-digit',day:'2-digit' });
export function dayKey(value) {
  const parts=Object.fromEntries(dayFormatter.formatToParts(new Date(value)).map(part=>[part.type,part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}
export function paymentMethod(value) {
  const text = String(value || '').trim().replace(/\s+/g,' ');
  const key = text.normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase().replace(/[^a-z0-9]/g,'');
  const aliases = { santander:'Santander',santanderurug:'Santander',itau:'Itaú',itauuruguay:'Itaú',ocablue:'OCA Blue',mercadopago:'MercadoPago',mercadopagonew:'MercadoPago',brou:'BROU',bancorepublica:'BROU',bankrepublicuruguay:'BROU',prex:'Prex',airtm:'Airtm' };
  return (Object.hasOwn(aliases,key) ? aliases[key] : text) || 'Sin especificar';
}
const methodKey = value => paymentMethod(value).normalize('NFC').toLocaleLowerCase('es-UY');
export function inRange(order,from='',to='') {
  const day = dayKey(order.date);
  return (!from || day >= from) && (!to || day <= to);
}
function addDays(date,number) { const value=new Date(`${date}T12:00:00Z`);value.setUTCDate(value.getUTCDate()+number);return value.toISOString().slice(0,10); }
export function chartBuckets(data,from='',to='') {
  if(!data.days.length)return { buckets:[],unit:'día' };
  const start=from || data.days[0].date, end=to || data.days.at(-1).date;
  const count=Math.round((new Date(end)-new Date(start))/86400000)+1;
  const unit=count<=31?'día':count<=120?'semana':count<=1096?'mes':'año';
  const buckets=new Map();
  const put=(key,label)=>{if(!buckets.has(key))buckets.set(key,{key,label,buy:0,sell:0,methods:new Map()});return buckets.get(key);};
  if(unit==='año') {
    for(let year=Number(start.slice(0,4));year<=Number(end.slice(0,4));year++)put(String(year),String(year));
  } else if(unit==='mes') {
    for(let key=start.slice(0,7);key<=end.slice(0,7);){put(key,key);const [year,month]=key.split('-').map(Number);key=`${year+(month===12?1:0)}-${String(month===12?1:month+1).padStart(2,'0')}`;}
  } else {
    for(let key=start;key<=end;key=addDays(key,unit==='día'?1:7))put(key,key);
  }
  for(const day of data.days){
    const offset=Math.round((new Date(day.date)-new Date(start))/86400000);
    const key=unit==='año'?day.date.slice(0,4):unit==='mes'?day.date.slice(0,7):unit==='semana'?addDays(start,Math.floor(offset/7)*7):day.date;
    const bucket=put(key,key);bucket.buy+=day.buy;bucket.sell+=day.sell;
    for(const [method,values] of day.methods){if(!bucket.methods.has(method))bucket.methods.set(method,{buy:0,sell:0});const current=bucket.methods.get(method);current.buy+=values.buy;current.sell+=values.sell;}
  }
  return { buckets:[...buckets.values()].sort((a,b)=>a.key.localeCompare(b.key)),unit };
}
