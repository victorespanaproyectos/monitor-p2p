// Pure comparison rules. Missing ads/fields do not establish a change.
export function changes(previous, current) {
  const labels={available:'Disponibles',price:'Precio',minFiat:'Mínimo',maxFiat:'Máximo configurado',effectiveMaxFiat:'Máximo efectivo'};
  const result=[];
  for(const [key,label] of Object.entries(labels)) {
    const a=previous?.[key], b=current?.[key];
    if(typeof a==='number' && typeof b==='number' && Number.isFinite(a) && Number.isFinite(b) && Math.abs(a-b)>1e-8)
      result.push({key,label,before:a,after:b});
  }
  return result;
}
export function compareProfile(previous, profile, name) {
  const identity=name+'|'+profile.userNo;
  const time=Date.parse(profile.updatedAt);
  if(!Number.isFinite(time))return {snapshot:previous,events:[]};
  if(previous?.identity===identity && time<=previous.time)return {snapshot:previous,events:[]};
  const ads=Object.fromEntries(profile.ads.filter(a=>a.id).map(a=>[a.id,a]));
  const events=[];
  if(previous?.identity===identity)for(const [id,ad] of Object.entries(ads)) {
    const old=previous.ads[id];
    // Same ID but a changed asset/currency is treated as a fresh baseline.
    if(old && old.asset===ad.asset && old.fiat===ad.fiat && old.tradeType===ad.tradeType) {
      const diff=changes(old,ad);if(diff.length)events.push({id,ad,diff});
    }
  }
  return {snapshot:{identity,time,ads},events};
}
