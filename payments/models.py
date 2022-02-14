from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.user.username + ' -> ' + str(self.amount)


class Transaction(models.Model):
    source_account = models.ForeignKey(Account, blank=True, null=True, related_name="source_account",
                                       on_delete=models.PROTECT)
    destination_account = models.ForeignKey(Account, blank=True, null=True, related_name="destination_account",
                                            on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        if self.source_user is None:
            return 'Creation: ' + self.destination_user.username
        elif self.destination_user is None:
            return "Destruction: " + self.source_user.username
        else:
            return self.source_user + " -> " + self.destination_user
