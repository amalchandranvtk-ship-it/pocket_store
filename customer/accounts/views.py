import random
import re
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from allauth.socialaccount.models import SocialAccount
from admin_panel.offers.utils import get_variant_offer_price


from .models import OTPVerification, Address
from admin_panel.catalog.models import Product
from django.views.decorators.cache import cache_control


from django.db import transaction
from customer.referrals.models import Referral
from decimal import Decimal
from customer.wallet.models import Wallet, WalletTransaction



User = get_user_model()


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_mail(email, otp):
    send_mail(
        "PocketStore OTP Verification",
        f"Your PocketStore OTP is {otp}. This OTP is valid for 1 minute.",
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False
    )


def is_valid_password(password):
    if len(password) < 8:
        return "Password must contain at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character"
    return None


def validate_address_data(full_name, phone, address_line1, city, state, zip_code, country):
    if not full_name or not full_name.replace(" ", "").isalpha():
        return "Name must contain only letters"

    if not phone or not re.fullmatch(r"[6-9]\d{9}", phone):
        return "Phone number must be 10 digits and start with 6, 7, 8 or 9"

    if not address_line1 or len(address_line1.strip()) < 10:
        return "Address must contain at least 10 characters"

    if not city or not city.replace(" ", "").isalpha():
        return "City must contain only letters"

    if not state or not state.replace(" ", "").isalpha():
        return "State must contain only letters"

    if not zip_code or not re.fullmatch(r"\d{6}", zip_code):
        return "PIN code must be exactly 6 digits"

    if not country or not country.replace(" ", "").isalpha():
        return "Country must contain only letters"

    return None


def is_customer_user(user):
    return user.is_authenticated and not user.is_staff and not user.is_superuser and user.role == "customer"


def create_otp(email, purpose, user=None):
    OTPVerification.objects.filter(email=email, purpose=purpose, is_used=False).delete()

    otp = generate_otp()

    OTPVerification.objects.create(
        user=user,
        email=email,
        otp_code=otp,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=1)
    )

    send_otp_mail(email, otp)


@never_cache

def public_home(request):
    mobiles = Product.objects.filter(
        category__type="mobiles",
        category__is_active=True,
        category__is_deleted=False,
        brand__is_active=True,
        product_status="active",
        is_deleted=False,
        variants__is_active=True,
        variants__stock_quantity__gt=0
    ).select_related(
        "category",
        "brand"
    ).prefetch_related(
        "variants",
        "variants__images"
    ).distinct().order_by("-id")[:4]

    for product in mobiles:

       variant = product.default_variant

       if variant:
           product.variant = variant

           product.offer_data = get_variant_offer_price(variant)

    return render(request, "accounts/public_home.html", {
        "mobiles": mobiles
    })


@never_cache
def signup(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            auth_logout(request)
            messages.error(request, "Admin cannot access customer side")
            return redirect("customer_login")
        return redirect("customer_home")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        referral_code = request.POST.get("referral_code", "").strip().upper()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not full_name or not email or not password or not confirm_password:
            messages.error(request, "All fields are required")
            return redirect("customer_signup")

        if not full_name.replace(" ", "").isalpha():
            messages.error(request, "Full name must contain only alphabets")
            return redirect("customer_signup")

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address")
            return redirect("customer_signup")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("customer_signup")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("customer_signup")

        password_error = is_valid_password(password)
        if password_error:
            messages.error(request, password_error)
            return redirect("customer_signup")
        if referral_code:

            try:
               User.objects.get(referral_code=referral_code)

            except User.DoesNotExist:
                messages.error(request, "Invalid Referral Code")
                return redirect("customer_signup")


        request.session["signup_referral_code"] = referral_code
        request.session["signup_full_name"] = full_name
        request.session["signup_email"] = email
        request.session["signup_password"] = password
        request.session["otp_email"] = email
        request.session["otp_purpose"] = "signup"

        create_otp(email, "signup")

        messages.success(request, "OTP sent to your email")
        return redirect("customer_verify_otp")

    return render(request, "accounts/signup.html")


@never_cache
def verify_otp(request):
    email = request.session.get("otp_email")
    purpose = request.session.get("otp_purpose")
    remaining_seconds = 60

    otp_obj = OTPVerification.objects.filter(
                    email=email,
                    purpose=purpose,
                    is_used=False).last()

    if otp_obj:
        remaining_seconds = max(0,int((otp_obj.expires_at - timezone.now()).total_seconds()))   

    if not email or not purpose:
        messages.error(request, "OTP session expired")
        return redirect("customer_signup")

    if request.method == "POST":
        entered_otp = "".join([
            request.POST.get("otp1", ""),
            request.POST.get("otp2", ""),
            request.POST.get("otp3", ""),
            request.POST.get("otp4", ""),
            request.POST.get("otp5", ""),
            request.POST.get("otp6", ""),
        ])

       
        if not otp_obj:
            messages.error(request, "OTP not found. Please resend OTP")
            return redirect("customer_verify_otp")

        if otp_obj.is_expired():
            messages.error(request, "OTP expired. Please resend OTP")
            return redirect("customer_verify_otp")

        if otp_obj.otp_code != entered_otp:
            messages.error(request, "Invalid OTP")
            
            return render(request, "accounts/otp_verify.html", {
                "title": "Verify Signup OTP" if purpose == "signup" else "Verify Password Reset OTP",
                "email": email,
                "back_url": "customer_signup" if purpose == "signup" else "customer_forgot_password",
                "back_text": "Back to Signup" if purpose == "signup" else "Back to Forgot Password",
                "timer_seconds": remaining_seconds
            })
        otp_obj.is_used = True
        otp_obj.save()

        if purpose == "signup":
            full_name = request.session.get("signup_full_name")
            signup_email = request.session.get("signup_email")
            signup_password = request.session.get("signup_password")

            user = User.objects.create_user(
                username=signup_email,
                email=signup_email,
                password=signup_password,
                full_name=full_name,
                first_name=full_name,
                role="customer"
            )

            user.save()

            referral_code = request.session.get("signup_referral_code")

            if referral_code:

                try:

                    referrer = User.objects.get(referral_code=referral_code)

                    reward_amount = Decimal("100.00")
                    Referral.objects.create(
                       referrer=referrer,
                       referred_user=user,
                       reward_amount=reward_amount,
                       status="Success"
                    )

                    referrer_wallet, created = Wallet.objects.get_or_create(
                      user=referrer
                    )

                    referrer_wallet.balance += reward_amount
                    referrer_wallet.save()

                    WalletTransaction.objects.create(
                       wallet=referrer_wallet,
                       user=referrer,
                       transaction_type="credit",
                       amount=reward_amount,
                       payment_method="wallet",
                       status="success",
                       description=f"Referral bonus for inviting {user.full_name}"
                    )

                    new_user_wallet, created = Wallet.objects.get_or_create(
                      user=user
                    )

                    new_user_wallet.balance += reward_amount
                    new_user_wallet.save()

                    WalletTransaction.objects.create(
                       wallet=new_user_wallet,
                       user=user,
                       transaction_type="credit",
                       amount=reward_amount,
                       payment_method="wallet",
                       status="success",
                       description="Welcome referral bonus"
                    )

                except User.DoesNotExist:
                   pass

            request.session.flush()
            messages.success(request, "Signup successful. Please login")
            return redirect("customer_login")

        if purpose == "forgot_password":
            request.session["reset_email"] = email
            messages.success(request, "OTP verified. Reset your password")
            return redirect("customer_reset_password")

    return render(request, "accounts/otp_verify.html", {
        "title": "Verify Signup OTP" if purpose == "signup" else "Verify Password Reset OTP",
        "email": email,
        "back_url": "customer_signup" if purpose == "signup" else "customer_forgot_password",
        "back_text": "Back to Signup" if purpose == "signup" else "Back to Forgot Password",
        "timer_seconds": remaining_seconds 
    })


@never_cache
def resend_otp(request):
    email = request.session.get("otp_email")
    purpose = request.session.get("otp_purpose")

    if not email or not purpose:
        messages.error(request, "Session expired")
        return redirect("customer_signup")

    create_otp(email, purpose)
    messages.success(request, "New OTP sent successfully")
    return redirect("customer_verify_otp")


@never_cache
def login(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            auth_logout(request)
            return redirect("customer_login")

        return redirect("public_home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Email and password are required")
            return redirect("customer_login")
        try:
            user_obj=User.objects.get(email=email)
            if not user_obj.is_active:
                messages.error(request,"Your account is blocked.Contact Admin")
                return redirect("customer_login")
        except User.DoesNotExist:
                pass

        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, "Invalid email or password")
            return redirect("customer_login")

        if user.is_staff or user.is_superuser:
            messages.error(request, "Admin cannot login in customer side")
            return redirect("customer_login")

        if not is_customer_user(user):
            messages.error(request, "Customer login only")
            return redirect("customer_login")

        auth_login(request, user)
        messages.success(request,"Welcome Back")
        return redirect("public_home")

    return render(request, "accounts/login.html")


@never_cache
def forgot_password(request):
    if request.user.is_authenticated:
        return redirect("customer_home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Email is required")
            return redirect("customer_forgot_password")

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address")
            return redirect("customer_forgot_password")

        user = User.objects.filter(email=email, role="customer").first()

        if not user:
            messages.error(request, "Email not registered")
            return redirect("customer_forgot_password")

        if not user.is_active:
            messages.error(request, "Your account is blocked. Contact admin")
            return redirect("customer_forgot_password")

        request.session["otp_email"] = email
        request.session["otp_purpose"] = "forgot_password"

        create_otp(email, "forgot_password", user)

        messages.success(request, "OTP sent to your email")
        return redirect("customer_verify_otp")

    return render(request, "accounts/forgot_password.html")


@never_cache
def reset_password(request):
    email = request.session.get("reset_email")

    if not email:
        messages.error(request, "Please verify OTP first")
        return redirect("customer_forgot_password")

    if request.method == "POST":
        password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not password or not confirm_password:
            messages.error(request, "All fields are required")
            return redirect("customer_reset_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("customer_reset_password")

        password_error = is_valid_password(password)
        if password_error:
            messages.error(request, password_error)
            return redirect("customer_reset_password")

        user = User.objects.filter(email=email, role="customer").first()

        if not user:
            messages.error(request, "User not found")
            return redirect("customer_forgot_password")

        user.set_password(password)
        user.save()

        request.session.flush()
        messages.success(request, "Password reset successful. Please login")
        return redirect("customer_login")

    return render(request, "accounts/reset_password.html")


@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="customer_login")
def customer_home(request):
    if not is_customer_user(request.user):
        auth_logout(request)
        messages.error(request, "Customer access only")
        return redirect("customer_login")

    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    if not default_address:
      default_address = Address.objects.filter(user=request.user).last()

    return render(request, "accounts/customer_home.html", {
        "user": request.user,
        "default_address": default_address,
    })


@never_cache
@login_required(login_url="customer_login")
def edit_profile(request):
    if not is_customer_user(request.user):
        auth_logout(request)
        return redirect("customer_login")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not full_name:
            messages.error(request, "Full name is required")
            return redirect("edit_profile")
        if not phone or not re.fullmatch(r"[6-9]\d{9}", phone):
            messages.error(request,"Enter Valid Phone Number")
            return redirect("edit_profile")



        request.user.full_name = full_name
        request.user.first_name = full_name
        request.user.phone = phone

        if request.FILES.get("profile_image"):
            request.user.profile_image = request.FILES.get("profile_image")

        request.user.save()
        messages.success(request, "Profile updated successfully")
        return redirect("customer_home")

    return render(request, "accounts/edit_profile.html", {"user": request.user})


@never_cache
@login_required(login_url="customer_login")
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not request.user.check_password(old_password):
            messages.error(request, "Old password is incorrect")
            return redirect("change_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("change_password")

        password_error = is_valid_password(new_password)
        if password_error:
            messages.error(request, password_error)
            return redirect("change_password")

        request.user.set_password(new_password)
        request.user.save()
        auth_logout(request)

        messages.success(request, "Password changed successfully. Please login again")
        return redirect("customer_login")

    return render(request, "accounts/change_password.html")


@never_cache
@login_required(login_url="customer_login")
def address_list(request):
    addresses = Address.objects.filter(user=request.user).order_by("-is_default", "-id")
    return render(request, "accounts/address_list.html", {"addresses": addresses})


@never_cache
@login_required(login_url="customer_login")
def add_address(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address_line1 = request.POST.get("address_line1", "").strip()
        address_line2 = request.POST.get("address_line2", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        zip_code = request.POST.get("zip_code", "").strip()
        country = request.POST.get("country", "").strip()
        address_type = request.POST.get("address_type", "").strip()

        error = validate_address_data(full_name, phone, address_line1, city, state, zip_code, country)

        if error:
            messages.error(request, error)
            return redirect("add_address")

        address = Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            zip_code=zip_code,
            country=country,
            address_type=address_type,
            is_default=bool(request.POST.get("is_default"))
        )

        if address.is_default:
            Address.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)

        messages.success(request, "Address added successfully")
        return redirect("address_list")

    return render(request, "accounts/address_form.html", {"address": None})
      

@never_cache
@login_required(login_url="customer_login")
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address_line1 = request.POST.get("address_line1", "").strip()
        address_line2 = request.POST.get("address_line2", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        zip_code = request.POST.get("zip_code", "").strip()
        country = request.POST.get("country", "").strip()
        address_type = request.POST.get("address_type", "").strip()

        error = validate_address_data(full_name, phone, address_line1, city, state, zip_code, country)

        if error:
            messages.error(request, error)
            return redirect("edit_address", address_id=address.id)

        address.full_name = full_name
        address.phone = phone
        address.address_line1 = address_line1
        address.address_line2 = address_line2
        address.city = city
        address.state = state
        address.zip_code = zip_code
        address.country = country
        address.address_type = address_type
        address.is_default = bool(request.POST.get("is_default"))
        address.save()

        if address.is_default:
            Address.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)

        messages.success(request, "Address updated successfully")
        return redirect("address_list")

    return render(request, "accounts/address_form.html", {"address": address})



        


@login_required(login_url="customer_login")
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully")
    return redirect("address_list")


@login_required(login_url="customer_login")
def set_default_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    Address.objects.filter(user=request.user).update(is_default=False)
    address.is_default = True
    address.save()
    messages.success(request, "Default address updated")
    return redirect("address_list")


@login_required(login_url="customer_login")
def delete_account(request):

    if request.user.is_staff or request.user.is_superuser:
        messages.error(request, "Admin account cannot be deleted")
        return redirect("customer_home")

    user = request.user

    SocialAccount.objects.filter(user=user).delete()

    auth_logout(request)

    user.delete()

    messages.success(request, "Account deleted successfully")
    return redirect("public_home")


@never_cache
def customer_logout(request):

    auth_logout(request)

    messages.success(request, "Logged out successfully.")

    return redirect("public_home")

