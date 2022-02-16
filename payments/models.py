from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    transaction_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        if self.source_user is None:
            return 'Creation: ' + self.destination_user.username
        elif self.destination_user is None:
            return "Destruction: " + self.source_user.username
        else:
            return self.source_user + " -> " + self.destination_user


class Loan(models.Model):
    loaner = models.ForeignKey(Account, related_name="loaner", on_delete=models.CASCADE)
    receiver = models.ForeignKey(Account, related_name="receiver", on_delete=models.CASCADE)
    lend_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.IntegerField()
    due_date = models.DateTimeField()
    loan_days = models.IntegerField()
    return_date = models.DateTimeField(default=None, blank=True, null=True)
    returned_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.loaner.user.username + " -> loaned -> " + self.receiver.user.username


