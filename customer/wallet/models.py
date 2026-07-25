from django.db import models
from django.conf import settings


class Wallet(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="wallet")
    balance = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name} Wallet"


class WalletTransaction(models.Model):

    TRANSACTION_TYPE = (
        ("credit", "Credit"),
        ("debit", "Debit"),
        ("refund","Refund"),
        ("cashback","Cashback"),
        ("referral", "Referral Bonus"),

    )

    PAYMENT_METHOD = (
        ("wallet", "Wallet"),
        ("razorpay", "Razorpay"),
        ("refund", "Refund"),
        ("referral", "Referral"),

    )

    STATUS = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    wallet = models.ForeignKey(Wallet,on_delete=models.CASCADE,related_name="transactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="wallet_transactions")
    transaction_type = models.CharField(max_length=20,choices=TRANSACTION_TYPE)
    amount = models.DecimalField(max_digits=12,decimal_places=2)
    payment_method = models.CharField(max_length=20,choices=PAYMENT_METHOD)
    status = models.CharField(max_length=20,choices=STATUS,default="success")
    description = models.CharField(max_length=255,blank=True,null=True)
    transaction_id = models.CharField(max_length=200,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.full_name} - {self.transaction_type}"
