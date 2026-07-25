from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from customer.accounts.models import User


class Coupon(models.Model):

    PERCENTAGE = "percentage"
    FLAT = "flat"

    DISCOUNT_TYPE_CHOICES = (
        (PERCENTAGE, "Percentage"),
        (FLAT, "Flat"),
    )

    coupon_code = models.CharField(max_length=50,unique=True)

    discount_type = models.CharField(max_length=20,choices=DISCOUNT_TYPE_CHOICES)

    discount_value = models.DecimalField(max_digits=10,decimal_places=2)

    minimum_order_value = models.DecimalField(max_digits=10,decimal_places=2)

    total_usage_limit = models.PositiveIntegerField()

    limit_per_user = models.PositiveIntegerField(default=1)

    start_date = models.DateField()

    expiry_date = models.DateField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        ordering = ["-created_at"]

    def __str__(self):

        return self.coupon_code

    @property
    def total_used(self):

        return self.usages.count()

    @property
    def remaining_usage(self):

        return self.total_usage_limit - self.total_used

    @property
    def is_expired(self):

        return timezone.now().date() > self.expiry_date

    def clean(self):

        if self.discount_value <= 0:
            raise ValidationError(
                {"discount_value": "Discount must be greater than zero."}
            )

        if self.minimum_order_value < 0:
            raise ValidationError(
                {"minimum_order_value": "Minimum order value cannot be negative."}
            )

        if self.discount_type == self.PERCENTAGE:

            if self.discount_value > 100:
                raise ValidationError(
                    {"discount_value": "Percentage discount cannot exceed 100%."}
                )

        if self.discount_type == self.FLAT:

            if self.discount_value >= self.minimum_order_value:
                raise ValidationError(
                    {
                        "discount_value":
                        "Flat discount must be less than minimum order value."
                    }
                )

        if self.start_date >= self.expiry_date:
            raise ValidationError(
                {"expiry_date": "Expiry date must be after start date."}
            )

        if self.total_usage_limit <= 0:
            raise ValidationError(
                {"total_usage_limit": "Usage limit must be greater than zero."}
            )

        if self.limit_per_user <= 0:
            raise ValidationError(
                {"limit_per_user": "Limit per user must be greater than zero."}
            )

    def save(self, *args, **kwargs):

        self.coupon_code = self.coupon_code.upper().strip()

        self.full_clean()

        super().save(*args, **kwargs)



class CouponUsage(models.Model):

    coupon = models.ForeignKey(Coupon,on_delete=models.CASCADE,related_name="usages")

    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="coupon_usages")

    order = models.ForeignKey("orders.Order",on_delete=models.CASCADE,related_name="coupon_usages")

    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        unique_together = ("coupon", "user", "order")

        ordering = ["-used_at"]

    def __str__(self):

        return f"{self.user.full_name} - {self.coupon.coupon_code}"