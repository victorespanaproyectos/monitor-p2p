"""Two-step import: validate all rows before transaction; duplicates never overwritten."""

import base64, json
from django.db import transaction
from django.utils import timezone
from .models import Account, Order, Movement
from . import services as s


def import_plan(op, payload, mapping):
    if (
        not isinstance(payload, dict)
        or payload.get("version") != 1
        or not isinstance(payload.get("orders"), list)
    ):
        raise ValueError("Selecciona un respaldo JSON versión 1.")
    if len(payload["orders"]) > 20000:
        raise ValueError("Máximo 20.000 órdenes por importación.")
    accounts = {a.key: a for a in op.accounts.filter(active=True)}
    existing = set(op.orders.values_list("number", flat=True))
    seen = set()
    new = []
    issues = []
    duplicates = 0
    from .views import receipt_data

    for index, r in enumerate(payload["orders"], 1):
        try:
            if not isinstance(r, dict):
                raise ValueError("Orden inválida.")
            num = str(r.get("number", "")).strip()
            if not num or len(num) > 100:
                raise ValueError("Número inválido.")
            if num in seen:
                raise ValueError("Número repetido dentro del archivo.")
            seen.add(num)
            if num in existing:
                duplicates += 1
                continue
            if r.get("type") not in ["buy", "sell"]:
                raise ValueError("Tipo inválido.")
            key = (
                mapping.get(r.get("accountKey"))
                or mapping.get(r.get("paymentMethod"))
                or r.get("accountKey")
            )
            if key not in accounts:
                raise ValueError(
                    "Asigna una cuenta para "
                    + str(r.get("paymentMethod") or r.get("accountKey"))
                )
            a = accounts[key]
            if str(r.get("paymentMethod", "")).lower() == "airtm" and not r.get(
                "currency"
            ):
                raise ValueError(
                    "Airtm antiguo sin moneda: confirma USD y sus importes antes de importar."
                )
            cur = r.get("currency") or (
                "USD" if str(r.get("paymentMethod", "")).lower() == "airtm" else "UYU"
            )
            if cur != a.currency:
                raise ValueError("Moneda y cuenta no coinciden.")
            cents = s.decimal(
                r.get("amountCents"), "Centavos", 0, s.D(1), s.D("1000000000000")
            )
            amount = cents / 100
            price = s.decimal(
                r.get("price"), "Precio", 6, s.D(".000001"), s.D("1000000000")
            )
            date = s.datevalue(r.get("date"))
            fee = s.decimal(
                r.get("feeRate", op.commission), "Comisión", 6, maximum=s.D(".1")
            )
            status = r.get("status", "completed")
            if status not in ["pending", "completed", "cancelled"]:
                raise ValueError("Estado inválido.")
            expense_rate = s.decimal(r.get("expenseRate", 0), "Cargo porcentual", 6, maximum=s.D(1))
            expense_fixed = s.decimal(r.get("expenseFixed", 0), "Gasto fijo", 2)
            if r["type"] == "sell" and (amount * expense_rate + expense_fixed).quantize(s.D(".01"), rounding=s.ROUND_HALF_UP) > amount:
                raise ValueError("Gastos superiores a la venta.")
            receipt = None
            if r.get("receipt", {}):
                if r["receipt"].get("data"):
                    receipt = receipt_data(r["receipt"])
            new.append(
                {
                    "number": num,
                    "type": r["type"],
                    "account": a,
                    "payment_method": str(r.get("paymentMethod") or a.name)[:100],
                    "currency": cur,
                    "amount": amount,
                    "price": price,
                    "date": date,
                    "fee_rate": fee,
                    "status": status,
                    "expense_rate": expense_rate,
                    "expense_fixed": expense_fixed,
                    "expense_note": str(r.get("expenseNote", ""))[:300],
                    "receipt": receipt,
                    "created_at": r.get("createdAt"),
                    "missingReceipt": bool(r.get("receipt") and not receipt),
                }
            )
        except (ValueError, TypeError, KeyError) as e:
            issues.append(
                {
                    "row": index,
                    "number": str(r.get("number", "")) if isinstance(r, dict) else "",
                    "error": str(e),
                }
            )
    movements = (
        payload.get("movements", {}).get("withdrawals", [])
        if isinstance(payload.get("movements"), dict)
        else []
    )
    movement_new = []
    known = {str(m.id) for m in op.movements.all()}
    seen_movements = set()
    import uuid

    for r in movements:
        try:
            source_id = str(uuid.UUID(str(r["id"])))
            mid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"p2p-import:{op.id}:{source_id}"))
            if mid in known or source_id in known:
                continue
            if mid in seen_movements:
                raise ValueError("Movimiento duplicado en archivo.")
            seen_movements.add(mid)
            key = mapping.get(r.get("accountKey")) or r.get("accountKey")
            a = accounts.get(key)
            if not a:
                raise ValueError("Asigna la cuenta del movimiento.")
            if r.get("currency", a.currency) != a.currency:
                raise ValueError("Moneda del movimiento incompatible.")
            kind = r.get("kind", "withdrawal")
            if kind not in ["deposit", "withdrawal"]:
                raise ValueError("Movimiento inválido.")
            movement_new.append(
                {
                    "id": mid,
                    "account": a,
                    "kind": kind,
                    "amount": s.decimal(
                        r.get("amountCents"),
                        "Centavos",
                        0,
                        s.D(1),
                        s.D("1000000000000"),
                    )
                    / 100,
                    "date": s.datevalue(r.get("date")),
                    "note": str(r.get("note", ""))[:300],
                }
            )
        except (ValueError, TypeError, KeyError) as e:
            issues.append({"error": "Movimiento: " + str(e)})
    summary = {
        "sourceOperator": payload.get("operator"),
        "sourceOperatorName": payload.get("operatorName"),
        "targetOperator": op.name,
        "existing": op.orders.count(),
        "new": len(new),
        "duplicates": duplicates,
        "total": op.orders.count() + len(new),
        "newMovements": len(movement_new),
        "missingReceipts": sum(r["missingReceipt"] for r in new),
        "issues": issues,
        "canImport": not issues,
        "preview": [
            {
                "number": r["number"],
                "type": r["type"],
                "amount": r["amount"],
                "currency": r["currency"],
                "account": r["account"].name,
                "date": s.iso(r["date"]),
            }
            for r in new[:100]
        ],
    }
    return summary, new, movement_new


def execute(op, payload, mapping, preserve=True):
    summary, rows, moves = import_plan(op, payload, mapping)
    if summary["issues"]:
        raise ValueError("Corrige todos los errores de la revisión antes de importar.")
    before = s.inventory(op)
    for r in rows:
        receipt = r.pop("receipt")
        r.pop("missingReceipt")
        created = r.pop("created_at")
        o = Order.objects.create(operator=op, **r)
        if receipt:
            o.receipt, o.receipt_name, o.receipt_mime = receipt
            o.save()
        if created:
            try:
                Order.objects.filter(pk=o.pk).update(created_at=s.datevalue(created))
            except ValueError:
                pass
    for r in moves:
        Movement.objects.create(operator=op, **r)
    if preserve:
        s.rebase(op, before)
    inv = s.inventory(op)
    if op.orders.filter(status="pending").exists() and inv["needsReview"]:
        raise ValueError("Las reservas importadas superan el saldo disponible. Concilia el saldo antes de importar.")
    return summary
