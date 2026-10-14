export const OPERATORS = window.P2P_CONTEXT.operators;
export function banksFor(operator){return window.P2P_CONTEXT.accounts[operator] || [];}
export function emptyInventory(operator) {
  return { accounts:Object.fromEntries(banksFor(operator).map(bank=>[bank.key,0])),funds:0,earn:0,updatedAt:null };
}
// Promedio ponderado por USDT nominales: pesos registrados / USDT registrados.
export const currencyOf = order => order.currency === 'USD' ? 'USD' : 'UYU';
export function averagePrices(orders,currency='UYU') {
  const side=type=>{
    const selected=orders.filter(order=>order.type===type && currencyOf(order)===currency && !order.legacyCurrencyReview),quantity=selected.reduce((sum,order)=>sum+order.quantity,0),amount=selected.reduce((sum,order)=>sum+order.amount,0);
    return { price:quantity>0?amount/quantity:null,count:selected.length,quantity,amount };
  };
  return { buy:side('buy'),sell:side('sell'),...(currency==='UYU'?{usd:averagePrices(orders,'USD')}:{}) };
}
export function accountFor(method,operator) {
  const key=String(method || '').normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase().replace(/[^a-z]/g,'');
  const aliases={santander:'santander',santanderurug:'santander',ocablue:'ocaBlue',prex:'prex',mercadopago:'mercadoPago',mercadopagonew:'mercadoPago',itau:'itau',itauuruguay:'itau',airtm:'airtm'};
  const account=Object.hasOwn(aliases,key)?aliases[key]:null;
  return banksFor(operator).some(bank=>bank.key===account)?account:null;
}
