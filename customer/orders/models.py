from django.db import models

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from admin_panel.catalog.models import ProductVariant
from customer.accounts.models import Address


class Order(models.Model):

    ORDER_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    COUPON_TYPE_CHOICES = (
        ("percentage", "Percentage"),
        ("fixed", "Fixed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="orders")
    address = models.ForeignKey(Address,on_delete=models.SET_NULL,null=True,blank=True)
    order_number = models.CharField(max_length=50,unique=True)
    order_status = models.CharField(max_length=30,choices=ORDER_STATUS_CHOICES,default="pending")
    payment_status = models.CharField(max_length=30,choices=PAYMENT_STATUS_CHOICES,default="pending")
    coupon_code = models.CharField(max_length=50,blank=True,null=True)
    coupon_discount_type = models.CharField(max_length=20,choices=COUPON_TYPE_CHOICES,blank=True,null=True )
    coupon_discount_value = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    subtotal = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    discount_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    delivery_charge = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    tax_amount = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    total_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    estimated_delivery = models.DateField(null=True,blank=True)
    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-placed_at"]

    def __str__(self):
        return self.order_number

    @property
    def total_items(self):
        return self.items.count()
    
class OrderItem(models.Model):

    ITEM_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
    )

    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name="items")
    variant = models.ForeignKey(ProductVariant,on_delete=models.SET_NULL,null=True,blank=True)
    product_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=12,decimal_places=2)
    total = models.DecimalField(max_digits=12,decimal_places=2)
    status = models.CharField(max_length=30,choices=ITEM_STATUS_CHOICES,default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} ({self.order.order_number})"
    

class Payment(models.Model):

    PAYMENT_METHOD_CHOICES = (
        ("cod", "Cash On Delivery"),
        ("razorpay", "Razorpay"),
        ("wallet", "Wallet"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    order = models.OneToOneField(Order,on_delete=models.CASCADE,related_name="payment")
    payment_method = models.CharField(max_length=30,choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=150,blank=True,null=True)
    amount = models.DecimalField(max_digits=12,decimal_places=2)
    payment_status = models.CharField(max_length=30,choices=PAYMENT_STATUS_CHOICES,default="pending")
    paid_at = models.DateTimeField(null=True,blank=True)

    def __str__(self):
        return f"{self.order.order_number}"
    
class OrderStatusHistory(models.Model):

    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name="history")
    status = models.CharField(max_length=50)
    note = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"
    
class OrderCancellation(models.Model):

    order_item = models.OneToOneField(OrderItem,on_delete=models.CASCADE,related_name="cancellation")
    reason = models.TextField(blank=True,null=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancelled - {self.order_item.id}"
    
