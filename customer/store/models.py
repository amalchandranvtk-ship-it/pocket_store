from django.db import models
from django.conf import settings


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "variant")

    def __str__(self):
        return f"{self.user.email} - {self.variant}"


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "variant")

    @property
    def total_price(self):
        from admin_panel.offers.utils import get_variant_offer_price

        offer_data = get_variant_offer_price(self.variant)

        return offer_data["selling_price"] * self.quantity

    def __str__(self):
        return f"{self.user.email} - {self.variant} - {self.quantity}"
