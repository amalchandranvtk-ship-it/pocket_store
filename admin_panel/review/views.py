from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Avg
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.shortcuts import render

from .models import Review


@staff_member_required
def review_list(request):

    reviews = Review.objects.select_related("user","product")

    search = request.GET.get("search")

    if search:
        reviews = reviews.filter(
           product__product_name__icontains=search
        ) | reviews.filter(
            user__full_name__icontains=search
        ) | reviews.filter(
            review_description__icontains=search
        )

    rating = request.GET.get("rating")

    if rating:
        reviews = reviews.filter(rating=rating)

    status = request.GET.get("status")

    if status:
        reviews = reviews.filter(status=status)

    paginator = Paginator(reviews, 10)

    page = request.GET.get("page")

    page_obj = paginator.get_page(page)

    context = {
        "page_obj": page_obj,
        "total_reviews": Review.objects.count(),
        "average_rating": Review.objects.aggregate(
            Avg("rating")
        )["rating__avg"] or 0,
        "five_star": Review.objects.filter(
            rating=5
        ).count(),
        "low_rating": Review.objects.filter(
            rating__lte=2
        ).count(),
    }

    return render(request,"review/review_list.html",context)


