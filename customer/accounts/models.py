from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = (
        ("customer", "Customer"),
        ("admin", "Admin"),
    )

    full_name = models.CharField(max_length=100,blank=True,null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to="profile_images/", blank=True, null=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="customer")
    referral_code = models.CharField(max_length=50, unique=True, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email", "full_name"]

    def __str__(self):
        return self.email


class OTPVerification(models.Model):
    PURPOSE_CHOICES = (
        ("signup", "Signup"),
        ("forgot_password", "Forgot Password"),
        ("email_change", "Email Change"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField()
    otp_code = models.CharField(max_length=10)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} - {self.purpose}"


class Address(models.Model):
    ADDRESS_CHOICES = (
        ("home", "Home"),
        ("work", "Work"),
        ("other", "Other"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    address_type = models.CharField(max_length=20, choices=ADDRESS_CHOICES, default="home")
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.address_type}"