from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from customer.orders.models import OrderItem
from .forms import ReviewForm
from admin_panel.review.models import Review


@login_required(login_url="login")
def add_review(request, order_item_id):

    order_item = get_object_or_404(
        OrderItem.objects.select_related(
            "order",
            "variant",
            "variant__product",
        ),
        id=order_item_id,
        order__user=request.user,
        status="delivered",
    )

    if Review.objects.filter(order_item=order_item).exists():

        messages.error(
            request,
            "You have already reviewed this product."
        )

        return redirect("order_detail", order_item.order.order_number)

    if request.method == "POST":

        form = ReviewForm(request.POST)

        if form.is_valid():

            review = form.save(commit=False)

            review.user = request.user

            review.product = order_item.variant.product

            review.order_item = order_item

            review.status = "Published"

            review.save()

            messages.success(
                request,
                "Review submitted successfully."
            )

            return redirect("order_detail", order_item.order.order_number)

    else:

        form = ReviewForm()

    return render(
        request,
        "reviews/add_review.html",
        {
            "form": form,
            "order_item": order_item,
            "variant": order_item.variant,
            "product": order_item.variant.product,
        },
    )