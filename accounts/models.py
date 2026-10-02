"""Usuario propio: el rol de negocio no se acepta desde el registro publico."""
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower


class TicketUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = "ORGANIZADOR"
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        SPECTATOR = "ESPECTADOR", "Espectador"
        ORGANIZER = "ORGANIZADOR", "Organizador"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=Role, default=Role.SPECTATOR)
    objects = TicketUserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("username"), name="account_username_ci_unique"),
            models.UniqueConstraint(Lower("email"), name="account_email_ci_unique"),
            models.CheckConstraint(condition=models.Q(role__in=["ESPECTADOR", "ORGANIZADOR"]), name="account_role_valid"),
        ]

    @property
    def is_organizer(self):
        return self.is_active and (self.is_superuser or self.role == self.Role.ORGANIZER)

    @property
    def effective_role(self):
        return self.Role.ORGANIZER if self.is_organizer else self.Role.SPECTATOR
