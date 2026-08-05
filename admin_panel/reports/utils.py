from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from customer.orders.models import Order


def get_sales_report_data(request):

    report_type = request.GET.get("report", "daily")

    selected_date = request.GET.get("date")

    week_from = request.GET.get("week_from")
    week_to = request.GET.get("week_to")

    month = request.GET.get("month")

    year = request.GET.get("year")

    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    today = timezone.localdate()

    orders = (
        Order.objects.filter(
            order_status="delivered",
            payment_status="paid",
        )
        .select_related(
            "user",
            "payment",
        )
        .prefetch_related("items")
        .order_by("-placed_at")
    )

    if report_type == "daily":

        if selected_date:
            orders = orders.filter(placed_at__date=selected_date)
        else:
            orders = orders.filter(placed_at__date=today)

    elif report_type == "weekly":

        if week_from and week_to:

            orders = orders.filter(placed_at__date__range=[week_from,week_to])

        else:

            start_date = today - timedelta(days=6)

            orders = orders.filter(placed_at__date__range=[start_date,today])

    elif report_type == "monthly":

        if month:

            year_value, month_value = month.split("-")

            orders = orders.filter(placed_at__year=int(year_value),placed_at__month=int(month_value))

        else:

            orders = orders.filter(placed_at__year=today.year,placed_at__month=today.month)

    elif report_type == "yearly":

        if year:

            orders = orders.filter(placed_at__year=int(year))

        else:

            orders = orders.filter(placed_at__year=today.year)

    elif report_type == "custom":

        if from_date and to_date:

            if from_date <= to_date:

                orders = orders.filter(placed_at__date__range=[from_date,to_date])

            else:

                orders = orders.none()

    summary = orders.aggregate(

        total_orders=Count("id"),

        total_sales=Sum("total_amount"),

        subtotal=Sum("subtotal"),

        total_discount=Sum("discount_amount"),

        coupon_discount=Sum("coupon_discount_value"),

        delivery_charge=Sum("delivery_charge"),

        tax_amount=Sum("tax_amount"),
    )

    summary["total_orders"] = summary["total_orders"] or 0
    summary["total_sales"] = summary["total_sales"] or 0
    summary["subtotal"] = summary["subtotal"] or 0
    summary["total_discount"] = summary["total_discount"] or 0
    summary["coupon_discount"] = summary["coupon_discount"] or 0
    summary["delivery_charge"] = summary["delivery_charge"] or 0
    summary["tax_amount"] = summary["tax_amount"] or 0

    total_products = 0

    for order in orders:
        total_products += order.items.count()

    summary["total_products"] = total_products

    average_order_value = 0

    if summary["total_orders"]:

        average_order_value = (
            summary["total_sales"] / summary["total_orders"]
        )

    summary["average_order_value"] = average_order_value

    return {

        "orders": orders,

        "summary": summary,

        "report_type": report_type,

        "selected_date": selected_date,

        "week_from": week_from,

        "week_to": week_to,

        "month": month,

        "year": year,

        "from_date": from_date,

        "to_date": to_date,
    }