from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    username = models.TextField(unique=True)
