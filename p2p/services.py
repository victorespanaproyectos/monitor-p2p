"""Financial rules: Decimal, independent currencies, FIFO and snapshot reconciliation."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from datetime import datetime, timedelta
from collections import defaultdict
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Account, DailySnapshot

D = Decimal
ZERO = D(0)


def decimal(value, label="Monto", places=None, minimum=ZERO, maximum=D("10000000000")):
    try:
        r = D(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label}: indica un número válido.")
    if not r.is_finite() or r < minimum or r > maximum:
        raise ValueError(f"{label}: fuera del rango permitido.")
    if places is not None and r != r.quantize(D(10) ** -places):
        raise ValueError(f"{label}: admite hasta {places} decimales.")
    return r


def datevalue(value):
    r = parse_datetime(str(value))
    if not r:
        raise ValueError("Indica una fecha válida.")
    if timezone.is_naive(r):
        raise ValueError("La fecha debe incluir zona horaria.")
    return r


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


def numeric(value):
    if isinstance(value, D):
        return float(value)
    if isinstance(value, dict):
        return {k: numeric(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [numeric(v) for v in value]
    return value


def banklist(op):
    return [
        {"key": a.key, "name": a.name, "currency": a.currency, "active": a.active}
        for a in op.accounts.all()
    ]


def default_accounts(op):
    for key, name, cur in [
        ("santander", "Santander", "UYU"),
        ("ocaBlue", "OCA Blue", "UYU"),
        ("prex", "Prex", "UYU"),
        ("mercadoPago", "Mercado Pago", "UYU"),
        ("itau", "Itaú", "UYU"),
        ("brou", "BROU", "UYU"),
        ("airtm", "Airtm", "USD"),
    ]:
        Account.objects.get_or_create(
            operator=op, key=key, defaults={"name": name, "currency": cur}
        )


def expenses(order):
    return (order.amount * order.expense_rate + order.expense_fixed).quantize(D(".01"), rounding=ROUND_HALF_UP)


def effect(order):
    if order.status != "completed":
        return {"account": order.account.key, "cash": "0", "funds": "0"}
    gross = order.amount / order.price
    return {
        "account": order.account.key,
        "cash": str(order.amount * (-1 if order.type == "buy" else 1) - expenses(order)),
        "funds": str(
            (
                gross
                * (1 - order.fee_rate if order.type == "buy" else -(1 + order.fee_rate))
            ).quantize(D(".00000001"), rounding=ROUND_HALF_UP)
        ),
    }


def movement_effect(m):
    return {
        "account": m.account.key,
        "cash": str(m.amount * (1 if m.kind == "deposit" else -1)),
        "funds": "0",
    }


def inventory(op):
    balances = {a.key: a.balance for a in op.accounts.all()}
    funds = op.funds

    def apply(e, sign):
        nonlocal funds
        if e["account"] in balances:
            balances[e["account"]] += D(e["cash"]) * sign
        funds += D(e["funds"]) * sign

    for e in op.order_baseline.values():
        apply(e, -1)
    for e in op.movement_baseline.values():
        apply(e, -1)
    for o in op.orders.select_related("account"):
        apply(effect(o), 1)
    for m in op.movements.select_related("account"):
        apply(movement_effect(m), 1)
    reserved = {key: ZERO for key in balances}
    reserved_funds = ZERO
    for o in op.orders.filter(status="pending").select_related("account"):
        if o.type == "buy":
            reserved[o.account.key] += o.amount + expenses(o)
        else:
            reserved_funds += (o.amount / o.price * (1 + o.fee_rate)).quantize(D(".00000001"), rounding=ROUND_HALF_UP)
    available = {key: balances[key] - reserved[key] for key in balances}
    return {
        "reservedAccounts": reserved,
        "availableAccounts": available,
        "reservedBinance": reserved_funds,
        "availableBinance": funds - reserved_funds,
        "pendingCount": op.orders.filter(status="pending").count(),
        "accounts": balances,
        "binance": funds,
        "funds": funds,
        "earn": ZERO,
        "updatedAt": iso(op.updated_at),
        "automatic": True,
        "needsReview": funds - reserved_funds < 0 or any(v < 0 for v in available.values()),
    }


def check_reservations(op, before):
    inv = inventory(op)
    for key, reserve in inv["reservedAccounts"].items():
        if reserve > 0 and inv["availableAccounts"][key] < 0 and (inv["availableAccounts"][key] < before["availableAccounts"][key] or not before["reservedAccounts"][key]):
            raise ValueError("El cambio dejaría reservas sin saldo en la cuenta. Revisa las órdenes pendientes.")
    if inv["reservedBinance"] > 0 and inv["availableBinance"] < 0 and (inv["availableBinance"] < before["availableBinance"] or not before["reservedBinance"]):
        raise ValueError("El cambio dejaría reservas sin USDT. Revisa las órdenes pendientes.")


def rebase(op, inv):
    for a in op.accounts.all():
        a.balance = inv["accounts"].get(a.key, ZERO)
        a.save(update_fields=["balance"])
    op.funds = inv["binance"]
    op.order_baseline = {
        str(o.id): effect(o) for o in op.orders.select_related("account")
    }
    op.movement_baseline = {
        str(m.id): movement_effect(m) for m in op.movements.select_related("account")
    }


def order_json(o, receipt_data=False):
    q = o.amount / o.price
    fee = q * o.fee_rate
    receipt = None
    if o.receipt:
        receipt = {
            "file": str(o.id),
            "name": o.receipt_name,
            "mime": o.receipt_mime,
            "size": len(o.receipt),
        }
        if receipt_data:
            import base64

            receipt["data"] = base64.b64encode(bytes(o.receipt)).decode()
    return {
        "id": str(o.id),
        "type": o.type,
        "status": o.status,
        "expenseRate": o.expense_rate,
        "expenseFixed": o.expense_fixed,
        "expenseNote": o.expense_note,
        "expenses": expenses(o),
        "cashTotal": o.amount + expenses(o) if o.type == "buy" else o.amount - expenses(o),
        "number": o.number,
        "paymentMethod": o.payment_method,
        "currency": o.currency,
        "accountKey": o.account.key,
        "price": o.price,
        "amount": o.amount,
        "amountCents": int(o.amount * 100),
        "quantity": q,
        "commission": fee,
        "feeRate": o.fee_rate,
        "total": o.amount,
        "netQuantity": q - fee if o.type == "buy" else q + fee,
        "date": iso(o.date),
        "createdAt": iso(o.created_at),
        "updatedAt": iso(o.updated_at),
        "receipt": receipt,
    }


def movement_json(m):
    return {
        "id": str(m.id),
        "kind": m.kind,
        "accountKey": m.account.key,
        "currency": m.account.currency,
        "amountCents": int(m.amount * 100),
        "date": iso(m.date),
        "note": m.note,
        "createdAt": iso(m.created_at),
        "updatedAt": iso(m.updated_at),
    }


def averages(op):
    def unit(cur):
        result = {}
        for side in ["buy", "sell"]:
            rows = list(op.orders.filter(currency=cur, type=side, status="completed"))
            amount = sum((o.amount for o in rows), ZERO)
            quantity = sum((o.amount / o.price for o in rows), ZERO)
            result[side] = {
                "price": amount / quantity if quantity else None,
                "count": len(rows),
                "amount": amount,
                "quantity": quantity,
            }
        return result

    return {**unit("UYU"), "usd": unit("USD")}


def valuation(op, inv=None, av=None):
    inv = inv or inventory(op)
    av = av or averages(op)
    rate = op.commission

    def pesos(q):
        return (
            ZERO
            if q == 0
            else q / (1 + rate) * av["sell"]["price"] if av["sell"]["price"] else None
        )

    accounts = []
    for a in op.accounts.all():
        amount = inv["accounts"][a.key]
        buy = (av["usd"] if a.currency == "USD" else av)["buy"]["price"]
        gross = ZERO if amount == 0 else amount / buy if buy else None
        net = gross * (1 - rate) if gross is not None else None
        accounts.append(
            {
                "key": a.key,
                "name": a.name,
                "currency": a.currency,
                "amount": amount,
                "gross": gross,
                "fee": gross * rate if gross is not None else None,
                "net": net,
                "pesos": (
                    amount
                    if a.currency == "UYU"
                    else pesos(net) if net is not None else None
                ),
            }
        )
    available_net = ZERO
    for a in op.accounts.filter(active=True):
        price = (av["usd"] if a.currency == "USD" else av)["buy"]["price"]
        amount = inv["availableAccounts"][a.key]
        if amount and not price:
            available_net = None
            break
        if price:
            available_net += amount / price * (1 - rate)
    bank = sum((a["amount"] for a in accounts if a["currency"] == "UYU"), ZERO)
    usd = [a for a in accounts if a["currency"] == "USD"]
    airtm = (
        None
        if any(a["pesos"] is None for a in usd)
        else sum((a["pesos"] for a in usd), ZERO)
    )
    binance = pesos(inv["binance"])
    buygross = (
        None
        if any(a["gross"] is None for a in accounts)
        else sum((a["gross"] for a in accounts), ZERO)
    )
    return {
        "accounts": accounts,
        "availableBuyNet": available_net,
        "bankTotal": bank,
        "airtmPesos": airtm,
        "buyGross": buygross,
        "buyFee": buygross * rate if buygross is not None else None,
        "buyNet": buygross * (1 - rate) if buygross is not None else None,
        "binanceTotal": inv["binance"],
        "binanceFee": inv["binance"] - inv["binance"] / (1 + rate),
        "binancePesos": binance,
        "fundsPesos": binance,
        "earnPesos": ZERO,
        "totalPesos": (
            None if binance is None or airtm is None else bank + airtm + binance
        ),
    }


def report(op, currency="UYU", start="", end=""):
    if currency not in ["UYU", "USD"]:
        raise ValueError("Moneda no admitida.")
    if start:
        from datetime import date

        date.fromisoformat(start)
    if end:
        from datetime import date

        date.fromisoformat(end)
    if start and end and start > end:
        raise ValueError("Rango de fechas inválido.")
    orders = list(op.orders.filter(currency=currency, status="completed").select_related("account"))
    lots = []
    sales = {}
    head = 0
    for o in orders:
        q = o.amount / o.price
        if o.type == "buy":
            lots.append([q * (1 - o.fee_rate), (o.amount + expenses(o)) / (q * (1 - o.fee_rate))])
            continue
        delivered = q * (1 + o.fee_rate)
        remaining = delivered
        cost = ZERO
        while remaining > D("0.000000001") and head < len(lots):
            take = min(remaining, lots[head][0])
            cost += take * lots[head][1]
            remaining -= take
            lots[head][0] -= take
            if lots[head][0] <= D("0.000000001"):
                head += 1
        missing = max(remaining, ZERO)
        matched = delivered - missing
        proceeds = (o.amount - expenses(o)) * matched / delivered
        sales[str(o.id)] = {
            "matched": matched,
            "missing": missing,
            "cost": cost,
            "proceeds": proceeds,
            "profit": proceeds - cost,
            "grossProceeds": o.amount * matched / delivered,
            "saleExpenses": expenses(o) * matched / delivered,
        }

    def within(dt):
        day = timezone.localtime(dt).date().isoformat()
        return (not start or day >= start) and (not end or day <= end)

    selected = [o for o in orders if within(o.date)]
    t = {
        key: ZERO
        for key in [
            "buy",
            "sell",
            "buyTotal",
            "sellTotal",
            "fees",
            "expenses",
            "count",
            "buyQuantity",
            "sellQuantity",
            "profit",
            "missing",
            "matched",
        ]
    }
    methods = {}
    days = {}
    for o in selected:
        side = o.type
        key = o.payment_method.casefold()
        name = o.payment_method
        day = timezone.localtime(o.date).date().isoformat()
        q = o.amount / o.price
        fee = q * o.fee_rate
        if key not in methods:
            methods[key] = {
                "key": key,
                "name": name,
                **{
                    k: ZERO
                    for k in [
                        "buy",
                        "sell",
                        "volume",
                        "fees",
                        "count",
                        "profit",
                        "missing",
                        "buyTotal",
                        "sellTotal",
                    ]
                },
            }
        if day not in days:
            days[day] = {"date": day, "methods": {}, "buy": ZERO, "sell": ZERO}
        daily = days[day]
        daily["methods"].setdefault(
            key, {"key": key, "name": name, "buy": ZERO, "sell": ZERO}
        )
        m = methods[key]
        t[side] += o.amount
        t[side + "Total"] += o.amount + (expenses(o) if side == "buy" else -expenses(o))
        t["expenses"] += expenses(o)
        t[side + "Quantity"] += q
        t["fees"] += fee
        t["count"] += 1
        m[side] += o.amount
        m[side + "Total"] += o.amount + (expenses(o) if side == "buy" else -expenses(o))
        m["volume"] += o.amount
        m["fees"] += fee
        m["count"] += 1
        daily[side] += o.amount
        daily["methods"][key][side] += o.amount
        if side == "sell":
            sale = sales[str(o.id)]
            for k in ["profit", "missing", "matched"]:
                t[k] += sale[k]
            for k in ["profit", "missing"]:
                m[k] += sale[k]
    withdrawals = [
        m
        for m in op.movements.select_related("account").filter(
            kind="withdrawal", account__currency=currency
        )
        if within(m.date)
    ]
    t["withdrawals"] = sum((m.amount for m in withdrawals), ZERO)
    t["reserve"] = max(ZERO, t["profit"]) / 10
    t["afterWithdrawals"] = t["profit"] - t["withdrawals"]
    t["volume"] = t["buy"] + t["sell"]
    t["cash"] = t["sellTotal"] - t["buyTotal"]
    t["cashAfterWithdrawals"] = t["cash"] - t["withdrawals"]
    return {
        "currency": currency,
        "selected": [order_json(o) for o in op.orders.filter(currency=currency).select_related("account") if within(o.date)],
        "statusCounts": {status: sum(1 for o in op.orders.filter(currency=currency, status=status) if within(o.date)) for status in ["pending", "completed", "cancelled"]},
        "totals": t,
        "methods": sorted(methods.values(), key=lambda m: (-m["volume"], m["name"])),
        "withdrawals": [movement_json(m) for m in withdrawals],
        "days": sorted(days.values(), key=lambda d: d["date"]),
        "sales": sales,
    }


def withdrawal_totals(op):
    t = {"UYU": ZERO, "USD": ZERO}
    for m in op.movements.select_related("account").filter(kind="withdrawal"):
        t[m.account.currency] += m.amount
    return t


def snapshot(op):
    today = timezone.localdate()
    total = valuation(op)["totalPesos"]
    withdrawals = {k: str(v) for k, v in withdrawal_totals(op).items()}
    DailySnapshot.objects.update_or_create(
        operator=op, day=today, defaults={"total": total, "withdrawals": withdrawals}
    )


def profits(operators):
    rows = []
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    prior = []
    eq = ZERO
    usd = ZERO
    uyu = ZERO
    pending = False
    for op in operators:
        inv = inventory(op)
        av = averages(op)
        val = valuation(op, inv, av)
        a = report(op)["totals"]
        b = report(op, "USD")["totals"]
        old = DailySnapshot.objects.filter(operator=op, day=yesterday).first()
        prior.append(old)
        wt = withdrawal_totals(op)
        if old:
            du = wt["UYU"] - D(old.withdrawals.get("UYU", "0"))
            ds = wt["USD"] - D(old.withdrawals.get("USD", "0"))
            uyu += du
            usd += ds
            eq += du
            if ds:
                if not av["usd"]["buy"]["price"] or not av["sell"]["price"]:
                    pending = True
                else:
                    eq += (
                        ds
                        / av["usd"]["buy"]["price"]
                        * (1 - op.commission)
                        / (1 + op.commission)
                        * av["sell"]["price"]
                    )
        rows.append(
            {
                "operator": str(op.id),
                "name": op.name,
                "inventoryTotal": val["totalPesos"],
                "inventoryNeedsReview": inv["needsReview"],
                "profit": a["profit"],
                "profitUSD": b["profit"],
                "missing": a["missing"],
                "missingUSD": b["missing"],
                "withdrawals": a["withdrawals"],
            }
        )
        snapshot(op)
    total = (
        None
        if any(r["inventoryTotal"] is None for r in rows)
        else sum((r["inventoryTotal"] for r in rows), ZERO)
    )
    previous = None
    if prior and all(prior):
        previous = {
            "total": (
                None
                if any(p.total is None for p in prior)
                else sum((p.total for p in prior), ZERO)
            ),
            "updatedAt": iso(max(p.updated_at for p in prior)),
        }
    change = (
        total - previous["total"]
        if previous and total is not None and previous["total"] is not None
        else None
    )
    retire = None if not previous or pending else eq
    comparison = {
        "today": str(today),
        "yesterday": str(yesterday),
        "previous": previous,
        "change": change,
        "percent": (
            change / previous["total"] * 100
            if change is not None and previous["total"] > 0
            else None
        ),
        "withdrawalsEquivalent": retire,
        "withdrawalsUSD": usd if previous else None,
        "withdrawalsUYU": uyu if previous else None,
        "withdrawalBasis": "snapshots" if previous else None,
        "adjustedChange": (
            change + retire if change is not None and retire is not None else None
        ),
    }
    return {
        "operators": rows,
        "inventoryTotal": total,
        "total": sum((r["profit"] for r in rows), ZERO),
        "totalUSD": sum((r["profitUSD"] for r in rows), ZERO),
        "missing": sum((r["missing"] for r in rows), ZERO),
        "inventoryComparison": comparison,
        "updatedAt": iso(timezone.now()),
    }


def calculate(buy, sell, amount, rate, buy_expense_rate=0, sell_expense_rate=0, buy_fixed=0, sell_fixed=0):
    buy = decimal(buy, "Precio de compra", 6, D(".000001"), D("1000000000"))
    sell = decimal(sell, "Precio de venta", 6, D(".000001"), D("1000000000"))
    q = decimal(amount, "USDT", 8, D(".00000001"), D("200000000"))
    received = q * (1 - rate)
    sellq = received / (1 + rate)
    purchase = q * buy
    sale = sellq * sell
    br = decimal(buy_expense_rate, "Cargo de compra", 6, maximum=D(1))
    sr = decimal(sell_expense_rate, "Cargo de venta", 6, maximum=D(1))
    bf = decimal(buy_fixed, "Gasto fijo de compra", 2)
    sf = decimal(sell_fixed, "Gasto fijo de venta", 2)
    buy_costs = (purchase * br + bf).quantize(D(".01"), rounding=ROUND_HALF_UP)
    sell_costs = (sale * sr + sf).quantize(D(".01"), rounding=ROUND_HALF_UP)
    cost = purchase + buy_costs
    proceeds = sale - sell_costs
    return {
        "quantity": q,
        "sellQuantity": sellq,
        "received": received,
        "purchase": purchase,
        "sale": sale,
        "extraCosts": buy_costs + sell_costs,
        "buyCosts": buy_costs,
        "sellCosts": sell_costs,
        "cost": cost,
        "proceeds": proceeds,
        "buyCommission": q * rate,
        "sellCommission": sellq * rate,
        "fees": (q + sellq) * rate,
        "gross": q * (sell - buy),
        "net": proceeds - cost,
        "roi": (proceeds - cost) / cost * 100,
        "spread": sell - buy,
        "spreadPercent": (sell - buy) / buy * 100,
    }
