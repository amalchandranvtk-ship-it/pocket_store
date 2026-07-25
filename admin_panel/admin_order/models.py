from django.db import models
from django.conf import settings
from customer.orders.models import Order, OrderItem


class Return(models.Model):

    RETURN_STATUS = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    )

    RETURN_METHOD = (
        ("pickup", "Door Pickup"),
        ("dropoff", "Drop Off"),
    )

    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name="returns")
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="returns")
    request_id = models.CharField(max_length=30,unique=True)
    return_method = models.CharField(max_length=20,choices=RETURN_METHOD,default="pickup")
    reason = models.TextField()
    additional_comments = models.TextField(blank=True,null=True)
    estimated_refund = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    status = models.CharField(max_length=20,choices=RETURN_STATUS,default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True,null=True)
    admin_note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return self.request_id
    

class ReturnItem(models.Model):

    return_request = models.ForeignKey(Return,on_delete=models.CASCADE,related_name="items")
    order_item = models.ForeignKey(OrderItem,on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.order_item.product_name  
    

class ReturnProofImage(models.Model):

    return_request = models.ForeignKey(Return,on_delete=models.CASCADE,related_name="proof_images")
    image = models.ImageField(upload_to="returns/")

    def __str__(self):
        return self.return_request.request_id
    
def generate_return_request_id():

    last = Return.objects.order_by("-id").first()

    if not last:
        return "RET100001"

    return f"RET{100000 + last.id + 1}"

