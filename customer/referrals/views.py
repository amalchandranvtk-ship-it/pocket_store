from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from django.db.models import Sum

from .models import Referral


@login_required(login_url="customer_login")
def referral_home(request):

    referrals = Referral.objects.filter(
        referrer=request.user
    ).select_related("referred_user").order_by("-created_at")

    total_referrals = referrals.count()

    total_earned = referrals.aggregate(
        total=Sum("reward_amount")
    )["total"] or 0

    referral_link = (
        f"{request.scheme}://{request.get_host()}"
        f"/signup/?ref={request.user.referral_code}"
    )

    context = {

        "referral_code": request.user.referral_code,

        "referral_link": referral_link,

        "total_referrals": total_referrals,

        "total_earned": total_earned,

        "referrals": referrals,

    }

    return render(request,"referrals/referral_home.html",context)
