from django.urls import path

from . import views

urlpatterns = [
    path("", views.offer_list, name="offer_list"),
    path("add/", views.offer_create, name="offer_add"),
    path("edit/<int:offer_id>/", views.offer_edit, name="offer_edit"),
    path("delete/<int:offer_id>/", views.offer_delete, name="offer_delete"),
]