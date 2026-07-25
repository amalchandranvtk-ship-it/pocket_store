import secrets

from django.db import models
from django.conf import settings


class Referral(models.Model):

    STATUS_CHOICES = (

        ("Pending", "Pending"),

        ("Completed", "Completed"),

    )

    referrer = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="referrals_made")
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="referred_by")
    reward_amount = models.DecimalField(max_digits=10,decimal_places=2,default=100)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="Completed")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):

        return f"{self.referrer.email} -> {self.referred_user.email}"
