from decimal import Decimal

from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.db.models import Sum

from .models import Wallet
from .models import WalletTransaction

import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.http import JsonResponse

@login_required(login_url="customer_login")
def wallet_view(request):

    wallet, created = Wallet.objects.get_or_create(user=request.user)

    transactions = WalletTransaction.objects.filter(
            user=request.user
        ).order_by("-created_at")[:5]

    

    total_credit = WalletTransaction.objects.filter(
            user=request.user,
            transaction_type="credit",
            status="success"
        ).aggregate(
            total=Sum("amount")
        )["total"]or Decimal("0.00")

    

    total_debit = WalletTransaction.objects.filter(
            user=request.user,
            transaction_type="debit",
            status="success"
        ).aggregate(
            total=Sum("amount")
        )["total"]or Decimal("0.00")

    

    context = {

        "wallet": wallet,

        "transactions": transactions,

        "total_credit": total_credit,

        "total_debit": total_debit,

    }

    return render(request,"wallet/wallet.html",context)

@login_required(login_url="customer_login")
def wallet_history(request):

    wallet = get_object_or_404(Wallet,user=request.user)

    transactions = wallet.transactions.all().order_by("-created_at")

    return render(request,"wallet/wallet_history.html",{"wallet": wallet,"transactions": transactions,})


@login_required(login_url="customer_login")
def add_money_wallet(request):

    if request.method != "POST":

        return redirect("wallet")

    amount = request.POST.get("amount")

    try:

        amount = Decimal(amount)

    except:

        messages.error(request,"Invalid amount.")

        return redirect("wallet")

    if amount < Decimal("100"):

        messages.error(request,"Minimum amount is ₹100.")

        return redirect("wallet")

    request.session["wallet_amount"] = str(amount)

    return redirect("wallet")


@login_required(login_url="customer_login")
def wallet_payment_success(request):

    messages.success(request,"Amount added successfully.")

    return redirect("wallet")


@login_required(login_url="customer_login")
def wallet_payment_failed(request):

    messages.error(request,"Wallet recharge failed.")

    return redirect("wallet")


@login_required(login_url="customer_login")
def create_wallet_order(request):

    if request.method != "POST":

        return JsonResponse({"success":False})

    amount=Decimal(request.POST.get("amount"))

    if amount<100:

        return JsonResponse({"success":False,"message":"Minimum amount ₹100"})

    request.session["wallet_amount"]=str(amount)

    client=razorpay.Client(

        auth=(settings.RAZORPAY_KEY_ID,settings.RAZORPAY_KEY_SECRET))

    razorpay_order=client.order.create(

        {

            "amount":int(amount*100),
            "currency":"INR",
            "payment_capture":1

        }

    )

    return JsonResponse(
        {

            "success":True,
            "razorpay_order_id":razorpay_order["id"],
            "amount":int(amount*100),
            "key":settings.RAZORPAY_KEY_ID

        }

    )

@csrf_exempt
@login_required(login_url="customer_login")
def verify_wallet_payment(request):

    if request.method!="POST":

        return redirect("wallet")

    razorpay_order_id=request.POST.get("razorpay_order_id")

    razorpay_payment_id=request.POST.get("razorpay_payment_id")

    razorpay_signature=request.POST.get("razorpay_signature")

    client=razorpay.Client(

        auth=(settings.RAZORPAY_KEY_ID,settings.RAZORPAY_KEY_SECRET))

    try:

        client.utility.verify_payment_signature(

            {

                "razorpay_order_id":razorpay_order_id,

                "razorpay_payment_id":razorpay_payment_id,

                "razorpay_signature":razorpay_signature

            }

        )
    except:

       return JsonResponse({"success": False,"message": "Payment verification failed."})
 

    amount=Decimal(

        request.session.get("wallet_amount","0"))

    wallet, created = Wallet.objects.get_or_create(user=request.user)
    wallet.balance+=amount

    wallet.save()

    WalletTransaction.objects.create(

        wallet=wallet,

        user=request.user,

        transaction_type="credit",

        payment_method="razorpay",

        amount=amount,

        transaction_id=razorpay_payment_id,

        status="success",

        description="Wallet Recharge"

    )

    request.session.pop("wallet_amount", None)

    return JsonResponse({"success": True})