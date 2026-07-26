import random
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from customer.accounts.models import User
from django.contrib.auth import update_session_auth_hash
from customer.accounts.views import is_valid_password



User = get_user_model()


def is_admin(user):
    return user.is_authenticated and user.is_staff



def send_admin_otp(request, email):
    otp = str(random.randint(100000, 999999))

    request.session["admin_email"] = email
    request.session["admin_otp"] = otp
    request.session["admin_otp_time"] = datetime.now().isoformat()

    send_mail(
        "PocketStore Admin OTP",
        f"Your PocketStore admin OTP is {otp}",
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False
    )


@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.role=="admin":
        return redirect("admin_dashboard")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        admin_user = User.objects.filter(email=email, role="admin").first()

        if admin_user:
            user = authenticate(request, username=admin_user.username, password=password)

            if user is not None:
                login(request, user)
                request.session.set_expiry(60 * 60 * 24 * 7)
                messages.success(request,"Welcome Back")
                return redirect("admin_dashboard")

        messages.error(request, "Invalid admin email or password")

    return render(request, "admin_accounts/login.html")


@never_cache
def forgot_pass(request):
    if request.method == "POST":
        email = request.POST.get("email")

        admin_user = User.objects.filter(email=email, is_staff=True).first()

        if not admin_user:
            messages.error(request, "Admin email not found")
            return redirect("admin_forgot_password")

        send_admin_otp(request, email)
        messages.success(request, "OTP sent successfully")
        return redirect("admin_otp_verification")

    return render(request, "admin_accounts/forgot_password.html")


@never_cache
def verify_otp(request):
    if not request.session.get("admin_email"):
        return redirect("admin_forgot_password")

    if request.method == "POST":
        otp = (
            request.POST.get("otp1", "") +
            request.POST.get("otp2", "") +
            request.POST.get("otp3", "") +
            request.POST.get("otp4", "") +
            request.POST.get("otp5", "") +
            request.POST.get("otp6", "")
        )

        saved_otp = request.session.get("admin_otp")
        otp_time = request.session.get("admin_otp_time")

        if not otp_time:
            messages.error(request, "OTP expired. Please resend OTP.")
            return redirect("admin_otp_verification")

        expiry_time = datetime.fromisoformat(otp_time) + timedelta(minutes=2)

        if datetime.now() > expiry_time:
            messages.error(request, "OTP expired. Please resend OTP.")
        elif otp == saved_otp:
            request.session["admin_otp_verified"] = True
            return redirect("admin_reset_password")
        else:
            messages.error(request, "Invalid OTP")

    return render(request, "admin_accounts/otp_verify.html", {
        "admin_email": request.session.get("admin_email")
    })


@never_cache
def resend_otp(request):
    email = request.session.get("admin_email")

    if not email:
        return redirect("admin_forgot_password")

    send_admin_otp(request, email)
    messages.success(request, "New OTP sent successfully")
    return redirect("admin_otp_verification")


@never_cache
def reset_password(request):
    if not request.session.get("admin_otp_verified"):
        return redirect("admin_otp_verification")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("admin_reset_password")

        password_error = is_valid_password(password)

        if password_error:
            messages.error(request, password_error)
            return redirect("admin_reset_password")

        email = request.session.get("admin_email")
        admin_user = User.objects.get(email=email, is_staff=True)

        admin_user.password = make_password(password)
        admin_user.save()

        request.session.pop("admin_email", None)
        request.session.pop("admin_otp", None)
        request.session.pop("admin_otp_time", None)
        request.session.pop("admin_otp_verified", None)

        messages.success(request, "Password reset successfully")
        return redirect("admin_login")

    return render(request, "admin_accounts/reset_password.html")


@never_cache
@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def customer_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    customers = User.objects.filter(
    role="customer",
    is_staff=False,
    is_superuser=False).order_by("-id")
    if q:
        customers = customers.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(full_name__icontains=q) |
            Q(phone__icontains=q)
        )

    if status == "active":
        customers = customers.filter(is_active=True)
    elif status == "blocked":
        customers = customers.filter(is_active=False)

    if q and not customers.exists():
        messages.error(request, "Customer not found")

    paginator = Paginator(customers, 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "admin_accounts/admin_customers.html", {
        "customers": page_obj,
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "admin_name": request.user.full_name if hasattr(request.user, "full_name") and request.user.full_name else request.user.username,
    })


@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def block_customer(request, user_id):
    customer = get_object_or_404(User, id=user_id, is_staff=False)
    customer.is_active = False
    customer.save()
    messages.success(request, "Customer blocked successfully")
    return redirect("admin_customers")


@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def unblock_customer(request, user_id):
    customer = get_object_or_404(User, id=user_id, is_staff=False)
    customer.is_active = True
    customer.save()
    messages.success(request, "Customer unblocked successfully")
    return redirect("admin_customers")


def admin_logout(request):
    logout(request)
    return redirect("admin_login")



@login_required(login_url="admin_login")
def edit_profile(request):

    if request.method != "POST":
        return redirect("admin_dashboard")

    user = request.user

    full_name = request.POST.get("full_name", "").strip()
    email = request.POST.get("email", "").strip()
    phone = request.POST.get("phone", "").strip()

    profile_image = request.FILES.get("profile_image")

    if User.objects.exclude(id=user.id).filter(email=email).exists():

        messages.error(request,"Email already exists.")

        return redirect("admin_dashboard")

    user.full_name = full_name
    user.email = email
    user.phone = phone

    if profile_image:

        user.profile_image = profile_image

    user.save()

    messages.success(request,"Profile updated successfully.")

    return redirect("admin_dashboard")



@login_required(login_url="admin_login")
def change_password(request):

    if request.method != "POST":
        return redirect("admin_dashboard")

    next_url = request.POST.get("next", "admin_dashboard")

    user = request.user

    new_password = request.POST.get("new_password")
    confirm_password = request.POST.get("confirm_password")

    if new_password != confirm_password:
        messages.error(request,"New password and confirm password do not match.")
        return redirect(next_url)

    password_error = is_valid_password(new_password)
    if password_error:
        messages.error(request, password_error)
        return redirect(next_url)

    user.set_password(new_password)
    user.save()

    update_session_auth_hash(request, user)

    messages.success(request, "Password changed successfully.")

    return redirect(next_url)