from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from customer.orders.models import Order, OrderStatusHistory
from customer.wallet.models import WalletTransaction,Wallet


from django.utils import timezone
from django.db import transaction
from .models import Return






def is_admin(user):
    return user.is_authenticated and user.is_staff

def admin_name(request):
    return request.user.full_name or request.user.first_name or request.user.username


@login_required(login_url="admin_login")
@user_passes_test(is_admin)
def admin_order_list(request):

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "new")

    orders = (Order.objects
        .select_related(
            "user",
            "payment",
            "address"
        )
        .prefetch_related(
            "items"
        )
    )

    
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search)
            |
            Q(user__full_name__icontains=search)
            |
            Q(user__username__icontains=search)
            |
            Q(user__email__icontains=search)
        )

    if status:
        orders = orders.filter(
            order_status=status
        )

   
    if sort == "old":
        orders = orders.order_by("placed_at")

    elif sort == "amount":
        orders = orders.order_by("-total_amount")

    else:
        orders = orders.order_by("-placed_at")

    paginator = Paginator(orders,10)

    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

   
    total_orders = Order.objects.count()

    pending_count = Order.objects.filter(
        order_status="pending"
    ).count()

    processing_count = Order.objects.filter(
        order_status__in=[
            "confirmed",
            "processing",
            "shipped",
            "out_for_delivery",
        ]
    ).count()

    delivered_count = Order.objects.filter(
        order_status="delivered"
    ).count()

    cancelled_count = Order.objects.filter(
        order_status="cancelled"
    ).count()

    context = {

        "page_obj": page_obj,

        "search": search,

        "status": status,

        "sort": sort,

        "total_orders": total_orders,

        "pending_count": pending_count,

        "processing_count": processing_count,

        "delivered_count": delivered_count,

        "cancelled_count": cancelled_count,
        "admin_name": admin_name(request),


    }

    return render(request,"admin_order/order_list.html",context,)


@login_required(login_url="admin_login")
@user_passes_test(is_admin)
def admin_order_detail(request, order_number):

    order = get_object_or_404(
        Order.objects
        .select_related(
            "user",
            "address",
            "payment",
        )
        .prefetch_related(
            "items__variant__product",
            "history",
        ),
        order_number=order_number,
    )

    subtotal = Decimal("0.00")
    discount = Decimal("0.00")

    for item in order.items.all():

        original_price = item.variant.price or Decimal("0.00")

        original_total = original_price * item.quantity

        subtotal += original_total

        discount += (original_total - item.total)

    history = order.history.all().order_by("-created_at")
    

    context = {

        "order": order,
        "subtotal": subtotal,
        "discount": discount,
        "coupon_discount": order.coupon_discount_value,
        "history": history,
        "total_items": order.items.count(),
        "admin_name": admin_name(request),


    }

    return render(request,"admin_order/order_details.html",context,)

@login_required(login_url="admin_login")
@user_passes_test(is_admin)
@transaction.atomic
def update_order_status(request, order_number):

    order = get_object_or_404(
        Order.objects.select_for_update().prefetch_related("items__variant"),
        order_number=order_number,
    )

    if request.method != "POST":
        return redirect("admin_order_detail", order_number=order_number)

    STATUS_FLOW = {
        "pending": "confirmed",
        "confirmed": "processing",
        "processing": "shipped",
        "shipped": "out_for_delivery",
        "out_for_delivery": "delivered",
    }

    new_status = request.POST.get("status", "").strip()
    old_status = order.order_status

    if new_status == old_status:
        messages.info(request, "Order status already updated.")
        return redirect("admin_order_detail", order_number=order.order_number)

    if new_status == "cancelled":

        if old_status in [
            "shipped",
            "out_for_delivery",
            "delivered",
            "cancelled",
            "returned",
        ]:

            messages.error(request,"This order cannot be cancelled.")

            return redirect("admin_order_detail",order_number=order.order_number)

    elif old_status in STATUS_FLOW:

        if STATUS_FLOW[old_status] != new_status:

            messages.error(request,f"Status should be '{STATUS_FLOW[old_status].title()}' first.")

            return redirect("admin_order_detail",order_number=order.order_number)

    order.order_status = new_status
    order.save(update_fields=["order_status"])

    order.items.update(status=new_status)

    if hasattr(order, "payment"):

        payment = order.payment

        if payment.payment_method == "cash_on_delivery":

            if new_status == "delivered":

                payment.payment_status = "paid"

                payment.save(update_fields=["payment_status"])

        elif payment.payment_method in [
            "wallet",
            "razorpay",
        ]:

            if payment.payment_status != "paid":

                payment.payment_status = "paid"

                payment.save(update_fields=["payment_status"])

        if new_status == "cancelled":

            for item in order.items.all():

                if item.variant:

                    item.variant.stock_quantity += item.quantity

                    item.variant.save()

            if payment.payment_method in [
                "wallet",
                "razorpay",
            ]:

                wallet, created = Wallet.objects.get_or_create(user=order.user)

                wallet.balance += order.total_amount

                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type="credit",
                    amount=order.total_amount,
                    description=f"Refund for Order {order.order_number}"
                )

                payment.payment_status = "refunded"

                payment.save(update_fields=["payment_status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=new_status,
        note=f"Order status changed from '{old_status}' to '{new_status}' by Admin."
    )

    messages.success(request,f"Order updated to '{new_status.title()}'.")

    return redirect("admin_order_detail",order_number=order.order_number)




@login_required(login_url="admin_login")
@user_passes_test(is_admin)
def admin_return_list(request):

    q = request.GET.get("q","")

    returns = (Return.objects.select_related("user","order").prefetch_related("items__order_item").order_by("-requested_at"))

    if q:

        returns = returns.filter(

            Q(request_id__icontains=q) |

            Q(order__order_number__icontains=q) |

            Q(user__full_name__icontains=q) |

            Q(user__email__icontains=q)

        )

    paginator = Paginator(returns,10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {

        "page_obj":page_obj,

        "query":q,

        "pending_count":
        Return.objects.filter(
            status="pending"
        ).count(),

        "approved_count":
        Return.objects.filter(
            status="approved"
        ).count(),

        "rejected_count":
        Return.objects.filter(
            status="rejected"
        ).count(),

        "completed_count":
        Return.objects.filter(
            status="completed"
        ).count(),

    }

    return render(request,"admin_order/return_list.html",context)


@login_required(login_url="admin_login")
@user_passes_test(is_admin)
def admin_return_detail(request,return_id):

    return_request = get_object_or_404(Return.objects.select_related("user","order")
        .prefetch_related("items__order_item__variant","proof_images"),id=return_id)

    return render(request,"admin_order/return_detail.html",{"return_request":return_request})

@login_required(login_url="admin_login")
@user_passes_test(is_admin)
@transaction.atomic
def approve_return(request, return_id):

    return_request = get_object_or_404(Return,id=return_id)

    if return_request.status != "pending":

        messages.error(request,"Return already processed.")

        return redirect("admin_return_detail",return_request.id)

    wallet, created = Wallet.objects.get_or_create(user=return_request.user,
        defaults={
            "balance": Decimal("0.00")
        }

    )

    refund_amount = Decimal("0.00")

    for item in return_request.items.all():

        order_item = item.order_item

        refund_amount += order_item.total


        if order_item.variant:

            order_item.variant.stock_quantity += item.quantity

            order_item.variant.save()


        order_item.status = "returned"

        order_item.save()


    wallet.balance += refund_amount

    wallet.save()


    WalletTransaction.objects.create(

        wallet=wallet,

        user=return_request.user,

        transaction_type="refund",

        amount=refund_amount,

        payment_method="wallet",

        status="success"

    )


    return_request.status = "approved"

    return_request.estimated_refund = refund_amount
    return_request.admin_note = request.POST.get("admin_note", "")


    return_request.processed_at = timezone.now()

    return_request.save()


    order = return_request.order

    if not order.items.exclude(status="returned").exists():

        order.order_status = "returned"

        order.save()

    messages.success(request,"Refund approved successfully.")

    return redirect("admin_return_detail",return_request.id)


@login_required(login_url="admin_login")
@user_passes_test(is_admin)
@transaction.atomic
def reject_return(request, return_id):

    return_request = get_object_or_404(Return,id=return_id)

    if return_request.status != "pending":

        messages.error(request,"Return already processed.")

        return redirect("admin_return_detail",return_request.id)

    return_request.status = "rejected"
    return_request.admin_note = request.POST.get("admin_note", "")

    return_request.processed_at = timezone.now()

    return_request.save()

    messages.success(request,"Return request rejected.")

    return redirect("admin_return_detail",return_request.id)
