from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.validators import MaxValueValidator


class Review(models.Model):
    STATUS_CHOICES = (
        ("Published", "Published"),
        ("Hidden", "Hidden"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="reviews")

    product = models.ForeignKey("catalog.Product",on_delete=models.CASCADE,related_name="reviews")

    order_item = models.OneToOneField("orders.OrderItem",on_delete=models.CASCADE,related_name="review")

    rating = models.PositiveSmallIntegerField(
                    validators=[MinValueValidator(1),MaxValueValidator(5),]
            )

    review_title = models.CharField(max_length=150)

    review_description = models.TextField()

    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="Published")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.product_name} - {self.user}"