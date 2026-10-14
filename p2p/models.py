import uuid
from django.conf import settings
from django.db import models


class Operator(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80)
    binance_username = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="operators", blank=True
    )
    commission = models.DecimalField(max_digits=8, decimal_places=6, default="0.002000")
    funds = models.DecimalField(max_digits=24, decimal_places=8, default=0)
    order_baseline = models.JSONField(default=dict)
    movement_baseline = models.JSONField(default=dict)
    revision = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.name


class Account(models.Model):
    operator = models.ForeignKey(
        Operator, on_delete=models.PROTECT, related_name="accounts"
    )
    key = models.CharField(max_length=50)
    name = models.CharField(max_length=80)
    currency = models.CharField(
        max_length=3, choices=[("UYU", "UYU"), ("USD", "USD")], default="UYU"
    )
    balance = models.DecimalField(max_digits=24, decimal_places=2, default=0)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["operator", "key"], name="unique_account_operator"
            )
        ]
        ordering = ["id"]


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator = models.ForeignKey(
        Operator, on_delete=models.PROTECT, related_name="orders"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="orders"
    )
    number = models.CharField(max_length=100)
    type = models.CharField(
        max_length=4, choices=[("buy", "Compra"), ("sell", "Venta")]
    )
    status = models.CharField(max_length=10, choices=[("pending", "Pendiente"), ("completed", "Completada"), ("cancelled", "Cancelada")], default="completed")
    expense_rate = models.DecimalField(max_digits=8, decimal_places=6, default=0)
    expense_fixed = models.DecimalField(max_digits=24, decimal_places=2, default=0)
    expense_note = models.CharField(max_length=300, blank=True)
    payment_method = models.CharField(max_length=100)
    currency = models.CharField(max_length=3)
    price = models.DecimalField(max_digits=24, decimal_places=6)
    amount = models.DecimalField(max_digits=24, decimal_places=2)
    fee_rate = models.DecimalField(max_digits=8, decimal_places=6, default="0.002000")
    date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    receipt = models.BinaryField(
        null=True, blank=True
    )  # transactional storage, authorized download only
    receipt_name = models.CharField(max_length=200, blank=True)
    receipt_mime = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["operator", "number"], name="unique_order_operator"
            )
        ]
        ordering = ["date", "created_at", "id"]


class Movement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator = models.ForeignKey(
        Operator, on_delete=models.PROTECT, related_name="movements"
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    kind = models.CharField(
        max_length=10, choices=[("deposit", "Depósito"), ("withdrawal", "Retiro")]
    )
    amount = models.DecimalField(max_digits=24, decimal_places=2)
    date = models.DateTimeField()
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Audit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT)
    action = models.CharField(max_length=50)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class DailySnapshot(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT)
    day = models.DateField()
    total = models.DecimalField(max_digits=28, decimal_places=8, null=True)
    withdrawals = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["operator", "day"], name="unique_daily_operator"
            )
        ]
