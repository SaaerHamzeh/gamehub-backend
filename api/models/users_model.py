from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_OWNER = "OWNER"
    ROLE_MANAGER = "MANAGER"
    ROLE_CASHIER = "CASHIER"
    ROLE_STAFF = "STAFF"

    ROLE_CHOICES = (
        (ROLE_OWNER, "Owner"),
        (ROLE_MANAGER, "Manager"),
        (ROLE_CASHIER, "Cashier"),
        (ROLE_STAFF, "Staff"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STAFF)
    pin = models.CharField(max_length=10, unique=True, null=True, blank=True)

    def __str__(self):
        return self.username
