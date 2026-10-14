"""Binance public web endpoints. Cached, bounded requests; no API keys or trades."""

import json, re, threading, time, math, urllib.request, urllib.error, urllib.parse
from decimal import Decimal, InvalidOperation
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.utils import timezone
from .services import iso

DEFAULTS = [
    ("prex", "Prex", r"prex"),
    ("santander", "Santander", r"santander"),
    ("itau", "Itaú", r"itau"),
    ("oca", "OCA Blue", r"ocablue"),
    ("mercadopago", "MercadoPago", r"mercadopago"),
    ("brou", "BROU", r"bankrepublicuruguay|brou|bankoftherepublicofuruguay"),
]
_cache = {}
_scans = {}
_lock = threading.RLock()
_gate = threading.BoundedSemaphore(2)


def now():
    return iso(timezone.now())


def number(v):
    try:
        result = float(v) if v not in (None, "") else None
        return result if result is not None and math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def online(a):
    value = a.get("isOnline", a.get("userOnlineStatus", a.get("online")))
    if value in (True, 1, "1", "true", "ONLINE"):
        return True
    if value in (False, 0, "0", "false", "OFFLINE"):
        return False
    return None


def query(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        "https://www.binance.com/" + path,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "P2PPortfolio/1.0",
        },
    )
    try:
        with _gate, urllib.request.urlopen(request, timeout=12) as response:
            r = json.load(response)
    except urllib.error.HTTPError as e:
        raise ValueError(
            "Binance limitó las consultas (429). Espera un minuto."
            if e.code == 429
            else "Binance no permite consultar anuncios en este momento."
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise ValueError("No se pudo conectar con Binance. Intenta más tarde.")
    if not isinstance(r, dict):
        raise ValueError("Binance no devolvió una respuesta válida.")
    if r.get("success") is False or r.get("code") not in (None, "000000"):
        raise ValueError("Binance no devolvió datos válidos.")
    return r.get("data")


def methods(fiat):
    if settings.P2P_MARKET_DEMO:
        return [
            {"identifier": name.replace(" ", "").replace("í", "i"), "name": name}
            for _, name, _ in definitions(fiat)
        ]
    key = "methods:" + fiat
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
    data = query("bapi/c2c/v1/public/c2c/agent/trade-methods?fiat=" + fiat)
    if not isinstance(data, list):
        raise ValueError("Medios de pago no disponibles.")
    result = [
        {
            "identifier": m["identifier"],
            "name": m.get("tradeMethodName")
            or m.get("tradeMethodShortName")
            or m["identifier"],
        }
        for m in data
        if isinstance(m.get("identifier"), str)
    ]
    with _lock:
        _cache[key] = (time.monotonic() + 600, result)
    return result


def definitions(fiat):
    return DEFAULTS if fiat == "UYU" else [("airtm", "Airtm", r"airtm")]


def side(identifier, trade_type, fiat, amount=None, amount_unit="fiat"):
    try:
        if settings.P2P_MARKET_DEMO:
            base = 41 if fiat == "UYU" else 1
            price = (
                base + (0.9 if fiat == "UYU" else 0.018)
                if trade_type == "BUY"
                else base
            )
            result = {
                "ads": [
                    {
                        "id": identifier + trade_type + str(i),
                        "price": price + i * (0.03 if fiat == "UYU" else 0.001),
                        "online": i % 2 == 0,
                        "nickname": "Demo " + str(i + 1),
                        "userNo": "demo_" + str(i+1),
                        "asset": "USDT", "fiat": fiat, "tradeType": trade_type, "tradable": True,
                        "completion": 98.5,
                        "orders": 120,
                        "available": 1000,
                        "minFiat": 1000 if fiat == "UYU" else 20,
                        "maxFiat": 50000 if fiat == "UYU" else 1000,
                        "min": 20,
                        "max": 1000,
                        "limitUnit": "USDT",
                        "minutes": 15,
                        "methods": [identifier],
                        "methodDetails": [
                            {"identifier": identifier, "name": identifier}
                        ],
                        "merchant": True,
                    }
                    for i in range(10)
                ],
                "error": None,
                "updatedAt": now(),
            }
            for ad in result["ads"]:
                ad["min"] = None
                ad["effectiveMaxFiat"] = min(ad["maxFiat"], ad["available"] * ad["price"])
            if amount is not None:
                result["ads"] = [ad for ad in result["ads"] if compatible(ad, amount, amount_unit)]
            result["scanned"] = 10
            return result
        payload = {
                "fiat": fiat, "asset": "USDT", "tradeType": trade_type,
                "page": 1, "rows": 10, "payTypes": [identifier] if identifier else [], "publisherType": None,
            }
        if amount is not None and amount_unit == "fiat":
            payload["transAmount"] = str(amount)
        data = query("bapi/c2c/v2/friendly/c2c/adv/search", payload)
        if not isinstance(data, list):
            raise ValueError("Binance no devolvió una lista válida.")
        ads = [normalize_market_item(item, fiat) for item in data[:10]]
        scanned = len(data)
        if amount is not None:
            ads = [ad for ad in ads if compatible(ad, amount, amount_unit)]
            # One additional page, bounded requests, to fill the filtered sample.
            if len(ads) < 10 and len(data) == 10:
                payload["page"] = 2
                extra = query("bapi/c2c/v2/friendly/c2c/adv/search", payload)
                if not isinstance(extra, list):
                    raise ValueError("Binance no devolvió una lista válida.")
                scanned += len(extra)
                ads += [ad for item in extra[:10] if compatible(ad := normalize_market_item(item, fiat), amount, amount_unit)]
        seen = set()
        ads = [ad for ad in ads if ad["id"] and not (ad["id"] in seen or seen.add(ad["id"]))][:10]
        return {"ads": ads, "error": None, "updatedAt": now(), "scanned": scanned}
    except ValueError as e:
        return {"ads": [], "error": str(e), "updatedAt": None}


def group(method, fiat, amount=None, amount_unit="fiat"):
    key = fiat + ":" + method["identifier"] + ":" + str(amount) + ":" + amount_unit
    # Serial cache lock avoids simultaneous callers flooding the same method.
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        expired = [k for k, v in _cache.items() if v[0] <= time.monotonic()]
        for old in expired:
            _cache.pop(old, None)
        if len(_cache) >= 500:
            for old in list(_cache)[:100]:
                _cache.pop(old, None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        buy = pool.submit(side, method["identifier"], "BUY", fiat, amount, amount_unit)
        sell = pool.submit(side, method["identifier"], "SELL", fiat, amount, amount_unit)
        r = {
            "key": method["identifier"],
            "name": method["name"],
            "buy": buy.result(),
            "sell": sell.result(),
        }
    with _lock:
        _cache[key] = (
            time.monotonic() + (60 if r["buy"]["error"] or r["sell"]["error"] else 1),
            r,
        )
    return r


def market(fiat, identifier=None, amount=None, amount_unit="fiat"):
    amount = amount_value(amount)
    if amount_unit not in ["fiat", "USDT"]:
        raise ValueError("Unidad de monto inválida.")
    all_methods = methods(fiat)
    if identifier:
        method = next((m for m in all_methods if m["identifier"] == identifier), None)
        if not method:
            raise ValueError("Medio de pago no disponible para esa moneda.")
        return {"groups": [group(method, fiat, amount, amount_unit)], "fetchedAt": now()}
    groups = []
    for key, name, pattern in definitions(fiat):
        m = next(
            (m for m in all_methods if re.search(pattern, m["identifier"], re.I)), None
        )
        empty = {
            "ads": [],
            "error": "Medio no disponible en Binance.",
            "updatedAt": None,
        }
        g = group(m, fiat, amount, amount_unit) if m else {"name": name, "buy": empty, "sell": empty}
        groups.append({**g, "key": key})
    return {"groups": groups, "fetchedAt": now()}


def run_scan(scan, items, fiat):
    try:
        for m in items:
            g = group(m, fiat)
            buyers = [a["price"] for a in g["sell"]["ads"]]
            sellers = [a["price"] for a in g["buy"]["ads"]]
            error = g["buy"]["error"] or g["sell"]["error"]
            quote = {
                "key": m["identifier"],
                "name": m["name"],
                "defaultKey": m.get("defaultKey"),
                "buy": max(buyers) if buyers else None,
                "sell": min(sellers) if sellers else None,
                "error": error,
                "updatedAt": (
                    min(g["buy"]["updatedAt"], g["sell"]["updatedAt"])
                    if g["buy"]["updatedAt"] and g["sell"]["updatedAt"]
                    else None
                ),
            }
            with _lock:
                scan["quotes"].append(quote)
                scan["consulted"] += 1
                scan["failed"] += bool(error)
                scan["updatedAt"] = now()
            if error and "429" in error:
                scan["limited"] = True
                break
    except Exception:
        scan["error"] = "No se pudo completar la comparación."
    finally:
        with _lock:
            scan["complete"] = True
            scan["finishedAt"] = now()
            scan["_finished"] = time.monotonic()


def recommendations(fiat):
    with _lock:
        old = _scans.get(fiat)
        if old and (
            not old["complete"] or time.monotonic() - old.get("_finished", 0) < 60
        ):
            return scan_view(old)
    items = [dict(m) for m in methods(fiat)]
    defs = definitions(fiat)
    for key, name, pattern in defs:
        m = next((m for m in items if re.search(pattern, m["identifier"], re.I)), None)
        if m:
            m["defaultKey"] = key
    items.sort(key=lambda m: not m.get("defaultKey"))
    with _lock:
        old = _scans.get(fiat)
        if old and (
            not old["complete"] or time.monotonic() - old.get("_finished", 0) < 60
        ):
            return scan_view(old)
        scan = {
            "fiat": fiat,
            "quotes": [],
            "total": len(items),
            "consulted": 0,
            "failed": 0,
            "complete": False,
            "limited": False,
            "error": None,
            "startedAt": now(),
            "updatedAt": None,
            "finishedAt": None,
            "defaultTotal": len(defs),
            "defaultAvailable": sum(bool(m.get("defaultKey")) for m in items),
            "cacheSeconds": 60,
        }
        _scans[fiat] = scan
        threading.Thread(target=run_scan, args=(scan, items, fiat), daemon=True).start()
        return scan_view(scan)


def scan_view(scan):
    return {
        **{k: v for k, v in scan.items() if not k.startswith("_")},
        "quotes": list(scan["quotes"]),
        "defaultConsulted": sum(bool(q.get("defaultKey")) for q in scan["quotes"]),
    }


def amount_value(value):
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Indica un monto válido.")
    if not amount.is_finite() or amount <= 0 or amount > Decimal("10000000000") or amount != amount.quantize(Decimal(".00000001")):
        raise ValueError("Monto fuera de rango o con más de ocho decimales.")
    return amount


def normalize_market_item(item, fiat):
    if not isinstance(item, dict):
        raise ValueError("Anuncio inválido.")
    return normalize_ad(item.get("adv", {}), item.get("advertiser", {}), fiat=fiat)


def normalize_ad(a, user, fiat=None, trade_type=None):
    price = number(a.get("price"))
    if not price or price <= 0:
        raise ValueError("Anuncio con precio inválido.")
    if not isinstance(a, dict) or not isinstance(user, dict):
        raise ValueError("Anuncio inválido.")
    methods = a.get("tradeMethods") or []
    if not isinstance(methods, list):
        raise ValueError("Medios de pago del anuncio inválidos.")
    details = [{"identifier": str(m.get("identifier") or m.get("payType") or ""), "name": str(m.get("tradeMethodName") or m.get("tradeMethodShortName") or m.get("identifier") or "")} for m in methods if isinstance(m, dict)]
    maximum = number(a.get("maxSingleTransAmount"))
    available = number(a.get("tradableQuantity"))
    dynamic = number(a.get("dynamicMaxSingleTransAmount"))
    max_quantity = number(a.get("maxSingleTransQuantity"))
    dynamic_quantity = number(a.get("dynamicMaxSingleTransQuantity"))
    candidates = [v for v in [maximum, dynamic, available * price if available is not None else None, max_quantity * price if max_quantity is not None else None, dynamic_quantity * price if dynamic_quantity is not None else None] if v is not None and v >= 0]
    return {
        "id": str(a.get("advNo", "")), "userNo": str(user.get("userNo") or ""),
        "nickname": user.get("nickName") or "Nombre no informado",
        "price": price, "asset": str(a.get("asset") or "USDT"), "fiat": str(a.get("fiatUnit") or fiat or ""),
        "tradeType": str(a.get("tradeType") or trade_type or ""),
        "online": online(user), "completion": number(user.get("monthFinishRate")) * 100 if number(user.get("monthFinishRate")) is not None else None,
        "orders": number(user.get("monthOrderCount")), "available": available,
        "min": number(a.get("minSingleTransQuantity")), "max": number(a.get("maxSingleTransQuantity")),
        "minFiat": number(a.get("minSingleTransAmount")), "maxFiat": maximum,
        "effectiveMaxFiat": min(candidates) if candidates else None,
        "dynamicMaxQuantity": number(a.get("dynamicMaxSingleTransQuantity")),
        "minutes": number(a.get("payTimeLimit")), "methods": [d["identifier"] for d in details], "methodDetails": details,
        "merchant": user.get("userType") == "merchant", "tradable": a.get("isTradable") is not False,
        "remarks": str(a.get("remarks") or "")[:4000], "limitUnit": "USDT",
    }


def compatible(ad, amount, unit="fiat"):
    if not ad.get("tradable", True):
        return False
    if unit == "USDT" and ad.get("asset", "USDT") != "USDT":
        return False
    price = Decimal(str(ad["price"]))
    quantity = amount / price if unit == "fiat" else amount
    fiat_amount = amount if unit == "fiat" else amount * price
    # Unknown availability or fiat limits cannot establish compatibility.
    for field in ["minFiat", "maxFiat", "effectiveMaxFiat", "available"]:
        if ad.get(field) is None:
            return False
    if not Decimal(str(ad["minFiat"])) <= fiat_amount <= Decimal(str(ad["effectiveMaxFiat"])):
        return False
    if quantity > Decimal(str(ad["available"])):
        return False
    if ad.get("min") is not None and quantity < Decimal(str(ad["min"])):
        return False
    if ad.get("max") is not None and quantity > Decimal(str(ad["max"])):
        return False
    if ad.get("dynamicMaxQuantity") is not None and quantity > Decimal(str(ad["dynamicMaxQuantity"])):
        return False
    return True


def advertiser(user_no):
    if not isinstance(user_no, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", user_no):
        raise ValueError("Identificador de anunciante inválido.")
    key = "advertiser:" + user_no + (":demo" if settings.P2P_MARKET_DEMO else ":real")
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
    if settings.P2P_MARKET_DEMO:
        if not re.fullmatch(r"demo_\d+", user_no):
            raise ValueError("Anunciante no disponible en la demostración.")
        i = int(user_no.split("_")[1]); user = {"userNo":user_no,"nickName":"Demo " + str(i),"monthOrderCount":120,"monthFinishRate":.985}
        data = {"userDetailVo":user, "buyList":[{"advNo":"profile-buy-"+user_no,"tradeType":"BUY","asset":"USDT","fiatUnit":"UYU","price":"41","minSingleTransAmount":"1000","maxSingleTransAmount":"50000","tradableQuantity":"1000","tradeMethods":[{"identifier":"Santander","tradeMethodName":"Santander"}]}], "sellList":[{"advNo":"profile-sell-"+user_no,"tradeType":"SELL","asset":"USDT","fiatUnit":"USD","price":"1.02","minSingleTransAmount":"20","maxSingleTransAmount":"1000","tradableQuantity":"500","tradeMethods":[{"identifier":"Airtm","tradeMethodName":"Airtm"}]}]}
    else:
        data = query("bapi/c2c/v2/friendly/c2c/user/profile-and-ads-list?" + urllib.parse.urlencode({"userNo":user_no}))
    if not isinstance(data, dict) or not isinstance(data.get("userDetailVo"), dict):
        raise ValueError("Binance no devolvió un perfil válido.")
    user = data["userDetailVo"]
    if user.get("userNo") and str(user["userNo"]) != user_no:
        raise ValueError("El perfil no corresponde al anunciante solicitado.")
    ads=[]; seen=set()
    for field, kind in [("buyList","BUY"),("sellList","SELL")]:
        rows = data.get(field)
        if not isinstance(rows, list):
            raise ValueError("Binance no devolvió la lista pública completa de este perfil.")
        for a in rows[:200]:
            if not isinstance(a, dict) or a.get("advStatus") not in [None, 1] or not a.get("advNo"):
                continue
            ad=normalize_ad(a, user, trade_type=kind)
            if ad["id"] not in seen:
                ads.append(ad);seen.add(ad["id"])
    result={"userNo":user_no,"nickname":str(user.get("nickName") or "Anunciante"),"orders":number(user.get("orderCount")),"completion":number(user.get("monthFinishRate"))*100 if number(user.get("monthFinishRate")) is not None else None,"ads":ads,"updatedAt":now(),"demo":settings.P2P_MARKET_DEMO,"limited":any(len(data[k])>200 for k in ["buyList","sellList"])}
    with _lock:
        # Small cap avoids indefinite growth as different profiles are visited.
        keys=[k for k in _cache if k.startswith("advertiser:")]
        if len(keys)>=100:
            for old in keys[:20]:_cache.pop(old, None)
        _cache[key]=(time.monotonic()+30,result)
    return result


def own_ads(username, hint=""):
    """Resolve a public profile from bounded samples; never infer changes from a search list."""
    username = username.strip()
    key = "own-profile:" + username.casefold() + (":demo" if settings.P2P_MARKET_DEMO else ":real")
    with _lock:
        hit = _cache.get(key)
    candidate = hint or (hit[1] if hit and hit[0] > time.monotonic() else "")
    if candidate:
        profile = advertiser(candidate)
        if profile["nickname"].strip().casefold() != username.casefold():
            if hint:
                raise ValueError("El perfil no corresponde al usuario Binance del operador.")
            candidate = ""
        else:
            with _lock:
                _cache[key] = (time.monotonic() + 3600, candidate)
            return {"status": "watching", **profile}
    # A failed lookup is cached briefly to keep absent profiles from causing repeated scans.
    if hit and hit[0] > time.monotonic() and not hit[1]:
        return {"status": "not_found", "message": "Tu perfil no aparece en la muestra consultada. Abre un mercado donde se vea tu anuncio; el monitor lo identificará automáticamente."}
    errors = []
    for fiat in ("UYU", "USD"):
        for kind in ("SELL", "BUY"):
            result = side("", kind, fiat)
            if result["error"]:
                errors.append(result["error"])
            for ad in result["ads"]:
                if ad.get("userNo") and ad["nickname"].strip().casefold() == username.casefold():
                    return own_ads(username, ad["userNo"])
    if errors:
        raise ValueError(errors[0])
    with _lock:
        if len([k for k in _cache if k.startswith("own-profile:")]) > 100:
            for k in list(_cache):
                if k.startswith("own-profile:"): _cache.pop(k, None)
        _cache[key] = (time.monotonic() + 60, "")
    return {"status": "not_found", "message": "Tu perfil no aparece en la muestra consultada. Abre un mercado donde se vea tu anuncio; el monitor lo identificará automáticamente."}
