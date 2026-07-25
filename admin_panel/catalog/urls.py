from django.urls import path
from . import views

urlpatterns = [
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_form, name="add_category"),
    path("categories/edit/<int:category_id>/", views.category_form, name="edit_category"),
    path("categories/delete/<int:category_id>/", views.delete_category, name="delete_category"),

    path("products/", views.product_list, name="product_list"),
    path("products/add/", views.product_form, name="add_product"),
    path("products/edit/<int:product_id>/", views.product_form, name="edit_product"),
    path("products/delete/<int:product_id>/", views.delete_product, name="delete_product"),

    path("products/<int:product_id>/variants/", views.variant_list, name="variant_list"),
    path("products/<int:product_id>/variants/add/", views.variant_form, name="add_variant"),
    path("variants/edit/<int:variant_id>/", views.variant_form, name="edit_variant"),
    path("variants/delete/<int:variant_id>/", views.delete_variant, name="delete_variant"),
]