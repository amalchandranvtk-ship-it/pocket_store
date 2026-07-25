from django.urls import path
from . import views

urlpatterns = [

    path("orders/",views.admin_order_list,name="admin_order_list"),
    path("orders/<str:order_number>/",views.admin_order_detail,name="admin_order_detail"),
    path("orders/<str:order_number>/status/",views.update_order_status,name="update_order_status"),

    path("returns/",views.admin_return_list,name="admin_return_list"),
    path("returns/<int:return_id>/",views.admin_return_detail,name="admin_return_detail"),
    path("returns/<int:return_id>/approve/",views.approve_return,name="approve_return"),
    path("returns/<int:return_id>/reject/",views.reject_return,name="reject_return"),

]