# models.py
from django.db import models
from django.utils import timezone

class EthUsdRate(models.Model):
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.rate} at {self.timestamp}"
