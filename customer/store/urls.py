from django.urls import path
from . import views

urlpatterns = [
    path("mobiles/", views.mobile_page, name="mobile_page"),
    path("audio/", views.audio_page, name="audio_page"),

    path("product/<slug:slug>/", views.product_detail, name="product_detail"),

    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/add/<int:variant_id>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/remove/<int:variant_id>/", views.remove_from_wishlist, name="remove_from_wishlist"),

    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:variant_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/increment/<int:item_id>/", views.increment_cart, name="increment_cart"),
    path("cart/decrement/<int:item_id>/", views.decrement_cart, name="decrement_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
]