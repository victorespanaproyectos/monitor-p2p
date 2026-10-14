// Ciclo cerrado: compra nominal, comisión de compra en USDT,
// venta del saldo neto reservando su comisión adicional en USDT.
export function profit({ buy, sell, amount }) {
  const values = [buy, sell, amount];
  if (values.some(v => !Number.isFinite(v)) || buy <= 0 || sell <= 0 || amount <= 0) return null;
  const rate=Number(window.P2P_CONTEXT.commission),quantity=amount,received=quantity*(1-rate),sellQuantity=received/(1+rate);
  const purchase=quantity*buy,sale=sellQuantity*sell,cost=purchase,proceeds=sale;
  const buyCommission=quantity*rate,sellCommission=sellQuantity*rate,fees=buyCommission+sellCommission;
  const gross=quantity*(sell-buy),net=sale-purchase;
  if(![purchase,sale,net].every(Number.isFinite))return null;
  return {quantity,sellQuantity,received,purchase,sale,buyCommission,sellCommission,fees,cost,proceeds,gross,net,roi:net/cost*100,spread:sell-buy,spreadPercent:(sell-buy)/buy*100};
}
export function spreadScenarios(group) {
  if (!group || group.buy.error || group.sell.error || !group.buy.ads.length || !group.sell.ads.length) return null;
  const buyers = group.sell.ads.map(a => a.price), sellers = group.buy.ads.map(a => a.price);
  return [
    { key:'competitive', name:'Spread competitivo', buy:Math.max(...buyers), sell:Math.min(...sellers), note:'Mayor precio de otros compradores y menor precio de otros vendedores.' },
    { key:'extremes', name:'Spread entre extremos', buy:Math.min(...buyers), sell:Math.max(...sellers), note:'Menor precio de otros compradores y mayor precio de otros vendedores, dentro de los 10 anuncios.' },
  ];
}
export function myPositions(ads, username) {
  const normalize = value => value.trim().normalize('NFC').toLocaleLowerCase('es-UY');
  const wanted = normalize(username);
  return wanted ? ads.flatMap((ad,i) => normalize(ad.nickname) === wanted ? [i+1] : []) : [];
}

// Comparación exacta a centésimas de UYU; el mínimo procede del anuncio en fiat.
export function minimumMatches(ads, username, fallback = null) {
  const own = myPositions(ads, username);
  const valid = own.map(position => ads[position-1].minFiat).filter(n => Number.isFinite(n) && n > 0);
  const minima = valid.length ? [...new Set(valid)] : Number.isFinite(fallback) && fallback > 0 ? [fallback] : [];
  const cents = new Set(minima.map(n => Math.round(n*100)));
  const positions = ads.flatMap((ad,i) => !own.includes(i+1) && Number.isFinite(ad.minFiat) && cents.has(Math.round(ad.minFiat*100)) ? [i+1] : []);
  return { minima, positions, fromOwn: valid.length > 0 };
}

// Compare competitive prices within a single payment method, on the same fiat page.
// Best = highest net profit for the same nominal buy amount; ties use method name.
export function rankedSpreads(quotes,amount,defaultsOnly=false){
  const valid=quotes.filter(q=>!q.error && (!defaultsOnly || q.defaultKey)).map(q=>{
    const estimate=profit({buy:q.buy,sell:q.sell,amount});
    return estimate?{...q,estimate}:null;
  }).filter(Boolean);
  valid.sort((a,b)=>b.estimate.net-a.estimate.net || a.name.localeCompare(b.name));
  return valid;
}

export function recommendedSpread(quotes,amount,defaultsOnly=false){
  return rankedSpreads(quotes,amount,defaultsOnly)[0] || null;
}
