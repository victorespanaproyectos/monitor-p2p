import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from p2p.models import Operator


class Command(BaseCommand):
    help = "Crea el primer Administrador. No modifica una instalación existente."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("Ya existe un administrador. No se modificó.")
            return
        username = options["username"]
        if User.objects.filter(username=username).exists():
            raise CommandError("Usuario existente. Selecciona otro nombre.")
        password = getpass.getpass("Contraseña del Administrador: ")
        confirmation = getpass.getpass("Repite la contraseña: ")
        if password != confirmation:
            raise CommandError("Las contraseñas no coinciden.")
        try:
            validate_password(password, User(username=username))
        except ValidationError as e:
            raise CommandError("; ".join(e.messages))
        with transaction.atomic():
            user = User.objects.create_superuser(username=username, password=password)
            op = Operator.objects.create(name="Administrador")
            op.users.add(user)
        self.stdout.write(
            self.style.SUCCESS(
                "Administrador creado. Inicia sesión y configura tu usuario Binance y tus saldos."
            )
        )
