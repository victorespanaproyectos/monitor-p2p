import json, base64
from decimal import Decimal as D
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.management import call_command
from .models import Operator, Account, Order, Movement, Audit, DailySnapshot
from . import services as s


class ApplicationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            "testadmin", password="Testing-secret-948!"
        )
        self.user = get_user_model().objects.create_user(
            "worker", password="Testing-secret-948!"
        )
        self.op = Operator.objects.create(name="Administrador")
        s.default_accounts(self.op)
        self.op.users.add(self.user)
        self.other = Operator.objects.create(name="Otro")
        s.default_accounts(self.other)
        self.client.force_login(self.admin)
        self.a = self.op.accounts.get(key="mercadoPago")
        self.dt = timezone.now() - timedelta(days=2)

    def url(self, path, op=None):
        return path + "?operator=" + str((op or self.op).id)

    def req(self, path, data, method="post", op=None):
        return getattr(self.client, method)(
            self.url(path, op), json.dumps(data), content_type="application/json"
        )

    def order(
        self, number="123", kind="buy", amount=4100, price=41, date=None, op=None
    ):
        return self.req(
            "/api/orders",
            {
                "type": kind,
                "number": number,
                "paymentMethod": "MercadoPago",
                "accountKey": "mercadoPago",
                "price": price,
                "amount": amount,
                "date": s.iso(date or self.dt),
            },
            op=op,
        )

    def test_login_wall_and_csrf(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.get("/api/orders").status_code, 401)
        self.assertEqual(c.get("/").status_code, 302)
        c.force_login(self.admin)
        self.assertEqual(
            c.post(
                self.url("/api/orders"), data="{}", content_type="application/json"
            ).status_code,
            403,
        )

    def test_operator_isolation_and_receipts(self):
        self.order(op=self.other)
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(self.url("/api/orders", self.other)).status_code, 404
        )
        self.assertEqual(
            self.client.get("/api/profits").json()["operators"][0]["name"],
            "Administrador",
        )
        self.assertEqual(self.req("/api/operators", {"name": "X"}).status_code, 403)

    def test_order_inventory_edit_delete(self):
        self.assertEqual(self.order().status_code, 201)
        self.op.refresh_from_db()
        inv = s.inventory(self.op)
        self.assertEqual(inv["accounts"]["mercadoPago"], D("-4100"))
        self.assertEqual(inv["binance"], D("99.8"))
        oid = self.op.orders.first().id
        r = self.req(
            "/api/orders/" + str(oid),
            {
                "type": "buy",
                "number": "123",
                "paymentMethod": "MercadoPago",
                "accountKey": "mercadoPago",
                "price": 41,
                "amount": 8200,
                "date": s.iso(self.dt),
            },
            "put",
        )
        self.assertEqual(r.status_code, 200)
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)["binance"], D("199.6"))
        self.req("/api/orders/" + str(oid), {}, "delete")
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)["binance"], 0)

    def test_duplicate_order_per_operator(self):
        self.order()
        self.assertEqual(self.order().status_code, 409)
        self.assertEqual(self.order(op=self.other).status_code, 201)

    def test_rebase_no_double_application_and_revision(self):
        self.order()
        self.op.refresh_from_db()
        r = self.req(
            "/api/inventory",
            {
                "accounts": {a.key: 1000 for a in self.op.accounts.all()},
                "binance": 200,
                "expectedRevision": str(self.op.revision),
                "reason": "Saldo verificado en prueba",
            },
            "put",
        )
        self.assertEqual(r.status_code, 200)
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)["binance"], 200)
        self.assertEqual(s.inventory(self.op)["accounts"]["mercadoPago"], 1000)
        self.assertEqual(
            self.req("/api/inventory", {"expectedRevision": "0"}, "put").status_code,
            409,
        )

    def test_withdrawal_rejected_rollback_deposit_and_delete(self):
        self.assertEqual(
            self.req(
                "/api/withdrawals",
                {
                    "kind": "withdrawal",
                    "accountKey": "mercadoPago",
                    "amount": 500,
                    "date": s.iso(self.dt),
                },
            ).status_code,
            400,
        )
        self.assertEqual(self.op.movements.count(), 0)
        r = self.req(
            "/api/withdrawals",
            {
                "kind": "deposit",
                "accountKey": "mercadoPago",
                "amount": 500,
                "date": s.iso(self.dt),
            },
        )
        self.assertEqual(r.status_code, 200)
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)["accounts"]["mercadoPago"], 500)
        mid = self.op.movements.first().id
        self.req("/api/withdrawals/" + str(mid), {}, "delete")
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)["accounts"]["mercadoPago"], 0)

    def test_fifo_fees_and_history_range(self):
        self.order()
        self.order("sale", "sell", 3798, 42.2, self.dt + timedelta(hours=1))
        r = s.report(self.op)["totals"]
        self.assertAlmostEqual(
            float(r["profit"]), 3798 - (90 * 1.002) * (4100 / 99.8), places=8
        )
        self.assertEqual(r["reserve"], max(D(0), r["profit"]) / 10)
        start = (timezone.localtime(self.dt + timedelta(hours=1)).date() + timedelta(days=1)).isoformat()
        self.assertEqual(s.report(self.op, start=start)["totals"]["count"], 0)

    def test_fifo_missing_never_uses_future_purchase(self):
        self.order("s", "sell", 4220, 42.2, self.dt)
        self.order("b", "buy", 4100, 41, self.dt + timedelta(hours=1))
        self.assertGreater(s.report(self.op)["totals"]["missing"], 0)
        self.assertEqual(s.report(self.op)["totals"]["profit"], 0)

    def test_usd_account_and_independent_report(self):
        r = self.req(
            "/api/orders",
            {
                "type": "buy",
                "number": "USD",
                "paymentMethod": "Otra billetera",
                "accountKey": "airtm",
                "currency": "USD",
                "price": 0.998,
                "amount": 99.8,
                "date": s.iso(self.dt),
            },
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(s.report(self.op)["totals"]["count"], 0)
        self.assertEqual(s.report(self.op, "USD")["totals"]["count"], 1)

    def test_currency_and_account_validation(self):
        r = self.req(
            "/api/orders",
            {
                "type": "buy",
                "number": "USD",
                "paymentMethod": "X",
                "accountKey": "airtm",
                "currency": "UYU",
                "price": 41,
                "amount": 100,
                "date": s.iso(self.dt),
            },
        )
        self.assertEqual(r.status_code, 400)
        r = self.req(
            "/api/orders",
            {
                "type": "buy",
                "number": "NaN",
                "accountKey": "mercadoPago",
                "price": "NaN",
                "amount": 100,
                "date": s.iso(self.dt),
            },
        )
        self.assertEqual(r.status_code, 400)

    def test_operators_users_dynamic_accounts(self):
        r = self.req(
            "/api/operators",
            {
                "name": "Nuevo",
                "binanceUsername": "MiUsuario",
                "commission": ".0016",
                "users": [self.user.id],
            },
        )
        self.assertEqual(r.status_code, 201)
        op = Operator.objects.get(id=r.json()["id"])
        self.assertEqual(op.accounts.count(), 0)
        self.assertTrue(op.users.filter(pk=self.user.pk).exists())
        r = self.req(
            "/api/accounts",
            {"key": "customUSD", "name": "Billetera USD", "currency": "USD"},
            op=op,
        )
        self.assertEqual(r.status_code, 200)

    def test_deactivate_operator_preserves_history(self):
        self.order()
        self.req(
            "/api/operators",
            {"id": str(self.op.id), "name": "Administrador", "active": False},
            "put",
        )
        self.assertEqual(self.client.get(self.url("/api/orders")).status_code, 404)
        self.assertEqual(Order.objects.count(), 1)

    def test_receipt_backup_roundtrip_authorized(self):
        self.order()
        o = self.op.orders.first()
        data = {
            "type": "buy",
            "number": "123",
            "accountKey": "mercadoPago",
            "paymentMethod": "MercadoPago",
            "price": 41,
            "amount": 4100,
            "date": s.iso(self.dt),
            "receipt": {
                "name": "demo.pdf",
                "data": base64.b64encode(b"%PDF-1.4\ndemo").decode(),
            },
        }
        self.assertEqual(
            self.req("/api/orders/" + str(o.id), data, "put").status_code, 200
        )
        backup = self.client.get(self.url("/api/orders/backup")).json()
        self.assertEqual(
            backup["orders"][0]["receipt"]["data"], data["receipt"]["data"]
        )
        self.assertEqual(
            self.client.get(
                self.url("/api/orders/" + str(o.id) + "/receipt")
            ).status_code,
            200,
        )
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(
                self.url("/api/orders/" + str(o.id) + "/receipt", self.other)
            ).status_code,
            404,
        )

    def payload(self):
        return {
            "version": 1,
            "operator": "victor",
            "orders": [
                {
                    "type": "buy",
                    "number": "OLD",
                    "paymentMethod": "MercadoPago",
                    "accountKey": "mercadoPago",
                    "currency": "UYU",
                    "price": 41,
                    "amountCents": 410000,
                    "date": s.iso(self.dt),
                }
            ],
        }

    def test_import_preview_confirm_idempotent_preserves_inventory(self):
        data = {"payload": self.payload()}
        r = self.req("/api/import", data)
        self.assertEqual(r.json()["new"], 1)
        self.assertEqual(Order.objects.count(), 0)
        data.update(confirm=True, expectedRevision="0", preserveInventory=True)
        self.assertEqual(self.req("/api/import", data).status_code, 200)
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)["binance"], 0)
        self.assertEqual(s.inventory(self.op)["accounts"]["mercadoPago"], 0)
        data["expectedRevision"] = str(self.op.revision)
        r = self.req("/api/import", data)
        self.assertEqual(r.json()["new"], 0)
        self.assertEqual(Order.objects.count(), 1)

    def test_import_invalid_rows_atomic_and_duplicate_source(self):
        p = self.payload()
        p["orders"].append(dict(p["orders"][0]))
        r = self.req(
            "/api/import", {"payload": p, "confirm": True, "expectedRevision": "0"}
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_daily_comparison_adjusts_withdrawals(self):
        self.order()
        self.op.refresh_from_db()
        s.rebase(
            self.op,
            {
                "accounts": {
                    a.key: D(1000) if a.currency == "UYU" else D(0)
                    for a in self.op.accounts.all()
                },
                "binance": D(0),
            },
        )
        self.op.save()
        DailySnapshot.objects.create(
            operator=self.op,
            day=timezone.localdate() - timedelta(days=1),
            total=D(6000),
            withdrawals={"UYU": "0", "USD": "0"},
        )
        self.req(
            "/api/withdrawals",
            {
                "accountKey": "mercadoPago",
                "kind": "withdrawal",
                "amount": 100,
                "date": s.iso(timezone.now()),
            },
        )
        self.op.refresh_from_db()
        d = s.profits([self.op])["inventoryComparison"]
        self.assertEqual(d["change"], -100)
        self.assertEqual(d["withdrawalsEquivalent"], 100)
        self.assertEqual(d["adjustedChange"], 0)

    def test_configurable_commission(self):
        self.op.commission = D(".0016")
        self.op.save()
        self.order()
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)["binance"], D("99.84"))

    @override_settings(P2P_MARKET_DEMO=True)
    def test_market_demo_and_methods(self):
        self.assertEqual(self.client.get("/api/methods?fiat=UYU").status_code, 200)
        r = self.client.get("/api/market?fiat=UYU")
        self.assertEqual(len(r.json()["groups"]), 6)
        self.assertEqual(len(r.json()["groups"][0]["buy"]["ads"]), 10)

    def test_pages_bootstrap_and_audit(self):
        for page in ["/", "/ordenes", "/inventario", "/usd-airtm", "/operadores"]:
            self.assertEqual(self.client.get(page).status_code, 200)
        self.order()
        self.assertEqual(
            self.client.get(self.url("/api/audit")).json()["records"][0]["action"],
            "order.create",
        )

    def test_setup_initial_and_idempotent(self):
        from io import StringIO

        out = StringIO()
        call_command("setup_admin", stdout=out)
        self.assertIn("Ya existe", out.getvalue())

    def test_calculator_python_and_bad_inputs(self):
        r = self.client.get(
            self.url("/api/calculate"), {"buy": "41", "sell": "42.2", "amount": "100"}
        )
        # query data replaces the URL query in Django Client; use explicit operator.
        r = self.client.get(
            "/api/calculate",
            {"operator": str(self.op.id), "buy": "41", "sell": "42.2", "amount": "100"},
        )
        self.assertEqual(r.status_code, 200)
        expected = s.calculate("41", "42.2", "100", D(".002"))
        self.assertAlmostEqual(
            r.json()["result"]["net"], float(expected["net"]), places=10
        )
        r = self.client.get(
            "/api/calculate",
            {
                "operator": str(self.op.id),
                "buy": "NaN",
                "sell": "42.2",
                "amount": "100",
            },
        )
        self.assertEqual(r.status_code, 400)

    def test_setup_creates_only_initial_operator_on_clean_database(self):
        self.other.accounts.all().delete()
        self.other.delete()
        self.op.accounts.all().delete()
        self.op.delete()
        get_user_model().objects.all().delete()
        from io import StringIO

        with patch(
            "getpass.getpass",
            side_effect=["Strong-setup-832-secret!", "Strong-setup-832-secret!"],
        ):
            call_command("setup_admin", stdout=StringIO())
        self.assertEqual(Operator.objects.count(), 1)
        self.assertEqual(Operator.objects.first().name, "Administrador")
        self.assertEqual(Operator.objects.first().accounts.count(), 0)
        self.assertTrue(get_user_model().objects.get(username="admin").is_superuser)

    def test_account_deactivation_blocks_new_orders_and_preserves_history(self):
        self.order()
        self.op.refresh_from_db()
        inv=s.inventory(self.op)
        inv['accounts']['mercadoPago']=D(0)
        s.rebase(self.op, inv)
        self.op.save()
        r = self.req(
            "/api/accounts",
            {
                "key": "mercadoPago",
                "name": "Mercado Pago",
                "currency": "UYU",
                "active": False,
            },
            "put",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.order("later").status_code, 400)
        self.assertEqual(self.op.orders.count(), 1)
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)["accounts"]["mercadoPago"], 0)

    def test_import_cross_currency_mapping_rejected(self):
        p = self.payload()
        p["orders"][0]["accountKey"] = "unknown"
        r = self.req("/api/import", {"payload": p, "mapping": {"unknown": "airtm"}})
        self.assertFalse(r.json()["canImport"])
        self.assertEqual(Order.objects.count(), 0)

    def test_report_timezone_and_invalid_range(self):
        self.order(date=s.datevalue("2026-10-02T01:30:00Z"))
        self.assertEqual(
            s.report(self.op, start="2026-10-01", end="2026-10-01")["totals"]["count"],
            1,
        )
        self.assertEqual(
            s.report(self.op, start="2026-10-02", end="2026-10-02")["totals"]["count"],
            0,
        )
        self.assertEqual(
            self.client.get(
                "/api/report",
                {"operator": str(self.op.id), "from": "2026-10-03", "to": "2026-10-01"},
            ).status_code,
            400,
        )

    def test_import_movements_remains_isolated_and_idempotent(self):
        import uuid

        payload = {
            "version": 1,
            "orders": [],
            "movements": {
                "withdrawals": [
                    {
                        "id": str(uuid.uuid4()),
                        "accountKey": "mercadoPago",
                        "kind": "deposit",
                        "currency": "UYU",
                        "amountCents": 10000,
                        "date": s.iso(self.dt),
                    }
                ]
            },
        }
        for op in [self.op, self.other]:
            response = self.req(
                "/api/import",
                {"payload": payload, "confirm": True, "expectedRevision": "0"},
                op=op,
            )
            self.assertEqual(response.status_code, 200)
            op.refresh_from_db()
            response = self.req(
                "/api/import",
                {
                    "payload": payload,
                    "confirm": True,
                    "expectedRevision": str(op.revision),
                },
                op=op,
            )
            self.assertEqual(response.json()["newMovements"], 0)
        self.assertEqual(Movement.objects.count(), 2)


class Phase1Tests(TestCase):
    setUp = ApplicationTests.setUp
    url = ApplicationTests.url
    req = ApplicationTests.req

    def seed(self, cash=1000, funds=100, rate='0.002'):
        self.a.balance = D(str(cash))
        self.a.save()
        self.op.funds = D(str(funds))
        self.op.commission = D(rate)
        self.op.save()

    def data(self, **changes):
        return {'type': 'buy', 'status': 'pending', 'number': 'phase1',
                'accountKey': 'mercadoPago', 'paymentMethod': 'MercadoPago',
                'amount': 100, 'price': 1, 'date': s.iso(self.dt), **changes}

    def save_order(self, **changes):
        r = self.req('/api/orders', self.data(**changes))
        self.assertEqual(r.status_code, 201, r.content)
        self.op.refresh_from_db()
        return r.json()['order']

    def change(self, row, **changes):
        return self.req('/api/orders/' + row['id'], {**row, **changes}, 'put')

    def test_pending_purchase_reserves_cash_and_costs_without_acquiring_usdt(self):
        self.seed()
        self.save_order(expenseRate=.01, expenseFixed=.5)
        inv = s.inventory(self.op)
        self.assertEqual(inv['accounts']['mercadoPago'], 1000)
        self.assertEqual(inv['reservedAccounts']['mercadoPago'], D('101.50'))
        self.assertEqual(inv['availableAccounts']['mercadoPago'], D('898.50'))
        self.assertEqual(inv['binance'], 100)
        self.assertEqual(s.report(self.op)['totals']['count'], 0)
        self.assertEqual(len(s.report(self.op)['selected']), 1)

    def test_pending_sell_reserves_quantity_including_fee_and_cancellation_releases(self):
        self.seed(funds=101)
        o = self.save_order(type='sell')
        self.assertEqual(s.inventory(self.op)['reservedBinance'], D('100.2'))
        self.assertEqual(self.change(o, status='cancelled').status_code, 200)
        self.op.refresh_from_db()
        inv = s.inventory(self.op)
        self.assertEqual(inv['binance'], 101)
        self.assertEqual(inv['reservedBinance'], 0)
        self.assertEqual(inv['accounts']['mercadoPago'], 1000)

    def test_completion_applies_once_and_repeated_save_does_not_repeat(self):
        self.seed()
        o = self.save_order(expenseRate=.01, expenseFixed=.5)
        r = self.change(o, status='completed')
        self.assertEqual(r.status_code, 200, r.content)
        r = self.change(r.json()['order'], status='completed')
        self.assertEqual(r.status_code, 200)
        self.op.refresh_from_db()
        inv = s.inventory(self.op)
        self.assertEqual(inv['accounts']['mercadoPago'], D('898.50'))
        self.assertEqual(inv['binance'], D('199.8'))
        self.assertEqual(inv['reservedAccounts']['mercadoPago'], 0)

    def test_insufficient_pending_cash_rolls_back(self):
        self.seed(cash=100)
        r = self.req('/api/orders', self.data(expenseFixed=1))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.op.orders.count(), 0)
        self.assertEqual(Audit.objects.count(), 0)

    def test_second_pending_sale_cannot_reserve_same_usdt(self):
        self.seed(funds=150)
        self.save_order(type='sell')
        r = self.req('/api/orders', self.data(type='sell', number='second'))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.op.orders.count(), 1)

    def test_withdrawal_cannot_spend_cash_reserved_by_order(self):
        self.seed(cash=150)
        self.save_order()
        r = self.req('/api/withdrawals', {'kind':'withdrawal', 'accountKey':'mercadoPago', 'amount':51, 'date':s.iso(self.dt)})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.op.movements.count(), 0)

    def test_completed_sale_cannot_spend_pending_sale_reserve(self):
        self.seed(funds=150)
        self.save_order(type='sell')
        r = self.req('/api/orders', self.data(type='sell', status='completed', number='second'))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.op.orders.count(), 1)

    def test_fifo_capitalizes_buy_costs_and_deducts_sale_costs_once(self):
        self.seed(rate='0')
        self.save_order(status='completed', expenseRate=.01, expenseFixed=.5)
        self.save_order(type='sell', status='completed', number='sale', price=1.1, amount=110, date=s.iso(self.dt+timedelta(hours=1)), expenseRate=.01, expenseFixed=.4)
        data = s.report(self.op)
        t = data['totals']
        self.assertEqual(t['profit'], D('7.00'))
        self.assertEqual(t['expenses'], D('3.00'))
        self.assertEqual(t['buyTotal'], D('101.50'))
        self.assertEqual(t['sellTotal'], D('108.50'))
        self.assertEqual(t['reserve'], D('.7'))
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)['accounts']['mercadoPago'], D('1007'))

    def test_cancelled_orders_do_not_affect_averages_fifo_or_costs(self):
        self.seed()
        self.save_order(status='cancelled', expenseFixed=500)
        self.assertIsNone(s.averages(self.op)['buy']['price'])
        self.assertEqual(s.report(self.op)['totals']['expenses'], 0)
        self.assertEqual(s.inventory(self.op)['accounts']['mercadoPago'], 1000)

    def test_reconciliation_requires_reason_and_logs_exact_difference(self):
        self.seed()
        d={'accounts':{a.key:float(a.balance) for a in self.op.accounts.all()},'binance':100,'expectedRevision':str(self.op.revision)}
        d['accounts']['mercadoPago']=1050
        self.assertEqual(self.req('/api/inventory', d, 'put').status_code, 400)
        self.assertEqual(self.req('/api/inventory', {**d,'reason':'Saldo verificado'}, 'put').status_code, 200)
        record=Audit.objects.get(action='inventory.reconcile')
        self.assertEqual(record.detail['differences']['mercadoPago'], 50)
        self.assertEqual(record.detail['before']['accounts']['mercadoPago'],1000)
        self.assertEqual(record.detail['after']['accounts']['mercadoPago'],1050)
        self.assertEqual(s.report(self.op)['totals']['profit'],0)

    def test_reconciliation_cannot_reduce_real_balance_below_reservations(self):
        self.seed()
        self.save_order()
        self.op.refresh_from_db()
        d={'accounts':{a.key:float(a.balance) for a in self.op.accounts.all()},'binance':100,'expectedRevision':str(self.op.revision),'reason':'Verificación'}
        d['accounts']['mercadoPago']=99
        self.assertEqual(self.req('/api/inventory', d, 'put').status_code, 400)
        self.a.refresh_from_db()
        self.assertEqual(self.a.balance,1000)

    def test_reconciliation_with_pending_completion_preserves_observed_balance(self):
        self.seed()
        o=self.save_order()
        d={'accounts':{a.key:float(a.balance) for a in self.op.accounts.all()},'binance':100,'expectedRevision':str(self.op.revision),'reason':'Saldo real'}
        d['accounts']['mercadoPago']=1200
        self.assertEqual(self.req('/api/inventory',d,'put').status_code,200)
        self.assertEqual(self.change(o,status='completed').status_code,200)
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)['accounts']['mercadoPago'],1100)

    def test_reopen_completed_reverses_effect_and_reserves(self):
        self.seed()
        o=self.save_order(status='completed')
        self.assertEqual(self.change(o,status='pending').status_code,200)
        self.op.refresh_from_db()
        inv=s.inventory(self.op)
        self.assertEqual(inv['accounts']['mercadoPago'],1000)
        self.assertEqual(inv['availableAccounts']['mercadoPago'],900)
        self.assertEqual(inv['binance'],100)

    def test_backup_import_preserves_status_costs_and_legacy_defaults(self):
        from .importing import execute
        self.seed()
        o=self.save_order(status='cancelled',expenseRate=.01,expenseFixed=.4,expenseNote='Cargo de prueba')
        payload=self.client.get(self.url('/api/orders/backup')).json()
        execute(self.other,payload,{})
        imported=self.other.orders.get()
        self.assertEqual(imported.status,'cancelled')
        self.assertEqual(imported.expense_rate,D('.01'))
        self.assertEqual(imported.expense_fixed,D('.4'))
        self.assertEqual(imported.expense_note,'Cargo de prueba')
        payload['orders'][0]['number']='legacy'
        for k in ['status','expenseRate','expenseFixed','expenseNote']:payload['orders'][0].pop(k)
        execute(self.other,payload,{})
        self.assertEqual(self.other.orders.get(number='legacy').status,'completed')
        self.assertEqual(self.other.orders.get(number='legacy').expense_fixed,0)

    def test_invalid_status_costs_and_sale_overcharge_rejected(self):
        self.seed()
        for d in [{'status':'fake'},{'expenseRate':1.1},{'expenseFixed':-1},{'expenseFixed':.001},{'type':'sell','expenseFixed':101},{'expenseNote':'a'*301}]:
            with self.subTest(d=d):self.assertEqual(self.req('/api/orders',self.data(**d)).status_code,400)
        self.assertEqual(self.op.orders.count(),0)

    def test_calculator_additional_costs_and_half_cent_rounding(self):
        result=s.calculate(1,1.1,100,D(0),D('.01'),D('.01'),D('.5'),D('.4'))
        self.assertEqual(result['net'],D(7))
        self.assertEqual(result['extraCosts'],D(3))
        self.assertEqual(result['cost'],D('101.50'))
        self.assertEqual(result['proceeds'],D('108.50'))
        self.assertEqual(s.calculate(1,1,1,D(0),D('.005'))['buyCosts'],D('.01'))

    def test_missing_purchase_cost_remains_partial_after_expenses(self):
        self.seed(rate='0')
        self.save_order(status='completed',amount=50)
        self.save_order(type='sell',status='completed',number='sale',amount=110,price=1.1,expenseFixed=10,date=s.iso(self.dt+timedelta(hours=1)))
        t=s.report(self.op)['totals']
        self.assertEqual(t['missing'],50)
        self.assertEqual(t['profit'],0)

    def test_costs_and_statuses_remain_separate_by_currency(self):
        self.seed(rate='0')
        self.save_order(status='completed', expenseFixed=2)
        self.req('/api/orders',self.data(status='completed',number='usd',accountKey='airtm',currency='USD',expenseFixed=1))
        self.assertEqual(s.report(self.op,'UYU')['totals']['expenses'],2)
        self.assertEqual(s.report(self.op,'USD')['totals']['expenses'],1)

    def test_order_audit_captures_state_and_cost_change(self):
        self.seed()
        o=self.save_order()
        self.assertEqual(self.change(o,status='completed',expenseFixed=2).status_code,200)
        detail=Audit.objects.get(action='order.update').detail
        self.assertEqual(detail['before']['status'],'pending')
        self.assertEqual(detail['after']['status'],'completed')
        self.assertEqual(detail['after']['expenseFixed'],2)


from django.test import TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Phase1MigrationTests(TransactionTestCase):
    def test_old_orders_and_reconciled_baselines_keep_balances(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('p2p','0001_initial')])
        old = executor.loader.project_state([('p2p','0001_initial')]).apps
        try:
            OldOp=old.get_model('p2p','Operator')
            OldAccount=old.get_model('p2p','Account')
            OldOrder=old.get_model('p2p','Order')
            op=OldOp.objects.create(name='Migración',funds=200)
            a=OldAccount.objects.create(operator=op,key='legacy',name='Cuenta anterior',currency='UYU',balance=1000)
            o=OldOrder.objects.create(operator=op,account=a,number='OLD-01',type='buy',payment_method='Cuenta anterior',currency='UYU',price=41,amount=4100,fee_rate='.002',date=timezone.now())
            op.order_baseline={str(o.id):{'account':'legacy','cash':'-4100','funds':'99.8'}}
            op.save()
        finally:
            executor=MigrationExecutor(connection)
            executor.migrate([('p2p','0002_order_expense_fixed_order_expense_note_and_more')])
        new=Operator.objects.get(id=op.id)
        order=new.orders.get()
        self.assertEqual(order.status,'completed')
        self.assertEqual(order.expense_rate,0)
        self.assertEqual(order.expense_fixed,0)
        inv=s.inventory(new)
        self.assertEqual(inv['accounts']['legacy'],1000)
        self.assertEqual(inv['binance'],200)
        self.assertEqual(inv['reservedBinance'],0)


class ReservationCorrectionTests(TestCase):
    setUp = ApplicationTests.setUp
    url = ApplicationTests.url
    req = ApplicationTests.req
    seed = Phase1Tests.seed
    data = Phase1Tests.data
    save_order = Phase1Tests.save_order
    change = Phase1Tests.change

    def test_delete_purchase_cannot_remove_funds_reserved_by_sale(self):
        self.seed(funds=0, rate='0')
        buy=self.save_order(status='completed')
        self.save_order(type='sell',number='pending-sale')
        response=self.req('/api/orders/'+buy['id'],{},'delete')
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.op.orders.count(),2)

    def test_pending_order_in_deactivated_account_can_be_cancelled(self):
        self.seed()
        o=self.save_order()
        self.a.active=False
        self.a.save()
        response=self.change(o,status='cancelled')
        self.assertEqual(response.status_code,200,response.content)
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)['reservedAccounts']['mercadoPago'],0)

    def test_delete_deposit_cannot_break_purchase_reservation(self):
        self.seed(cash=0)
        response=self.req('/api/withdrawals',{'kind':'deposit','accountKey':'mercadoPago','amount':100,'date':s.iso(self.dt)})
        self.assertEqual(response.status_code,200)
        self.save_order()
        m=self.op.movements.get()
        response=self.req('/api/withdrawals/'+str(m.id),{},'delete')
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.op.movements.count(),1)


class DynamicAccountTests(TestCase):
    setUp=ApplicationTests.setUp
    url=ApplicationTests.url
    req=ApplicationTests.req

    def test_new_operator_has_no_default_accounts(self):
        r=self.req('/api/operators',{'name':'Solo mis cuentas'})
        self.assertEqual(r.status_code,201,r.content)
        self.assertEqual(Operator.objects.get(id=r.json()['id']).accounts.count(),0)

    def test_assigned_user_can_create_named_account_without_internal_key(self):
        self.client.force_login(self.user)
        r=self.req('/api/accounts',{'name':'Mi banco personal','currency':'USD'})
        self.assertEqual(r.status_code,200,r.content)
        a=self.op.accounts.get(name='Mi banco personal')
        self.assertEqual(a.balance,0)
        self.assertEqual(a.currency,'USD')
        self.assertTrue(a.active)
        self.assertTrue(a.key.startswith('cuenta_'))
        self.assertEqual(self.req('/api/accounts',{'name':'No autorizada','currency':'UYU'},op=self.other).status_code,404)

    def test_only_admin_can_create_operators(self):
        self.client.force_login(self.user)
        self.assertEqual(self.req('/api/operators',{'name':'No permitido'}).status_code,403)

    def test_archive_empty_and_reactivate_preserves_identity(self):
        self.client.force_login(self.user)
        r=self.req('/api/accounts',{'key':'brou','action':'archive'},'put')
        self.assertEqual(r.status_code,200)
        a=self.op.accounts.get(key='brou')
        self.assertFalse(a.active)
        self.assertEqual(self.req('/api/accounts',{'key':'brou','action':'activate'},'put').status_code,200)
        a.refresh_from_db();self.assertTrue(a.active)
        self.assertEqual(Audit.objects.filter(action='account.archive').count(),1)

    def test_nonzero_balances_or_pending_orders_cannot_be_hidden(self):
        self.a.balance=100;self.a.save()
        self.assertEqual(self.req('/api/accounts',{'key':self.a.key,'action':'archive'},'put').status_code,400)
        o=Order.objects.create(operator=self.op,account=self.a,number='PENDING',type='sell',status='pending',payment_method=self.a.name,currency='UYU',amount=1,price=1,date=self.dt)
        self.a.balance=0;self.a.save()
        self.assertEqual(self.req('/api/accounts',{'key':self.a.key,'action':'archive'},'put').status_code,400)

    def test_reconciliation_accepts_visible_active_accounts_only(self):
        self.req('/api/accounts',{'key':'brou','action':'archive'},'put')
        self.op.refresh_from_db()
        balances={a.key:0 for a in self.op.accounts.filter(active=True)}
        balances['mercadoPago']=100
        r=self.req('/api/inventory',{'accounts':balances,'binance':0,'expectedRevision':str(self.op.revision),'reason':'Saldo real'},'put')
        self.assertEqual(r.status_code,200,r.content)
        self.op.refresh_from_db()
        self.assertEqual(s.inventory(self.op)['accounts']['brou'],0)
        self.assertEqual(s.inventory(self.op)['accounts']['mercadoPago'],100)

    def test_no_accounts_inventory_accepts_binance_only(self):
        op=Operator.objects.create(name='Vacío')
        r=self.req('/api/inventory',{'accounts':{},'binance':50,'expectedRevision':'0','reason':'Capital inicial'},'put',op=op)
        self.assertEqual(r.status_code,200,r.content)
        self.assertEqual(r.json()['inventory']['binance'],50)

    def test_invalid_account_currency_rejected_and_duplicate_labels_allowed(self):
        self.assertEqual(self.req('/api/accounts',{'name':'Cuenta','currency':'EUR'}).status_code,400)
        for i in range(2):self.assertEqual(self.req('/api/accounts',{'name':'Santander','currency':'UYU'}).status_code,200)
        self.assertEqual(self.op.accounts.filter(name='Santander').count(),3)


class AccountDemoTests(TestCase):
    def test_demo_only_creates_the_account_it_uses(self):
        from io import StringIO
        op=Operator.objects.create(name='Administrador')
        call_command('load_demo',stdout=StringIO())
        self.assertEqual(op.accounts.count(),1)
        self.assertEqual(op.accounts.get().key,'mercadoPago')
        self.assertEqual(op.orders.count(),6)


class MarketEnhancementTests(TestCase):
    def setUp(self):
        from . import market
        self.m=market
        market._cache.clear()
        self.user=get_user_model().objects.create_user('marketuser',password='Testing-948-secret')
        self.client.force_login(self.user)

    def raw(self, **changes):
        return {'advNo':'ad1','asset':'USDT','fiatUnit':'UYU','tradeType':'BUY','price':'41.32','minSingleTransAmount':'309','maxSingleTransAmount':'60000','dynamicMaxSingleTransAmount':'4213','tradableQuantity':'101.98','minSingleTransQuantity':'7.47','maxSingleTransQuantity':'1452.08','dynamicMaxSingleTransQuantity':'101.98','tradeMethods':[{'identifier':'Prex','tradeMethodName':'Prex'}],**changes}

    def ad(self, **changes):
        return self.m.normalize_ad(self.raw(**changes),{'userNo':'test_user','nickName':'Anunciante ficticio'})

    def test_effective_limits_and_fiat_amount_boundaries(self):
        ad=self.ad()
        self.assertEqual(ad['effectiveMaxFiat'],4213)
        for value,result in [('308',False),('309',True),('1000',True),('4213',True),('4214',False),('10000',False)]:
            self.assertEqual(self.m.compatible(ad,D(value)),result)

    def test_usdt_filter_converts_with_each_ad_price(self):
        ad=self.ad()
        self.assertTrue(self.m.compatible(ad,D(100),'USDT'))
        self.assertFalse(self.m.compatible(ad,D(102),'USDT'))
        self.assertFalse(self.m.compatible(ad,D(7),'USDT'))
        self.assertFalse(self.m.compatible(self.ad(asset='BTC'),D(1),'USDT'))

    def test_unknown_availability_and_nontradable_excluded(self):
        for changes in [{'tradableQuantity':None},{'minSingleTransAmount':None},{'isTradable':False}]:
            self.assertFalse(self.m.compatible(self.ad(**changes),D(1000)))

    def test_dynamic_quantity_and_quantity_limits(self):
        self.assertFalse(self.m.compatible(self.ad(dynamicMaxSingleTransQuantity='10'),D(1000)))
        self.assertFalse(self.m.compatible(self.ad(minSingleTransQuantity='30'),D(1000)))
        self.assertFalse(self.m.compatible(self.ad(maxSingleTransQuantity='10'),D(1000)))

    def test_available_quantity_caps_missing_dynamic_max(self):
        ad=self.ad(dynamicMaxSingleTransAmount=None,tradableQuantity='10')
        self.assertAlmostEqual(ad['effectiveMaxFiat'],413.2)
        self.assertFalse(self.m.compatible(ad,D(1000)))

    def test_amount_validation_rejects_bad_values(self):
        for value in ['0','-1','NaN','Infinity','10000000001','0.000000001','abc']:
            with self.assertRaises(ValueError):self.m.amount_value(value)
        self.assertIsNone(self.m.amount_value(''))
        self.assertEqual(self.m.amount_value('1000'),1000)

    def test_fiat_search_passes_amount_and_validates_availability(self):
        row={'adv':self.raw(),'advertiser':{'userNo':'test_user','nickName':'Ficticio'}}
        with patch.object(self.m,'query',return_value=[row]) as query:
            result=self.m.side('Prex','SELL','UYU',D(1000),'fiat')
        self.assertEqual(len(result['ads']),1)
        self.assertEqual(query.call_args.args[1]['transAmount'],'1000')
        self.assertEqual(result['ads'][0]['userNo'],'test_user')

    def test_usdt_scan_second_page_is_bounded_and_deduplicates(self):
        rows=[{'adv':self.raw(advNo=str(i),minSingleTransAmount='5000'),'advertiser':{}} for i in range(10)]
        compatible={'adv':self.raw(advNo='valid'),'advertiser':{}}
        with patch.object(self.m,'query',side_effect=[rows,[compatible,compatible]]) as query:
            result=self.m.side('Prex','SELL','UYU',D(100),'USDT')
        self.assertEqual(query.call_count,2)
        self.assertNotIn('transAmount',query.call_args.args[1])
        self.assertEqual(len(result['ads']),1)
        self.assertEqual(query.call_args.args[1]['page'],2)

    def test_profile_returns_both_sides_and_other_assets_without_private_data(self):
        data={'userDetailVo':{'userNo':'test_user','nickName':'Ficticio','mobile':'PRIVATE','email':'PRIVATE'},'buyList':[self.raw(remarks='<script>text</script>')],'sellList':[self.raw(advNo='ad2',asset='BTC',fiatUnit='USD',tradeType='SELL')]}
        with patch.object(self.m,'query',return_value=data) as query:
            result=self.m.advertiser('test_user')
            again=self.m.advertiser('test_user')
        self.assertEqual(query.call_count,1)
        self.assertEqual(len(result['ads']),2)
        self.assertEqual(result['ads'][1]['asset'],'BTC')
        self.assertNotIn('mobile',result)
        self.assertNotIn('email',result)
        self.assertEqual(result,again)
        self.assertIn('userNo=test_user',query.call_args.args[0])

    def test_empty_profile_distinct_from_upstream_error(self):
        with patch.object(self.m,'query',return_value={'userDetailVo':{'userNo':'test_user'},'buyList':[],'sellList':[]}):
            self.assertEqual(self.m.advertiser('test_user')['ads'],[])
        self.m._cache.clear()
        with patch.object(self.m,'query',side_effect=ValueError('Binance no disponible')):
            r=self.client.get('/api/advertiser?userNo=test_user')
            self.assertEqual(r.status_code,502)
            self.assertNotIn('ads',r.json())

    def test_invalid_and_mismatched_profile_identifiers(self):
        for uid in ['','../path','a&userNo=other','a'*101]:
            with self.assertRaises(ValueError):self.m.advertiser(uid)
        with patch.object(self.m,'query',return_value={'userDetailVo':{'userNo':'other'},'buyList':[],'sellList':[]}):
            with self.assertRaises(ValueError):self.m.advertiser('test_user')

    def test_missing_profile_side_not_reported_as_complete(self):
        with patch.object(self.m,'query',return_value={'userDetailVo':{'userNo':'test_user'},'buyList':[]}):
            with self.assertRaises(ValueError):self.m.advertiser('test_user')

    def test_profile_deduplicates_and_skips_offline_ads(self):
        data={'userDetailVo':{'userNo':'test_user'},'buyList':[self.raw(),self.raw(advStatus=3,advNo='paused')],'sellList':[self.raw()]}
        with patch.object(self.m,'query',return_value=data):self.assertEqual(len(self.m.advertiser('test_user')['ads']),1)

    @override_settings(P2P_MARKET_DEMO=True)
    def test_demo_filtered_market_and_profile_api(self):
        r=self.client.get('/api/market?fiat=UYU&amount=1000&amountUnit=fiat')
        self.assertEqual(r.status_code,200)
        ad=r.json()['groups'][0]['buy']['ads'][0]
        self.assertTrue(ad['userNo'].startswith('demo_'))
        profile=self.client.get('/api/advertiser?userNo='+ad['userNo'])
        self.assertEqual(profile.status_code,200)
        self.assertEqual(len(profile.json()['ads']),2)
        self.assertTrue(profile.json()['demo'])
        self.assertEqual(self.client.get('/api/market?fiat=UYU&amount=-1').status_code,400)
        self.assertEqual(self.client.get('/api/market?fiat=UYU&amountUnit=BTC').status_code,400)

    def test_profile_requires_login_and_get_only(self):
        self.assertEqual(Client().get('/api/advertiser?userNo=test_user').status_code,401)
        self.assertEqual(self.client.post('/api/advertiser?userNo=test_user').status_code,405)

class NotificationTests(TestCase):
    setUp = ApplicationTests.setUp
    url = ApplicationTests.url
    req = ApplicationTests.req
    order = ApplicationTests.order

    def test_notification_state_respects_operator_and_reservations(self):
        self.order()
        self.op.orders.update(status='pending')
        result=self.client.get(self.url('/api/notification-state')).json()
        self.assertEqual(len(result['pending']),1)
        self.assertLess(result['availableAccounts'][self.a.key],s.inventory(self.op)['accounts'][self.a.key])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url('/api/notification-state',self.other)).status_code,404)
        self.assertEqual(self.client.get(self.url('/api/own-ads',self.other)).status_code,404)

    @override_settings(P2P_MARKET_DEMO=True)
    def test_own_profile_verified_and_unfiltered(self):
        self.op.binance_username='Demo 1';self.op.save()
        response=self.client.get(self.url('/api/own-ads')+'&userNo=demo_1&amount=999999&method=unknown')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['status'],'watching')
        self.assertEqual(len(response.json()['ads']),2)
        self.assertEqual(self.client.get(self.url('/api/own-ads')+'&userNo=demo_2').status_code,502)

    @override_settings(P2P_MARKET_DEMO=True)
    def test_profile_not_found_is_not_empty_ads(self):
        self.op.binance_username='Absent-demo-username';self.op.save()
        result=self.client.get(self.url('/api/own-ads')).json()
        self.assertEqual(result['status'],'not_found')
        self.assertNotIn('ads',result)

    def test_missing_username_and_methods(self):
        self.op.binance_username='';self.op.save()
        self.assertEqual(self.client.get(self.url('/api/own-ads')).json()['status'],'unconfigured')
        self.assertEqual(self.req('/api/notification-state',{}).status_code,405)
        self.assertEqual(self.req('/api/own-ads',{}).status_code,405)
