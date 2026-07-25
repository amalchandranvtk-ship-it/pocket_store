from decimal import Decimal

from django.utils import timezone

from .models import (
    OfferProduct, OfferCategory
)



def calculate_discount(price, offer):
   

    price = Decimal(price)

    if offer.offer_type == "percentage":

        discount = (
            price * Decimal(offer.discount_value)
        ) / Decimal("100")

    else:

        discount = Decimal(offer.discount_value)

    if discount > price:
        discount = price

    return discount


def get_product_offer(product):
   

    today = timezone.localdate()

    offer_product = (
        OfferProduct.objects
        .select_related("offer")
        .filter(
            product=product,
            offer__is_active=True,
            offer__valid_from__lte=today,
            offer__valid_to__gte=today,
        )
        .first()
    )

    return offer_product


def get_category_offer(product):
   

    today = timezone.localdate()

    offer_category = (
        OfferCategory.objects
        .select_related("offer")
        .filter(
            category=product.category,
            offer__is_active=True,
            offer__valid_from__lte=today,
            offer__valid_to__gte=today,
        )
        .first()
    )

    return offer_category


def get_best_offer(product, price):
   

    best_offer = None
    offer_type = None
    best_discount = Decimal("0.00")

    product_offer = get_product_offer(product)

    if product_offer:

        discount = calculate_discount(
            price,
            product_offer.offer
        )

        if discount > best_discount:

            best_discount = discount
            best_offer = product_offer.offer
            offer_type = "product"

    category_offer = get_category_offer(product)

    if category_offer:

        discount = calculate_discount(
            price,
            category_offer.offer
        )

        if discount > best_discount:

            best_discount = discount
            best_offer = category_offer.offer
            offer_type = "category"

    return best_offer, offer_type, best_discount


def get_variant_offer_price(variant):
    

    original_price = Decimal(variant.price)

    offer, offer_type, discount = get_best_offer(
        variant.product,
        original_price
    )

    selling_price = original_price - discount

    if selling_price < 0:
        selling_price = Decimal("0.00")

    label = ""

    if offer:

        if offer.offer_type == "percentage":

            label = f"{int(offer.discount_value)}% OFF"

        else:

            label = f"₹{offer.discount_value} OFF"

    return {

        "original_price": original_price,

        "selling_price": selling_price.quantize(
            Decimal("0.01")
        ),

        "discount_amount": discount.quantize(
            Decimal("0.01")
        ),

        "offer": offer,

        "offer_type": offer_type,

        "label": label,

        "has_offer": offer is not None,

    }