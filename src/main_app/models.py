from operator import mul

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy


class Contractor(models.Model):
    name = models.CharField(max_length=50)
    address1 = models.CharField(max_length=50)
    address2 = models.CharField(max_length=50)
    NIP = models.CharField(max_length=10, unique=True)

    def save(self, *args, **kwargs):
        if not self.validate_nip(self.NIP):
            raise ValidationError(
                ugettext_lazy('NIP: %(nip) is incorrect'),
                params={'nip': self.NIP}
            )
        super().save(*args, **kwargs)

    @staticmethod
    def validate_nip(nip):
        nip = nip.replace('-', '')
        if len(nip) != 10 or not nip.isdigit():
            return False
        *digits, crc = map(int, nip)
        weights = (6, 5, 7, 2, 3, 4, 5, 6, 7)
        check_sum = sum(map(mul, digits, weights))
        return check_sum % 11 == crc

    def __str__(self):
        return '{}, NIP:{}'.format(self.name, self.NIP)


class Line(models.Model):
    invoice = models.ForeignKey('Invoice', related_name='lines')
    description = models.CharField(max_length=100)
    price = models.FloatField()
    amount = models.PositiveSmallIntegerField(default=1)
    tax = models.PositiveSmallIntegerField(default=23)

    class Meta:
        unique_together = ['invoice', 'description']

    @property
    def net(self):
        n = self.price * self.amount
        return round(n, 2)

    @property
    def gross(self):
        g = self.net * (1 + self.tax / 100)
        return round(g, 2)

    def __str__(self):
        return '{}: ({} + {}%) * {}'.format(
            self.description, self.price, self.tax, self.amount
        )


class Invoice(models.Model):
    date = models.DateField(default=timezone.now)
    number = models.PositiveIntegerField()
    issuer = models.ForeignKey(Contractor, related_name='issuer')
    receiver = models.ForeignKey(Contractor, related_name='receiver')

    def save(self, *args, **kwargs):
        if self.issuer == self.receiver:
            raise ValidationError(
                ugettext_lazy('Issuer and receiver cannot be the same'),
            )
        super().save(*args, **kwargs)

    @property
    def lines(self):
        return Line.objects.filter(invoice=self)

    @property
    def total_net(self):
        s = sum(i.net for i in self.lines)
        return round(s, 2)

    @property
    def total_gross(self):
        s = sum(i.gross for i in self.lines)
        return round(s, 2)

    def __str__(self):
        return '#{} on {} from {} to {}'.format(
            self.number, self.date, self.issuer, self.receiver
        )
