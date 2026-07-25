from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import OfferForm
from .models import Offer
from .models import Offer, OfferProduct, OfferCategory




def is_admin(user):
    return user.is_authenticated and user.is_staff


@login_required(login_url="admin_login")
@user_passes_test(is_admin)
def offer_list(request):
    offers = Offer.objects.all().order_by("-created_at")

    search = request.GET.get("search", "").strip()
    offer_type = request.GET.get("offer_type", "")
    status = request.GET.get("status", "")

    if search:
        offers = offers.filter(
            Q(offer_name__icontains=search)
            | Q(apply_to__icontains=search)
        )

    if offer_type:
        offers = offers.filter(offer_type=offer_type)

    today = timezone.localdate()

    if status == "active":
        offers = offers.filter(
            is_active=True,
            valid_from__lte=today,
            valid_to__gte=today,
        )

    elif status == "inactive":
        offers = offers.filter(is_active=False)

    elif status == "expired":
        offers = offers.filter(valid_to__lt=today)

    paginator = Paginator(offers, 10)

    page = request.GET.get("page")

    page_obj = paginator.get_page(page)

    context = {
        "page_obj": page_obj,
        "search": search,
        "offer_type": offer_type,
        "status": status,
    }

    return render(request,"offers/offer_list.html",context)




@login_required(login_url="admin_login")
@user_passes_test(is_admin)
def offer_create(request):
    if request.method == "POST":
        form = OfferForm(request.POST)

        if form.is_valid():
            offer = form.save()

            if offer.apply_to == "product":
                products = form.cleaned_data["products"]

                for product in products:
                    OfferProduct.objects.create(offer=offer,product=product)

            if offer.apply_to == "category":
                categories = form.cleaned_data["categories"]

                for category in categories:
                    OfferCategory.objects.create(offer=offer,category=category)

            messages.success(request,"Offer created successfully.")

            return redirect("offer_list")

    else:
        form = OfferForm()

    context = {"form": form}

    return render(request,"offers/offer_add.html",context)




@login_required(login_url="admin_login")
@user_passes_test(is_admin)
def offer_edit(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)

    initial = {}

    if offer.apply_to == "product":
        initial["products"] = [
            item.product
            for item in offer.offer_products.select_related("product")
        ]

    if offer.apply_to == "category":
        initial["categories"] = [
            item.category
            for item in offer.offer_categories.select_related("category")
        ]

    if request.method == "POST":
        form = OfferForm(
            request.POST,
            instance=offer
        )

        if form.is_valid():
            offer = form.save()

            OfferProduct.objects.filter(offer=offer).delete()

            OfferCategory.objects.filter(offer=offer).delete()

            if offer.apply_to == "product":
                products = form.cleaned_data["products"]

                for product in products:
                    OfferProduct.objects.create(offer=offer,product=product)

            if offer.apply_to == "category":
                categories = form.cleaned_data["categories"]

                for category in categories:
                    OfferCategory.objects.create(offer=offer,category=category)

            messages.success(request,"Offer updated successfully.")

            return redirect("offer_list")

    else:
        form = OfferForm(
            instance=offer,
            initial=initial,
        )

    context = {
        "form": form,
        "offer": offer,
    }

    return render(request,"offers/offer_edit.html",context)


@login_required(login_url="admin_login")
@user_passes_test(is_admin)
def offer_delete(request, offer_id):
    offer = get_object_or_404(Offer,id=offer_id)

    OfferProduct.objects.filter(offer=offer).delete()

    OfferCategory.objects.filter(offer=offer).delete()

    offer.delete()

    messages.success(request,"Offer deleted successfully.")

    return redirect("offer_list")
