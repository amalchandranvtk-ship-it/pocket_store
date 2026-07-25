from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CouponForm
from .models import Coupon, CouponUsage

from admin_panel.admin_accounts.views import is_admin
from django.contrib.auth.decorators import user_passes_test


@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def coupon_list(request):

    coupons = Coupon.objects.all().order_by("-created_at")

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")

    if search:
        coupons = coupons.filter(
            Q(coupon_code__icontains=search)
        )

    if status == "active":
        coupons = coupons.filter(is_active=True)

    elif status == "inactive":
        coupons = coupons.filter(is_active=False)

    paginator = Paginator(coupons, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {

        "page_obj": page_obj,
        "search": search,
        "status": status,

    }

    return render(request,"coupons/coupon_list.html",context)


@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def create_coupon(request):

    if request.method == "POST":

        form = CouponForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(request,"Coupon created successfully.")

            return redirect("coupon_list")

    else:

        form = CouponForm()

    context = {"form": form,}

    return render(request,"coupons/create_coupon.html",context)


@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def edit_coupon(request, coupon_id):

    coupon = get_object_or_404(Coupon,id=coupon_id)

    if request.method == "POST":

        form = CouponForm(request.POST,instance=coupon)

        if form.is_valid():

            form.save()

            messages.success(request,"Coupon updated successfully.")

            return redirect("coupon_list")

    else:

        form = CouponForm(instance=coupon)

    context = {

        "form": form,
        "coupon": coupon,

    }

    return render(request,"coupons/edit_coupon.html",context)

@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def delete_coupon(request, coupon_id):

    coupon = get_object_or_404(Coupon,id=coupon_id)

    used = CouponUsage.objects.filter(coupon=coupon).exists()

    if used:

        messages.error(request,"This coupon has already been used and cannot be deleted.")

        return redirect("coupon_list")

    coupon.delete()

    messages.success(request,"Coupon deleted successfully.")

    return redirect("coupon_list")