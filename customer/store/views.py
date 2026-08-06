from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator
from django.db.models import Q, Min

from admin_panel.catalog.models import Product, ProductVariant, Category, Brand
from .models import CartItem, Wishlist
from django.db.models.functions import Lower
from django.db.models import Min, Case, When, F, DecimalField
from admin_panel.offers.utils import get_variant_offer_price
from admin_panel.review.models import Review


MAX_CART_QTY = 5

VALID_SORTS = [
    "price_low",
    "price_high",
    "a_z",
    "z_a",
    "az",
    "za",
]


def safe_decimal(value):
    try:
        if value in ["", None]:
            return None

        value = Decimal(value)

        if value < 0:
            return None

        return value

    except InvalidOperation:
        return None


def get_product_price(variant):
    if variant.discount_price and variant.discount_price > 0:
        return variant.price - variant.discount_price

    return variant.price


def is_product_available(variant):
    product = variant.product

    if product.is_deleted:
        return False, "Product is unavailable"

    if product.product_status != "active":
        return False, "Product is unavailable"

    if product.category.is_deleted:
        return False, "Product category is unavailable"

    if not product.category.is_active:
        return False, "Product category is unavailable"

    if not product.brand.is_active:
        return False, "Product brand is unavailable"

    if not variant.is_active:
        return False, "Selected variant is unavailable"

    if variant.stock_quantity <= 0:
        return False, "Product is out of stock"

    return True, None


def validate_cart_item(cart_item):
    valid, error = is_product_available(cart_item.variant)

    if not valid:
        return False, error

    if cart_item.quantity <= 0:
        return False, "Invalid cart quantity"

    if cart_item.quantity > cart_item.variant.stock_quantity:
        return False, "Quantity exceeds available stock"

    if cart_item.quantity > MAX_CART_QTY:
        return False, f"Maximum {MAX_CART_QTY} quantity allowed"

    return True, None


def product_listing(request, product_type):
    if product_type not in ["mobiles", "audio"]:
        messages.error(request, "Invalid product type")
        return redirect("public_home")

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    brand = request.GET.get("brand", "").strip()
    sort = request.GET.get("sort", "").strip()

    if sort == "az":
        sort = "a_z"

    if sort == "za":
        sort = "z_a"

    min_price = safe_decimal(request.GET.get("min_price", ""))
    max_price = safe_decimal(request.GET.get("max_price", ""))

    if sort and sort not in VALID_SORTS:
        sort = ""

    products = Product.objects.filter(
        category__type=product_type,
        category__is_active=True,
        category__is_deleted=False,
        brand__is_active=True,
        product_status="active",
        is_deleted=False,
        variants__is_active=True,
        variants__stock_quantity__gt=0
    ).select_related(
        "category",
        "brand"
    ).prefetch_related(
        "variants",
        "variants__images"
    ).distinct()
    

    if q:
        products = products.filter(
            Q(product_name__icontains=q) |
            Q(short_description__icontains=q) |
            Q(full_description__icontains=q) |
            Q(category__category_name__icontains=q) |
            Q(brand__brand_name__icontains=q)
        )

    if category:
        if Category.objects.filter(
            id=category,
            type=product_type,
            is_active=True,
            is_deleted=False
        ).exists():
            products = products.filter(category_id=category)
        else:
            messages.error(request, "Invalid category selected")

    if brand:
        if Brand.objects.filter(id=brand, is_active=True).exists():
            products = products.filter(brand_id=brand)
        else:
            messages.error(request, "Invalid brand selected")

    if min_price is not None and max_price is not None and min_price > max_price:
        messages.error(request, "Minimum price cannot be greater than maximum price")
    else:
        if min_price is not None:
            products = products.filter(variants__price__gte=min_price)

        if max_price is not None:
            products = products.filter(variants__price__lte=max_price)
    products = products.distinct()

    products = products.annotate(sort_price=Min("variants__price"))
    if sort == "price_low":
        products = products.order_by("sort_price")
    elif sort == "price_high":
        products = products.order_by("-sort_price")
    elif sort == "a_z":
        products = products.order_by(Lower("product_name"))
    elif sort == "z_a":
        products = products.order_by(Lower("product_name").desc())
    else:
        products = products.order_by("-created_at")


    paginator = Paginator(products, 8)
    page_obj = paginator.get_page(request.GET.get("page"))
    for product in page_obj:
    
        variant = product.default_variant
    
        if variant:
    
            product.offer_data = get_variant_offer_price(variant)

    categories = Category.objects.filter(
        type=product_type,
        is_active=True,
        is_deleted=False
    )
   
    brands = Brand.objects.filter(
        is_active=True,
        products__category__type=product_type,
        products__product_status="active",
        products__is_deleted=False
    ).distinct()

    template_name = "store/mobile.html"

    if product_type == "audio":
        template_name = "store/audio.html"

    return render(request, template_name, {
        "products": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "brands": brands,
        "product_type": product_type,
        "page_title": "Mobiles" if product_type == "mobiles" else "Audio",
        "q": q,
        "selected_category": category,
        "selected_brand": brand,
        "min_price": min_price if min_price is not None else "",
        "max_price": max_price if max_price is not None else "",
        "sort": sort,
    })


def mobile_page(request):
    return product_listing(request, "mobiles")


def audio_page(request):
    return product_listing(request, "audio")


def product_detail(request, slug):
    product = get_object_or_404(
        Product,
        slug=slug,
        product_status="active",
        is_deleted=False,
        category__is_active=True,
        category__is_deleted=False,
        brand__is_active=True
    )
    variant = product.default_variant


    variants = product.variants.filter(
        is_active=True
    ).prefetch_related("images")


    if not variants.exists():
        messages.error(request, "Product is currently unavailable")

        if product.category.type == "audio":
            return redirect("audio_page")

        return redirect("mobile_page")

    selected_variant_id = request.GET.get("variant", "").strip()

    if selected_variant_id:
        selected_variant = variants.filter(id=selected_variant_id).first()

        if not selected_variant:
            messages.error(request, "Selected variant not found")
            return redirect("product_detail", slug=slug)
    else:
        selected_variant = variants.filter(is_default=True).first() or variants.first()
    offer_data = get_variant_offer_price(selected_variant)
    is_available, availability_error = is_product_available(selected_variant)

    related_products = Product.objects.filter(
        category__type=product.category.type,
        product_status="active",
        is_deleted=False,
        category__is_active=True,
        category__is_deleted=False,
        brand__is_active=True,
        variants__is_active=True,
        variants__stock_quantity__gt=0
    ).exclude(
        id=product.id
    ).select_related(
        "category",
        "brand"
    ).prefetch_related(
        "variants",
        "variants__images"
    ).distinct()[:4]
    for related_product in related_products:

        variant = related_product.default_variant

        if variant:
            related_product.offer_data = get_variant_offer_price(variant)
    reviews = Review.objects.filter(product=product,status="Published").select_related("user")
    print("Product:", product.id)
    print("Reviews:", reviews)
    print("Count:", reviews.count())
    return render(request, "store/product_detail.html", {
        "product": product,
        "variants": variants,
        "selected_variant": selected_variant,
        "related_products": related_products,
        "specifications": product.specifications.all(),
        "is_available": is_available,
        "availability_error": availability_error,
        "offer_data": offer_data,
        "reviews" : reviews,
    })


@never_cache
@login_required(login_url="customer_login")
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user,
        variant__is_deleted=False,
        variant__is_active=True,
        variant__product__is_deleted=False,
        variant__product__product_status="active"
    ).select_related(
        "variant",
        "variant__product",
        "variant__product__brand",
        "variant__product__category"
    ).prefetch_related(
        "variant__images"
    ).order_by("-created_at")
    for item in wishlist_items:

      item.offer_data = get_variant_offer_price(
        item.variant
    )

    return render(request, "store/wishlist.html", {
        "wishlist_items": wishlist_items
    })


@login_required(login_url="customer_login")
def add_to_wishlist(request, variant_id):
    variant = get_object_or_404(
        ProductVariant,
        id=variant_id
    )

    valid, error = is_product_available(variant)

    if not valid:
        messages.error(request, error)
        return redirect(request.META.get("HTTP_REFERER", "wishlist"))

    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        variant=variant
    )

    if not created:
        messages.error(request, "This product is already in your wishlist")
        return redirect(request.META.get("HTTP_REFERER", "wishlist"))

    messages.success(request, "Product added to wishlist")
    return redirect(request.META.get("HTTP_REFERER", "wishlist"))


@login_required(login_url="customer_login")
def remove_from_wishlist(request, variant_id):
    deleted, _ = Wishlist.objects.filter(
        user=request.user,
        variant_id=variant_id
    ).delete()

    if deleted:
        messages.success(request, "Product removed from wishlist")
    else:
        messages.error(request, "Wishlist item not found")

    return redirect(request.META.get("HTTP_REFERER", "wishlist"))


@never_cache
@login_required(login_url="customer_login")
def cart_view(request):

   deleted_items=CartItem.objects.filter(
       user=request.user
   ).filter(
        Q(variant__is_deleted=True)|
        Q(variant__product__is_deleted=True)
   )
   deleted_count=deleted_items.count()
   if deleted_count:
        deleted_items.delete()
        messages.warning(request,
                        f"{deleted_count} item(s) were removed because they are no longer available.")

   cart_items = CartItem.objects.filter(
        user=request.user,
        variant__is_deleted=False,
        variant__product__is_deleted=False,
    ).select_related(
        "variant",
        "variant__product",
        "variant__product__brand",
        "variant__product__category"
    ).prefetch_related(
        "variant__images"
    ).order_by("-created_at")
   
   for item in cart_items:

        item.offer_data = get_variant_offer_price(
            item.variant
        )

   subtotal = Decimal("0.00")
   discount_total = Decimal("0.00")
   total = Decimal("0.00")
   cart_valid = True

   for item in cart_items:
     
        item.error_message = None
        if(not item.variant.is_active or
           item.variant.product.product_status!="active"):
               cart_valid=False
               item.error_message="This product is currently unavailable."
               continue

        valid, error = validate_cart_item(item)
        

    
        if not valid:
            cart_valid = False
            item.error_message = error

        price = item.offer_data["original_price"]

        selling_price = item.offer_data["selling_price"]

        original_amount = price * item.quantity

        item_selling_amount = selling_price * item.quantity

        discount_amount = original_amount - item_selling_amount

        item.original_amount = original_amount
        item.discount_amount = discount_amount
        item.selling_amount = item_selling_amount

        subtotal += original_amount
        discount_total += discount_amount
        total += item_selling_amount

   return render(request, "store/cart.html", {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "discount_total": discount_total,
        "total": total,
        "cart_valid": cart_valid,
        "max_cart_qty": MAX_CART_QTY,
    })




@login_required(login_url="customer_login")
def add_to_cart(request, variant_id):
    variant = get_object_or_404(
        ProductVariant,
        id=variant_id
    )

    valid, error = is_product_available(variant)

    if not valid:
        messages.error(request, error)
        return redirect(request.META.get("HTTP_REFERER", "cart"))

    cart_item = CartItem.objects.filter(
        user=request.user,
        variant=variant
    ).first()

    if cart_item:
        messages.error(request, "This product is already in your cart")
        return redirect(request.META.get("HTTP_REFERER", "cart"))

    CartItem.objects.create(
        user=request.user,
        variant=variant,
        quantity=1
    )

    Wishlist.objects.filter(
        user=request.user,
        variant=variant
    ).delete()

    messages.success(request, "Product added to cart")
    return redirect(request.META.get("HTTP_REFERER", "cart"))


@login_required(login_url="customer_login")
def increment_cart(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        user=request.user
    )

    valid, error = is_product_available(cart_item.variant)

    if not valid:
        messages.error(request, error)
        return redirect("cart")

    if cart_item.quantity >= cart_item.variant.stock_quantity:
        messages.error(request, "Maximum stock limit reached")
        return redirect("cart")

    if cart_item.quantity >= MAX_CART_QTY:
        messages.error(request, f"Maximum {MAX_CART_QTY} quantity allowed")
        return redirect("cart")

    cart_item.quantity += 1
    cart_item.save()

    return redirect("cart")


@login_required(login_url="customer_login")
def decrement_cart(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        user=request.user
    )

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
        messages.success(request, "Product removed from cart")

    return redirect("cart")


@login_required(login_url="customer_login")
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        user=request.user
    )

    cart_item.delete()

    messages.success(request, "Product removed from cart")
    return redirect("cart")
