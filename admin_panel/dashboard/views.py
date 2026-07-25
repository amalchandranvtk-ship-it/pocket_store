from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import (
    ExtractHour,
    ExtractMonth,
    ExtractYear,
)
from django.shortcuts import redirect, render
from django.utils import timezone

import re

from customer.accounts.models import User
from customer.orders.models import Order, OrderItem
from admin_panel.catalog.models import Product


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

        messages.error(
            request,
            "Email already exists."
        )

        return redirect("admin_dashboard")

    user.full_name = full_name
    user.email = email
    user.phone = phone

    if profile_image:

        user.profile_image = profile_image

    user.save()

    messages.success(
        request,
        "Profile updated successfully."
    )

    return redirect("admin_dashboard")



@login_required(login_url="admin_login")
def change_password(request):

    if request.method != "POST":
        return redirect("admin_dashboard")

    user = request.user

    new_password = request.POST.get("new_password")
    confirm_password = request.POST.get("confirm_password")

  

   

    if new_password != confirm_password:

        messages.error(
            request,
            "New password and confirm password do not match."
        )

        return redirect("admin_dashboard")

    if len(new_password) < 8:

        messages.error(
            request,
            "Password must contain at least 8 characters."
        )

        return redirect("admin_dashboard")

    if not re.search(r"[A-Z]", new_password):

        messages.error(
            request,
            "Password must contain at least one uppercase letter."
        )

        return redirect("admin_dashboard")

    if not re.search(r"[a-z]", new_password):

        messages.error(
            request,
            "Password must contain at least one lowercase letter."
        )

        return redirect("admin_dashboard")

    if not re.search(r"\d", new_password):

        messages.error(
            request,
            "Password must contain at least one number."
        )

        return redirect("admin_dashboard")

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", new_password):

        messages.error(
            request,
            "Password must contain at least one special character."
        )

        return redirect("admin_dashboard")

    user.set_password(new_password)
    user.save()

    update_session_auth_hash(
        request,
        user
    )

    messages.success(
        request,
        "Password changed successfully."
    )

    return redirect("admin_dashboard")

 

    

  


@login_required(login_url="admin_login")
def dashboard(request):

    today = timezone.localdate()

    filter_type = request.GET.get("filter", "monthly")

    selected_year = int(
        request.GET.get(
            "year",
            today.year
        )
    )

    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    

    total_orders = Order.objects.count()

    total_customers = (
        Order.objects
        .values("user")
        .distinct()
        .count()
    )

    total_products = Product.objects.count()

    total_sales = (

        Order.objects.filter(

            payment_status="paid"

        ).aggregate(

            total=Sum("total_amount")

        )["total"] or 0

    )

    

    chart_labels = []

    chart_data = []


    if filter_type == "today":

        sales = (

            Order.objects.filter(

                payment_status="paid",

                placed_at__date=today

            )

            .annotate(

                hour=ExtractHour("placed_at")

            )

            .values("hour")

            .annotate(

                total=Sum("total_amount")

            )

            .order_by("hour")

        )

        chart_labels = [

            f"{i}:00"

            for i in range(24)

        ]

        chart_data = [0] * 24

        for row in sales:

            chart_data[row["hour"]] = float(

                row["total"]

            )


    elif filter_type == "weekly":

        week_start = today - timedelta(days=6)

        sales = (

            Order.objects.filter(

                payment_status="paid",

                placed_at__date__range=(

                    week_start,

                    today

                )

            )

            .values(

                "placed_at__date"

            )

            .annotate(

                total=Sum(

                    "total_amount"

                )

            )

            .order_by(

                "placed_at__date"

            )

        )

        chart_labels = []

        chart_data = []

        current = week_start

        while current <= today:

            chart_labels.append(

                current.strftime("%d %b")

            )

            amount = 0

            for row in sales:

                if row["placed_at__date"] == current:

                    amount = float(

                        row["total"]

                    )

                    break

            chart_data.append(amount)

            current += timedelta(days=1)


    elif filter_type == "monthly":

        sales = (

            Order.objects.filter(

                payment_status="paid",

                placed_at__year=selected_year

            )

            .annotate(

                month=ExtractMonth(

                    "placed_at"

                )

            )

            .values("month")

            .annotate(

                total=Sum(

                    "total_amount"

                )

            )

            .order_by("month")

        )

        chart_labels = [

            "Jan","Feb","Mar","Apr",

            "May","Jun","Jul","Aug",

            "Sep","Oct","Nov","Dec"

        ]

        chart_data = [0] * 12

        for row in sales:

            chart_data[

                row["month"] - 1

            ] = float(

                row["total"]

            )


    elif filter_type == "yearly":

        sales = (

            Order.objects.filter(

                payment_status="paid"

            )

            .annotate(

                year=ExtractYear("placed_at")

            )

            .values("year")

            .annotate(

                total=Sum("total_amount")

            )

            .order_by("year")

        )

        chart_labels = []

        chart_data = []

        for row in sales:

            chart_labels.append(

                str(row["year"])

            )

            chart_data.append(

                float(row["total"])

            )


    elif (

        filter_type == "custom"

        and from_date

        and to_date

    ):

        sales = (

            Order.objects.filter(

                payment_status="paid",

                placed_at__date__range=[

                    from_date,

                    to_date

                ]

            )

            .values(

                "placed_at__date"

            )

            .annotate(

                total=Sum("total_amount")

            )

            .order_by(

                "placed_at__date"

            )

        )

        chart_labels = []

        chart_data = []

        for row in sales:

            chart_labels.append(

                row["placed_at__date"].strftime(

                    "%d %b"

                )

            )

            chart_data.append(

                float(row["total"])

            )

    else:

        chart_labels = [

            "Jan","Feb","Mar","Apr",

            "May","Jun","Jul","Aug",

            "Sep","Oct","Nov","Dec"

        ]

        chart_data = [0] * 12

    

    best_products = (

        OrderItem.objects.filter(

            order__payment_status="paid"

        )

        .values(

            "variant",

            "product_name",

            "variant__main_image",

            "variant__product__slug"

        )

        .annotate(

            total_quantity=Sum("quantity"),

            total_sales=Sum("total")

        )

        .order_by(

            "-total_quantity"

        )[:10]

    )

    

    best_categories = (

        OrderItem.objects.filter(

            order__payment_status="paid"

        )

        .values(

            "variant__product__category__category_name"

        )

        .annotate(

            total_quantity=Sum("quantity"),

            total_sales=Sum("total")

        )

        .order_by(

            "-total_quantity"

        )[:10]

    )

   

    best_brands = (

        OrderItem.objects.filter(

            order__payment_status="paid"

        )

        .values(

            "variant__product__brand__brand_name"

        )

        .annotate(

            total_quantity=Sum("quantity"),

            total_sales=Sum("total")

        )

        .order_by(

            "-total_quantity"

        )[:10]

    )

    years = list(

        range(

            today.year - 4,

            today.year + 2

        )

    )

    context = {

        "admin_user": request.user,

        "filter_type": filter_type,

        "selected_year": selected_year,

        "chart_labels": chart_labels,

        "chart_data": chart_data,

        "total_orders": total_orders,

        "total_customers": total_customers,

        "total_products": total_products,

        "total_sales": total_sales,

        "best_products": best_products,

        "best_categories": best_categories,

        "best_brands": best_brands,

        "years": years,

        "from_date": from_date,

        "to_date": to_date,

    }

    return render(

        request,

        "dashboard/dashboard.html",

        context

    )