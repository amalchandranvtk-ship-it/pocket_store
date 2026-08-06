from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from customer.store.models import CartItem
from customer.accounts.models import Address
from customer.wallet.models import Wallet,WalletTransaction
from .models import (Order, OrderItem,Payment,OrderStatusHistory,OrderCancellation)
from admin_panel.admin_order.models import (
    Return,
    ReturnItem,
    ReturnProofImage,
    generate_return_request_id,
)

from django.http import JsonResponse
from django.urls import reverse
from admin_panel.offers.utils import get_variant_offer_price

import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from admin_panel.coupons.models import Coupon

from io import BytesIO
import os
from decimal import Decimal

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image
)

from reportlab.pdfbase.pdfmetrics import stringWidth




def add_page_number(canvas, doc):

    page_num = canvas.getPageNumber()

    text = f"Page {page_num}"

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.grey)

    canvas.drawRightString(
        A4[0] - 40,
        20,
        text,
    )

def add_footer(canvas, doc):

    canvas.saveState()

    canvas.setStrokeColor(colors.HexColor("#2563EB"))
    canvas.setLineWidth(0.5)

    canvas.line(
        40,
        45,
        A4[0] - 40,
        45
    )

    canvas.setFont(
        "Helvetica",
        9
    )

    canvas.setFillColor(colors.grey)

    canvas.drawString(
        40,
        30,
        "Thank you for shopping with PocketStore."
    )

    canvas.drawRightString(
        A4[0] - 40,
        30,
        "www.pocketstore.com"
    )

    add_page_number(canvas, doc)

    canvas.restoreState()





def refund_to_wallet(user, amount, description):

    wallet, created = Wallet.objects.get_or_create(user=user)

    amount = Decimal(amount)

    wallet.balance += amount

    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(

        wallet=wallet,

        user=user,

        transaction_type="credit",

        payment_method="wallet",

        amount=amount,

        status="success",

        description=description,

    )

    return wallet


def calculate_cart_totals(cart_items,request=None):

    subtotal = Decimal("0.00")
    discount_total = Decimal("0.00")
    final_total = Decimal("0.00")
    total_items = 0

    for item in cart_items:
        offer = get_variant_offer_price(item.variant)

        price = offer["original_price"]

        selling_price = offer["selling_price"]

        original_amount = price * item.quantity

        if selling_price > 0 and selling_price < price:

            selling_amount = selling_price * item.quantity

            discount_amount = original_amount - selling_amount

        else:

            selling_amount = original_amount

            discount_amount = Decimal("0.00")

        item.original_amount = original_amount
        item.discount_amount = discount_amount
        item.selling_amount = selling_amount
        item.unit_price = selling_price if selling_price > 0 else price

        subtotal += original_amount
        discount_total += discount_amount
        final_total += selling_amount

        total_items += item.quantity

    delivery_charge = Decimal("0.00")

    tax_amount = Decimal("0.00")

    coupon_discount = Decimal("0.00")
    coupon = None

    if request:

       coupon_id = request.session.get("coupon_id")

       if coupon_id:

           try:

                coupon = Coupon.objects.get(
                     id=coupon_id,
                     is_active=True
                )

                if coupon.discount_type == "percentage":

                    coupon_discount = (
                         final_total * coupon.discount_value
                        ) / Decimal("100")

                else:

                    coupon_discount = coupon.discount_value

                if coupon_discount > final_total:

                     coupon_discount = final_total

           except Coupon.DoesNotExist:

                pass

    grand_total = (
         final_total
         - coupon_discount
         + delivery_charge
         + tax_amount
    )
    return {

        "cart_items": cart_items,

        "subtotal": subtotal,

        "discount_amount": discount_total,

        "coupon_discount": coupon_discount,


        "delivery_charge": delivery_charge,

        "tax_amount": tax_amount,

        "total_amount": grand_total,

        "total_items": total_items,
        
        "coupon": coupon,


    }

@login_required(login_url="customer_login")
def checkout_view(request):

    cart_items = (
        CartItem.objects
        .filter(user=request.user)
        .select_related(
            "variant",
            "variant__product",
            "variant__product__brand",
        )
    )

    if not cart_items.exists():

        messages.error(request,"Your cart is empty.")

        return redirect("cart")

    addresses = (
        Address.objects
        .filter(user=request.user)
        .order_by("-is_default", "-id")
    )

    default_address = addresses.filter(
        is_default=True
    ).first()

    if not default_address:

        default_address = addresses.first()

    totals = calculate_cart_totals(cart_items,request)

    coupons = Coupon.objects.filter(is_active=True)

    context = {

        "cart_items": totals["cart_items"],

        "addresses": addresses,

        "default_address": default_address,

        "subtotal": totals["subtotal"],

        "discount_amount": totals["discount_amount"],

        "coupon_discount": totals["coupon_discount"],

        "coupon": totals["coupon"],

        "delivery_charge": totals["delivery_charge"],

        "tax_amount": totals["tax_amount"],

        "total_amount": totals["total_amount"],

        "total_items": totals["total_items"],

        "coupons": coupons,

        "applied_coupon": totals["coupon"],



    }

    return render(request,"orders/checkout.html",context,)

@login_required(login_url="customer_login")
def payment_view(request):

    cart_items = (
        CartItem.objects
        .filter(user=request.user)
        .select_related(
            "variant",
            "variant__product",
            "variant__product__brand"
        )
    )
    if not cart_items.exists():

        messages.error(request,"Your cart is empty.")

        return redirect("cart")

    address_id = request.POST.get("address")

    if not address_id:

        messages.error(request,"Please select a delivery address.")

        return redirect("checkout")

    address = get_object_or_404(Address,id=address_id,user=request.user)
    wallet = Wallet.objects.filter(user=request.user).first()

    if wallet:
        balance = wallet.balance
    else:
        balance = 0

    totals = calculate_cart_totals(cart_items,request)

    context = {

        "address": address,

        "cart_items": totals["cart_items"],

        "subtotal": totals["subtotal"],

        "discount_amount": totals["discount_amount"],

        "coupon_discount": totals["coupon_discount"],

        "coupon": totals["coupon"],

        "delivery_charge": totals["delivery_charge"],

        "tax_amount": totals["tax_amount"],

        "total_amount": totals["total_amount"],

        "total_items": totals["total_items"],

        "balance"    : balance

    }

    return render(request,"orders/payment.html",context)


@login_required(login_url="customer_login")
@transaction.atomic
def place_order(request):

    if request.method != "POST":

        return redirect("checkout")

    cart_items = CartItem.objects.filter(user=request.user).select_related("variant","variant__product",)

    if not cart_items.exists():

        messages.error(request,"Your cart is empty.")

        return redirect("cart")

    address_id = request.POST.get("address")

    if not address_id:

        messages.error(request,"Please select a delivery address.")

        return redirect("checkout")

    address = get_object_or_404(Address,id=address_id,user=request.user)

    payment_method = request.POST.get("payment_method","cod")

    totals = calculate_cart_totals(cart_items,request)

    for item in cart_items:

        if item.quantity > item.variant.stock_quantity:

            message = f"{item.variant.product.product_name} is out of stock."

            if payment_method in ["wallet","razorpay"]:

                return JsonResponse({"success": False,"message": message})

            messages.error(request,message)

            return redirect("checkout")


    payment_status = "pending"
    if payment_method == "wallet":

        wallet = Wallet.objects.select_for_update().get(user=request.user)

        if wallet.balance < totals["total_amount"]:

            return JsonResponse({

            "success": False,

            "message": "Insufficient Wallet Balance"

        })

        payment_status = "paid"

    elif payment_method == "razorpay":

        payment_status = "pending"

    elif payment_method == "cod":
        payment_status = "pending"

    coupon = totals["coupon"]

    if payment_method == "razorpay":

        request.session["checkout_address"] = address.id
        request.session["payment_method"] = "razorpay"

        return JsonResponse({"success": True})

    if payment_method != "razorpay":


        order_number = ("PS"+ timezone.now().strftime("%Y%m%d%H%M%S"))

        order = Order.objects.create(

           user=request.user,

           address=address,

           order_number=order_number,

           subtotal=totals["subtotal"],

           discount_amount=totals["discount_amount"] ,
           coupon_code=(coupon.coupon_code if coupon else None),

           coupon_discount_type=(coupon.discount_type if coupon else None),

           coupon_discount_value=(totals["coupon_discount"]),
           delivery_charge=totals["delivery_charge"],

           tax_amount=totals["tax_amount"],

           total_amount=totals["total_amount"],

           payment_status=payment_status,

           order_status="pending",

           estimated_delivery=timezone.now().date()

           + timedelta(days=5)

        )
        for item in cart_items:

           variant = item.variant

           offer_data = get_variant_offer_price(variant)

           unit_price = offer_data["selling_price"]

           OrderItem.objects.create(

               order=order,

               variant=variant,

               product_name=variant.product.product_name,

               sku=variant.sku,

               quantity=item.quantity,

               price=unit_price,

               total=unit_price * item.quantity,

               status="pending"

            )

           variant.stock_quantity -= item.quantity

           variant.save()

        payment = Payment.objects.create(

            order=order,

            payment_method=payment_method,

            amount=totals["total_amount"],

            payment_status=payment_status

        )

        OrderStatusHistory.objects.create(order=order,status="Pending",note="Order placed successfully.")

    if payment_method == "cod":

        cart_items.delete()
        request.session.pop("coupon_id", None)
        request.session.pop("coupon_code", None)

        return redirect("order_success",order_number=order.order_number)

    if payment_method == "wallet":

        wallet = Wallet.objects.get(user=request.user)

        wallet.balance -= totals["total_amount"]

        wallet.save()

        WalletTransaction.objects.create(

            wallet=wallet,

            user=request.user,

            transaction_type="debit",

            payment_method="wallet",

            amount=totals["total_amount"],

            status="success",

            description=f"Order Payment - {order.order_number}"

        )

        payment.payment_status = "paid"

        payment.save(update_fields=["payment_status"])

        order.payment_status = "paid"

        order.save(update_fields=["payment_status"])

        cart_items.delete()
        request.session.pop("coupon_id", None)
        request.session.pop("coupon_code", None)

        return JsonResponse({"success": True,

            "redirect_url": reverse(

                "order_success",

                kwargs={

                    "order_number": order.order_number

                }

            )

        })


    return JsonResponse({"success": True})


@login_required(login_url="customer_login")
def create_razorpay_order(request):

    if request.method != "POST":

        return JsonResponse({"success": False,"message": "Invalid request."})
    cart_items = CartItem.objects.filter(user=request.user).select_related("variant")

    totals = calculate_cart_totals(cart_items,request)

    client = razorpay.Client(

        auth=(settings.RAZORPAY_KEY_ID,settings.RAZORPAY_KEY_SECRET))

    razorpay_order = client.order.create({

        "amount": int(totals["total_amount"] *100),
        "currency": "INR",

        "payment_capture": 1

    })


    return JsonResponse({

        "success": True,

        "key": settings.RAZORPAY_KEY_ID,

        "amount": int(totals["total_amount"] * 100),
        "order_id": razorpay_order["id"]

    })



@csrf_exempt
@login_required(login_url="customer_login")
@transaction.atomic
def verify_razorpay_payment(request):

    if request.method != "POST":

        return JsonResponse({"success": False})

    razorpay_order_id = request.POST.get("razorpay_order_id")

    razorpay_payment_id = request.POST.get("razorpay_payment_id")

    razorpay_signature = request.POST.get("razorpay_signature")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID,settings.RAZORPAY_KEY_SECRET))

    try:

        client.utility.verify_payment_signature({

            "razorpay_order_id": razorpay_order_id,

            "razorpay_payment_id": razorpay_payment_id,

            "razorpay_signature": razorpay_signature,

        })

    except:

        return JsonResponse({"success": False,"message": "Payment verification failed."})

    cart_items = CartItem.objects.filter(user=request.user).select_related("variant","variant__product")
    if not cart_items.exists():
       return JsonResponse({"success": False,"message": "Cart is empty."})

    address_id = request.session.get("checkout_address")

    if not address_id:
        return JsonResponse({"success": False,"message": "Address not found."})

    address = get_object_or_404(Address,id=address_id,user=request.user)
    totals = calculate_cart_totals(cart_items,request)

    coupon = totals["coupon"]

    order_number = ("PS" +timezone.now().strftime("%Y%m%d%H%M%S"))

    
    order = Order.objects.create(

           user=request.user,

           address=address,

           order_number=order_number,

           subtotal=totals["subtotal"],

           discount_amount=totals["discount_amount"] ,
           coupon_code=(coupon.coupon_code if coupon else None),

           coupon_discount_type=(coupon.discount_type if coupon else None),

           coupon_discount_value=(totals["coupon_discount"]),
           delivery_charge=totals["delivery_charge"],

           tax_amount=totals["tax_amount"],

           total_amount=totals["total_amount"],

           payment_status="paid",

           order_status="pending",

           estimated_delivery=timezone.now().date()

           + timedelta(days=5)

        )
    for item in cart_items:

           variant = item.variant

           offer_data = get_variant_offer_price(variant)

           unit_price = offer_data["selling_price"]

           OrderItem.objects.create(

               order=order,

               variant=variant,

               product_name=variant.product.product_name,

               sku=variant.sku,

               quantity=item.quantity,

               price=unit_price,

               total=unit_price * item.quantity,

               status="pending"

            )

           variant.stock_quantity -= item.quantity

           variant.save()

    payment = Payment.objects.create(

            order=order,

            payment_method="razorpay",

            amount=totals["total_amount"],

            payment_status="paid",
            transaction_id=razorpay_payment_id,
            paid_at=timezone.now(),

        )

    OrderStatusHistory.objects.create(order=order,status="Pending",note="Order placed successfully.")

 

    cart_items.delete()
    request.session.pop("checkout_address",None)

    request.session.pop("coupon_id", None)
    request.session.pop("coupon_code", None)
    request.session.pop("payment_method", None)

    return JsonResponse({"success": True,"redirect_url": reverse(
        "order_success",

            kwargs={

                "order_number": order.order_number

            }

        )

    })


@login_required(login_url="customer_login")
def order_success(request, order_number):

    order = get_object_or_404(
        Order.objects.select_related(
            "payment",
            "address"
        ),
        order_number=order_number,
        user=request.user
    )

    return render(request,"orders/order_success.html",{"order": order})

@login_required(login_url="customer_login")
def order_list(request):

    query = request.GET.get("q", "").strip()

    orders = (
    Order.objects
    .filter(user=request.user)
    .select_related("address")
    .prefetch_related(
        "items",
        "items__variant",
        "items__variant__product",
        "items__variant__images",
    )
    .order_by("-placed_at")
)

    if query:

        orders = orders.filter(

            Q(order_number__icontains=query)

            |

            Q(order_status__icontains=query)

        )

    paginator = Paginator(orders,10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {

        "page_obj": page_obj,

        "query": query,

        "total_orders": orders.count(),

        "pending_orders": orders.filter(
            order_status="pending"
        ).count(),

        "processing_orders": orders.filter(
            order_status__in=[
                "confirmed",
                "processing",
                "shipped",
                "out_for_delivery"
            ]
        ).count(),

        "delivered_orders": orders.filter(
            order_status="delivered"
        ).count(),

        "cancelled_orders": orders.filter(
            order_status="cancelled"
        ).count(),

    }

    return render(request,"orders/order_list.html",context)

@login_required(login_url="customer_login")
def order_detail(request, order_number):

    order = get_object_or_404(

        Order.objects

        .select_related(
            "payment",
            "address"
        )

        .prefetch_related(
            "items",
            "items__variant",
            "items__variant__product",
            "items__variant__product__brand",
            "items__variant__images",
             "history",
        ),

        order_number=order_number,

        user=request.user

    )

    subtotal = Decimal("0.00")

    discount = Decimal("0.00")

    for item in order.items.all():

        original = item.variant.price * item.quantity

        subtotal += original

        discount += (original - item.total)

    status_map = {
            "pending": 1,
            "confirmed": 2,
            "processing": 2,
            "shipped": 3,
            "out_for_delivery": 3,
            "delivered": 4,
            "cancelled": 0,
            "returned": 4,
   }
    

    context = {

        "order": order,

        "subtotal": subtotal,
        "coupon_discount": order.coupon_discount_value,

        "discount": discount,
        "status_step": status_map.get(order.order_status, 1),


    }

    return render(request,"orders/order_detail.html",context)

@login_required(login_url="customer_login")
def search_orders(request):

    query = request.GET.get("q", "").strip()

    return redirect( f"/orders/?q={query}" )

@login_required(login_url="customer_login")
def order_failed(request):

    reason = request.GET.get(
        "reason",
        "Your order could not be completed."
    )

    order_number = request.GET.get(
        "order_number",
        ""
    )

    context = {

        "reason": reason,

        "order_number": order_number,

    }

    return render(request,"orders/order_failed.html",context)


@login_required(login_url="customer_login")
@transaction.atomic
def cancel_order(request, order_number):

    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user
    )

    if order.order_status in [
        "shipped",
        "out_for_delivery",
        "delivered",
        "cancelled",
        "returned"
    ]:

        messages.error(request,"This order cannot be cancelled.")

        return redirect(
            "order_detail",
            order.order_number
        )

    reason = request.POST.get("reason", "")

    for item in order.items.all():

        if item.variant:

            item.variant.stock_quantity += item.quantity

            item.variant.save()

        item.status = "cancelled"

        item.save()

        OrderCancellation.objects.get_or_create(

            order_item=item,

            defaults={
                "reason": reason
            }

        )

    order.order_status = "cancelled"

    payment = getattr(order, "payment", None)

    if payment:

        if payment.payment_method == "cod":

            payment.payment_status = "pending"

            order.payment_status = "pending"

            payment.save(update_fields=["payment_status"])

        elif payment.payment_method in [

            "wallet",

            "razorpay",

        ]:

            payment.payment_status = "refunded"

            order.payment_status = "refunded"

            payment.save(update_fields=["payment_status"])

            refund_to_wallet(

                user=request.user,

                amount=order.total_amount,

                description=f"Refund for cancelled order {order.order_number}"

            )

    order.save(
        update_fields=[
            "order_status",
            "payment_status",
        ]
    )

    OrderStatusHistory.objects.create(

        order=order,

        status="Cancelled",

        note=reason or "Cancelled by customer"

    )

    messages.success(request,"Order cancelled successfully.")

    return redirect("order_detail",order.order_number)


@login_required(login_url="customer_login")
@transaction.atomic
def cancel_order_item(request, item_id):

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__user=request.user
    )
    order = item.order

    if item.order.order_status in [
        "shipped",
        "out_for_delivery",
        "delivered",
        "cancelled",
        "returned",
    ]:

        messages.error(request,"This product cannot be cancelled.")

        return redirect("order_detail",item.order.order_number)

    if item.status in ["cancelled","returned"]:

        messages.error(request,"Already cancelled.")

        return redirect("order_detail",item.order.order_number)

    reason = request.POST.get("reason", "")

    if item.variant:

        item.variant.stock_quantity += item.quantity

        item.variant.save()

    item.status = "cancelled"

    item.save()

    OrderCancellation.objects.get_or_create(

        order_item=item,

        defaults={
            "reason": reason
        }

    )

    payment = getattr(item.order, "payment", None)

    if payment:

        refund_amount = item.total
        coupon_share = Decimal("0.00")

        if order.total_amount > 0:
            coupon_share = (refund_amount / (order.total_amount + order.coupon_discount_value)) * order.coupon_discount_value

        refund_amount -= coupon_share

        if refund_amount < 0:
            refund_amount = Decimal("0.00")

        refund_amount = refund_amount.quantize(Decimal("0.01"))
        if payment.payment_method in ["wallet","razorpay"]:
           refund_to_wallet(

                user=request.user,

                amount=refund_amount,

                description=f"Refund for cancelled product {item.product_name}"

            ) 

        remaining_items = item.order.items.exclude(status="cancelled").count()

        if remaining_items == 0:

            item.order.order_status = "cancelled"

            if payment.payment_method == "cod":

                item.order.payment_status = "pending"

                payment.payment_status = "pending"

            else:

                item.order.payment_status = "refunded"

                payment.payment_status = "refunded"

            payment.save(update_fields=["payment_status"])

            item.order.save(
                update_fields=[
                    "order_status",
                    "payment_status"
                ]
            )

    OrderStatusHistory.objects.create(

        order=item.order,

        status="Item Cancelled",

        note=f"{item.product_name} cancelled by customer"

    )

    messages.success(request,"Product cancelled successfully.")

    return redirect("order_detail",item.order.order_number)


@login_required(login_url="customer_login")
def delete_address(request, id):

    address = get_object_or_404(

        Address,

        id=id,

        user=request.user

    )

    address.delete()

    messages.success( request, "Address removed.")

    return redirect("checkout" )

@login_required(login_url="customer_login")
def download_invoice(request, order_number):

    order = get_object_or_404(
        Order.objects.select_related(
            "address",
            "payment",
            "user",
        ).prefetch_related(
            "items"
        ),
        order_number=order_number,
        user=request.user,
    )

    payment = getattr(order, "payment", None)

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{order.order_number}.pdf"'
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=40,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()

    story = []
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=16,
        textColor=colors.black,
    )

    right_style = ParagraphStyle(
        "RightStyle",
        parent=normal_style,
        alignment=TA_RIGHT,
    )

    bold_style = ParagraphStyle(
        "BoldStyle",
        parent=normal_style,
        fontName="Helvetica-Bold",
    )
    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "images",
        "logo.png"
    )

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=60,
            height=60,
        )

    else:

        logo = Paragraph(
            "",
            normal_style
        )
        company_details = Paragraph(
        """
        <font size="20"><b>PocketStore</b></font><br/>
        Premium Mobile & Audio Store<br/>
        Kerala, India<br/>
        Email : support@pocketstore.com<br/>
        Phone : +91 9876543210
        """,
        normal_style,
    )

    header_table = Table(
        [
            [
                logo,
                company_details,
            ]
        ],
        colWidths=[
            75,
            400,
        ]
    )

    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    story.append(header_table)

    story.append(Spacer(1, 18))
    story.append(
           Paragraph(
            "TAX INVOICE",
            title_style,
        )
    )

    story.append(
          Spacer(
            1,
            10,
        )
    )
      

    invoice_info = [
        ["Invoice No", order.order_number],
        [
            "Invoice Date",
            order.placed_at.strftime("%d-%m-%Y %I:%M %p")
            if order.placed_at else "-"
        ],
        [
            "Estimated Delivery",
            order.estimated_delivery.strftime("%d-%m-%Y")
            if order.estimated_delivery else "-"
        ],
        [
            "Order Status",
            order.get_order_status_display()
        ],
        [
            "Payment Status",
            order.get_payment_status_display()
        ],
        [
            "Payment Method",
            payment.get_payment_method_display()
            if payment else "-"
        ],
    ]

    invoice_table = Table(
        invoice_info,
        colWidths=[140, 240]
    )

    invoice_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (1, 0), (1, -1), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(invoice_table)
    story.append(Spacer(1, 18))


    story.append(
        Paragraph(
            "Customer Details",
            heading_style,
        )
    )


    customer_name = (
        order.address.full_name
        if order.address and order.address.full_name
        else (
            order.user.full_name
            if order.user.full_name
            else order.user.username
        )
    )

    customer_phone = (
        order.address.phone
        if order.address else "-"
    )

    customer_email = order.user.email


    customer_table = Table(
        [
            ["Customer", customer_name],
            ["Email", customer_email],
            ["Phone", customer_phone],
        ],
        colWidths=[140, 340],
    )

    customer_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#DBEAFE")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1E3A8A")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
            ]
        )
    )

    story.append(customer_table)
    story.append(Spacer(1, 18))


    story.append(
        Paragraph(
            "Billing Address",
            heading_style,
        )
    )


    if order.address:

        address_text = f"""
        <b>{order.address.full_name}</b><br/>
        {order.address.address_line1}<br/>
        """

        if order.address.address_line2:
            address_text += f"{order.address.address_line2}<br/>"

        address_text += f"""
        {order.address.city}, {order.address.state}<br/>
        {order.address.country} - {order.address.zip_code}<br/>
        Phone : {order.address.phone}
        """

    else:

        address_text = """
        No billing address available.
        """


    address_table = Table(
        [
            [
                Paragraph(
                    address_text,
                    normal_style,
                )
            ]
        ],
        colWidths=[480],
    )

    address_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#2563EB")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    story.append(address_table)
    story.append(Spacer(1, 22))
    story.append(
        Paragraph(
            "Order Items",
            heading_style,
        )
    )

    product_data = [
        [
            "Sl No",
            "Product",
            "SKU",
            "Qty",
            "Unit Price",
            "Total",
        ]
    ]

    order_items = order.items.all()

    for index, item in enumerate(order_items, start=1):

        product_data.append(
            [
                str(index),
                Paragraph(
                    f"<b>{item.product_name}</b>",
                    normal_style,
                ),
                item.sku,
                str(item.quantity),
                f"₹ {item.price:,.2f}",
                f"₹ {item.total:,.2f}",
            ]
        )

    product_table = Table(
        product_data,
        colWidths=[
            40,    
            180,    
            90,     
            45,    
            75,    
            85,     
        ],
        repeatRows=1,
    )

    table_style = TableStyle(

        [

          
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),

           
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),

            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("ALIGN", (0, 1), (0, -1), "CENTER"),   
            ("ALIGN", (2, 1), (2, -1), "CENTER"),   
            ("ALIGN", (3, 1), (3, -1), "CENTER"),  
            ("ALIGN", (4, 1), (5, -1), "RIGHT"),    

            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#2563EB")),

        ]

    )

    for row in range(1, len(product_data)):

        if row % 2 == 0:

            table_style.add(
                "BACKGROUND",
                (0, row),
                (-1, row),
                colors.HexColor("#F8FAFC"),
            )

        else:

            table_style.add(
                "BACKGROUND",
                (0, row),
                (-1, row),
                colors.white,
            )

    product_table.setStyle(table_style)

    story.append(product_table)

    story.append(
        Spacer(
            1,
            20,
        )
    )
       

    story.append(
        Paragraph(
            "Order Summary",
            heading_style,
        )
    )
    
    cart_items = (CartItem.objects.filter(user=request.user))
    totals = calculate_cart_totals(cart_items,request)

    summary_data = [
        [
            "Subtotal",
            f"₹ {order.subtotal:,.2f}",
        ],
        [
            "Coupon Discount",
            f"- ₹ {order.coupon_discount_value:,.2f}",
        ],
        [
            "Discount",
            f"- ₹ {order.discount_amount - order.coupon_discount_value:,.2f}",
        ],
        [
            "Tax",
            f"₹ {order.tax_amount:,.2f}",
        ],
        [
            "Grand Total",
            f"₹ {order.total_amount:,.2f}",
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[180, 140],
        hAlign="RIGHT",
    )

    summary_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                ("BACKGROUND", (0, 0), (0, -2), colors.HexColor("#EFF6FF")),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(summary_table)

    story.append(Spacer(1, 25))


    

    if payment:

        payment_text = f"""
        <b>Payment Method :</b> {payment.get_payment_method_display()}<br/>
        <b>Payment Status :</b> {payment.get_payment_status_display()}<br/>
        <b>Transaction ID :</b> {payment.transaction_id or "-"}<br/>
        """

        if payment.paid_at:
            payment_text += (
                f"<b>Paid On :</b> "
                f"{payment.paid_at.strftime('%d-%m-%Y %I:%M %p')}"
            )

    else:

        payment_text = """
        <b>Payment Information Not Available</b>
        """

    story.append(
        Paragraph(
            payment_text,
            normal_style,
        )
    )

    story.append(Spacer(1, 25))


    

    thank_you = Paragraph(
        """
        <para align="center">
        <font size="15" color="#2563EB">
        <b>Thank You For Shopping With PocketStore!</b>
        </font>
        <br/><br/>
        We appreciate your trust in PocketStore.
        <br/>
        We look forward to serving you again.
        </para>
        """,
        normal_style,
    )

    story.append(thank_you)

    story.append(Spacer(1, 15))


    

    terms = Paragraph(
        """
        <font size="8">
        • This is a computer generated invoice and does not require a signature.<br/>
        • Goods once delivered can only be returned according to the PocketStore Return Policy.<br/>
        • Warranty is provided by the respective manufacturer wherever applicable.<br/>
        • Please keep this invoice for warranty and future reference.
        </font>
        """,
        normal_style,
    )

    story.append(terms)


    

    doc.build(
        story,
        onFirstPage=add_footer,
        onLaterPages=add_footer,
    )

    pdf = buffer.getvalue()
    buffer.close()

    response.write(pdf)

    return response


@login_required(login_url="customer_login")
@transaction.atomic
def return_request(request, item_id):

    item = get_object_or_404(OrderItem,id=item_id,order__user=request.user)

    if request.method != "POST":
        return redirect("order_detail", item.order.order_number)

    if item.status != "delivered":
        messages.error(request,"Only delivered products can be returned.")
        return redirect("order_detail", item.order.order_number)

    if ReturnItem.objects.filter(order_item=item).exists():
        messages.warning(request,"Return request already submitted.")
        return redirect("order_detail", item.order.order_number)

    reason = request.POST.get("reason", "").strip()

    if not reason:
        messages.error(request,"Please enter a return reason.")
        return redirect("order_detail", item.order.order_number)

   
    return_request = Return.objects.create(
        order=item.order,
        user=request.user,
        request_id=generate_return_request_id(),
        reason=reason,
        estimated_refund=item.total,
        status="pending",
    )

    
    ReturnItem.objects.create(
        return_request=return_request,
        order_item=item,
        quantity=item.quantity,
    )

    
    images = request.FILES.getlist("images")

    for image in images:
        ReturnProofImage.objects.create(return_request=return_request,image=image)

    
    OrderStatusHistory.objects.create(
        order=item.order,
        status="Return Requested",
        note=f"{item.product_name} return requested.",
    )

    messages.success(request,"Return request submitted successfully.")

    return redirect("order_detail",item.order.order_number,)


@login_required(login_url="customer_login")
def apply_coupon(request):

    if request.method != "POST":
        return redirect("checkout")

    if request.session.get("coupon_id"):

        messages.warning(request,"A coupon is already applied.")

        return redirect("checkout")

    coupon_id = request.POST.get("coupon_id")

    try:

        coupon = Coupon.objects.get(id=coupon_id,is_active=True)

    except Coupon.DoesNotExist:

        messages.error(request,"Invalid coupon.")

        return redirect("checkout")

    today = timezone.now().date()

    if coupon.start_date > today or coupon.expiry_date < today:

        messages.error(request,"Coupon expired.")

        return redirect("checkout")

    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related("variant")

    totals = calculate_cart_totals(cart_items,request)

    if totals["total_amount"] < coupon.minimum_order_value:

        messages.error(request,f"Minimum purchase should be ₹{coupon.minimum_order_value}")

        return redirect("checkout")

    request.session["coupon_id"] = coupon.id
    request.session["coupon_code"] = coupon.coupon_code

    messages.success(request,"Coupon applied successfully.")

    return redirect("checkout")

@login_required(login_url="customer_login")
def remove_coupon(request):

    request.session.pop("coupon_id",None)
    request.session.pop("coupon_code",None)
    messages.success(request,"Coupon removed.")

    return redirect("checkout")