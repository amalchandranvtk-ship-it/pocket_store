from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from admin_panel.catalog.models import Product, Category


class Offer(models.Model):
    APPLY_CHOICES = (
        ("product", "Product"),
        ("category", "Category"),
    )

    TYPE_CHOICES = (
        ("percentage", "Percentage"),
        ("flat", "Flat"),
    )

    offer_name = models.CharField(max_length=150)
    offer_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    apply_to = models.CharField(max_length=20, choices=APPLY_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateField()
    valid_to = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.offer_name

    @property
    def expired(self):
        return self.valid_to < timezone.localdate()

    @property
    def active(self):
        today = timezone.localdate()
        return (
            self.is_active
            and self.valid_from <= today <= self.valid_to
        )


class OfferProduct(models.Model):
    offer = models.ForeignKey(Offer,on_delete=models.CASCADE,related_name="offer_products")
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name="product_offers")

    class Meta:
        unique_together = ("offer", "product")

    def __str__(self):
        return f"{self.offer} - {self.product}"


class OfferCategory(models.Model):
    offer = models.ForeignKey(Offer,on_delete=models.CASCADE,related_name="offer_categories")
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="category_offers")

    class Meta:
        unique_together = ("offer", "category")

    def __str__(self):
        return f"{self.offer} - {self.category}"


class Referral(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("expired", "Expired"),
    )

    referrer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_referrals",
    )

    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_referrals",
        null=True,
        blank=True,
    )

    referral_code = models.CharField(max_length=20,unique=True)

    reward_amount = models.DecimalField(max_digits=10,decimal_places=2,default=Decimal("0.00"))

    status = models.CharField(max_length=20,choices=STATUS,default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.referral_code
