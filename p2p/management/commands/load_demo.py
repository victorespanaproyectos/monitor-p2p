from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from p2p.models import Operator, Order, Movement, Account
from p2p.services import rebase, snapshot


class Command(BaseCommand):
    help = (
        "Carga ejemplos ficticios en un operador vacío; nunca incluye datos personales."
    )

    def handle(self, *args, **kwargs):
        op = Operator.objects.filter(name="Administrador", active=True).first()
        if not op:
            raise CommandError("Ejecuta primero setup_admin.")
        if op.orders.exists() or op.movements.exists():
            raise CommandError(
                "El operador tiene datos. La demostración no los sobrescribe."
            )
        with transaction.atomic():
            a, _ = Account.objects.get_or_create(operator=op, key="mercadoPago", defaults={"name":"MercadoPago", "currency":"UYU"})
            date = timezone.now() - timedelta(days=2)
            for i in range(6):
                Order.objects.create(
                    operator=op,
                    account=a,
                    number="DEMO-" + str(i + 1),
                    type="buy" if i % 2 == 0 else "sell",
                    payment_method="MercadoPago",
                    currency="UYU",
                    price=Decimal("41.00") if i % 2 == 0 else Decimal("42.20"),
                    amount=Decimal("4100") if i % 2 == 0 else Decimal("3798"),
                    date=date + timedelta(hours=i),
                )
            Movement.objects.create(
                operator=op,
                account=a,
                kind="withdrawal",
                amount=Decimal("500"),
                date=timezone.now(),
                note="Ejemplo ficticio de retiro",
            )
            rebase(
                op,
                {
                    "accounts": {
                        x.key: (
                            Decimal("10000") if x.key == "mercadoPago" else Decimal(0)
                        )
                        for x in op.accounts.all()
                    },
                    "binance": Decimal("1000"),
                },
            )
            op.revision += 1
            op.save()
            snapshot(op)
        self.stdout.write(
            "Datos ficticios cargados. Para anuncios simulados configura P2P_MARKET_DEMO=1."
        )
