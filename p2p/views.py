import base64, binascii, json, re, uuid
from pathlib import Path
from functools import wraps
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, IntegrityError, connection
from django.db.models import F
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from .models import Operator, Account, Order, Movement, Audit
from . import services as s, market as markets

User = get_user_model()


def reply(data, status=200):
    return JsonResponse(
        s.numeric(data), status=status, json_dumps_params={"ensure_ascii": False}
    )


def api(fn):
    @wraps(fn)
    def call(request, *args, **kwargs):
        try:
            return fn(request, *args, **kwargs)
        except (
            ValueError,
            TypeError,
            KeyError,
            ValidationError,
            json.JSONDecodeError,
        ) as e:
            return reply(
                {
                    "error": (
                        "; ".join(e.messages)
                        if isinstance(e, ValidationError)
                        else str(e)
                    )
                },
                400,
            )
        except Http404:
            return reply({"error": "Registro no encontrado o sin acceso."}, 404)
        except PermissionDenied:
            return reply({"error": "Esta acción requiere Administrador."}, 403)
        except IntegrityError:
            return reply(
                {
                    "error": "Registro duplicado o cambio concurrente. Recarga y revisa los datos."
                },
                409,
            )

    return call


def body(request):
    if not request.content_type.startswith("application/json"):
        raise ValueError("Envía datos JSON.")
    r = json.loads(request.body)
    if not isinstance(r, dict):
        raise ValueError("Datos inválidos.")
    return r


def allowed(user):
    return (
        Operator.objects.filter(active=True)
        if user.is_superuser
        else user.operators.filter(active=True)
    )


def operator(request, lock=False):
    key = request.GET.get("operator")
    if not key:
        raise ValueError("Selecciona un operador.")
    qs = allowed(request.user)
    if lock:
        qs = qs.select_for_update()
    op = get_object_or_404(qs, id=key)
    if lock and connection.vendor == "sqlite":
        Operator.objects.filter(pk=op.pk).update(revision=F("revision"))
        op.refresh_from_db()
    return op


def admin_required(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Esta acción requiere Administrador.")


def account(op, key, active=True):
    qs = op.accounts.all()
    if active:
        qs = qs.filter(active=True)
    a = qs.filter(key=key).first()
    if not a:
        raise ValueError("La cuenta no corresponde al operador o está desactivada.")
    return a


def name(value, maxlen, label):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maxlen:
        raise ValueError(f"{label}: indica un texto de hasta {maxlen} caracteres.")
    return value.strip()


def audit(request, op, action, detail=None):
    Audit.objects.create(
        user=request.user, operator=op, action=action, detail=detail or {}
    )


def touch(op):
    op.revision += 1
    op.save()


def check_operator(data, op):
    if data.get("operator") and data["operator"] != str(op.id):
        raise ValueError("El operador enviado no corresponde al seleccionado.")


def boot(request, op=None):
    operators = list(allowed(request.user))
    op = op or next(iter(operators), None)
    return {
        "operator": str(op.id) if op else None,
        "name": op.name if op else "",
        "binanceUsername": op.binance_username if op else "",
        "commission": op.commission if op else s.D(".002"),
        "operators": {str(o.id): o.name for o in operators},
        "accounts": {str(o.id): s.banklist(o) for o in operators},
        "isAdmin": request.user.is_superuser,
        "username": request.user.username,
        "demo": settings.P2P_MARKET_DEMO,
    }


@ensure_csrf_cookie
def page(request, kind="index"):
    ops = allowed(request.user)
    try:
        op = (
            ops.filter(id=request.GET.get("operator")).first()
            if request.GET.get("operator")
            else ops.first()
        )
    except (ValueError, ValidationError):
        op = ops.first()
    if not op and kind != "management":
        return render(request, "empty.html", status=403)
    if kind == "management" and not request.user.is_superuser:
        return HttpResponse("Solo Administrador.", status=403)
    b = s.numeric(boot(request, op))
    source = (
        (settings.BASE_DIR / "static" / f"{kind}.html").read_text(encoding="utf-8")
        if kind != "management"
        else (settings.BASE_DIR / "templates" / "management.html").read_text(encoding="utf-8")
    )
    source = source.replace(
        "</head>",
        '<script id="p2p-bootstrap" type="application/json">'
        + json.dumps(b, ensure_ascii=False).replace("<", "\\u003c")
        + '</script><script src="/static/api-client.js?v=market-1.4.2"></script><link rel="stylesheet" href="/static/notifications.css?v=1.4.2"><script type="module" src="/static/notifications.js?v=1.4.2"></script></head>',
    )
    return render(request, "shell.html", {"content": source})


@api
def health(request):
    return reply({"status": "ok", "application": "P2P Python"})


@api
def context(request):
    return reply(
        boot(request, operator(request) if request.GET.get("operator") else None)
    )


@api
def operators_api(request):
    if request.method == "GET":
        return reply(
            {
                "operators": [
                    {
                        "id": str(o.id),
                        "name": o.name,
                        "binanceUsername": o.binance_username,
                        "active": o.active,
                        "commission": o.commission,
                        "users": list(o.users.values_list("id", flat=True)),
                    }
                    for o in (
                        Operator.objects.all()
                        if request.user.is_superuser
                        else allowed(request.user)
                    )
                ],
                "users": (
                    list(User.objects.values("id", "username", "is_active"))
                    if request.user.is_superuser
                    else []
                ),
            }
        )
    admin_required(request)
    data = body(request)
    if request.method not in ["POST", "PUT"]:
        return reply({"error": "Método no permitido."}, 405)
    with transaction.atomic():
        op = (
            get_object_or_404(Operator.objects.select_for_update(), id=data.get("id"))
            if request.method == "PUT"
            else Operator()
        )
        op.name = name(data.get("name"), 80, "Nombre")
        op.binance_username = str(data.get("binanceUsername", "")).strip()
        if len(op.binance_username) > 100:
            raise ValueError("Usuario Binance demasiado largo.")
        op.commission = s.decimal(
            data.get("commission", ".002"), "Comisión", 6, maximum=s.D(".1")
        )
        op.active = bool(data.get("active", True))
        op.save()
        if data.get("users") is not None:
            op.users.set(User.objects.filter(id__in=data["users"], is_active=True))
        audit(
            request,
            op,
            "operator.create" if request.method == "POST" else "operator.update",
        )
        return reply(
            {"id": str(op.id), "name": op.name},
            201 if request.method == "POST" else 200,
        )


@api
def users_api(request):
    admin_required(request)
    if request.method != "POST":
        return reply({"error": "Método no permitido."}, 405)
    data = body(request)
    username = name(data.get("username"), 150, "Usuario")
    password = data.get("password", "")
    user = User(username=username)
    validate_password(password, user)
    user.set_password(password)
    with transaction.atomic():
        user.save()
        ids = data.get("operators", [])
        ops = list(Operator.objects.filter(id__in=ids, active=True))
        user.operators.set(ops)
        for op in ops:
            audit(request, op, "user.create", {"username": username})
    return reply({"id": user.id, "username": username}, 201)


@api
def accounts_api(request):
    op = operator(request)
    if request.method == "GET":
        return reply({"accounts": s.banklist(op)})
    data = body(request)
    if request.method not in ["POST", "PUT"]:
        return reply({"error": "Método no permitido."}, 405)
    with transaction.atomic():
        op = operator(request, True)
        check_operator(data, op)
        if request.method == "POST" and not data.get("key"):
            import uuid
            data["key"] = ("cuenta_" + uuid.uuid4().hex[:16])
        key = name(data.get("key"), 50, "Clave")
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", key):
            raise ValueError("Clave: usa letras, números, guiones o guion bajo.")
        a = (
            account(op, key, False)
            if request.method == "PUT"
            else Account(operator=op, key=key)
        )
        if request.method == "PUT" and data.get("action") in ["archive", "activate"]:
            if data["action"] == "archive":
                inv = s.inventory(op)
                if inv["accounts"][key] != 0 or op.orders.filter(account=a, status="pending").exists():
                    raise ValueError("Solo puedes quitar una cuenta con saldo cero y sin órdenes pendientes. Su historial se conserva.")
                a.active = False
            else:
                a.active = True
            a.save(update_fields=["active"])
            touch(op)
            audit(request, op, "account.archive" if not a.active else "account.activate", {"key": key, "name": a.name})
            return reply({"accounts": s.banklist(op)})
        if request.method == "PUT":
            admin_required(request)
        a.name = name(data.get("name"), 80, "Nombre")
        currency = data.get("currency", "UYU")
        if currency not in ["UYU", "USD"]:
            raise ValueError("Moneda no admitida.")
        if (
            a.pk
            and currency != a.currency
            and (
                a.orders.exists()
                or Movement.objects.filter(account=a).exists()
                or a.balance
            )
        ):
            raise ValueError(
                "No se puede cambiar la moneda de una cuenta con historial o saldo."
            )
        a.currency = currency
        a.active = bool(data.get("active", True))
        if not a.active and a.pk:
            inv = s.inventory(op)
            if inv["accounts"].get(key, 0) != 0 or op.orders.filter(account=a, status="pending").exists():
                raise ValueError("La cuenta debe tener saldo cero y no tener órdenes pendientes para quitarla.")
        a.save()
        touch(op)
        audit(request, op, "account.update")
        return reply({"accounts": s.banklist(op)})


def receipt_data(value):
    if not isinstance(value, dict):
        raise ValueError("Comprobante inválido.")
    try:
        raw = base64.b64decode(value["data"], validate=True)
    except (binascii.Error, KeyError, TypeError):
        raise ValueError("Comprobante inválido.")
    if not raw or len(raw) > 10 * 1024 * 1024:
        raise ValueError("Comprobante: máximo 10 MB.")
    if raw.startswith(b"%PDF-"):
        mime = "application/pdf"
    elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif raw.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError("Solo PDF, PNG, JPG o WebP.")
    return raw, str(value.get("name", "comprobante"))[:200], mime


def fill_order(op, data, o=None):
    check_operator(data, op)
    o = o or Order(operator=op)
    kind = data.get("type")
    if kind not in ["buy", "sell"]:
        raise ValueError("Selecciona compra o venta.")
    existing_account = not o._state.adding and o.account.key == data.get("accountKey")
    a = account(op, data.get("accountKey"), active=not existing_account)
    currency = data.get("currency", a.currency)
    if currency != a.currency:
        raise ValueError("La moneda debe coincidir con la cuenta.")
    o.account = a
    o.currency = a.currency
    o.type = kind
    o.number = name(str(data.get("number", "")), 100, "Número de orden")
    o.payment_method = name(data.get("paymentMethod") or a.name, 100, "Medio de pago")
    o.price = s.decimal(
        data.get("price"), "Precio", 6, s.D(".000001"), s.D("1000000000")
    )
    o.amount = s.decimal(data.get("amount"), "Monto", 2, s.D(".01"))
    o.date = s.datevalue(data.get("date"))
    o.status = data.get("status", o.status or "completed")
    if o.status not in ["pending", "completed", "cancelled"]:
        raise ValueError("Estado de orden inválido.")
    o.expense_rate = s.decimal(data.get("expenseRate", o.expense_rate), "Cargo porcentual", 6, maximum=s.D(1))
    o.expense_fixed = s.decimal(data.get("expenseFixed", o.expense_fixed), "Gasto fijo", 2)
    o.expense_note = str(data.get("expenseNote", o.expense_note)).strip()
    if len(o.expense_note) > 300:
        raise ValueError("Descripción del gasto: máximo 300 caracteres.")
    if o.type == "sell" and s.expenses(o) > o.amount:
        raise ValueError("Los gastos de venta no pueden superar el importe de la orden.")
    if not o.pk or o._state.adding:
        o.fee_rate = op.commission
    if data.get("receipt"):
        o.receipt, o.receipt_name, o.receipt_mime = receipt_data(data["receipt"])
    elif data.get("removeReceipt"):
        o.receipt = None
        o.receipt_name = ""
        o.receipt_mime = ""
    return o


@api
def orders_api(request, pk=None, receipt=False, backup=False):
    op = operator(request)
    if (
        request.method == "POST"
        and pk is not None
        or request.method in ["PUT", "DELETE"]
        and pk is None
    ):
        return reply({"error": "Método no permitido en esta ruta."}, 405)
    if request.method == "GET":
        if receipt:
            o = get_object_or_404(op.orders, id=pk)
            if not o.receipt:
                return reply({"error": "Comprobante no disponible."}, 404)
            response = HttpResponse(bytes(o.receipt), content_type=o.receipt_mime)
            extension = {
                "application/pdf": "pdf",
                "image/png": "png",
                "image/jpeg": "jpg",
                "image/webp": "webp",
            }.get(o.receipt_mime, "bin")
            response["Content-Disposition"] = (
                f'attachment; filename="comprobante.{extension}"'
            )
            response["Content-Security-Policy"] = "sandbox"
            response["X-Content-Type-Options"] = "nosniff"
            return response
        if backup:
            data = {
                "version": 1,
                "operator": str(op.id),
                "operatorName": op.name,
                "exportedAt": s.iso(timezone.now()),
                "orders": [
                    s.order_json(o, True) for o in op.orders.select_related("account")
                ],
                "inventory": s.inventory(op),
                "accounts": s.banklist(op),
                "movements": {
                    "withdrawals": [
                        s.movement_json(m)
                        for m in op.movements.select_related("account")
                    ]
                },
            }
            response = reply(data)
            response["Content-Disposition"] = 'attachment; filename="respaldo-p2p.json"'
            return response
        return reply(
            {
                "operator": str(op.id),
                "orders": [
                    s.order_json(o) for o in op.orders.select_related("account")
                ],
                "withdrawals": [
                    s.movement_json(m) for m in op.movements.select_related("account")
                ],
            }
        )
    if request.method not in ["POST", "PUT", "DELETE"]:
        return reply({"error": "Método no permitido."}, 405)
    with transaction.atomic():
        op = operator(request, True)
        s.snapshot(op)
        inventory_before = s.inventory(op)
        old = get_object_or_404(op.orders, id=pk) if pk else None
        if request.method == "DELETE":
            if not old:
                raise ValueError("Orden no encontrada.")
            oid = str(old.id)
            before = s.numeric(s.order_json(old))
            old.delete()
            s.check_reservations(op, inventory_before)
            audit(request, op, "order.delete", {"id": oid, "before": before})
            touch(op)
            s.snapshot(op)
            return reply({"ok": True, "operator": str(op.id)})
        if request.method == "PUT" and not old:
            raise ValueError("Orden no encontrada.")
        before = s.numeric(s.order_json(old)) if old else None
        o = fill_order(op, body(request), old)
        o.save()
        s.check_reservations(op, inventory_before)
        if o.status == "pending":
            inv = s.inventory(op)
            if o.type == "buy" and inv["availableAccounts"][o.account.key] < 0 or o.type == "sell" and inv["availableBinance"] < 0:
                raise ValueError("Saldo disponible insuficiente para reservar esta orden.")
        audit(
            request,
            op,
            "order.update" if old else "order.create",
            {"id": str(o.id), "number": o.number, "before": before, "after": s.numeric(s.order_json(o))},
        )
        touch(op)
        s.snapshot(op)
        return reply(
            {
                "operator": str(op.id),
                "order": s.order_json(o),
                "inventory": s.inventory(op),
            },
            200 if old else 201,
        )


@api
def inventory_api(request):
    if request.method not in ["GET", "PUT"]:
        return reply({"error": "Método no permitido."}, 405)
    with transaction.atomic():
        op = operator(request, request.method == "PUT")
        if request.method == "PUT":
            data = body(request)
            check_operator(data, op)
            if str(data.get("expectedRevision")) != str(op.revision):
                return reply(
                    {"error": "El inventario cambió. Recarga antes de guardar."}, 409
                )
            s.snapshot(op)
            accounts = data.get("accounts")
            if not isinstance(accounts, dict):
                raise ValueError("Completa los saldos.")
            before_accounts = s.inventory(op)["accounts"]
            keys = {a.key for a in op.accounts.all()}
            active_keys = {a.key for a in op.accounts.filter(active=True)}
            if set(accounts) not in [keys, active_keys]:
                raise ValueError("Las cuentas no corresponden al inventario.")
            inv = {
                "accounts": {
                    k: (s.decimal(accounts[k], "Saldo " + k, 2) if k in accounts else before_accounts[k]) for k in keys
                },
                "binance": s.decimal(
                    data.get("binance"), "Binance", 8, maximum=s.D("200000000")
                ),
            }
            before = s.inventory(op)
            changed = inv["binance"] != before["binance"] or inv["accounts"] != before["accounts"]
            reason = str(data.get("reason", "")).strip()
            if changed and not reason:
                raise ValueError("Indica el motivo de la conciliación.")
            if len(reason) > 300:
                raise ValueError("Motivo: máximo 300 caracteres.")
            if inv["binance"] < before["reservedBinance"] or any(inv["accounts"][k] < before["reservedAccounts"][k] for k in keys):
                raise ValueError("El saldo real no cubre las reservas. Corrige o cancela las órdenes pendientes.")
            differences = {k: inv["accounts"][k] - before["accounts"][k] for k in keys}
            s.rebase(op, inv)
            touch(op)
            audit(request, op, "inventory.reconcile", s.numeric({"reason": reason, "before": {"accounts": before["accounts"], "binance": before["binance"]}, "after": inv, "differences": differences, "binanceDifference": inv["binance"] - before["binance"]}))
            s.snapshot(op)
        inv = s.inventory(op)
        av = s.averages(op)
        return reply(
            {
                "operator": str(op.id),
                "inventory": inv,
                "averages": av,
                "values": s.valuation(op, inv, av),
                "withdrawals": [
                    s.movement_json(m) for m in op.movements.select_related("account")
                ],
                "revision": str(op.revision),
            }
        )


@api
def movements_api(request, pk=None):
    op = operator(request)
    if (
        request.method == "POST"
        and pk is not None
        or request.method in ["PUT", "DELETE"]
        and pk is None
    ):
        return reply({"error": "Método no permitido en esta ruta."}, 405)
    if request.method == "GET":
        return reply(
            {
                "operator": str(op.id),
                "withdrawals": [
                    s.movement_json(m) for m in op.movements.select_related("account")
                ],
                "inventory": s.inventory(op),
            }
        )
    if request.method not in ["POST", "PUT", "DELETE"]:
        return reply({"error": "Método no permitido."}, 405)
    with transaction.atomic():
        op = operator(request, True)
        s.snapshot(op)
        inventory_before = s.inventory(op)
        old = get_object_or_404(op.movements, id=pk) if pk else None
        if request.method == "DELETE":
            if not old:
                raise ValueError("Movimiento no encontrado.")
            old.delete()
            s.check_reservations(op, inventory_before)
            audit(request, op, "movement.delete", {"id": str(pk)})
        else:
            data = body(request)
            check_operator(data, op)
            m = old or Movement(operator=op)
            m.account = account(op, data.get("accountKey"))
            m.amount = s.decimal(data.get("amount"), "Monto", 2, s.D(".01"))
            m.kind = data.get("kind", "withdrawal")
            if m.kind not in ["deposit", "withdrawal"]:
                raise ValueError("Movimiento inválido.")
            m.date = s.datevalue(data.get("date"))
            m.note = str(data.get("note", "")).strip()
            if len(m.note) > 300:
                raise ValueError("Descripción: máximo 300 caracteres.")
            m.save()
            s.check_reservations(op, inventory_before)
            if s.inventory(op)["availableAccounts"][m.account.key] < 0:
                raise ValueError("El retiro supera el saldo disponible.")
            audit(
                request,
                op,
                "movement.update" if old else "movement.create",
                {"id": str(m.id)},
            )
        touch(op)
        s.snapshot(op)
        return reply(
            {
                "operator": str(op.id),
                "withdrawals": [
                    s.movement_json(m) for m in op.movements.select_related("account")
                ],
                "inventory": s.inventory(op),
            }
        )


@api
def report_api(request):
    if request.method != "GET":
        return reply({"error": "Método no permitido."}, 405)
    op = operator(request)
    start = request.GET.get("from", "")
    end = request.GET.get("to", "")
    return reply(
        {
            "operator": str(op.id),
            "reports": {c: s.report(op, c, start, end) for c in ["UYU", "USD"]},
        }
    )


@api
def profits_api(request):
    if request.method != "GET":
        return reply({"error": "Método no permitido."}, 405)
    return reply(s.profits(list(allowed(request.user))))


@api
def market_api(request, kind):
    if request.method != "GET":
        return reply({"error": "Método no permitido."}, 405)
    fiat = request.GET.get("fiat", "UYU")
    if fiat not in ["UYU", "USD"]:
        raise ValueError("Moneda no admitida.")
    if kind == "market":
        markets.amount_value(request.GET.get("amount"))
        if request.GET.get("amountUnit", "fiat") not in ["fiat", "USDT"]:
            raise ValueError("Unidad de monto inválida.")
    try:
        data = (
            {"methods": markets.methods(fiat)}
            if kind == "methods"
            else (
                markets.recommendations(fiat)
                if kind == "recommendations"
                else markets.market(fiat, request.GET.get("method"), request.GET.get("amount"), request.GET.get("amountUnit", "fiat"))
            )
        )
        return reply(data)
    except ValueError as e:
        return reply({"error": str(e)}, 502)


@api
def audit_api(request):
    if request.method != "GET":
        return reply({"error": "Método no permitido."}, 405)
    op = operator(request)
    return reply(
        {
            "records": [
                {
                    "action": a.action,
                    "user": a.user.username if a.user else "Usuario eliminado",
                    "date": s.iso(a.created_at),
                    "detail": a.detail,
                }
                for a in Audit.objects.filter(operator=op)
                .select_related("user")
                .order_by("-created_at")[:200]
            ]
        }
    )


@api
def import_api(request):
    if request.method != "POST":
        return reply({"error": "Método no permitido."}, 405)
    from .importing import import_plan, execute

    data = body(request)
    with transaction.atomic():
        op = operator(request, True)
        check_operator(data, op)
        payload = data.get("payload")
        mapping = data.get("mapping", {})
        if not isinstance(mapping, dict):
            raise ValueError("Mapeo de cuentas inválido.")
        if not data.get("confirm"):
            return reply(import_plan(op, payload, mapping)[0])
        if str(data.get("expectedRevision")) != str(op.revision):
            return reply(
                {"error": "Los datos cambiaron. Realiza de nuevo la revisión."}, 409
            )
        s.snapshot(op)
        summary = execute(
            op, payload, mapping, bool(data.get("preserveInventory", True))
        )
        touch(op)
        audit(
            request,
            op,
            "import",
            {
                "new": summary["new"],
                "sourceOperator": payload.get("operator"),
                "preserveInventory": bool(data.get("preserveInventory", True)),
            },
        )
        s.snapshot(op)
        return reply(summary)


@api
def calculate_api(request):
    if request.method != "GET":
        return reply({"error": "Método no permitido."}, 405)
    op = operator(request)
    return reply(
        {
            "operator": str(op.id),
            "result": s.calculate(
                request.GET.get("buy"),
                request.GET.get("sell"),
                request.GET.get("amount"),
                op.commission,
                request.GET.get("buyExpenseRate", 0), request.GET.get("sellExpenseRate", 0),
                request.GET.get("buyFixed", 0), request.GET.get("sellFixed", 0),
            ),
        }
    )


@api
def advertiser_api(request):
    if request.method != "GET":
        return reply({"error":"Método no permitido."},405)
    user_no=request.GET.get("userNo", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", user_no):
        raise ValueError("Identificador de anunciante inválido.")
    try:
        return reply(markets.advertiser(user_no))
    except ValueError as e:
        return reply({"error":str(e)},502)


@api
def own_ads_api(request):
    if request.method != "GET":
        return reply({"error": "Método no permitido."}, 405)
    op = operator(request)
    if not op.binance_username.strip():
        return reply({"status": "unconfigured", "message": "Configura el usuario Binance del operador."})
    try:
        result = markets.own_ads(op.binance_username, request.GET.get("userNo", ""))
        return reply({"operator": str(op.id), **result})
    except ValueError as e:
        return reply({"error": str(e)}, 502)


@api
def notification_state_api(request):
    if request.method != "GET":
        return reply({"error": "Método no permitido."}, 405)
    op = operator(request)
    inv = s.inventory(op)
    return reply({"operator": str(op.id), "accounts": s.banklist(op),
                  "availableAccounts": inv["availableAccounts"], "availableBinance": inv["availableBinance"],
                  "pending": [{"id": str(o.id), "number": o.number, "date": s.iso(o.date)} for o in op.orders.filter(status="pending")],
                  "updatedAt": s.iso(timezone.now())})
