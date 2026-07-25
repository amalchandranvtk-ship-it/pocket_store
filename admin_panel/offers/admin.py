from django.contrib import admin

from .models import (
    Offer,
    OfferCategory,
    OfferProduct,
    Referral,
)


class OfferProductInline(admin.TabularInline):
    model = OfferProduct
    extra = 0


class OfferCategoryInline(admin.TabularInline):
    model = OfferCategory
    extra = 0


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "offer_name",
        "offer_type",
        "apply_to",
        "discount_value",
        "valid_from",
        "valid_to",
        "is_active",
    )

    search_fields = ("offer_name",)

    list_filter = ("offer_type","apply_to","is_active",)

    inlines = [OfferProductInline,OfferCategoryInline]


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "referrer_user",
        "referred_user",
        "referral_code",
        "reward_amount",
        "status",
        "created_at",
    )

    search_fields = ("referral_code",)

    list_filter = ("status",)
